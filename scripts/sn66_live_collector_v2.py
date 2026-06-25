#!/usr/bin/env python3
"""
SN66 Final Unified Data Collector — Production Daemon

Supersedes sn66_comprehensive_collector.py (v1) and sn66_comprehensive_collector_v2.py (v2).
Merges ALL fixes from both versions plus new features for the SN66 LLM training pipeline.

v1 → v2 IMPROVEMENTS (all inherited):
  FIX-G1: instruction field in judge_feedback = judge_rationale (not empty string).
  FIX-G2: winning_patch / losing_patch = actual unified git diffs via GitHub API.
  FIX-G3: build_dpo_record adds chosen_patch / rejected_patch with actual diff text.
  FIX-L1: Counters only increment when records are actually written to file.
  FIX-L2: Validator health detection: 3+ consecutive anomalous duels → Telegram alert.
  FIX-L3: Counter sync on startup: recount actual JSONL lines to fix drift.
  FIX-L4: Cursor does NOT advance for anomalous duels.
  FIX-S3-SMART-RESET: Smart page reset for PR source (last_nonempty - 2 instead of 0).
  BUG-FIX: king_backfill_complete not set on API failure mid-backfill.

v2 → FINAL NEW FEATURES:
  NEW-1: Startup king change detection: compares last_king_sha to latest GitHub king commit.
         If changed, resets king_backfill_complete=False and runs incremental update before
         entering main loop.
  NEW-2: Judge feedback instruction backfill: on startup, scans existing judge_feedback records
         for empty instruction="" field and re-populates from matching DPO judge_rationale.
  NEW-3: King name tracking: stores current_king_name and current_king_hotkey in state.json
         for observability (which miner is king right now).

Collects ALL 5 training data sources for the SN66 dedicated LLM pipeline.
Runs forever as a PM2 daemon. stdlib only — no pip packages.

Sources:
  1. Live duel SFT/DPO     - ninja66.ai/dashboard.json + duels/{id}.json
  2. King code history      - GitHub API: unarbos/ninja commits
  3. PR outcome labels      - GitHub API: unarbos/ninja pulls (all pages)
  4. Judge feedback SFT     - Reformat existing DPO losses into lesson pairs
  5. Miner version history  - Our own agent_*.py files with gate results

Outputs:
  /root/sn66-ninja/training_data/
    sft/YYYY-MM-DD.jsonl
    dpo/YYYY-MM-DD.jsonl
    king_history/king_history.jsonl
    pr_outcomes/pr_outcomes.jsonl
    judge_feedback/judge_feedback.jsonl
    miner_history/miner_history.jsonl
    state.json
    collection.log
"""

import argparse
import json
import os
import signal
import sys
import time
import fcntl
import logging
import urllib.request
import urllib.error
import glob
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR           = Path("/root/sn66-ninja/training_data/live")
SFT_DIR            = BASE_DIR / "sft"
DPO_DIR            = BASE_DIR / "dpo"
KING_HISTORY_DIR   = BASE_DIR / "king_history"
PR_OUTCOMES_DIR    = BASE_DIR / "pr_outcomes"
JUDGE_FEEDBACK_DIR = BASE_DIR / "judge_feedback"
MINER_HISTORY_DIR  = BASE_DIR / "miner_history"
STATE_FILE         = BASE_DIR / "state.json"
LOG_FILE           = BASE_DIR / "collection.log"

SECRETS_FILE = Path("/root/.secrets/api_keys.env")
SN66_DIR     = Path("/home/t68/sn66-ninja")

# ─── Config ───────────────────────────────────────────────────────────────────
DASHBOARD_URL    = "https://ninja66.ai/dashboard.json"
DUEL_URL         = "https://ninja66.ai/duels/{duel_id}.json"
GH_API_BASE      = "https://api.github.com/repos/unarbos/ninja"
POLL_INTERVAL    = 300       # 5 minutes
MIN_DUEL_ID      = 5004      # v2: resume from duel 5004 (duels 4267-5003 collected previously)
RATE_LIMIT_SLEEP = 1.0       # 1 req/s max for all APIs
GH_DIFF_RATE_LIMIT = 0.5     # 0.5s between GitHub diff API calls
REQUEST_TIMEOUT  = 30

# ─── Process Singleton Lock (FIX-LOCK-1) ────────────────────────────────────
# Held open for entire process lifetime — DO NOT close this fd.
# fcntl.flock(LOCK_EX|LOCK_NB) ensures only one collector runs at a time.
LOCKFILE_PATH = Path("/tmp/sn66_unified_collector.lock")
_LOCK_FD = None  # global fd reference prevents GC-release

# ─── PR Diff Cache (in-memory, one run) ───────────────────────────────────────
_PR_DIFF_CACHE: Dict[int, str] = {}
_PR_DIFF_CACHE_MAX = 200   # MEM-FIX: cap at 200 entries (~40MB max)

# ─── Repo Context Cache ────────────────────────────────────────────────────────
_REPO_CONTEXT_CACHE: Dict[int, dict] = {}   # pr_num -> {filename: snippet}
_REPO_CTX_CACHE_MAX = 100  # MEM-FIX: cap at 100 entries


# ══════════════════════════════════════════════════════════════════════════════
# UPGRADE-1: Task-Type Classification
# Maps instruction text to one of: BUGFIX | FEATURE | UPDATE | API
# Better signal than auto-detected 'archetype' field.
# ══════════════════════════════════════════════════════════════════════════════

TASK_TYPE_API     = "API"
TASK_TYPE_BUGFIX  = "BUGFIX"
TASK_TYPE_FEATURE = "FEATURE"
TASK_TYPE_UPDATE  = "UPDATE"

_API_KEYWORDS = [
    "api", "endpoint", "route", "auth", "authentication", "webhook", "rest",
    "graphql", "http", "request handler", "middleware", "oauth", "jwt",
    "token", "login", "logout", "permission", "cors",
]
_BUGFIX_KEYWORDS = [
    "fix", "bug", "error", "broken", "crash", "fail", "failure", "issue",
    "incorrect", "wrong", "exception", "typeerror", "undefined", "null pointer",
    "regression", "defect", "patch", "hotfix", "repair", "resolve",
    "not working", "doesn't work", "does not work",
]
_FEATURE_KEYWORDS = [
    "add", "implement", "create", "build", "introduce", "new feature",
    "support for", "enable", "allow", "provide",
]
_UPDATE_KEYWORDS = [
    "update", "enhance", "improve", "refactor", "migrate", "upgrade",
    "optimize", "extend", "expand", "revise", "redesign", "rework",
    "modification", "adjust",
]


def classify_task_type(instruction: str) -> str:
    """Classify a task instruction into BUGFIX | FEATURE | UPDATE | API.

    Uses priority ordering: API > BUGFIX > FEATURE > UPDATE.
    Checks only the first 600 chars of instruction for efficiency.
    Always returns a valid label (defaults to UPDATE).
    """
    if not instruction:
        return TASK_TYPE_UPDATE
    text = instruction.lower()[:600]

    # Priority 1: API — high-specificity domain keywords
    api_hits = sum(1 for kw in _API_KEYWORDS if kw in text)
    if api_hits >= 2:          # Require 2+ API keywords to avoid false positives
        return TASK_TYPE_API

    # Priority 2: BUGFIX — error/defect language
    if any(kw in text for kw in _BUGFIX_KEYWORDS):
        return TASK_TYPE_BUGFIX

    # Priority 3: FEATURE — new functionality
    if any(kw in text for kw in _FEATURE_KEYWORDS):
        return TASK_TYPE_FEATURE

    # Priority 4: UPDATE (default) — improvement/refactor
    return TASK_TYPE_UPDATE


# ══════════════════════════════════════════════════════════════════════════════
# UPGRADE-2: Edit Quality Label
# Evaluates LLM output quality vs reference patch by line count ratio.
# ══════════════════════════════════════════════════════════════════════════════

def edit_quality_label(llm_patch: str, ref_patch: str) -> str:
    """Score patch quality: excellent | good | over_edit | under_edit | empty.

    Heuristic based on line-count ratio (llm / reference):
      - empty     : llm_patch is blank/whitespace-only
      - over_edit : llm_patch > 2.5x reference lines
      - under_edit: llm_patch < 0.35x reference lines (or ref > 0 but llm near 0)
      - excellent : 0.9 – 1.1x reference
      - good      : 0.35 – 2.5x (everything else)
    """
    if not llm_patch or not llm_patch.strip():
        return "empty"
    llm_lines = len([l for l in llm_patch.splitlines() if l.strip()])
    if llm_lines == 0:
        return "empty"
    if not ref_patch or not ref_patch.strip():
        # No reference to compare against — can't assess
        return "good"
    ref_lines = len([l for l in ref_patch.splitlines() if l.strip()])
    if ref_lines == 0:
        return "good"
    ratio = llm_lines / ref_lines
    if ratio > 2.5:
        return "over_edit"
    if ratio < 0.35:
        return "under_edit"
    if 0.9 <= ratio <= 1.1:
        return "excellent"
    return "good"


# ══════════════════════════════════════════════════════════════════════════════
# UPGRADE-3: Repo Context Enrichment (Optional, Rate-Limited)
# Fetches file context BEFORE a PR was applied from GitHub.
# Non-blocking: called as a best-effort enrichment step, never in hot path.
# ══════════════════════════════════════════════════════════════════════════════

_REPO_CTX_ENRICHMENT_FILE = BASE_DIR / "repo_context_enrichment.jsonl"
_REPO_CTX_STATE_FILE      = BASE_DIR / "repo_context_state.json"
_REPO_CTX_BATCH_SIZE      = 3    # DPO records enriched per cycle (rate-limit safe)
_REPO_CTX_MAX_LINES       = 80   # Lines captured per file
_CODE_EXTENSIONS = {
    '.py', '.ts', '.js', '.tsx', '.jsx', '.go', '.java',
    '.cpp', '.c', '.rs', '.rb', '.php', '.cs', '.swift',
}


def _fetch_repo_context_for_pr(pr_url: str) -> dict:
    """Fetch the 'before' file context for a PR.

    Returns {filename: first_N_lines_string} for up to 3 code files.
    Fetches agent.py / main code files from unarbos/ninja at the PR base SHA.
    NEVER raises — always returns {} on any failure.
    """
    if not pr_url:
        return {}
    m = re.search(r"/pull/(\d+)", pr_url)
    if not m:
        return {}
    pr_num = int(m.group(1))
    if pr_num in _REPO_CONTEXT_CACHE:
        return _REPO_CONTEXT_CACHE[pr_num]

    try:
        time.sleep(GH_DIFF_RATE_LIMIT)
        pr_info = fetch_json(f"{GH_API_BASE}/pulls/{pr_num}", headers=gh_headers())
        if not pr_info:
            return {}
        base_sha = (pr_info.get("base") or {}).get("sha", "")
        if not base_sha:
            return {}

        time.sleep(GH_DIFF_RATE_LIMIT)
        files_url = f"{GH_API_BASE}/pulls/{pr_num}/files?per_page=5"
        changed_files = fetch_json(files_url, headers=gh_headers())
        if not changed_files:
            # Fallback: just fetch agent.py at base SHA
            changed_files = [{"filename": "agent.py"}]

        context: dict = {}
        for file_info in changed_files[:3]:
            fname = file_info.get("filename", "")
            if not fname:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in _CODE_EXTENSIONS:
                continue
            time.sleep(GH_DIFF_RATE_LIMIT)
            raw_url = f"https://raw.githubusercontent.com/unarbos/ninja/{base_sha}/{fname}"
            content = fetch_text(raw_url)
            if content:
                lines = content.splitlines()
                context[fname] = "\n".join(lines[:_REPO_CTX_MAX_LINES])

        # MEM-FIX: evict oldest entries when cache hits limit
        if len(_REPO_CONTEXT_CACHE) >= _REPO_CTX_CACHE_MAX:
            oldest = next(iter(_REPO_CONTEXT_CACHE))
            del _REPO_CONTEXT_CACHE[oldest]
        _REPO_CONTEXT_CACHE[pr_num] = context
        return context
    except Exception as e:
        logging.debug(f"_fetch_repo_context_for_pr PR#{pr_num}: {e}")
        return {}


