#!/usr/bin/env python3
"""
SN66 Gap Backfill — Duels 5005 → 5525

One-shot script to backfill missed duels from the collector gap.
Writes SFT + DPO records to /root/sn66-ninja/training_data/live/
in the same format as sn66_live_collector_v2.py.

Rate: 2 req/sec for duel fetches, 0.5s for GitHub commit diffs.
Skips duels already in state.json seen-set.
Private-submission repos: skip patch, still write metadata + judge_rationale.
King patches (unarbos/ninja): fetch via commit_sha.

Usage:
    nohup python3 sn66_backfill_5005_5525.py > /tmp/sn66_backfill.log 2>&1 &
"""

import json
import logging
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
BACKFILL_START   = 5005
BACKFILL_END     = 5525
BASE_DIR         = Path("/root/sn66-ninja/training_data/live")
SFT_DIR          = BASE_DIR / "sft"
DPO_DIR          = BASE_DIR / "dpo"
STATE_FILE       = BASE_DIR / "state.json"
LOG_FILE         = Path("/tmp/sn66_backfill.log")

DUEL_URL         = "https://ninja66.ai/duels/{duel_id}.json"
GH_API_BASE      = "https://api.github.com/repos"
SECRETS_FILE     = Path("/root/.secrets/api_keys.env")

# Rate limiting
DUEL_RATE_SLEEP  = 0.5      # 2 req/sec for duel fetches
GH_DIFF_SLEEP    = 0.5      # 2 req/sec for GitHub diffs
REQUEST_TIMEOUT  = 30

# Quality thresholds (match collector)
SFT_MIN_WINNER_SCORE = 0.6
DPO_MIN_SCORE_DIFF   = 0.15

SKIP_EXIT_REASONS = {"solver_error", "timeout", "too_long", "validation_error"}

LOG_EVERY = 50   # print progress every N duels

# In-memory diff cache (keyed by sha[:12])
_DIFF_CACHE: dict = {}

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("backfill")


# ─────────────────────────────────────────────────────────────
# Secrets
# ─────────────────────────────────────────────────────────────
def _load_secret(key: str) -> Optional[str]:
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
    return (
        _load_secret("BACKUP_GH_PAT_PRIMARY")
        or _load_secret("BACKUP_GH_PAT_SECONDARY")
        or _load_secret("GH_PAT")
        or _load_secret("GITHUB_PAT")
    )