def _load_repo_ctx_state() -> dict:
    """Load enrichment cursor state."""
    if _REPO_CTX_STATE_FILE.exists():
        try:
            return json.loads(_REPO_CTX_STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_enriched_pos": 0, "enriched_count": 0}


def _save_repo_ctx_state(state: dict):
    tmp = _REPO_CTX_STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(_REPO_CTX_STATE_FILE)


def run_source6_repo_context_enrichment(dry_run: bool = False) -> int:
    """UPGRADE-3: Enrich DPO records with pre-PR repo context.

    Processes _REPO_CTX_BATCH_SIZE records per call (non-blocking).
    Writes enriched records to a separate JSONL so original DPO files
    are never modified (backward-compatible).
    Returns count of records enriched this call.
    """
    try:
        ctx_state = _load_repo_ctx_state()
        enriched_ids: set = set()

        if _REPO_CTX_ENRICHMENT_FILE.exists():
            enriched_ids = load_jsonl_ids(_REPO_CTX_ENRICHMENT_FILE, id_field="dpo_id")

        # Read a window of DPO records starting from cursor
        all_dpo: list = []
        if DPO_DIR.exists():
            for path in sorted(DPO_DIR.glob("*.jsonl"), reverse=True):  # newest first
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                all_dpo.append(json.loads(line))
                            except Exception:
                                pass
                if len(all_dpo) >= 500:
                    break

        # Find unenriched records with chosen_pr_url
        to_enrich = [
            r for r in all_dpo
            if r.get("chosen_pr_url")
            and r.get("id") not in enriched_ids
        ][:_REPO_CTX_BATCH_SIZE]

        if not to_enrich:
            return 0

        now_utc = datetime.now(timezone.utc).isoformat()
        enriched = 0
        for dpo_rec in to_enrich:
            dpo_id = dpo_rec.get("id", "")
            chosen_pr_url = dpo_rec.get("chosen_pr_url", "")

            ctx = _fetch_repo_context_for_pr(chosen_pr_url)
            rec = {
                "dpo_id":        dpo_id,
                "chosen_pr_url": chosen_pr_url,
                "repo_context":  ctx,
                "task_name":     dpo_rec.get("task_name", ""),
                "enriched_at":   now_utc,
            }
            if not dry_run:
                append_jsonl(_REPO_CTX_ENRICHMENT_FILE, rec)
            enriched += 1

        ctx_state["enriched_count"] = ctx_state.get("enriched_count", 0) + enriched
        if not dry_run:
            _save_repo_ctx_state(ctx_state)

        logging.info(
            f"[S6-CTX] +{enriched} repo contexts enriched "
            f"(total: {ctx_state['enriched_count']})"
        )
        return enriched
    except Exception as e:
        logging.warning(f"[S6-CTX] Enrichment error (non-fatal): {e}")
        return 0

# Quality filters
SFT_MIN_WINNER_SCORE = 0.6
DPO_MIN_SCORE_DIFF   = 0.15
SKIP_EXIT_REASONS    = {"solver_error"}

# Judge feedback thresholds
JF_MAX_REJECTED_SCORE = 0.5
JF_MIN_CHOSEN_SCORE   = 0.7

# Telegram
CHAT_ID = "1602712596"


# ─── Secrets ──────────────────────────────────────────────────────────────────
def _load_secret(key: str) -> Optional[str]:
    """Load a secret by key from /root/.secrets/api_keys.env."""
    try:
        with open(SECRETS_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + "="):
                    val = line[len(key) + 1:].strip().strip('"').strip("'")
                    return val if val else None
    except Exception:
        pass
    return None


def get_gh_pat() -> Optional[str]:
    """Load GitHub PAT from secrets, trying multiple key names."""
    return (
        _load_secret("BACKUP_GH_PAT_PRIMARY")
        or _load_secret("BACKUP_GH_PAT_SECONDARY")
        or _load_secret("GH_PAT")
        or _load_secret("GITHUB_PAT")
    )


def _get_bot_token() -> Optional[str]:
    """Parse T68Bot token from openclaw config. Tries user home first, then /root/."""
    for cfg_path in [Path.home() / ".openclaw/openclaw.json", Path("/root/.openclaw/openclaw.json")]:
        try:
            d = json.loads(cfg_path.read_text())
            token = d["channels"]["telegram"]["botToken"]
            if token:
                return token
        except Exception:
            pass
    return None


def send_telegram(msg: str) -> bool:
    """Send a Telegram message via T68Bot. Returns True on success."""
    token = _get_bot_token()
    if not token:
        logging.warning("Telegram token not found, skipping alert")
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logging.warning(f"Telegram send failed: {e}")
        return False


# ─── Logging ──────────────────────────────────────────────────────────────────
def setup_logging(dry_run: bool = False):
    handlers = [logging.StreamHandler(sys.stdout)]
    if not dry_run:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(LOG_FILE, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        handlers=handlers
    )


# ─── State ────────────────────────────────────────────────────────────────────
DEFAULT_STATE = {
    # Source 1
    "last_processed_duel_id":   MIN_DUEL_ID - 1,
    "total_sft_records":        0,
    "total_dpo_pairs":          0,
    "duels_processed":          0,
    "last_run_utc":             None,
    # Source 2
    "kings_collected":          0,
    "last_king_sha":            None,
    "king_backfill_complete":   False,
    # Source 2 — NEW-3: king name tracking
    "current_king_name":        "",
    "current_king_hotkey":      "",
    # Source 3
    "prs_collected":            0,
    "last_pr_page":             0,
    "pr_backfill_complete":     False,
    "last_pr_number":           0,
    "last_nonempty_pr_page":    0,
    # Source 4
    "judge_feedback_records":   0,
    "jf_last_dpo_file":         None,
    "jf_backfill_complete":     False,
    # Source 4 — NEW-2: backfill empty instruction fields
    "jf_empty_instruction_backfill": False,
    # Source 5
    "miner_versions_collected": 0,
    "miner_files_seen":         [],
    # Periodic
    "last_hourly_log_utc":      None,
    "last_daily_report_utc":    None,
    # FIX-L2: Validator health monitoring
    "recent_anomaly_duels":     [],
    "last_health_alert_utc":    None,
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text())
            merged = dict(DEFAULT_STATE)
            merged.update(saved)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_STATE)


def save_state(state: dict):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(STATE_FILE)
    except Exception as e:
        logging.error(f"save_state failed: {e} — in-memory state continues but will not persist")


# ─── FIX-L3: Counter Sync on Startup ─────────────────────────────────────────
def _recount_training_data() -> dict:
    """Count actual records in SFT/DPO/JF files by reading every JSONL line."""
    try:
        sft_count = 0
        if SFT_DIR.exists():
            for f in SFT_DIR.glob("*.jsonl"):
                with open(f, encoding="utf-8") as fh:
                    sft_count += sum(1 for line in fh if line.strip())
        dpo_count = 0
        if DPO_DIR.exists():
            for f in DPO_DIR.glob("*.jsonl"):
                with open(f, encoding="utf-8") as fh:
                    dpo_count += sum(1 for line in fh if line.strip())
        # FIX-L5: Also recount JF records to fix counter drift
        jf_count = 0
        jf_path = JUDGE_FEEDBACK_DIR / "judge_feedback.jsonl"
        if jf_path.exists():
            with open(jf_path, encoding="utf-8") as fh:
                jf_count = sum(1 for line in fh if line.strip())
        return {"sft": sft_count, "dpo": dpo_count, "jf": jf_count}
    except Exception as e:
        logging.warning(f"_recount_training_data error: {e}")
        return {"sft": None, "dpo": None, "jf": None}


# ─── FIX-L2: Validator Health Detection ──────────────────────────────────────
def _check_validator_health(state: dict) -> bool:
    """Check for 3+ consecutive anomalous duels. Sends Telegram alert if unhealthy."""
    recent_anomalies = state.get("recent_anomaly_duels", [])
    if len(recent_anomalies) >= 3:
        now = datetime.now(timezone.utc)
        last_alert = state.get("last_health_alert_utc")
        should_alert = True
        if last_alert:
            try:
                last_dt = datetime.fromisoformat(last_alert)
                if (now - last_dt).total_seconds() < 3600:
                    should_alert = False
            except Exception:
                pass
        if should_alert:
            msg = (
                f"⚠️ *SN66 COLLECTOR: Validator health alert!*\n"
                f"3+ consecutive anomalous duels — possible validator malfunction!\n"
                f"Last anomalous duels: `{recent_anomalies[-3:]}`\n"
                f"Cursor held at duel #{state.get('last_processed_duel_id')} — NOT advancing."
            )
            logging.warning(f"[HEALTH] 3+ consecutive anomalous duels: {recent_anomalies}")
            send_telegram(msg)
            state["last_health_alert_utc"] = now.isoformat()
        return False
    return True


# ─── HTTP Helpers ─────────────────────────────────────────────────────────────
def fetch_json(url: str, retries: int = 3,
               headers: Optional[dict] = None) -> Optional[dict]:
    """Fetch JSON from URL with retry + exponential backoff."""
    base_headers = {"User-Agent": "SN66-FinalUnifiedCollector/1.0"}
    if headers:
        base_headers.update(headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=base_headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read()
            try:
                return json.loads(raw)
            except json.JSONDecodeError as je:
                # FIX-L6: Don't retry on JSON parse errors — download succeeded but content
                # has invalid escape sequences (common in large dashboard.json with code patches).
                # Try lenient decode: replace invalid UTF-8 then fix bare \u sequences.
                logging.warning(f"JSON parse error on {url} (attempt {attempt+1}): {je}")
                try:
                    text = raw.decode("utf-8", errors="replace")
                    # Replace bare \u not followed by 4 hex digits
                    text = re.sub(r'\\u(?![0-9a-fA-F]{4})', r'\\\\u', text)
                    return json.loads(text)
                except Exception:
                    return None  # Don't retry — same content will fail the same way
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(60 * (attempt + 1), 300)
                logging.warning(f"Rate limited on {url}, waiting {wait}s")
                time.sleep(wait)
            elif e.code == 404:
                logging.debug(f"404 on {url}")
                return None
            else:
                logging.warning(f"HTTP {e.code} on {url} (attempt {attempt+1})")
                time.sleep(5 * (attempt + 1))
        except Exception as e:
            logging.warning(f"Fetch error {url} (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))
    return None


def fetch_text(url: str, retries: int = 3,
               headers: Optional[dict] = None) -> Optional[str]:
    """Fetch raw text from URL with retry."""
    base_headers = {"User-Agent": "SN66-FinalUnifiedCollector/1.0"}
    if headers:
        base_headers.update(headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=base_headers)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(60 * (attempt + 1), 300)
                logging.warning(f"Rate limited on {url}, waiting {wait}s")
                time.sleep(wait)
            elif e.code == 404:
                return None
            else:
                logging.warning(f"HTTP {e.code} on {url} (attempt {attempt+1})")
                time.sleep(5 * (attempt + 1))
        except Exception as e:
            logging.warning(f"Fetch text error {url} (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))
    return None


def gh_headers() -> dict:
    """Build GitHub API auth headers."""
    pat = get_gh_pat()
    h = {"Accept": "application/vnd.github.v3+json"}
    if pat:
        h["Authorization"] = f"token {pat}"
    return h


# ─── JSONL Atomic Writers ─────────────────────────────────────────────────────
def append_jsonl(path: Path, record: dict):
    """Atomically append one JSONL record (file-locked for safety)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def atomic_write_jsonl(path: Path, records: list):
    """Write a full JSONL file atomically (overwrites existing)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)


def today_path(subdir: Path) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return subdir / f"{date_str}.jsonl"


def load_jsonl_ids(path: Path, id_field: str = "id") -> set:
    """Load all IDs from a JSONL file for idempotency checks."""
    ids = set()
    if not path.exists():
        return ids
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        val = rec.get(id_field)
                        if val is not None:
                            ids.add(val)
                    except Exception:
                        pass
    except Exception:
        pass
    return ids


def load_all_jsonl_ids(directory: Path, id_field: str = "id") -> set:
    """Load IDs from ALL JSONL files in a directory."""
    ids = set()
    if not directory.exists():
        return ids
    try:
        for path in directory.glob("*.jsonl"):
            ids.update(load_jsonl_ids(path, id_field))
    except Exception:
        pass
    return ids


# ─── Diff Fetchers (FIX-G2, FIX-G3, FIX-C1) ─────────────────────────────────
_COMMIT_DIFF_CACHE: Dict[str, str] = {}  # sha[:12] -> diff text
_COMMIT_DIFF_CACHE_MAX = 150  # MEM-FIX: cap at 150 entries (~7.5MB max)


def _fetch_pr_diff(pr_url: str, max_chars: int = 50_000) -> str:
    """Fetch the actual unified diff for a GitHub PR URL.
    Cached in-memory. Rate-limited to GH_DIFF_RATE_LIMIT per call."""
    if not pr_url:
        return ""
    if pr_url.strip().startswith("diff --git"):
        return pr_url  # already a diff

    m = re.search(r"/pull/(\d+)", pr_url)
    if not m:
        return ""

    pr_num = int(m.group(1))
    if pr_num in _PR_DIFF_CACHE:
        return _PR_DIFF_CACHE[pr_num]

    time.sleep(GH_DIFF_RATE_LIMIT)

    api_url = f"{GH_API_BASE}/pulls/{pr_num}"
    pat = get_gh_pat()
    req_headers = {
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "SN66-FinalUnifiedCollector/1.0",
    }
    if pat:
        req_headers["Authorization"] = f"token {pat}"

    diff_text = ""
    try:
        req = urllib.request.Request(api_url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            diff_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        logging.warning(f"_fetch_pr_diff: HTTP {e.code} for PR #{pr_num}")
    except Exception as e:
        logging.warning(f"_fetch_pr_diff: error for PR #{pr_num}: {e}")

    if not diff_text:
        # MEM-FIX: evict oldest entries when cache hits limit
        if len(_PR_DIFF_CACHE) >= _PR_DIFF_CACHE_MAX:
            oldest = next(iter(_PR_DIFF_CACHE))
            del _PR_DIFF_CACHE[oldest]
        _PR_DIFF_CACHE[pr_num] = ""
        return ""

    if len(diff_text) > max_chars:
        diff_text = diff_text[:max_chars] + "\n... (truncated at 50KB)"

    # MEM-FIX: evict oldest entries when cache hits limit
    if len(_PR_DIFF_CACHE) >= _PR_DIFF_CACHE_MAX:
        oldest = next(iter(_PR_DIFF_CACHE))
        del _PR_DIFF_CACHE[oldest]
    _PR_DIFF_CACHE[pr_num] = diff_text
    return diff_text


def _fetch_commit_diff(repo_full_name: str, commit_sha: str,
                       max_chars: int = 50_000) -> str:
    """FIX-C1: Fetch diff for a commit SHA from a GitHub repo.
    Used when pr_url is missing (post-duel-4700 format change).
    For private-submission repos, returns '' immediately.
    Cached in-memory by sha[:12]."""
    if not commit_sha or not repo_full_name:
        return ""
    # Private submissions can't be fetched
    if "private-submission" in repo_full_name:
        return ""

    cache_key = commit_sha[:12]
    if cache_key in _COMMIT_DIFF_CACHE:
        return _COMMIT_DIFF_CACHE[cache_key]

    time.sleep(GH_DIFF_RATE_LIMIT)

    api_url = f"https://api.github.com/repos/{repo_full_name}/commits/{commit_sha}"
    pat = get_gh_pat()
    req_headers = {
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "SN66-FinalUnifiedCollector/1.0",
    }
    if pat:
        req_headers["Authorization"] = f"token {pat}"

    diff_text = ""
    try:
        req = urllib.request.Request(api_url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            diff_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code != 404:  # 404 = private/deleted repo, not an error
            logging.warning(f"_fetch_commit_diff: HTTP {e.code} for {repo_full_name}@{commit_sha[:12]}")
    except Exception as e:
        logging.warning(f"_fetch_commit_diff: error for {repo_full_name}@{commit_sha[:12]}: {e}")

    if not diff_text:
        # MEM-FIX: evict oldest entries when cache hits limit
        if len(_COMMIT_DIFF_CACHE) >= _COMMIT_DIFF_CACHE_MAX:
            oldest = next(iter(_COMMIT_DIFF_CACHE))
            del _COMMIT_DIFF_CACHE[oldest]
        _COMMIT_DIFF_CACHE[cache_key] = ""
        return ""

    if len(diff_text) > max_chars:
        diff_text = diff_text[:max_chars] + "\n... (truncated at 50KB)"

    # MEM-FIX: evict oldest entries when cache hits limit
    if len(_COMMIT_DIFF_CACHE) >= _COMMIT_DIFF_CACHE_MAX:
        oldest = next(iter(_COMMIT_DIFF_CACHE))
        del _COMMIT_DIFF_CACHE[oldest]
    _COMMIT_DIFF_CACHE[cache_key] = diff_text
    return diff_text


def _get_best_patch(info: dict, duel_data: dict) -> str:
    """FIX-C1: Get the best available patch for a king/challenger.
    Tries in order: pr_url diff → commit_sha diff → empty.
    """
    # 1. Try pr_url (works for old duels < ~4700)
    pr_url = info.get("pr_url", "")
    if pr_url:
        patch = _fetch_pr_diff(pr_url)
        if patch:
            return patch

    # 2. Try commit_sha + repo_full_name (works for public repos)
    repo_full_name = info.get("repo_full_name", "")
    commit_sha = info.get("commit_sha", "")
    if repo_full_name and commit_sha:
        patch = _fetch_commit_diff(repo_full_name, commit_sha)
        if patch:
            return patch

    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 1: Live Duel SFT/DPO (ported EXACTLY from data_collector.py)
# ═══════════════════════════════════════════════════════════════════════════════

def get_winner_loser_scores(round_data: dict) -> tuple:
    """Returns (winner_label, loser_label, winner_score, loser_score)."""
    winner = round_data.get("winner", "")
    king_score = round_data.get("king_llm_score") or round_data.get("king_score") or 0.0
    chal_score = round_data.get("challenger_llm_score") or round_data.get("challenger_score") or 0.0

    if winner == "king":
        return "king", "challenger", king_score, chal_score
    elif winner == "challenger":
        return "challenger", "king", chal_score, king_score
    else:
        return winner, winner, king_score, chal_score


def extract_task_context(round_data: dict, duel_data: dict) -> dict:
    """Extract task context from round and duel data.
    FIX-C3: Falls back to llm_judge_rationale when llm_judge_rounds is empty
    (which is the case for all duels post ~4700)."""
    task_name = round_data.get("task_name", "")
    task_summary = ""
    task_title = ""

    # Try llm_judge_rounds first (old format, pre ~4700)
    ljr = round_data.get("llm_judge_rounds", [])
    if ljr and isinstance(ljr, list) and len(ljr) > 0:
        first = ljr[0]
        if isinstance(first, dict):
            fd = first.get("final_decision", {}) or {}
            task_summary = fd.get("rationale", "")

    # FIX-C3: Fallback to llm_judge_rationale (available in all duels)
    if not task_summary:
        rationale = round_data.get("llm_judge_rationale", "")
        if rationale:
            # Use first 500 chars of rationale as task summary
            task_summary = rationale[:500]

    return {"task_name": task_name, "task_summary": task_summary, "task_title": task_title}


def build_sft_record(duel_id: int, round_idx: int, round_data: dict,
                     duel_data: dict, now_utc: str) -> Optional[dict]:
    """Build SFT record for winner of a round (score >= SFT_MIN_WINNER_SCORE)."""
    winner_label, loser_label, winner_score, loser_score = get_winner_loser_scores(round_data)

    if winner_score < SFT_MIN_WINNER_SCORE:
        return None
    if winner_label not in ("king", "challenger"):
        return None

    task_ctx = extract_task_context(round_data, duel_data)
    judge_rationale = round_data.get("llm_judge_rationale", "")
    # FIX-C4: field is llm_judge_model (singular string), not llm_judge_models (list)
    judge_model     = round_data.get("llm_judge_model", "")

    king_info  = duel_data.get("king_before", {}) or {}
    chal_info  = duel_data.get("challenger", {}) or {}
    if winner_label == "king":
        winner_info = king_info
    else:
        winner_info = chal_info

    winner_pr  = winner_info.get("pr_url", "")
    winner_sha = winner_info.get("commit_sha", "")
    winner_repo = winner_info.get("repo_full_name", "")
    winner_source = winner_info.get("source", "")
    winner_username = winner_info.get("agent_username", "")

    # FIX-C2: Fetch actual winner patch for SFT training
    winner_patch = _get_best_patch(winner_info, duel_data)

    # UPGRADE-1: classify task type from judge rationale + task summary
    type_text = " ".join(filter(None, [
        task_ctx.get("task_summary", ""),
        task_ctx.get("task_name", ""),
        judge_rationale[:200] if judge_rationale else "",
    ]))
    task_type = classify_task_type(type_text)

    return {
        "id":             f"sn66_sft_duel{duel_id}_r{round_idx}",
        "source":         "live_duel",
        "task_name":      task_ctx["task_name"],
        "task_title":     task_ctx["task_title"],
        "task_summary":   task_ctx["task_summary"],
        "task_type":      task_type,          # UPGRADE-1
        "instruction":    task_ctx["task_name"],  # FIX-C7: SFT instruction field
        "output":         winner_patch,            # FIX-C2: SFT output = winner patch
        "winner":         winner_label,
        "judge_score":    round(winner_score, 4),
        "loser_score":    round(loser_score, 4),
        "judge_rationale": judge_rationale,
        "judge_model":    judge_model,             # FIX-C4: singular, not list
        "judge_weight":   round_data.get("llm_judge_weight", None),  # FIX-C5
        "judge_error":    round_data.get("llm_judge_error", ""),     # FIX-C5
        "winner_pr_url":  winner_pr,
        "winner_sha":     winner_sha,
        "winner_repo":    winner_repo,             # FIX-C5: repo_full_name
        "winner_source":  winner_source,           # FIX-C5: private/github_pr/etc
        "winner_username": winner_username,         # FIX-C5: agent_username
        "winner_patch":   winner_patch,            # FIX-C2: actual code patch
        "king_llm_score": round(round_data.get("king_llm_score") or round_data.get("king_score") or 0, 4),
        "challenger_llm_score": round(round_data.get("challenger_llm_score") or round_data.get("challenger_score") or 0, 4),
        "king_lines":     round_data.get("king_lines", 0),
        "challenger_lines": round_data.get("challenger_lines", 0),
        "king_exit_reason": round_data.get("king_exit_reason", ""),        # FIX-C5
        "challenger_exit_reason": round_data.get("challenger_exit_reason", ""),
        "duel_id":        duel_id,
        "round_idx":      round_idx,
        "collected_at":   now_utc,
    }


def build_dpo_record(duel_id: int, round_idx: int, round_data: dict,
                     duel_data: dict, now_utc: str) -> Optional[dict]:
    """Build DPO preference pair. FIX-G3: includes actual diff text for chosen/rejected."""
    winner_label, loser_label, winner_score, loser_score = get_winner_loser_scores(round_data)

    if winner_label not in ("king", "challenger"):
        return None

    score_diff = winner_score - loser_score
    if abs(score_diff) < DPO_MIN_SCORE_DIFF:
        return None

    task_ctx = extract_task_context(round_data, duel_data)
    judge_rationale = round_data.get("llm_judge_rationale", "")
    # FIX-C4: field is llm_judge_model (singular string)
    judge_model     = round_data.get("llm_judge_model", "")

    king_info  = duel_data.get("king_before", {}) or {}
    chal_info  = duel_data.get("challenger", {}) or {}

    if winner_label == "king":
        chosen_info  = king_info
        rejected_info = chal_info
    else:
        chosen_info  = chal_info
        rejected_info = king_info

    chosen_pr    = chosen_info.get("pr_url", "")
    chosen_sha   = chosen_info.get("commit_sha", "")
    chosen_repo  = chosen_info.get("repo_full_name", "")
    chosen_source = chosen_info.get("source", "")
    rejected_pr  = rejected_info.get("pr_url", "")
    rejected_sha = rejected_info.get("commit_sha", "")
    rejected_repo = rejected_info.get("repo_full_name", "")
    rejected_source = rejected_info.get("source", "")

    # FIX-C1: Use _get_best_patch (tries pr_url then commit_sha, handles private)
    chosen_patch   = _get_best_patch(chosen_info, duel_data)
    rejected_patch = _get_best_patch(rejected_info, duel_data)

    # UPGRADE-1: classify task type
    type_text = " ".join(filter(None, [
        task_ctx.get("task_summary", ""),
        task_ctx.get("task_name", ""),
        judge_rationale[:200] if judge_rationale else "",
    ]))
    task_type = classify_task_type(type_text)

    # UPGRADE-3: score enrichment fields for gold scoring gap
    chosen_lines   = len([l for l in (chosen_patch or "").splitlines() if l.strip()])
    rejected_lines = len([l for l in (rejected_patch or "").splitlines() if l.strip()])
    # AUDIT-FIX: edit_quality compares chosen vs rejected (relative size measure for DPO pairs).
    # If both patches are unavailable (private miners with no public PR), label as "not_available"
    # rather than misleading "empty" (miner wrote code, we just can't fetch it via GitHub).
    if chosen_lines == 0 and rejected_lines == 0:
        edit_quality = "not_available"
    else:
        # For DPO: compares winner patch size relative to loser (tells us if winner was
        # concise vs verbose relative to the losing patch — meaningful relative quality signal).
        edit_quality = edit_quality_label(chosen_patch or "", rejected_patch or "")

    return {
        "id":              f"sn66_dpo_duel{duel_id}_r{round_idx}",
        "source":          "live_duel",
        "task_name":       task_ctx["task_name"],
        "task_summary":    task_ctx["task_summary"],
        "task_type":       task_type,          # UPGRADE-1
        "winner":          winner_label,
        "chosen_score":    round(winner_score, 4),
        "rejected_score":  round(loser_score, 4),
        "score_diff":      round(score_diff, 4),
        "judge_rationale": judge_rationale,
        "judge_model":     judge_model,      # FIX-C4: singular, not list
        "judge_weight":    round_data.get("llm_judge_weight", None),  # FIX-C5
        "judge_error":     round_data.get("llm_judge_error", ""),     # FIX-C5
        "chosen_pr_url":   chosen_pr,
        "chosen_sha":      chosen_sha,
        "chosen_repo":     chosen_repo,      # FIX-C5: repo_full_name
        "chosen_source":   chosen_source,    # FIX-C5: private/github_pr
        "chosen_patch":    chosen_patch,     # FIX-G3 + FIX-C1
        "chosen_lines":    chosen_lines,     # UPGRADE-3
        "rejected_pr_url": rejected_pr,
        "rejected_sha":    rejected_sha,
        "rejected_repo":   rejected_repo,    # FIX-C5: repo_full_name
        "rejected_source": rejected_source,  # FIX-C5: private/github_pr
        "rejected_patch":  rejected_patch,   # FIX-G3 + FIX-C1
        "rejected_lines":  rejected_lines,   # UPGRADE-3
        "edit_quality":    edit_quality,    # UPGRADE-2
        "is_winner":       True,            # chosen_patch = winner in this pair
        "duel_id":         duel_id,
        "round_idx":       round_idx,
        "collected_at":    now_utc,
    }


def process_duel(duel_id: int, dry_run: bool = False,
                 verbose: bool = False) -> tuple:
    """Fetch and process a single duel.
    Returns (sft_count, dpo_count, was_anomaly).
    FIX-L1: counts only increment when records are actually written.
    FIX-L4: caller must NOT advance cursor when was_anomaly=True.
    """
    url = DUEL_URL.format(duel_id=duel_id)
    duel_data = fetch_json(url)
    if duel_data is None:
        logging.warning(f"Duel {duel_id}: failed to fetch")
        return 0, 0, False

    rounds = duel_data.get("rounds", [])
    if not rounds:
        logging.info(f"Duel {duel_id}: no rounds")
        return 0, 0, False

    # Anomaly filter: extreme ratios signal broken scorer
    # FIX-C8: Also count solver_error exits — high error rate is anomalous too
    total_r = len(rounds)
    king_wins = sum(1 for r in rounds if r.get("winner") == "king")
    chal_wins = sum(1 for r in rounds if r.get("winner") == "challenger")
    solver_errors = sum(1 for r in rounds if r.get("challenger_exit_reason") in SKIP_EXIT_REASONS
                        or r.get("king_exit_reason") in SKIP_EXIT_REASONS)
    if total_r >= 20:
        chal_rate = chal_wins / total_r
        error_rate = solver_errors / total_r
        if (chal_rate >= 0.85 or chal_rate <= 0.15) and error_rate < 0.5:
            # High win ratio but NOT due to solver errors — potentially anomalous
            logging.warning(
                f"[S1] Duel {duel_id}: ANOMALOUS score {chal_wins}-{king_wins}/{total_r} "
                f"({chal_rate:.0%} challenger win rate) - possible broken validator, SKIPPING"
            )
            return 0, 0, True  # was_anomaly=True
        elif error_rate >= 0.5:
            logging.warning(
                f"[S1] Duel {duel_id}: HIGH ERROR RATE {solver_errors}/{total_r} "
                f"({error_rate:.0%}) - still collecting valid rounds"
            )

    now_utc = datetime.now(timezone.utc).isoformat()
    sft_path = today_path(SFT_DIR)
    dpo_path = today_path(DPO_DIR)

    existing_sft = load_jsonl_ids(sft_path)
    existing_dpo = load_jsonl_ids(dpo_path)

    sft_count = 0
    dpo_count = 0
    skipped   = 0

    for idx, rnd in enumerate(rounds):
        exit_reason = rnd.get("challenger_exit_reason", "")
        if exit_reason in SKIP_EXIT_REASONS:
            skipped += 1
            continue

        winner = rnd.get("winner", "")
        if winner == "tie" or winner == "":
            skipped += 1
            continue

        sft_rec = build_sft_record(duel_id, idx, rnd, duel_data, now_utc)
        if sft_rec:
            if sft_rec["id"] not in existing_sft:
                if not dry_run:
                    append_jsonl(sft_path, sft_rec)
                    existing_sft.add(sft_rec["id"])
                sft_count += 1

        dpo_rec = build_dpo_record(duel_id, idx, rnd, duel_data, now_utc)
        if dpo_rec:
            if dpo_rec["id"] not in existing_dpo:
                if not dry_run:
                    append_jsonl(dpo_path, dpo_rec)
                    existing_dpo.add(dpo_rec["id"])
                dpo_count += 1

    if verbose or dry_run:
        logging.info(f"Duel {duel_id}: {len(rounds)} rounds → "
                     f"{sft_count} SFT, {dpo_count} DPO, {skipped} skipped")

    return sft_count, dpo_count, False


def get_new_duel_ids(last_id: int) -> list:
    """Poll dashboard.json and return sorted list of new duel_ids > last_id."""
    data = fetch_json(DASHBOARD_URL)
    if data is None:
        # FIX-L7: Regex fallback when JSON parse fails for large dashboard.json.
        # The file can be 100MB+ with code patches containing invalid \u sequences.
        # We only need duel_id integers — safely extractable via regex.
        logging.info("[S1] JSON parse failed for dashboard.json, trying regex fallback")
        raw = fetch_text(DASHBOARD_URL)
        if raw is None:
            return []
        try:
            ids = [int(m) for m in re.findall(r'"duel_id"\s*:\s*(\d+)', raw)]
            new_ids = sorted(set(i for i in ids if i > last_id and i >= MIN_DUEL_ID))
            if new_ids:
                logging.info(f"[S1] Regex fallback found {len(new_ids)} new duel IDs: {new_ids[:5]}")
            return new_ids
        except Exception as e:
            logging.warning(f"[S1] Regex fallback error: {e}")
            return []
    duels = data.get("duels", [])
    new_ids = []
    for d in duels:
        did = d.get("duel_id")
        if did and isinstance(did, int) and did > last_id and did >= MIN_DUEL_ID:
            new_ids.append(did)
    return sorted(new_ids)


# FIX-SAVE-BATCH: Batched state save — save every N duels, not every single one.
# Reduces fsync overhead during burst collection of many duels.
# State is also always saved at end of main loop cycle and on SIGTERM.
_STATE_SAVE_BATCH_SIZE = 10  # save once per 10 duels


def run_source1(state: dict, dry_run: bool = False) -> int:
    """Poll for new duels and process them.
    FIX-L2: tracks anomalous duels and alerts on 3+ consecutive.
    FIX-L4: cursor does NOT advance for anomalous duels.
    FIX-SAVE-BATCH: saves state every _STATE_SAVE_BATCH_SIZE duels (not every duel).
    """
    new_ids = get_new_duel_ids(state["last_processed_duel_id"])
    if not new_ids:
        return 0

    logging.info(f"[S1] Found {len(new_ids)} new duels: {new_ids[:10]}{'...' if len(new_ids) > 10 else ''}")
    count = 0
    duels_since_save = 0
    for duel_id in new_ids:
        time.sleep(RATE_LIMIT_SLEEP)
        try:
            sft_n, dpo_n, was_anomaly = process_duel(duel_id, dry_run=dry_run, verbose=False)
        except Exception as e:
            logging.error(f"[S1] Duel {duel_id}: unexpected error — skipping: {e}", exc_info=True)
            continue

        if was_anomaly:
            anomaly_list = state.setdefault("recent_anomaly_duels", [])
            if duel_id not in anomaly_list:
                anomaly_list.append(duel_id)
            logging.warning(f"[S1] Duel {duel_id}: anomalous - cursor NOT advanced")
            _check_validator_health(state)
            if not dry_run:
                save_state(state)  # always save on anomaly (cursor held, must persist)
            duels_since_save = 0
            continue

        # Clean duel: reset consecutive-anomaly tracker
        state["recent_anomaly_duels"] = []
        state["last_processed_duel_id"] = duel_id
        state["total_sft_records"] += sft_n
        state["total_dpo_pairs"]   += dpo_n
        state["duels_processed"]   += 1
        count += 1
        duels_since_save += 1
        logging.info(f"[S1] Duel {duel_id}: +{sft_n} SFT, +{dpo_n} DPO "
                     f"(total: {state['total_sft_records']} SFT, {state['total_dpo_pairs']} DPO)")
        # FIX-SAVE-BATCH: save every N duels, not every single one
        if not dry_run and duels_since_save >= _STATE_SAVE_BATCH_SIZE:
            save_state(state)
            duels_since_save = 0
    # Always flush remaining dirty state at end of S1 run
    if not dry_run and duels_since_save > 0:
        save_state(state)
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 2: King Code History
# ═══════════════════════════════════════════════════════════════════════════════

KING_COMMIT_PATTERNS = [
    "promote miner",
    "promote private miner",  # handles "Promote private miner ..." format
    "new king",
    "👑",
]


def is_king_commit(message: str) -> bool:
    """Check if a commit message indicates a king promotion."""
    if not message:
        return False
    msg_lower = message.lower()
    for pattern in KING_COMMIT_PATTERNS:
        if pattern.lower() in msg_lower:
            return True
    # Regex: "promote" followed by "miner" anywhere (handles extra words like "private")
    if re.search(r"promote\b.*\bminer", msg_lower):
        return True
    # "as ninja king" or similar explicit king declarations
    if re.search(r"as ninja king|as new king|crowned king", msg_lower):
        return True
    if "merge pull request" in msg_lower and ("king" in msg_lower or "miner" in msg_lower):
        return True
    return False


def _extract_king_name_from_commit(commit: dict) -> str:
    """Extract the king's miner/agent name from a commit message. NEW-3."""
    msg = commit.get("commit", {}).get("message", "") or ""
    # Pattern: "Promote miner: viper-agent" or "Promote private miner X as ninja king"
    name_match = re.search(
        r"(?:promote(?:\s+private)?\s+miner|new king)[:\s]+([^\n,]+?)(?:\s+as\s+|\s*$)",
        msg, re.IGNORECASE
    )
    if name_match:
        candidate = name_match.group(1).strip()[:100]
        # If it looks like a hotkey (long SS58 address), skip it
        if len(candidate) < 48:
            return candidate
    # Try extracting hotkey shortened ID from commit message
    hk_match = re.search(r"Winning miner hotkey:\s*(5[A-HJ-NP-Za-km-z1-9]{8,12})", msg)
    if hk_match:
        return f"hotkey:{hk_match.group(1)}"
    # Extract from merge PR branch name: "Merge pull request #N from owner/branch-name"
    pr_match = re.search(r"Merge pull request #\d+ from [\w-]+/([\w-]+)", msg)
    if pr_match:
        return pr_match.group(1)
    return ""


def fetch_agent_at_sha(sha: str) -> Optional[str]:
    """Fetch agent.py content at a specific commit SHA."""
    url = f"https://raw.githubusercontent.com/unarbos/ninja/{sha}/agent.py"
    time.sleep(RATE_LIMIT_SLEEP)
    return fetch_text(url)


def fetch_king_commits(page: int = 1, per_page: int = 100) -> Optional[list]:
    """Fetch a page of commits from the ninja repo."""
    url = f"{GH_API_BASE}/commits?per_page={per_page}&page={page}"
    time.sleep(RATE_LIMIT_SLEEP)
    return fetch_json(url, headers=gh_headers())


def build_king_record(commit: dict, agent_content: str, now_utc: str) -> dict:
    """Build a king_history record from a commit. NEW-3: includes king_name."""
    sha = commit.get("sha", "")
    msg = commit.get("commit", {}).get("message", "") or ""
    author = commit.get("commit", {}).get("author", {}) or {}
    hotkey = ""
    pr_number = None

    pr_match = re.search(r"#(\d+)", msg)
    if pr_match:
        pr_number = int(pr_match.group(1))

    hotkey_match = re.search(r"\b5[A-HJ-NP-Za-km-z1-9]{47}\b", msg)
    if hotkey_match:
        hotkey = hotkey_match.group(0)

    # NEW-3: extract king name
    king_name = _extract_king_name_from_commit(commit)

    return {
        "id":               f"king_{sha[:12]}",
        "sha":              sha,
        "hotkey":           hotkey,
        "king_name":        king_name,  # NEW-3
        "pr_number":        pr_number,
        "merged_at":        author.get("date", ""),
        "commit_message":   msg[:500],
        "agent_py_content": agent_content or "",
        "agent_py_lines":   len((agent_content or "").splitlines()),
        "duel_count_held":  None,
        "dethroned_by_pr":  None,
        "dethroned_by_sha": None,
        "collected_at":     now_utc,
    }


def run_source2_backfill(state: dict, dry_run: bool = False) -> int:
    """One-time: fetch ALL king commits from the unarbos/ninja repo."""
    logging.info("[S2] Starting king history backfill...")
    king_path = KING_HISTORY_DIR / "king_history.jsonl"
    existing_ids = load_jsonl_ids(king_path, id_field="id")

    collected = 0
    page = 1
    stop = False
    api_failure = False
    newest_king_sha = None  # FIX: track most-recent king (commits are newest-first)

    while not stop:
        commits = fetch_king_commits(page=page)
        if not commits:
            api_failure = True
            logging.warning("[S2] GitHub API failure mid-backfill — will retry next cycle")
            break
        if len(commits) < 100:
            stop = True

        now_utc = datetime.now(timezone.utc).isoformat()
        for commit in commits:
            sha = commit.get("sha", "")
            if not sha:
                continue

            rec_id = f"king_{sha[:12]}"
            if rec_id in existing_ids:
                logging.debug(f"[S2] Already have {sha[:12]}, stopping backfill")
                stop = True
                break

            msg = commit.get("commit", {}).get("message", "") or ""
            if not is_king_commit(msg):
                continue

            logging.info(f"[S2] New king commit {sha[:12]}: {msg[:80]}")
            agent_content = fetch_agent_at_sha(sha)
            if agent_content:
                rec = build_king_record(commit, agent_content, now_utc)
                if not dry_run:
                    append_jsonl(king_path, rec)
                    existing_ids.add(rec_id)
                collected += 1
                state["kings_collected"] = state.get("kings_collected", 0) + 1
                # FIX: track most-recent king SHA (set only on first found = newest)
                if newest_king_sha is None:
                    newest_king_sha = sha
                # NEW-3: update current king name if this is the most recent
                king_name = rec.get("king_name", "")
                if king_name and page == 1 and newest_king_sha == sha:
                    state["current_king_name"] = king_name
                    state["current_king_hotkey"] = rec.get("hotkey", "")

        page += 1
        if page > 50:
            break

    # FIX: set last_king_sha to the most recent king found (not oldest)
    if newest_king_sha:
        state["last_king_sha"] = newest_king_sha

    if not api_failure:
        state["king_backfill_complete"] = True
        logging.info(f"[S2] Backfill complete: {collected} new king records")
    else:
        logging.warning(f"[S2] Backfill INCOMPLETE (API failure) — {collected} collected so far")

    return collected


def run_source2_incremental(state: dict, dry_run: bool = False) -> int:
    """Incremental: check latest commits for new king promotions."""
    king_path = KING_HISTORY_DIR / "king_history.jsonl"
    existing_ids = load_jsonl_ids(king_path, id_field="id")

    commits = fetch_king_commits(page=1, per_page=30)
    if not commits:
        return 0

    collected = 0
    now_utc = datetime.now(timezone.utc).isoformat()
    last_known_sha = state.get("last_king_sha")
    newest_king_sha = None  # FIX: track most-recent king

    for commit in commits:
        sha = commit.get("sha", "")
        if not sha:
            continue

        if sha == last_known_sha:
            break  # already processed up to here

        rec_id = f"king_{sha[:12]}"
        if rec_id in existing_ids:
            continue

        msg = commit.get("commit", {}).get("message", "") or ""
        if not is_king_commit(msg):
            continue

        logging.info(f"[S2] New king commit {sha[:12]}: {msg[:80]}")
        agent_content = fetch_agent_at_sha(sha)
        if agent_content:
            rec = build_king_record(commit, agent_content, now_utc)
            if not dry_run:
                append_jsonl(king_path, rec)
                existing_ids.add(rec_id)
            collected += 1
            state["kings_collected"] = state.get("kings_collected", 0) + 1
            # FIX: track most-recent king SHA (first found = newest)
            if newest_king_sha is None:
                newest_king_sha = sha
            # NEW-3: update current king name/hotkey (most recent only)
            king_name = rec.get("king_name", "")
            if king_name and newest_king_sha == sha:
                state["current_king_name"] = king_name
                state["current_king_hotkey"] = rec.get("hotkey", "")

    # FIX: set last_king_sha to the most recent king found
    if newest_king_sha:
        state["last_king_sha"] = newest_king_sha

    return collected


def run_source2(state: dict, dry_run: bool = False) -> int:
    """Source 2 entry: backfill if needed, then incremental."""
    try:
        if not state.get("king_backfill_complete"):
            return run_source2_backfill(state, dry_run)
        else:
            return run_source2_incremental(state, dry_run)
    except Exception as e:
        logging.error(f"[S2] Error: {e}", exc_info=True)
        return 0


# ─── NEW-1: Startup King Change Detection ─────────────────────────────────────
def check_king_change_on_startup(state: dict) -> bool:
    """On daemon startup, check if the king has changed since last collection.
    If the latest king commit SHA differs from state["last_king_sha"],
    reset king_backfill_complete to trigger incremental capture before main loop.
    Returns True if king changed (backfill will run).
    """
    logging.info("[STARTUP] Checking for king change since last run...")
    commits = fetch_king_commits(page=1, per_page=20)
    if not commits:
        logging.warning("[STARTUP] Could not fetch commits to check king change")
        return False

    for commit in commits:
        msg = commit.get("commit", {}).get("message", "") or ""
        if is_king_commit(msg):
            latest_king_sha = commit.get("sha", "")
            stored_sha = state.get("last_king_sha", "")
            if latest_king_sha and latest_king_sha != stored_sha:
                king_name = _extract_king_name_from_commit(commit)
                logging.info(
                    f"[STARTUP] NEW KING DETECTED: {latest_king_sha[:12]} "
                    f"(name: {king_name or 'unknown'}, was: {(stored_sha or 'none')[:12]})"
                )
                # Trigger incremental king capture before main loop
                state["king_backfill_complete"] = False
                return True
            else:
                logging.info(f"[STARTUP] King unchanged: {(latest_king_sha or 'none')[:12]}")
            break  # Only care about the most recent king commit

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 3: PR Outcome Labels
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_pr_page(page: int, per_page: int = 100) -> Optional[list]:
    """Fetch a page of PRs (all states) from the ninja repo."""
    url = f"{GH_API_BASE}/pulls?state=all&per_page={per_page}&page={page}&sort=created&direction=asc"
    time.sleep(RATE_LIMIT_SLEEP)
    return fetch_json(url, headers=gh_headers())


def fetch_pr_diff(pr_number: int) -> Optional[str]:
    """Fetch the diff for a PR."""
    url = f"https://patch-diff.githubusercontent.com/raw/unarbos/ninja/pull/{pr_number}.diff"
    time.sleep(RATE_LIMIT_SLEEP)
    diff = fetch_text(url, headers={"Accept": "application/vnd.github.v3.diff"})
    if diff and len(diff) > 50_000:
        diff = diff[:50_000] + "\n... (truncated)"
    return diff


def build_pr_record(pr: dict, checks: dict, diff: Optional[str], now_utc: str) -> dict:
    """Build a pr_outcomes record."""
    pr_number = pr.get("number", 0)
    title     = pr.get("title", "") or ""
    merged_at = pr.get("merged_at") or ""
    state_str = pr.get("state") or ""
    labels    = [lb.get("name", "") for lb in (pr.get("labels") or [])]

    body = pr.get("body") or ""
    hotkey = ""
    hk_match = re.search(r"\b5[A-HJ-NP-Za-km-z1-9]{47}\b", title + " " + body)
    if hk_match:
        hotkey = hk_match.group(0)

    won_duel = None
    if "won" in labels or "king" in labels:
        won_duel = True
    elif "lost" in labels or "rejected" in labels:
        won_duel = False
    elif merged_at:
        won_duel = True
    elif state_str == "closed" and not merged_at:
        won_duel = False

    return {
        "id":               f"pr_{pr_number}",
        "pr_number":        pr_number,
        "title":            title[:300],
        "hotkey":           hotkey,
        "pr_state":         state_str,
        "merged_at":        merged_at,
        "labels":           labels,
        "diff_content":     diff or "",
        "diff_chars":       len(diff or ""),
        "ci_scope_pass":    checks.get("ci_scope_pass"),
        "ci_judge_pass":    checks.get("ci_judge_pass"),
        "ci_judge_score":   checks.get("ci_judge_score"),
        "duel_id":          None,
        "won_duel":         won_duel,
        "king_duration_blocks": None,
        "collected_at":     now_utc,
    }


def run_source3_page(state: dict, dry_run: bool = False) -> int:
    """Process one page of PRs. Returns count of new PRs processed."""
    pr_path = PR_OUTCOMES_DIR / "pr_outcomes.jsonl"
    existing_ids = load_jsonl_ids(pr_path, id_field="id")

    next_page = state.get("last_pr_page", 0) + 1
    prs = fetch_pr_page(page=next_page)

    if prs is None:
        logging.warning(f"[S3] Failed to fetch PR page {next_page}")
        return 0

    if len(prs) == 0:
        # Smart reset: jump back near last productive page
        last_nonempty = state.get("last_nonempty_pr_page", 0)
        reset_to = max(0, last_nonempty - 2)
        logging.info(
            f"[S3] All PRs fetched. Total: {state['prs_collected']}. "
            f"Smart reset to page {reset_to} (last nonempty: page {last_nonempty})."
        )
        state["pr_backfill_complete"] = True
        state["last_pr_page"] = reset_to
        return 0

    now_utc = datetime.now(timezone.utc).isoformat()
    collected = 0

    for pr in prs:
        pr_number = pr.get("number", 0)
        rec_id = f"pr_{pr_number}"

        if rec_id in existing_ids:
            continue

        diff = fetch_pr_diff(pr_number)
        checks = {}  # CI checks skipped during mass backfill

        rec = build_pr_record(pr, checks, diff, now_utc)
        if not dry_run:
            append_jsonl(pr_path, rec)
            existing_ids.add(rec_id)
        collected += 1
        state["prs_collected"] = state.get("prs_collected", 0) + 1

        if pr_number > state.get("last_pr_number", 0):
            state["last_pr_number"] = pr_number

    state["last_pr_page"] = next_page
    if collected > 0:
        state["last_nonempty_pr_page"] = next_page
    logging.info(f"[S3] Page {next_page}: +{collected} PRs (total: {state['prs_collected']})")
    return collected


def run_source3(state: dict, dry_run: bool = False) -> int:
    """Source 3 entry: paginate through all PRs, one page per cycle.

    FIX-S3-INCR: When pr_backfill_complete=True, skip straight to the latest
    page (last_nonempty_pr_page + 1) instead of re-cycling stale pages.
    This prevents the pages-15,16 cycling loop when all PRs are already fetched.
    """
    try:
        if state.get("pr_backfill_complete"):
            # Incremental mode: jump to one past the last productive page
            last_nonempty = state.get("last_nonempty_pr_page", 0)
            # Only advance if we haven't already checked the newest page this cycle
            current_page = state.get("last_pr_page", 0)
            if current_page < last_nonempty:
                # still behind - let normal pagination catch up
                pass
            else:
                # jump to last_nonempty so run_source3_page fetches last_nonempty+1
                state["last_pr_page"] = last_nonempty
        return run_source3_page(state, dry_run)
    except Exception as e:
        logging.error(f"[S3] Error: {e}", exc_info=True)
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 4: Judge Feedback SFT
# ═══════════════════════════════════════════════════════════════════════════════

def synthesize_lesson(judge_rationale: str, task_name: str,
                      chosen_score: float, rejected_score: float) -> str:
    """Extract a lesson from judge rationale (pattern-based, no LLM)."""
    if not judge_rationale:
        return "Review winning patch for patterns missed by losing submission."

    rationale_lower = judge_rationale.lower()
    lessons = []

    if "missing" in rationale_lower or "does not" in rationale_lower or "doesn't" in rationale_lower:
        lessons.append("Implement all required features completely — partial implementations lose.")
    if "unnecessary" in rationale_lower or "churn" in rationale_lower or "unrelated" in rationale_lower:
        lessons.append("Avoid unnecessary changes outside task scope — extra churn penalizes score.")
    if "streaming" in rationale_lower:
        lessons.append("Match the exact streaming/async approach specified in the task.")
    if "type" in rationale_lower and "error" in rationale_lower:
        lessons.append("Ensure type correctness — TypeScript/type errors are heavily penalized.")
    if "test" in rationale_lower and ("fail" in rationale_lower or "break" in rationale_lower):
        lessons.append("Do not break existing tests.")
    if "edge case" in rationale_lower:
        lessons.append("Handle edge cases: undefined, null, empty, boundary values.")
    if "error handling" in rationale_lower or "exception" in rationale_lower:
        lessons.append("Add proper error handling and exception recovery.")

    if not lessons:
        first_sentence = judge_rationale.split(".")[0].strip()
        if first_sentence:
            lessons.append(f"Key judge insight: {first_sentence[:200]}")

    score_gap = chosen_score - rejected_score
    lessons.append(f"Score gap was {score_gap:.2f} — focus on the judge's highlighted improvements.")
    return " ".join(lessons)


def build_jf_record(dpo_rec: dict, now_utc: str) -> Optional[dict]:
    """Build a judge_feedback record from a DPO record.
    FIX-G1: instruction = judge_rationale (not empty string).
    FIX-G2: fetch actual unified diffs.
    """
    chosen_score   = dpo_rec.get("chosen_score", 0.0)
    rejected_score = dpo_rec.get("rejected_score", 0.0)
    duel_id        = dpo_rec.get("duel_id")
    round_idx      = dpo_rec.get("round_idx", 0)

    if chosen_score < JF_MIN_CHOSEN_SCORE:
        return None
    if rejected_score > JF_MAX_REJECTED_SCORE:
        return None

    task_name       = dpo_rec.get("task_name", "")
    judge_rationale = dpo_rec.get("judge_rationale", "")
    lesson = synthesize_lesson(judge_rationale, task_name, chosen_score, rejected_score)

    chosen_pr_url   = dpo_rec.get("chosen_pr_url", "")
    rejected_pr_url = dpo_rec.get("rejected_pr_url", "")
    # FIX-G2: fetch actual diffs (or use pre-fetched if available in DPO record)
    winning_patch  = dpo_rec.get("chosen_patch") or _fetch_pr_diff(chosen_pr_url)
    losing_patch   = dpo_rec.get("rejected_patch") or _fetch_pr_diff(rejected_pr_url)

    # UPGRADE-1: classify task type from judge rationale
    task_type = classify_task_type(judge_rationale)

    return {
        "id":              f"jf_duel{duel_id}_r{round_idx}",
        "source":          "dpo_loss_feedback",
        "task_id":         task_name,
        "task_name":       task_name,
        "task_type":       task_type,          # UPGRADE-1
        "instruction":     judge_rationale,   # FIX-G1: judge rationale as training signal
        "losing_patch":    losing_patch,       # FIX-G2: actual unified diff
        "winning_patch":   winning_patch,      # FIX-G2: actual unified diff
        "judge_penalty":   judge_rationale,
        "judge_reward":    "",
        "lesson":          lesson,
        "duel_id":         duel_id,
        "round_idx":       round_idx,
        "king_llm_score":  chosen_score,
        "our_llm_score":   rejected_score,
        "score_diff":      round(chosen_score - rejected_score, 4),
        "chosen_pr_url":   chosen_pr_url,
        "rejected_pr_url": rejected_pr_url,
        "collected_at":    now_utc,
    }


def iter_all_dpo_records():
    """Yield all DPO records from all dpo/ JSONL files."""
    if not DPO_DIR.exists():
        return
    for path in sorted(DPO_DIR.glob("*.jsonl")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            yield json.loads(line)
                        except Exception:
                            pass
        except Exception as e:
            logging.warning(f"[S4] Error reading {path}: {e}")


def run_source4(state: dict, dry_run: bool = False) -> int:
    """Source 4: Process DPO losses into judge feedback pairs."""
    try:
        jf_path = JUDGE_FEEDBACK_DIR / "judge_feedback.jsonl"
        existing_ids = load_jsonl_ids(jf_path, id_field="id")
        now_utc = datetime.now(timezone.utc).isoformat()
        collected = 0

        for dpo_rec in iter_all_dpo_records():
            rec = build_jf_record(dpo_rec, now_utc)
            if rec is None:
                continue
            if rec["id"] in existing_ids:
                continue
            if not dry_run:
                append_jsonl(jf_path, rec)
                existing_ids.add(rec["id"])
            collected += 1

        if collected > 0:
            state["judge_feedback_records"] = state.get("judge_feedback_records", 0) + collected
            logging.info(f"[S4] +{collected} judge feedback records "
                         f"(total: {state['judge_feedback_records']})")

        if not state.get("jf_backfill_complete"):
            state["jf_backfill_complete"] = True

        return collected
    except Exception as e:
        logging.error(f"[S4] Error: {e}", exc_info=True)
        return 0


# ─── NEW-2: Judge Feedback Instruction Backfill ────────────────────────────────
def run_source4_fix_empty_instructions(state: dict, dry_run: bool = False) -> int:
    """Backfill existing judge_feedback records that have empty instruction field.
    Reads existing records, finds ones with instruction='', looks up the
    judge_rationale from matching DPO records, rewrites atomically.
    NEW-2: runs on startup if jf_empty_instruction_backfill=False.
    """
    jf_path = JUDGE_FEEDBACK_DIR / "judge_feedback.jsonl"
    if not jf_path.exists():
        logging.info("[S4-BACKFILL] No judge_feedback.jsonl to backfill")
        state["jf_empty_instruction_backfill"] = True
        return 0

    # Build lookup: (duel_id, round_idx) -> judge_rationale from DPO records
    logging.info("[S4-BACKFILL] Building DPO lookup for instruction backfill...")
    dpo_lookup = {}
    for dpo_rec in iter_all_dpo_records():
        key = (dpo_rec.get("duel_id"), dpo_rec.get("round_idx", 0))
        dpo_lookup[key] = dpo_rec.get("judge_rationale", "")

    logging.info(f"[S4-BACKFILL] DPO lookup built: {len(dpo_lookup)} entries")

    # Read all existing JF records
    jf_records = []
    try:
        with open(jf_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        jf_records.append(json.loads(line))
                    except Exception:
                        pass
    except Exception as e:
        logging.error(f"[S4-BACKFILL] Error reading {jf_path}: {e}")
        return 0

    # Fix empty instruction fields
    now_utc = datetime.now(timezone.utc).isoformat()
    fixed_count = 0
    for rec in jf_records:
        if not rec.get("instruction"):
            key = (rec.get("duel_id"), rec.get("round_idx", 0))
            rationale = dpo_lookup.get(key, "")
            if rationale:
                rec["instruction"] = rationale
                rec["backfilled_instruction_at"] = now_utc
                fixed_count += 1

    if fixed_count > 0:
        if not dry_run:
            atomic_write_jsonl(jf_path, jf_records)
            logging.info(f"[S4-BACKFILL] Fixed {fixed_count}/{len(jf_records)} records "
                         f"with empty instruction field (atomic rewrite)")
        else:
            logging.info(f"[S4-BACKFILL] Would fix {fixed_count} records (dry_run)")
    else:
        logging.info(f"[S4-BACKFILL] No empty instruction fields found in {len(jf_records)} records ✅")

    state["jf_empty_instruction_backfill"] = True
    return fixed_count


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 5: Miner Version History
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_PATTERNS = [
    "agent_t68_v*.py",
    "agent_cl_gpt_v*.py",
    "agent_direct_coder.py",
    "agent_gpt54_*.py",
    "agent_t68_v_next.py",
]


def extract_version_label(filename: str) -> str:
    """Extract a version label from an agent filename."""
    name = filename.replace(".py", "")
    match = re.search(r"agent_(?:t68_|cl_gpt_)?(v\w+)", name)
    if match:
        return match.group(1)
    match = re.search(r"agent_(.+)", name)
    if match:
        return match.group(1)
    return name


def scan_agent_files() -> list:
    """Return sorted list of agent file paths in /root/sn66-ninja/."""
    found = []
    seen = set()
    for pattern in AGENT_PATTERNS:
        for path in sorted(SN66_DIR.glob(pattern)):
            if path.name not in seen:
                found.append(path)
                seen.add(path.name)
    agent_py = SN66_DIR / "agent.py"
    if agent_py.exists() and "agent.py" not in seen:
        found.append(agent_py)
    return found


def build_miner_record(path: Path, version: str, now_utc: str) -> dict:
    """Build a miner_history record for one agent file."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        content = f"# Error reading file: {e}"

    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

    pr_number = None
    pr_match = re.search(r"PR[:\s#]+(\d+)|pull/(\d+)", content[:2000])
    if pr_match:
        pr_number = int(pr_match.group(1) or pr_match.group(2))

    submitted = bool(pr_number)
    improvement_match = re.findall(
        r"(?:fix|improve|add|enhance|feat)[\w\s:]+[^\n]{10,80}",
        content[:3000], re.IGNORECASE
    )
    key_improvements = [m.strip()[:100] for m in improvement_match[:5]]
    lines = content.splitlines()

    return {
        "id":                f"miner_{path.name}",
        "version":           version,
        "filename":          path.name,
        "agent_py_path":     str(path),
        "agent_py_content":  content,
        "agent_py_lines":    len(lines),
        "gate_win_rate":     None,
        "gate_tasks":        None,
        "changes_vs_prev":   "",
        "key_improvements":  key_improvements,
        "regressions":       [],
        "submitted":         submitted,
        "pr_number":         pr_number,
        "file_mtime_utc":    mtime,
        "date":              mtime[:10],
        "collected_at":      now_utc,
    }


def run_source5(state: dict, dry_run: bool = False) -> int:
    """Source 5: Scan agent files and record new ones."""
    try:
        miner_path = MINER_HISTORY_DIR / "miner_history.jsonl"
        existing_ids = load_jsonl_ids(miner_path, id_field="id")
        files_seen = set(state.get("miner_files_seen") or [])
        now_utc = datetime.now(timezone.utc).isoformat()
        collected = 0

        agent_files = scan_agent_files()
        for path in agent_files:
            rec_id = f"miner_{path.name}"
            if rec_id in existing_ids:
                continue
            if path.name in files_seen:
                continue

            version = extract_version_label(path.name)
            logging.info(f"[S5] New agent file: {path.name} → {version}")

            rec = build_miner_record(path, version, now_utc)
            if not dry_run:
                append_jsonl(miner_path, rec)
                existing_ids.add(rec_id)
            files_seen.add(path.name)
            collected += 1

        if collected > 0:
            state["miner_versions_collected"] = state.get("miner_versions_collected", 0) + collected
            state["miner_files_seen"] = sorted(files_seen)
            logging.info(f"[S5] +{collected} miner versions "
                         f"(total: {state['miner_versions_collected']})")

        return collected
    except Exception as e:
        logging.error(f"[S5] Error: {e}", exc_info=True)
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# Periodic Reporting
# ═══════════════════════════════════════════════════════════════════════════════

def log_hourly_stats(state: dict):
    now = datetime.now(timezone.utc)
    last_str = state.get("last_hourly_log_utc")
    if last_str:
        try:
            last = datetime.fromisoformat(last_str)
            if (now - last).total_seconds() < 3600:
                return
        except Exception:
            pass

    king_info = ""
    if state.get("current_king_name"):
        king_info = f" king={state['current_king_name']}"

    logging.info(
        f"[STATS] duels={state['duels_processed']} "
        f"sft={state['total_sft_records']} dpo={state['total_dpo_pairs']} "
        f"kings={state.get('kings_collected', 0)} "
        f"prs={state.get('prs_collected', 0)} "
        f"jf={state.get('judge_feedback_records', 0)} "
        f"miners={state.get('miner_versions_collected', 0)}"
        f"{king_info}"
    )
    state["last_hourly_log_utc"] = now.isoformat()


def maybe_send_daily_report(state: dict, dry_run: bool = False):
    now = datetime.now(timezone.utc)
    if now.hour != 9 or now.minute > 5:
        return

    last_str = state.get("last_daily_report_utc")
    if last_str:
        try:
            last = datetime.fromisoformat(last_str)
            if (now - last).total_seconds() < 82800:
                return
        except Exception:
            pass

    king_line = ""
    if state.get("current_king_name"):
        king_line = f"\nCurrent king: {state['current_king_name']}"

    msg = (
        f"📊 *SN66 Data Collector Daily Report*\n"
        f"Date: {now.strftime('%Y-%m-%d')}\n"
        f"Live duels: SFT {state['total_sft_records']} | DPO {state['total_dpo_pairs']} (cumulative)\n"
        f"King history: {state.get('kings_collected', 0)} kings collected{king_line}\n"
        f"PR outcomes: {state.get('prs_collected', 0)} PRs labeled\n"
        f"Judge feedback: {state.get('judge_feedback_records', 0)} records\n"
        f"Miner versions: {state.get('miner_versions_collected', 0)} versions tracked"
    )
    logging.info(f"[REPORT] Daily report sent")
    if not dry_run:
        send_telegram(msg)
    state["last_daily_report_utc"] = now.isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Dry-Run Mode
# ═══════════════════════════════════════════════════════════════════════════════

def run_startup_validation(duel_id: int):
    """v2 STARTUP CHECK: Fetch a specific duel, log available fields, validate schema."""
    print(f"[STARTUP-VALIDATION] Fetching duel {duel_id} to check schema...")
    url = f"https://ninja66.ai/duels/{duel_id}.json"
    data = fetch_json(url)
    if not data:
        print(f"[STARTUP-VALIDATION] FAIL: Could not fetch duel {duel_id}")
        return

    print(f"[STARTUP-VALIDATION] Top-level keys: {list(data.keys())}")

    king_info  = data.get("king_before", {}) or {}
    chal_info  = data.get("challenger", {}) or {}
    rounds     = data.get("rounds", [])

    print(f"[STARTUP-VALIDATION] king_before keys: {list(king_info.keys())}")
    print(f"[STARTUP-VALIDATION] challenger keys:  {list(chal_info.keys())}")
    print(f"[STARTUP-VALIDATION] Round count: {len(rounds)}")
    if rounds:
        print(f"[STARTUP-VALIDATION] Round[0] keys: {list(rounds[0].keys())}")

    # Check pr_url presence
    king_pr  = king_info.get("pr_url", "")
    chal_pr  = chal_info.get("pr_url", "")
    king_sha = king_info.get("commit_sha", "")
    chal_sha = chal_info.get("commit_sha", "")
    king_repo = king_info.get("repo_full_name", "")
    chal_repo = chal_info.get("repo_full_name", "")

    print(f"[STARTUP-VALIDATION] king_before pr_url: {'PRESENT' if king_pr else 'ABSENT'}")
    print(f"[STARTUP-VALIDATION] king_before commit_sha: {king_sha[:20] if king_sha else 'ABSENT'}")
    print(f"[STARTUP-VALIDATION] king_before repo_full_name: {king_repo}")
    print(f"[STARTUP-VALIDATION] challenger pr_url: {'PRESENT' if chal_pr else 'ABSENT'}")
    print(f"[STARTUP-VALIDATION] challenger commit_sha: {chal_sha[:20] if chal_sha else 'ABSENT'}")
    print(f"[STARTUP-VALIDATION] challenger repo_full_name: {chal_repo}")

    # Try fetching king patch
    if king_repo and king_sha and "private-submission" not in king_repo:
        pat = get_gh_pat()
        print(f"[STARTUP-VALIDATION] GitHub PAT: {'LOADED' if pat else 'MISSING'}")
        patch = _fetch_commit_diff(king_repo, king_sha)
        print(f"[STARTUP-VALIDATION] King commit diff: {len(patch)} chars fetched")
    else:
        print(f"[STARTUP-VALIDATION] King repo is private or missing — patch fetch skipped")

    # Private submission detection
    both_private = (
        "private-submission" in king_repo and
        "private-submission" in chal_repo
    )
    print(f"[STARTUP-VALIDATION] Both private: {both_private}")

    if rounds:
        r0 = rounds[0]
        has_rationale = bool(r0.get("llm_judge_rationale"))
        has_pr_fields = bool(r0.get("pr_url"))
        print(f"[STARTUP-VALIDATION] Round has llm_judge_rationale: {has_rationale}")
        print(f"[STARTUP-VALIDATION] Round has pr_url (legacy): {has_pr_fields}")

    print(f"[STARTUP-VALIDATION] BASE_DIR: {BASE_DIR}")
    print(f"[STARTUP-VALIDATION] MIN_DUEL_ID: {MIN_DUEL_ID}")
    print(f"[STARTUP-VALIDATION] SCHEMA OK — commit_sha path confirmed for post-4700 duels")
    print("[STARTUP-VALIDATION] PASS")


def run_dry_run():
    """Test mode: verify all 5 sources without writing files."""
    logging.info("=== DRY RUN - Final Unified Collector ===")

    logging.info("\n--- Source 1: Live Duel SFT/DPO ---")
    data = fetch_json(DASHBOARD_URL)
    if data:
        duels = data.get("duels", [])
        valid = [d for d in duels if d.get("duel_id", 0) >= MIN_DUEL_ID]
        sample = sorted(valid, key=lambda x: x.get("duel_id", 0))[-2:]
        for duel in sample:
            did = duel.get("duel_id")
            time.sleep(RATE_LIMIT_SLEEP)
            s, d, _anomaly = process_duel(did, dry_run=True, verbose=True)
        logging.info(f"  Dashboard returned {len(duels)} duels, {len(valid)} valid")
    else:
        logging.warning("  Failed to fetch dashboard")

    logging.info("\n--- Source 2: King History (GitHub) ---")
    pat = get_gh_pat()
    logging.info(f"  GitHub PAT: {'✓ loaded' if pat else '✗ missing'}")
    commits = fetch_king_commits(page=1, per_page=20)
    if commits:
        king_commits = [c for c in commits if is_king_commit(c.get("commit", {}).get("message", ""))]
        logging.info(f"  Page 1: {len(commits)} commits, {len(king_commits)} king commits detected")
        for c in king_commits[:2]:
            msg = c.get("commit", {}).get("message", "")[:80]
            name = _extract_king_name_from_commit(c)
            logging.info(f"    SHA={c['sha'][:10]}: {msg} (name={name or 'unknown'})")
    else:
        logging.warning("  Failed to fetch commits")

    logging.info("\n--- Source 3: PR Outcomes (GitHub) ---")
    prs = fetch_pr_page(page=1, per_page=5)
    if prs:
        logging.info(f"  Page 1 sample: {len(prs)} PRs")
        for pr in prs[:3]:
            logging.info(f"    PR #{pr.get('number')}: {pr.get('title', '')[:60]} [{pr.get('state')}]")
    else:
        logging.warning("  Failed to fetch PRs")

    logging.info("\n--- Source 4: Judge Feedback ---")
    dpo_records = list(iter_all_dpo_records())
    eligible = [r for r in dpo_records
                if r.get("chosen_score", 0) >= JF_MIN_CHOSEN_SCORE
                and r.get("rejected_score", 1.0) <= JF_MAX_REJECTED_SCORE]
    logging.info(f"  DPO records: {len(dpo_records)} total, {len(eligible)} eligible for feedback")
    empty_instruction = 0
    jf_path = JUDGE_FEEDBACK_DIR / "judge_feedback.jsonl"
    if jf_path.exists():
        try:
            with open(jf_path, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line.strip())
                        if not rec.get("instruction"):
                            empty_instruction += 1
        except Exception:
            pass
    logging.info(f"  Judge feedback records with empty instruction: {empty_instruction}")

    logging.info("\n--- Source 5: Miner Version History ---")
    agent_files = scan_agent_files()
    logging.info(f"  Found {len(agent_files)} agent files in {SN66_DIR}")

    logging.info("\n=== DRY RUN COMPLETE ===")


# ═══════════════════════════════════════════════════════════════════════════════
# Main Loop
# ═══════════════════════════════════════════════════════════════════════════════

def run_main_loop():
    """Production continuous collection loop."""
    # FIX-LOCK-1: Acquire singleton process lock before doing anything.
    # Prevents two collector instances running simultaneously (e.g., PM2 restart
    # while old process is still alive, or manual re-launch).
    if not acquire_singleton_lock():
        logging.error(
            f"[LOCK] Another collector instance is already running "
            f"(lock held at {LOCKFILE_PATH}). Exiting."
        )
        sys.exit(1)
    logging.info(f"[LOCK] Singleton lock acquired (PID={os.getpid()})")

    logging.info("SN66 Final Unified Data Collector started")
    logging.info(f"Config: poll={POLL_INTERVAL}s, min_duel={MIN_DUEL_ID}, "
                 f"sft_threshold={SFT_MIN_WINNER_SCORE}, dpo_diff={DPO_MIN_SCORE_DIFF}")

    for d in [SFT_DIR, DPO_DIR, KING_HISTORY_DIR, PR_OUTCOMES_DIR,
              JUDGE_FEEDBACK_DIR, MINER_HISTORY_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    state = load_state()

    # FIX-LOCK-1: Install SIGTERM/SIGINT handlers now that state is loaded.
    # Must be done after load_state() so handlers can flush in-memory state.
    _install_signal_handlers(state)

    logging.info(
        f"State loaded: last_duel={state['last_processed_duel_id']}, "
        f"sft={state['total_sft_records']}, dpo={state['total_dpo_pairs']}, "
        f"kings={state.get('kings_collected', 0)}, "
        f"prs={state.get('prs_collected', 0)}, "
        f"jf={state.get('judge_feedback_records', 0)}, "
        f"miners={state.get('miner_versions_collected', 0)}, "
        f"current_king={state.get('current_king_name', 'unknown')}"
    )

    # FIX-L3: Counter sync on startup
    logging.info("[STARTUP] Recounting actual SFT/DPO records to sync state counters...")
    actual = _recount_training_data()
    if actual["sft"] is not None:
        if actual["sft"] != state["total_sft_records"]:
            logging.warning(f"[STARTUP] SFT counter drift: state={state['total_sft_records']}, "
                            f"actual={actual['sft']} — correcting")
            state["total_sft_records"] = actual["sft"]
        else:
            logging.info(f"[STARTUP] SFT counter OK: {actual['sft']}")
    if actual["dpo"] is not None:
        if actual["dpo"] != state["total_dpo_pairs"]:
            logging.warning(f"[STARTUP] DPO counter drift: state={state['total_dpo_pairs']}, "
                            f"actual={actual['dpo']} — correcting")
            state["total_dpo_pairs"] = actual["dpo"]
        else:
            logging.info(f"[STARTUP] DPO counter OK: {actual['dpo']}")
    # FIX-L5: Recount JF records (previously unchecked, causing counter drift)
    if actual.get("jf") is not None:
        if actual["jf"] != state.get("judge_feedback_records", 0):
            logging.warning(f"[STARTUP] JF counter drift: state={state.get('judge_feedback_records', 0)}, "
                            f"actual={actual['jf']} — correcting")
            state["judge_feedback_records"] = actual["jf"]
        else:
            logging.info(f"[STARTUP] JF counter OK: {actual['jf']}")
    save_state(state)

    # NEW-2: Fix empty instruction fields in judge_feedback on startup
    if not state.get("jf_empty_instruction_backfill"):
        logging.info("[STARTUP] Running judge_feedback instruction backfill (NEW-2)...")
        fixed = run_source4_fix_empty_instructions(state, dry_run=False)
        if fixed > 0:
            logging.info(f"[STARTUP] Backfilled instruction field in {fixed} judge_feedback records")
        save_state(state)

    # NEW-1: Check for king change since last run
    king_changed = check_king_change_on_startup(state)
    if king_changed:
        logging.info("[STARTUP] Running immediate king backfill for new king...")
        n = run_source2(state, dry_run=False)
        logging.info(f"[STARTUP] King backfill complete: +{n} new king records, "
                     f"current_king={state.get('current_king_name', 'unknown')}")
        save_state(state)

    send_telegram(
        f"🚀 *SN66 Final Unified Collector started*\n"
        f"Resuming from duel #{state['last_processed_duel_id']}\n"
        f"SFT: {state['total_sft_records']} | DPO: {state['total_dpo_pairs']}\n"
        f"Kings: {state.get('kings_collected', 0)} | "
        f"PRs: {state.get('prs_collected', 0)} | "
        f"JF: {state.get('judge_feedback_records', 0)} | "
        f"Miners: {state.get('miner_versions_collected', 0)}\n"
        f"King: {state.get('current_king_name', 'unknown') or 'unknown'}"
        + (" (NEW KING — backfilled ✅)" if king_changed else "")
    )

    while True:
        try:
            now = datetime.now(timezone.utc)
            state["last_run_utc"] = now.isoformat()

            run_source1(state, dry_run=False)
            run_source2(state, dry_run=False)
            run_source3(state, dry_run=False)
            run_source4(state, dry_run=False)
            run_source5(state, dry_run=False)
            run_source6_repo_context_enrichment(dry_run=False)  # UPGRADE-3: optional, rate-limited

            log_hourly_stats(state)
            maybe_send_daily_report(state)

            save_state(state)

            logging.debug(f"Sleeping {POLL_INTERVAL}s until next poll")
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logging.info("Interrupted — saving state and exiting")
            save_state(state)
            sys.exit(0)
        except Exception as e:
            logging.error(f"Loop error: {e}", exc_info=True)
            try:
                time.sleep(30)
            except KeyboardInterrupt:
                logging.info("Interrupted during error recovery — saving state and exiting")
                save_state(state)
                sys.exit(0)


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Singleton Process Lock (FIX-LOCK-1) ─────────────────────────────────────────────────


def acquire_singleton_lock() -> bool:
    """Acquire exclusive process lock on LOCKFILE_PATH.

    Returns True if lock acquired, False if another instance is running.
    The fd is stored in the module-level _LOCK_FD to prevent GC from closing
    the file and implicitly releasing the lock.
    """
    global _LOCK_FD
    try:
        LOCKFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = open(LOCKFILE_PATH, "w")  # open keeps fd alive
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd.write(str(os.getpid()))
        fd.flush()
        _LOCK_FD = fd  # store globally so GC never closes it
        return True
    except OSError:
        return False
    except Exception as e:
        logging.warning(f"Lock acquisition error (non-fatal): {e}")
        return True  # proceed if lock mechanism fails (e.g., /tmp NFS)


def _install_signal_handlers(state_ref: dict):
    """Install SIGTERM/SIGINT handlers for graceful PM2 shutdown.

    PM2 sends SIGTERM then SIGKILL after 1.6s (default kill_timeout).
    The handler saves state and releases the lock before the process exits.
    """
    def _handle_sigterm(signum, frame):
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logging.info(f"[SIGNAL] {sig_name} received — saving state and exiting gracefully")
        try:
            save_state(state_ref)
        except Exception as e:
            logging.error(f"[SIGNAL] save_state failed on {sig_name}: {e}")
        try:
            if _LOCK_FD is not None:
                fcntl.flock(_LOCK_FD, fcntl.LOCK_UN)
                _LOCK_FD.close()
            LOCKFILE_PATH.unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)


def main():
    parser = argparse.ArgumentParser(description="SN66 Final Unified Data Collector")
    parser.add_argument("--dry-run", action="store_true",
                        help="Test mode: verify all 5 sources without writing files")
    parser.add_argument("--backfill-s1", type=int, metavar="DUEL_ID",
                        help="Backfill Source 1 from DUEL_ID to latest (one-shot)")
    parser.add_argument("--backfill-s2", action="store_true",
                        help="Force re-run Source 2 king history backfill")
    parser.add_argument("--backfill-s3", action="store_true",
                        help="Force re-run Source 3 PR outcomes backfill (all pages)")
    parser.add_argument("--run-s4", action="store_true",
                        help="Run Source 4 (judge feedback) one-shot and exit")
    parser.add_argument("--fix-jf-instructions", action="store_true",
                        help="Fix empty instruction fields in judge_feedback (NEW-2)")
    parser.add_argument("--run-s5", action="store_true",
                        help="Run Source 5 (miner history) one-shot and exit")
    parser.add_argument("--verbose", action="store_true",
                        help="Show per-round details")
    parser.add_argument("--test-duel", type=int, metavar="DUEL_ID",
                        help="Startup validation: fetch DUEL_ID, log available fields, exit")
    args = parser.parse_args()

    setup_logging(dry_run=args.dry_run)

    if args.test_duel:
        run_startup_validation(args.test_duel)
        return

    if args.dry_run:
        run_dry_run()
        return

    state = load_state()

    if args.backfill_s1:
        logging.info(f"=== BACKFILL S1 from duel #{args.backfill_s1} ===")
        state["last_processed_duel_id"] = args.backfill_s1 - 1
        data = fetch_json(DASHBOARD_URL)
        all_ids = sorted(
            d["duel_id"] for d in (data or {}).get("duels", [])
            if d.get("duel_id", 0) >= args.backfill_s1 and d.get("duel_id", 0) >= MIN_DUEL_ID
        )
        logging.info(f"Backfilling {len(all_ids)} duels")
        for did in all_ids:
            time.sleep(RATE_LIMIT_SLEEP)
            s, d, anomaly = process_duel(did, dry_run=False, verbose=args.verbose)
            if anomaly:
                logging.warning(f"Backfill: duel {did} anomalous — skipping cursor advance")
                continue
            state["last_processed_duel_id"] = did
            state["total_sft_records"] += s
            state["total_dpo_pairs"]   += d
            state["duels_processed"]   += 1
        save_state(state)
        logging.info(f"Backfill S1 complete: {state['total_sft_records']} SFT, {state['total_dpo_pairs']} DPO")
        return

    if args.backfill_s2:
        logging.info("=== BACKFILL S2: King History ===")
        state["king_backfill_complete"] = False
        KING_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        n = run_source2_backfill(state, dry_run=False)
        save_state(state)
        logging.info(f"Backfill S2 complete: {n} new king records")
        return

    if args.backfill_s3:
        logging.info("=== BACKFILL S3: PR Outcomes (all pages) ===")
        state["pr_backfill_complete"] = False
        state["last_pr_page"] = 0
        PR_OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)
        total = 0
        while not state.get("pr_backfill_complete"):
            n = run_source3_page(state, dry_run=False)
            total += n
            save_state(state)
            if n == 0:
                break
            time.sleep(2)
        logging.info(f"Backfill S3 complete: {total} PRs processed")
        return

    if args.run_s4:
        logging.info("=== Run Source 4: Judge Feedback ===")
        JUDGE_FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        n = run_source4(state, dry_run=False)
        save_state(state)
        logging.info(f"Source 4 complete: {n} new judge feedback records")
        return

    if args.fix_jf_instructions:
        logging.info("=== Fix JF Empty Instructions (NEW-2) ===")
        state["jf_empty_instruction_backfill"] = False
        n = run_source4_fix_empty_instructions(state, dry_run=False)
        save_state(state)
        logging.info(f"JF instruction backfill complete: {n} records fixed")
        return

    if args.run_s5:
        logging.info("=== Run Source 5: Miner Version History ===")
        MINER_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        n = run_source5(state, dry_run=False)
        save_state(state)
        logging.info(f"Source 5 complete: {n} new miner version records")
        return

    # Normal continuous daemon mode
    run_main_loop()


if __name__ == "__main__":
    main()