# ─────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────
def fetch_json(url: str, headers: dict = None, retries: int = 3) -> Optional[dict]:
    hdrs = {"User-Agent": "SN66-Backfill/1.0", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 or e.code >= 500:
                wait = 10 * (attempt + 1)
                log.warning(f"HTTP {e.code} on {url} — retrying in {wait}s")
                time.sleep(wait)
            else:
                log.warning(f"HTTP {e.code} on {url}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                log.warning(f"fetch_json error {url}: {e}")
    return None


def _fetch_commit_diff(repo_full_name: str, commit_sha: str) -> str:
    """Fetch unified diff for a commit. Private repos return ''."""
    if not commit_sha or not repo_full_name:
        return ""
    if "private-submission" in repo_full_name:
        return ""

    cache_key = commit_sha[:12]
    if cache_key in _DIFF_CACHE:
        return _DIFF_CACHE[cache_key]

    time.sleep(GH_DIFF_SLEEP)

    api_url = f"{GH_API_BASE}/{repo_full_name}/commits/{commit_sha}"
    pat = get_gh_pat()
    hdrs = {
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "SN66-Backfill/1.0",
    }
    if pat:
        hdrs["Authorization"] = f"token {pat}"

    diff_text = ""
    try:
        req = urllib.request.Request(api_url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            diff_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code not in (404, 422):
            log.debug(f"commit diff HTTP {e.code}: {repo_full_name}@{commit_sha[:12]}")
    except Exception as e:
        log.debug(f"commit diff error: {repo_full_name}@{commit_sha[:12]}: {e}")

    if len(diff_text) > 50_000:
        diff_text = diff_text[:50_000] + "\n... (truncated at 50KB)"

    _DIFF_CACHE[cache_key] = diff_text
    return diff_text


def _get_best_patch(info: dict) -> str:
    """Get best available patch: commit_sha diff first (post-4700), skip private."""
    repo = info.get("repo_full_name", "")
    sha  = info.get("commit_sha", "")
    if repo and sha and "private-submission" not in repo:
        patch = _fetch_commit_diff(repo, sha)
        if patch:
            return patch
    return ""


# ─────────────────────────────────────────────────────────────
# Task type classification (mirrors collector)
# ─────────────────────────────────────────────────────────────
def classify_task_type(text: str) -> str:
    text_lower = text.lower()
    if any(k in text_lower for k in ("bug", "fix", "error", "crash", "fail", "broken")):
        return "BUGFIX"
    if any(k in text_lower for k in ("add feature", "implement", "new feature", "create")):
        return "FEATURE"
    if any(k in text_lower for k in ("update", "upgrade", "refactor", "improve", "enhance")):
        return "UPDATE"
    if any(k in text_lower for k in ("api", "endpoint", "rest", "graphql", "webhook")):
        return "API"
    return "OTHER"


# ─────────────────────────────────────────────────────────────
# State: load seen duel IDs
# ─────────────────────────────────────────────────────────────
def load_seen_ids() -> set:
    """Return set of duel IDs already in state.json (last_processed_duel_id cursor)."""
    if not STATE_FILE.exists():
        return set()
    try:
        s = json.loads(STATE_FILE.read_text())
        # Everything up to and including last_processed_duel_id was collected
        last = s.get("last_processed_duel_id", 0)
        return set(range(BACKFILL_START, last + 1))
    except Exception:
        return set()


def load_existing_ids(path: Path) -> set:
    """Load IDs from an existing JSONL file to avoid duplicates."""
    ids = set()
    if not path.exists():
        return ids
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        if "id" in rec:
                            ids.add(rec["id"])
                    except Exception:
                        pass
    except Exception:
        pass
    return ids


def today_path(directory: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return directory / f"{today}.jsonl"


def append_jsonl(path: Path, record: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────
# Record builders (mirrors collector logic)
# ─────────────────────────────────────────────────────────────
def get_winner_loser(round_data: dict):
    winner = round_data.get("winner", "")
    king_score = round_data.get("king_llm_score") or round_data.get("king_score") or 0.0
    chal_score = round_data.get("challenger_llm_score") or round_data.get("challenger_score") or 0.0
    if winner == "king":
        return "king", "challenger", float(king_score), float(chal_score)
    elif winner == "challenger":
        return "challenger", "king", float(chal_score), float(king_score)
    return winner, winner, float(king_score), float(chal_score)


def build_sft(duel_id: int, round_idx: int, rnd: dict, duel_data: dict, now_utc: str) -> Optional[dict]:
    winner_label, _, winner_score, loser_score = get_winner_loser(rnd)
    if winner_score < SFT_MIN_WINNER_SCORE:
        return None
    if winner_label not in ("king", "challenger"):
        return None

    king_info = duel_data.get("king_before", {}) or {}
    chal_info = duel_data.get("challenger", {}) or {}
    winner_info = king_info if winner_label == "king" else chal_info

    task_name       = rnd.get("task_name", "")
    judge_rationale = rnd.get("llm_judge_rationale", "")
    judge_model     = rnd.get("llm_judge_model", "")
    type_text       = " ".join(filter(None, [task_name, judge_rationale[:200] if judge_rationale else ""]))
    task_type       = classify_task_type(type_text)

    winner_patch = _get_best_patch(winner_info)

    return {
        "id":              f"sn66_sft_duel{duel_id}_r{round_idx}",
        "source":          "live_duel_backfill",
        "task_name":       task_name,
        "task_title":      "",
        "task_summary":    judge_rationale[:500] if judge_rationale else "",
        "task_type":       task_type,
        "instruction":     task_name,
        "output":          winner_patch,
        "winner":          winner_label,
        "judge_score":     round(winner_score, 4),
        "loser_score":     round(loser_score, 4),
        "judge_rationale": judge_rationale,
        "judge_model":     judge_model,
        "judge_weight":    rnd.get("llm_judge_weight"),
        "judge_error":     rnd.get("llm_judge_error", ""),
        "winner_repo":     winner_info.get("repo_full_name", ""),
        "winner_sha":      winner_info.get("commit_sha", ""),
        "winner_source":   winner_info.get("source", ""),
        "winner_username": winner_info.get("agent_username", ""),
        "winner_patch":    winner_patch,
        "king_llm_score":  round(float(rnd.get("king_llm_score") or rnd.get("king_score") or 0), 4),
        "challenger_llm_score": round(float(rnd.get("challenger_llm_score") or rnd.get("challenger_score") or 0), 4),
        "king_lines":      rnd.get("king_lines", 0),
        "challenger_lines": rnd.get("challenger_lines", 0),
        "king_exit_reason":       rnd.get("king_exit_reason", ""),
        "challenger_exit_reason": rnd.get("challenger_exit_reason", ""),
        "duel_id":         duel_id,
        "round_idx":       round_idx,
        "collected_at":    now_utc,
    }


def build_dpo(duel_id: int, round_idx: int, rnd: dict, duel_data: dict, now_utc: str) -> Optional[dict]:
    winner_label, loser_label, winner_score, loser_score = get_winner_loser(rnd)
    if winner_label not in ("king", "challenger"):
        return None

    score_diff = winner_score - loser_score
    if abs(score_diff) < DPO_MIN_SCORE_DIFF:
        return None

    king_info = duel_data.get("king_before", {}) or {}
    chal_info = duel_data.get("challenger", {}) or {}
    chosen_info   = king_info if winner_label == "king" else chal_info
    rejected_info = chal_info if winner_label == "king" else king_info

    task_name       = rnd.get("task_name", "")
    judge_rationale = rnd.get("llm_judge_rationale", "")
    judge_model     = rnd.get("llm_judge_model", "")
    type_text       = " ".join(filter(None, [task_name, judge_rationale[:200] if judge_rationale else ""]))
    task_type       = classify_task_type(type_text)

    chosen_patch   = _get_best_patch(chosen_info)
    rejected_patch = _get_best_patch(rejected_info)

    return {
        "id":               f"sn66_dpo_duel{duel_id}_r{round_idx}",
        "source":           "live_duel_backfill",
        "task_name":        task_name,
        "task_title":       "",
        "task_summary":     judge_rationale[:500] if judge_rationale else "",
        "task_type":        task_type,
        "instruction":      task_name,
        "chosen_patch":     chosen_patch,
        "rejected_patch":   rejected_patch,
        "winner":           winner_label,
        "loser":            loser_label,
        "chosen_score":     round(winner_score, 4),
        "rejected_score":   round(loser_score, 4),
        "score_diff":       round(score_diff, 4),
        "judge_rationale":  judge_rationale,
        "judge_model":      judge_model,
        "judge_weight":     rnd.get("llm_judge_weight"),
        "judge_error":      rnd.get("llm_judge_error", ""),
        "chosen_repo":      chosen_info.get("repo_full_name", ""),
        "chosen_sha":       chosen_info.get("commit_sha", ""),
        "chosen_source":    chosen_info.get("source", ""),
        "chosen_username":  chosen_info.get("agent_username", ""),
        "rejected_repo":    rejected_info.get("repo_full_name", ""),
        "rejected_sha":     rejected_info.get("commit_sha", ""),
        "rejected_source":  rejected_info.get("source", ""),
        "rejected_username": rejected_info.get("agent_username", ""),
        "king_llm_score":   round(float(rnd.get("king_llm_score") or rnd.get("king_score") or 0), 4),
        "challenger_llm_score": round(float(rnd.get("challenger_llm_score") or rnd.get("challenger_score") or 0), 4),
        "king_exit_reason":       rnd.get("king_exit_reason", ""),
        "challenger_exit_reason": rnd.get("challenger_exit_reason", ""),
        "duel_id":          duel_id,
        "round_idx":        round_idx,
        "collected_at":     now_utc,
    }


# ─────────────────────────────────────────────────────────────
# Per-duel processor
# ─────────────────────────────────────────────────────────────
def process_one_duel(duel_id: int, sft_seen: set, dpo_seen: set,
                     sft_path: Path, dpo_path: Path) -> tuple:
    """Fetch and process one duel. Returns (sft_written, dpo_written, skipped_rounds)."""
    url = DUEL_URL.format(duel_id=duel_id)
    duel_data = fetch_json(url)
    if duel_data is None:
        log.warning(f"Duel {duel_id}: fetch failed — skipping")
        return 0, 0, 0

    rounds = duel_data.get("rounds", [])
    if not rounds:
        log.debug(f"Duel {duel_id}: no rounds")
        return 0, 0, 0

    now_utc   = datetime.now(timezone.utc).isoformat()
    sft_n     = 0
    dpo_n     = 0
    skipped   = 0

    for idx, rnd in enumerate(rounds):
        exit_reason = rnd.get("challenger_exit_reason", "")
        if exit_reason in SKIP_EXIT_REASONS:
            skipped += 1
            continue
        winner = rnd.get("winner", "")
        if winner in ("tie", ""):
            skipped += 1
            continue

        sft_rec = build_sft(duel_id, idx, rnd, duel_data, now_utc)
        if sft_rec and sft_rec["id"] not in sft_seen:
            append_jsonl(sft_path, sft_rec)
            sft_seen.add(sft_rec["id"])
            sft_n += 1

        dpo_rec = build_dpo(duel_id, idx, rnd, duel_data, now_utc)
        if dpo_rec and dpo_rec["id"] not in dpo_seen:
            append_jsonl(dpo_path, dpo_rec)
            dpo_seen.add(dpo_rec["id"])
            dpo_n += 1

    return sft_n, dpo_n, skipped


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    log.info(f"=== SN66 Gap Backfill: duels {BACKFILL_START}→{BACKFILL_END} ===")
    log.info(f"BASE_DIR: {BASE_DIR}")

    # Ensure dirs exist
    for d in [SFT_DIR, DPO_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Load existing IDs already in today's JSONL to avoid duplicates
    sft_path = today_path(SFT_DIR)
    dpo_path = today_path(DPO_DIR)
    sft_seen = load_existing_ids(sft_path)
    dpo_seen = load_existing_ids(dpo_path)
    log.info(f"Existing today: {len(sft_seen)} SFT IDs, {len(dpo_seen)} DPO IDs in today's files")

    # Load state.json to detect already-processed duels
    already_done = load_seen_ids()
    log.info(f"State cursor covers up to {max(already_done) if already_done else 'none'}")

    # Build duel list
    all_duels = list(range(BACKFILL_START, BACKFILL_END + 1))
    to_process = [d for d in all_duels if d not in already_done]
    skipped_by_state = len(all_duels) - len(to_process)
    log.info(f"Total gap: {len(all_duels)} duels | "
             f"Already in state: {skipped_by_state} | "
             f"To backfill: {len(to_process)}")

    if not to_process:
        log.info("All duels already covered by state.json — nothing to do.")
        return

    pat = get_gh_pat()
    log.info(f"GitHub PAT: {'LOADED' if pat else 'MISSING (unauthenticated mode)'}")

    total_sft    = 0
    total_dpo    = 0
    total_skip   = 0
    failed       = 0
    processed    = 0
    t_start      = time.monotonic()

    for duel_id in to_process:
        try:
            time.sleep(DUEL_RATE_SLEEP)
            sft_n, dpo_n, skip_n = process_one_duel(
                duel_id, sft_seen, dpo_seen, sft_path, dpo_path
            )
            total_sft  += sft_n
            total_dpo  += dpo_n
            total_skip += skip_n
            processed  += 1

            if processed % LOG_EVERY == 0:
                elapsed   = time.monotonic() - t_start
                remaining = len(to_process) - processed
                rate      = processed / elapsed if elapsed > 0 else 0
                eta_s     = remaining / rate if rate > 0 else 0
                eta_m     = int(eta_s // 60)
                log.info(
                    f"[PROGRESS] {processed}/{len(to_process)} duels done "
                    f"(duel {duel_id}) | "
                    f"+{total_sft} SFT, +{total_dpo} DPO | "
                    f"rate={rate:.1f}/s | ETA ~{eta_m}m"
                )

        except Exception as e:
            log.error(f"Duel {duel_id}: unexpected error — skipping: {e}", exc_info=True)
            failed += 1
            continue

    elapsed = time.monotonic() - t_start
    log.info("=" * 60)
    log.info(f"BACKFILL COMPLETE")
    log.info(f"  Duels processed : {processed}/{len(to_process)}")
    log.info(f"  Failed          : {failed}")
    log.info(f"  SFT records     : {total_sft}")
    log.info(f"  DPO pairs       : {total_dpo}")
    log.info(f"  Rounds skipped  : {total_skip}")
    log.info(f"  Elapsed         : {int(elapsed)}s ({int(elapsed/60)}m)")
    log.info(f"  Output          : {sft_path}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
