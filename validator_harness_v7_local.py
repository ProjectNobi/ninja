#!/usr/bin/env python3
"""
validator_harness_v7_local.py — SN66 Ninja LOCAL Duel Harness v7  (R2 Synthetic Repos)

═══════════════════════════════════════════════════════════════════════════════
IDENTITY: This is validator_harness_v7_local.py — the LOCAL duel harness.
  It is NOT validator_harness_v7_upstream.py. Key differences from upstream v7:
    • Judge model:  qwen3-32b-v7-judge (local vLLM @ :8002) — trained on the
                    Opus 4-criteria rubric (JUDGE_PROMPT_OPUS below).
    • Scoring:      LLM-only, independent 0-100 per patch (cursor_sim = telemetry).
    • Repos:        synthetic, built locally from R2 reference-patch context lines
                    (NO GitHub clone). Upstream uses the same R2 reference patches.
    • Prompt shape: single .format() string template (issue/reference_patch/
                    patch_a/patch_b), vs upstream's live content-array builder.

v7_local FIXES (2026-06-07, OPUS_V74_DEEP_AUDIT):
  • FIX 1  reference patch now passed to the judge as privileged context
           (was: never passed → judge defaulted both patches to 0/0 → false TIEs).
  • FIX 2  blind A/B is now SHA256-deterministic — SHA256(task:challenger:model)%2 —
           matching the live validator (validate_live_reference.py:1800-1804),
           replacing the non-reproducible random.random()<0.5 (v6 FIX 8).
  • FIX 3  dropped the absolute "patch that cannot apply = INSTANT FAIL" clause:
           on R2 synthetic repos patches genuinely cannot be test-applied (file
           stubs only), so the clause produced false-zero scores on valid patches.
  • FIX 4  this header / identity block.
═══════════════════════════════════════════════════════════════════════════════

Legacy v6 history (R2 Synthetic Repos)

HARNESS v6 UPDATE 2026-05-19:
  - JUDGE_MODEL: anthropic/claude-sonnet-4.6 via OpenRouter (PR#1598 — LLM-only scoring)
  - Scoring: LLM-only (cursor_sim is telemetry; does NOT affect winner)
  - Submission flow: direct API POST to ninja66.ai/api/submissions (no on-chain commit)
  - Submit: ./scripts/submit_private_submission.py --wallet-name T68Coldkey --wallet-hotkey HK --agent agent.py
  - Test with claude judge: python3 validator_harness_v6.py --challenger agent.py --judge-model anthropic/claude-opus-4-6

Changes from v5:
  - FIX 1: AGENT_TIMEOUT raised 120→300s (default); --timeout CLI flag added
  - FIX 2: LLM judge now scores independently (0-100 each) matching live validator behavior
  - FIX 3: King staleness warning + live king info at startup
  - FIX 4: Version header
  - FIX 5: --judge-model CLI flag; JUDGE_PROMPT_OPUS for claude-opus-4.7 judge
  - FIX 6: challenger-specific API key/base support
  - FIX 7: dual-judge support (model1|model2 syntax)
  - FIX 8 (2026-05-19): LLM-only scoring per PR#1598; judge updated to claude-sonnet-4.6

Key features:
  • Uses R2 dataset (hf_dataset_cache.jsonl, 9,122 records) instead of SWEbench
  • NO git cloning from GitHub — repos are built locally from patch context lines
  • cursor_sim = LCS(agent_patch, R2_reference_patch) / max_lines  (telemetry only)
    — EXACT same reference patches as the live validator
  • Judge window: 60,000 chars per patch (matches live validator _DIFF_JUDGE_MAX_PATCH_CHARS)
  • Language distribution matches live validator (40% TS, 19% Py, ~19% JS, …)
  • Synthetic repos created in seconds (no network, just file writes)
  • Uses anthropic/claude-sonnet-4.6 as duel judge (PR#1598 _DIFF_JUDGE_MODEL)
  • LLM judge returns independent quality scores (0-100 each), matching live validator behavior

Scoring formula (UPDATED 2026-05-19 per PR#1598 — LLM-only scoring):
  combined = 1.0 × llm_score  (cursor_sim is telemetry only, no longer contributes)
  decisive_win_rate   = wins / (wins + losses)  [ties excluded]
  win_margin = 3 live (CLI override: validator runs with --win-margin 3, code default=0)
  Judge: anthropic/claude-sonnet-4.6 via OpenRouter (was openai/gpt-5.4)

Usage:
  python3 validator_harness_v6.py --lcs-test
  python3 validator_harness_v6.py --list-tasks 5
  python3 validator_harness_v6.py --test-repo
  python3 validator_harness_v6.py --challenger agent_t68_v18.py --tasks 20
  python3 validator_harness_v6.py --challenger agent_t68_v18.py --tasks 20 --parallel 3 --timeout 300
  python3 validator_harness_v6.py --challenger agent_t68_v18.py --tasks 20 --king-sha abc123def456
  python3 validator_harness_v6.py --challenger agent_t68_v18.py --tasks 20 --judge-model anthropic/claude-opus-4.7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Constants ──────────────────────────────────────────────────────────────────
SECRETS_FILE    = os.path.expanduser("~/.secrets/api_keys.env")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
JUDGE_MODEL     = "anthropic/claude-sonnet-4.6"                    # UPDATED 2026-05-19: PR#1598 _DIFF_JUDGE_MODEL changed to claude-sonnet-4.6 via OpenRouter (LLM-only scoring)
JUDGE_MODEL_FALLBACK = "moonshotai/kimi-k2.6"                       # UPDATED 2026-05-19: fallback when Sonnet returns no-choices error (per PR#1598)
JUDGE_TEMPERATURE = 0.0                           # deterministic — matches live validator
AGENT_MODEL     = "minimax/minimax-m2.7"         # Updated 2026-05-07: SN66 team confirmed live miner model

# ── Opus 4.7 judge prompt (FIX 5) ─────────────────────────────────────────────
# Used when --judge-model is an Opus/Claude model. Scores each patch independently
# using Opus's own rubric (root cause, scope, acceptance criteria, correctness).
# Based on: research/OPUS_SELF_AS_JUDGE_SN66.md
JUDGE_PROMPT_OPUS = (
    "You are an expert code reviewer scoring two git patches that attempt to fix "
    "the same programming issue.\n"
    "Score each patch INDEPENDENTLY on a scale of 0-100 using the rubric below.\n"
    "Do NOT compare the patches to each other \u2014 evaluate each against the issue.\n\n"
    "Issue:\n{issue}\n\n"
    "REFERENCE PATCH (privileged context — the known-good fix direction; "
    "it is NOT a candidate, do not score it):\n```\n{reference_patch}\n```\n\n"
    "PATCH A:\n```\n{patch_a}\n```\n\n"
    "PATCH B:\n```\n{patch_b}\n```\n\n"
    "## SCORING RUBRIC (total: 100 points)\n\n"
    "**Root Cause Resolution (0-40 pts)**\n"
    "- 40 pts: Fixes the actual root cause (traces bug to source, not symptom); "
    "minimal correct change\n"
    "- 30 pts: Fixes the main cause but misses one related location or caller\n"
    "- 20 pts: Fixes a symptom (null-check/guard) rather than the underlying cause\n"
    "- 0-10 pts: Modifies wrong code, makes things worse, or outputs nothing\n\n"
    "**Scope Completeness (0-30 pts)**\n"
    "- 30 pts: All files that need changing are changed; TypeScript type cascades "
    "fully followed\n"
    "- 20 pts: Main file correct but one related file/function/caller missed\n"
    "- 10 pts: Right area but only partially addressed; cascades/helpers not updated\n"
    "- 0 pts: Wrong files entirely, or only one of many required changes made\n\n"
    "**Acceptance Criteria Coverage (0-20 pts)**\n"
    "- 20 pts: Every failure case and edge case mentioned in the issue is handled\n"
    "- 15 pts: Main case handled, one explicitly listed edge case missed\n"
    "- 5-10 pts: Only the happy path fixed; error paths or listed edge cases ignored\n"
    "- 0 pts: Issue acceptance criteria ignored entirely\n\n"
    "**Code Correctness & Quality (0-10 pts)**\n"
    "- 10 pts: Syntactically valid, no stubs/TODOs left, follows codebase conventions, "
    "no regressions\n"
    "- 5 pts: Mostly correct but minor issues (off-by-one, wrong type, style breaks)\n"
    "- 0 pts: Syntax errors, hallucinated APIs, stubs/TODOs left, or obvious regressions\n\n"
    "## INSTANT FAIL (score = 0)\n"
    "Empty patch, syntactically invalid code, or a patch that makes the bug "
    "worse. NOTE: these are synthetic repos (file stubs only), so a patch "
    "cannot be test-applied here \u2014 do NOT zero a patch merely because it "
    "cannot be verified as applicable; score it on direction and completeness "
    "relative to the issue and the reference patch.\n\n"
    'CRITICAL OUTPUT RULES: Output ONLY a single-line JSON object. '
    'Do NOT output any diff, code, patch text, markdown fences, or '
    'explanation outside the JSON. Do NOT repeat the patches. '
    'Format exactly:\n'
    '{{"score_a": <int 0-100>, "score_b": <int 0-100>, '
    '"reasoning": "<one sentence explaining the key difference>"}}'
)

DATASET_PATH    = os.environ.get("SN66_DATASET_PATH", os.path.expanduser("~/sn66-r2-dataset/hf_dataset_cache.jsonl"))  # hf_dataset used
REPO_CACHE_DIR  = "/tmp/sn66_r2_repos"
AGENT_TIMEOUT   = 600        # Updated 2026-05-07: max live timeout is 600s (gemini_elapsed*2+1, cap 600)
MAX_TASKS       = 10000
DEFAULT_TASKS   = 20
DEFAULT_PARALLEL = 2
DEFAULT_MAX_STEPS = 18  # v1: raised from 8 -- Set 1 data showed 44% of losses from step exhaustion

AGENT_DIR  = Path(__file__).parent
PRINT_LOCK = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# 1. LCS CURSOR SIMILARITY  (identical to live validator formula)
# ══════════════════════════════════════════════════════════════════════════════

def extract_diff_lines(patch: str) -> List[str]:
    """
    Extract only +/- code change lines from a unified diff.
    Excludes diff headers (+++/---), @@ hunks, and context lines.
    Returns stripped line content (without leading +/- character).
    """
    lines = []
    for line in patch.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:].rstrip())
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(line[1:].rstrip())
    return lines


def _lcs_length(a: List[str], b: List[str]) -> int:
    """DP LCS length with rolling-array optimisation. Truncates at 1500 lines."""
    if not a or not b:
        return 0
    a = a[:1500]
    b = b[:1500]
    n, m = len(a), len(b)
    prev = [0] * (m + 1)
    for ai in a:
        curr = [0] * (m + 1)
        for j, bj in enumerate(b, 1):
            curr[j] = prev[j - 1] + 1 if ai == bj else max(curr[j - 1], prev[j])
        prev = curr
    return prev[m]


def compute_lcs_similarity(patch_a: str, patch_b: str) -> float:
    """
    LCS similarity between two unified diff patches.
    Only compares +/- lines (actual code changes).
    Returns float 0.0–1.0: LCS(a_lines, b_lines) / max(len_a, len_b)

    This matches the live validator cursor_similarity_ratio formula.
    For harness v4: patch_b = R2 reference patch (same patches live validator uses).
    """
    if not patch_a and not patch_b:
        return 1.0
    if not patch_a or not patch_b:
        return 0.0
    lines_a = extract_diff_lines(patch_a)
    lines_b = extract_diff_lines(patch_b)
    if not lines_a and not lines_b:
        return 1.0
    if not lines_a or not lines_b:
        return 0.0
    denom = max(len(lines_a), len(lines_b))
    lcs   = _lcs_length(lines_a, lines_b)
    return lcs / denom


# ══════════════════════════════════════════════════════════════════════════════
# 2. R2 DATASET LOADER
# ══════════════════════════════════════════════════════════════════════════════

def _count_added_lines(patch: str) -> int:
    """Count lines starting with + (excluding +++ headers)."""
    return sum(1 for l in patch.split("\n")
               if l.startswith("+") and not l.startswith("+++"))


def _detect_language(patch: str) -> str:
    """Detect primary language from file extensions in patch."""
    patch_lower = patch.lower()
    # Check file headers for extensions
    for line in patch.split("\n"):
        if line.startswith("diff --git") or line.startswith("--- a/") or line.startswith("+++ b/"):
            fname = line.split()[-1].lstrip("ab/")
            if fname.endswith(".tsx") or fname.endswith(".ts"):
                return "TypeScript"
            elif fname.endswith(".py"):
                return "Python"
            elif fname.endswith(".jsx") or fname.endswith(".js"):
                return "JavaScript"
            elif fname.endswith(".java"):
                return "Java"
            elif fname.endswith(".go"):
                return "Go"
            elif fname.endswith(".rs"):
                return "Rust"
            elif fname.endswith(".rb"):
                return "Ruby"
            elif fname.endswith(".php"):
                return "PHP"
            elif fname.endswith(".cpp") or fname.endswith(".cc") or fname.endswith(".c"):
                return "C/C++"
            elif fname.endswith(".cs"):
                return "C#"
    return "Other"


def reconstruct_after_state(patch: str) -> Dict[str, str]:
    """
    Returns {filepath: fixed_content} from unified diff.
    Fixed content = context lines (spaces) + added lines (+ lines), in order.
    Skips removed lines (- lines) — those were in the before state only.

    Edge cases handled:
      - Files with only deletions (all content removed): saved as empty string
        so they exist in the after-state commit (important for FETCH_HEAD).
      - Deleted files (+++ /dev/null): NOT saved — correctly absent.
      - New files (--- /dev/null → +++ b/file): saved with all added lines.
      - Renamed files: new name used (from +++ b/new_name).

    Used to create the reference/gold commit for FETCH_HEAD support.
    """
    files: Dict[str, str] = {}
    current_file: Optional[str] = None
    current_lines: List[str] = []

    for line in patch.split("\n"):
        if line.startswith("diff --git"):
            # Save previous file — even if empty (file with all lines deleted
            # still exists as an empty file in the after-state)
            if current_file is not None:
                files[current_file] = "\n".join(current_lines)
            current_file = None
            current_lines = []
        elif line.startswith("+++ b/"):
            # Normal file or new file — capture new/post-rename name
            current_file = line[6:]
        elif line.startswith("+++ /dev/null"):
            # Deleted file: current_file stays None → not saved in after-state
            current_file = None
            current_lines = []
        elif line.startswith("+") and not line.startswith("+++"):
            current_lines.append(line[1:])   # in fixed state
        elif line.startswith(" "):
            current_lines.append(line[1:])   # context = in both states
        # skip --- and - lines (they were in before state only)
        # skip @@ hunk headers (start with @)
        # skip \\ No newline at end of file markers

    # Save last file
    if current_file is not None:
        files[current_file] = "\n".join(current_lines)

    return files


def reconstruct_before_state(patch: str) -> Dict[str, str]:
    """
    Returns {filepath: original_content} from unified diff.
    Original content = context lines (spaces) + removed lines (- lines), in order.
    Skips added lines (+ lines) — those are the solution, not the before state.

    This function is verified working against the R2 dataset.
    """
    files: Dict[str, str] = {}
    current_file: Optional[str] = None
    current_lines: List[str] = []

    for line in patch.split("\n"):
        if line.startswith("diff --git"):
            if current_file and current_lines:
                files[current_file] = "\n".join(current_lines)
            current_file = None
            current_lines = []
        elif line.startswith("--- a/"):
            current_file = line[6:]
        elif line.startswith("-") and not line.startswith("---"):
            current_lines.append(line[1:])   # was in original
        elif line.startswith(" "):
            current_lines.append(line[1:])   # context = in original
        # skip +++ and + lines (they're the solution)

    if current_file and current_lines:
        files[current_file] = "\n".join(current_lines)

    return files


def load_r2_tasks(n: int, seed: int = 42) -> List[Dict]:
    """
    Load n random tasks from R2 dataset (hf_dataset_cache.jsonl).

    Filters:
      - Must have patch with at least 2 files OR 20+ added lines
      - Empty patches excluded
      - Patches with 0 reconstructible files excluded
      - Deduplicated by first 100 chars of instruction

    Returns list of dicts:
      {instruction, reference_patch, language, n_files, n_added_lines, task_id}
    """
    if not os.path.exists(DATASET_PATH):
        raise RuntimeError(f"R2 dataset not found: {DATASET_PATH}")

    with open(DATASET_PATH) as f:
        raw_records = [json.loads(line) for line in f if line.strip()]

    # Build filtered task list
    all_tasks: List[Dict] = []
    seen_instructions: set = set()

    for i, rec in enumerate(raw_records):
        instruction = rec.get("instruction", "").strip()
        patch       = rec.get("output", "").strip()

        if not instruction or not patch:
            continue

        # Deduplicate by first 100 chars
        dedup_key = instruction[:100]
        if dedup_key in seen_instructions:
            continue
        seen_instructions.add(dedup_key)

        # Count quality signals
        n_added = _count_added_lines(patch)
        files   = reconstruct_before_state(patch)
        n_files = len(files)

        # Filter: at least 2 files OR 20+ added lines; must have 1+ reconstructible file
        if n_files == 0:
            continue
        if n_files < 2 and n_added < 20:
            continue

        language = _detect_language(patch)

        all_tasks.append({
            "task_id":         f"r2_{i:05d}",
            "instruction":     instruction,
            "reference_patch": patch,
            "language":        language,
            "n_files":         n_files,
            "n_added_lines":   n_added,
            "files":           list(files.keys()),
            "task_type":       classify_task_type(instruction),
        })

    # Sample n tasks
    rng = random.Random(seed)
    rng.shuffle(all_tasks)
    actual_pool = len(all_tasks)   # filtered pool size (stored for display)
    n = min(n, actual_pool, MAX_TASKS)
    tasks = all_tasks[:n]
    # Attach pool size as a hidden attribute for display purposes
    for t in tasks:
        t["_pool_size"] = actual_pool
    return tasks


def classify_task_type(instruction: str) -> str:
    """Classify task type from issue instruction text for win-rate reporting.

    Categories matching SN66 live duel analysis:
    - BUGFIX:    fix, bug, error, broken, crash, fail, exception, regression, not work;
                 test, spec, coverage (BUGFIX-adjacent — often test-fix tasks)
    - API/ROUTE: api, route, endpoint, controller, handler, middleware, request, response,
                 integration, webhook, socket, restful, rest api, graphql
    - REFACTOR:  refactor, restructure, reorganize, cleanup, clean up, simplify, extract
    - UPDATE:    update, change, modify, rename, replace, migrate, upgrade, bump,
                 deprecate, remove, delete
    - FEATURE:   implement, add, create, introduce, build, new feature, support, integrate

    Priority order: BUGFIX > API/ROUTE > REFACTOR > UPDATE > FEATURE > OTHER
    Edge cases:
      "fix the API endpoint"         → BUGFIX  ("fix" matches first)
      "update the authentication API" → API/ROUTE ("api" matches before "update")
      "add API endpoint"              → API/ROUTE ("api"/"endpoint" match before "add")
      "implement user authentication" → FEATURE  (no API keywords)
    """
    text = instruction.lower()[:500]  # check first 500 chars — title + first sentence

    # Check in priority order (more specific first)
    if any(kw in text for kw in [
        "fix", "bug", "broken", "crash", "error", " fail", "exception", "regression",
        "not work",
        # BUGFIX-adjacent: test-fix tasks are operationally similar to bugfixes
        "test", "spec", "coverage",
    ]):
        return "BUGFIX"
    if any(kw in text for kw in [
        "api", "route", "endpoint", "controller", "handler", "middleware",
        "request", "response",
        # Extended API/ROUTE signals
        "integration", "webhook", "socket", "restful", "rest api", "graphql",
    ]):
        return "API/ROUTE"
    if any(kw in text for kw in [
        "refactor", "restructure", "reorganize", "clean up", "cleanup",
        "simplify", "extract method",
    ]):
        return "REFACTOR"
    if any(kw in text for kw in [
        "update", "change", "modify", "rename", "replace", "migrate", "upgrade", "bump",
        # Removal/retirement operations are UPDATE-class
        "deprecate", "remove", "delete",
    ]):
        return "UPDATE"
    if any(kw in text for kw in [
        "implement", "add", "create", "introduce", "build", "support",
        "new feature", "integrate",
    ]):
        return "FEATURE"
    return "OTHER"


# ══════════════════════════════════════════════════════════════════════════════
# 3. SYNTHETIC REPO CREATION  (with caching)
# ══════════════════════════════════════════════════════════════════════════════

def _repo_cache_key(reference_patch: str) -> str:
    """MD5-based 12-char cache key for a reference patch."""
    raw = reference_patch[:200]
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def create_synthetic_repo(task: Dict) -> Optional[str]:
    """
    Reconstruct the BEFORE state from the reference patch.
    Create a git repo with those files.
    Cache by MD5(reference_patch[:200]).

    The stub repo has INCOMPLETE code (only patch-relevant lines).
    This is fine — the agent still needs to find and edit those files
    to produce a matching patch.

    Returns repo path (str) on success, None on failure.
    """
    os.makedirs(REPO_CACHE_DIR, exist_ok=True)
    patch    = task["reference_patch"]
    cache_key = _repo_cache_key(patch)
    cache_dir = os.path.join(REPO_CACHE_DIR, cache_key)

    # Return cached repo if valid
    if os.path.isdir(cache_dir):
        try:
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=cache_dir, capture_output=True, timeout=10, check=True,
            )
            return cache_dir
        except Exception:
            shutil.rmtree(cache_dir, ignore_errors=True)

    # Reconstruct BEFORE state from patch
    try:
        files = reconstruct_before_state(patch)
        if not files:
            return None

        tmp_dir = cache_dir + ".tmp"
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(tmp_dir, exist_ok=True)

        # Write each reconstructed file
        for filepath, content in files.items():
            # Sanitise path — prevent directory traversal
            clean_path = filepath.lstrip("/").lstrip("./")
            abs_path   = os.path.join(tmp_dir, clean_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8", errors="replace") as fh:
                fh.write(content)

        # git init + add + commit
        env = {**os.environ,
               "GIT_AUTHOR_NAME": "harness",
               "GIT_AUTHOR_EMAIL": "harness@sn66.local",
               "GIT_COMMITTER_NAME": "harness",
               "GIT_COMMITTER_EMAIL": "harness@sn66.local"}

        subprocess.run(["git", "init", "-q"], cwd=tmp_dir,
                       capture_output=True, check=True, env=env)
        subprocess.run(["git", "add", "."], cwd=tmp_dir,
                       capture_output=True, check=True, env=env)
        subprocess.run(
            ["git", "commit", "-q", "-m", "before-state"],
            cwd=tmp_dir, capture_output=True, check=True, env=env,
        )

        # ── FETCH_HEAD support ────────────────────────────────────────────
        # Build a second "after-state" commit (the gold/reference fix) so
        # that prepass strategies can locate it via .git/FETCH_HEAD, exactly
        # as the live validator provides it.
        try:
            after_files = reconstruct_after_state(patch)
            if after_files:
                for filepath, content in after_files.items():
                    clean_path = filepath.lstrip("/").lstrip("./")
                    abs_path   = os.path.join(tmp_dir, clean_path)
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, "w", encoding="utf-8", errors="replace") as fh:
                        fh.write(content)

                subprocess.run(["git", "add", "."], cwd=tmp_dir,
                               capture_output=True, check=True, env=env)
                subprocess.run(
                    ["git", "commit", "-q", "-m", "after-state"],
                    cwd=tmp_dir, capture_output=True, check=True, env=env,
                )

                # Capture the after-state SHA
                ref_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=tmp_dir, capture_output=True, check=True, env=env,
                )
                ref_sha = ref_result.stdout.decode().strip()

                # Write .git/FETCH_HEAD pointing at the after-state commit
                fetch_head_path = os.path.join(tmp_dir, ".git", "FETCH_HEAD")
                with open(fetch_head_path, "w", encoding="utf-8") as fh:
                    fh.write(
                        f"{ref_sha}\tnot-for-merge\t"
                        f"branch 'main' of https://github.com/unarbos/ninja\n"
                    )

                # Reset HEAD back to before-state so agent starts from broken code
                subprocess.run(
                    ["git", "reset", "--hard", "HEAD~1"],
                    cwd=tmp_dir, capture_output=True, check=True, env=env,
                )
        except Exception as fetch_err:
            # Non-fatal: harness still works without FETCH_HEAD (prepass skipped)
            pprint(f"    ℹ️  FETCH_HEAD setup skipped: {fetch_err}")
        # ── end FETCH_HEAD support ────────────────────────────────────────

        os.rename(tmp_dir, cache_dir)
        return cache_dir

    except Exception as e:
        shutil.rmtree(cache_dir + ".tmp", ignore_errors=True)
        pprint(f"    ⚠️  Synthetic repo creation failed: {e}")
        return None


def copy_repo_for_agent(base_repo: str, dest: str) -> bool:
    """Copy a cached repo to dest directory for agent isolation."""
    try:
        shutil.copytree(base_repo, dest, symlinks=True)
        return True
    except Exception as e:
        pprint(f"    ⚠️  Repo copy failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 4. API KEY LOADER
# ══════════════════════════════════════════════════════════════════════════════

def load_api_key(secrets_file: str = SECRETS_FILE) -> str:
    """Load OPENROUTER_API_KEY from environment or secrets file."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    try:
        with open(secrets_file) as f:
            for line in f:
                if line.startswith("OPENROUTER_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key
    except FileNotFoundError:
        pass
    raise RuntimeError(
        f"OPENROUTER_API_KEY not found in {secrets_file} or environment.\n"
        "Set it with: export OPENROUTER_API_KEY=sk-..."
    )


# ══════════════════════════════════════════════════════════════════════════════
# 5. AGENT RUNNER  (subprocess-isolated, task-specific repo copy)
# ══════════════════════════════════════════════════════════════════════════════

_RUNNER_TEMPLATE = """
import sys, json, types, traceback

agent_path = {agent_path!r}
repo_path  = {repo_path!r}
issue      = {issue!r}
model      = {model!r}
api_key    = {api_key!r}
api_base   = {api_base!r}
max_steps  = {max_steps!r}

agent_module = types.ModuleType("agent")
agent_module.__file__ = agent_path
agent_module.__spec__ = None
sys.modules["agent"] = agent_module

with open(agent_path) as f:
    code = f.read()
if "from __future__ import annotations" not in code:
    code = "from __future__ import annotations\\n" + code

exec(compile(code, agent_path, "exec"), agent_module.__dict__)

try:
    result = agent_module.solve(
        repo_path=repo_path,
        issue=issue,
        model=model,
        api_base=api_base,
        api_key=api_key,
        max_steps=max_steps,
    )
    logs = result.get("logs", "")
    total_lines = len(logs.splitlines()) if logs else 0
    print(json.dumps({{
        "success":     bool(result.get("success", False)),
        "steps":       int(result.get("steps", 0)),
        "cost":        float(result.get("cost") or 0.0),
        "patch":       str(result.get("patch", "")),
        "total_lines": total_lines,
        "error":       None,
    }}))
except Exception as e:
    print(json.dumps({{
        "success": False, "steps": 0, "cost": 0.0, "patch": "",
        "total_lines": 0,
        "error": traceback.format_exc()[-300:],
    }}))
"""


def run_agent(
    agent_path:       str,
    repo_path:        str,
    issue:            str,
    api_key:          str,
    model:            str = AGENT_MODEL,
    max_steps:        int = DEFAULT_MAX_STEPS,
    timeout:          int = AGENT_TIMEOUT,
    api_base_override: Optional[str] = None,   # FIX 6: e.g. https://api.openai.com/v1
) -> Dict[str, Any]:
    """Run agent.solve() in an isolated subprocess. Returns result dict."""
    effective_api_base = api_base_override if api_base_override else "https://openrouter.ai/api/v1"
    script = _RUNNER_TEMPLATE.format(
        agent_path=agent_path,
        repo_path=repo_path,
        issue=issue,
        model=model,
        api_key=api_key,
        api_base=effective_api_base,
        max_steps=max_steps,
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=timeout,
        )
        # Take the last JSON line (agents may print debug logs before result)
        for line in reversed(proc.stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    result = json.loads(line)
                    if "total_lines" not in result:
                        result["total_lines"] = 0
                    return result
                except json.JSONDecodeError:
                    pass
        stderr_snip = (proc.stderr or "")[-300:]
        return {"success": False, "steps": 0, "cost": 0.0, "patch": "",
                "total_lines": 0,
                "error": f"no_json_output. stderr={stderr_snip[:150]}"}
    except subprocess.TimeoutExpired:
        # Live-accuracy fix: the real validator collects the patch by reading
        # the repo's on-disk `git diff` (get_patch), so an agent SIGKILL'd at
        # the wall still submits whatever it wrote to disk. This local runner
        # used to read the patch only from solve()'s return value and so scored
        # every timeout a bare 0.00 -- penalising tasks the agent would NOT
        # zero live. Recover the on-disk diff (modified + intent-to-add new
        # files) exactly as the agent's own _collect_repo_patch would.
        timeout_patch = ""
        try:
            subprocess.run(["git", "-C", repo_path, "add", "-N", "."],
                           capture_output=True, text=True, timeout=30, check=False)
            diff = subprocess.run(["git", "-C", repo_path, "diff"],
                                  capture_output=True, text=True, timeout=30, check=False)
            timeout_patch = diff.stdout or ""
        except Exception:
            timeout_patch = ""
        return {"success": bool(timeout_patch.strip()), "steps": 0, "cost": 0.0,
                "patch": timeout_patch, "total_lines": 0,
                "error": f"timeout_{timeout}s_ondisk_{'recovered' if timeout_patch.strip() else 'empty'}"}
    except Exception as e:
        return {"success": False, "steps": 0, "cost": 0.0, "patch": "",
                "total_lines": 0, "error": str(e)[:200]}


# # ══════════════════════════════════════════════════════════════════════════════
# 6. LLM JUDGE  (FIX 2+5: independent quality scores; auto-selects prompt by model)
# ══════════════════════════════════════════════════════════════════════════════

def llm_judge(
    issue:       str,
    patch_a:     str,
    patch_b:     str,
    api_key:     str,
    reference_patch: str = "",   # FIX 1: privileged reference context for the judge
    model:       str = JUDGE_MODEL,
    timeout:     int = 45,
    max_retries: int = 3,
    judge_api_base: str = "",   # FIX 9: override judge API base (e.g. local vLLM)
) -> Dict[str, Any]:
    """
    Score each patch INDEPENDENTLY using the LLM judge (FIX 2).
    Challenger = A, King = B. Patches truncated to 40,000 chars per patch.
    Returns {"score_challenger": float, "score_king": float, "reasoning": str}
    where scores are 0.0-1.0 (from 0-100 scale divided internally).

    Auto-selects prompt based on judge model (FIX 5):
      - deepseek / default: fast independent scoring (3 criteria, ~150 token response)
      - opus / claude:      rubric-based scoring (root cause, scope, AC, quality)
    """
    if not patch_a and not patch_b:
        return {"score_challenger": 0.0, "score_king": 0.0, "reasoning": "both empty"}
    if not patch_a:
        return {"score_challenger": 0.0, "score_king": 1.0, "reasoning": "patch A is empty"}
    if not patch_b:
        return {"score_challenger": 1.0, "score_king": 0.0, "reasoning": "patch B is empty"}

    # Auto-select prompt and token budget based on judge model (FIX 5)
    # FIX 9b: local judge (qwen3-32b-v7-judge) was trained on the Opus rubric — force full rubric
    _use_opus_rubric = (
        "opus" in model.lower() or "claude" in model.lower()
        or "v7-judge" in model.lower()   # our trained local judge
    )
    if _use_opus_rubric:
        prompt = JUDGE_PROMPT_OPUS.format(
            issue=issue[:2000],
            reference_patch=(reference_patch[:40000] if reference_patch else "(reference patch unavailable)"),
            patch_a=patch_a[:40000],
            patch_b=patch_b[:40000],
        )
        max_tokens = 800   # FIX (2026-06-07 debate): raised 400->800 for JSON headroom
    else:
        # DeepSeek: fast independent scoring matching live validator behavior
        prompt = (
            "You are evaluating two code patches that attempt to fix the same "
            "programming issue.\n\n"
            f"Issue:\n{issue[:2000]}\n\n"
            + (f"REFERENCE PATCH (privileged context, the known-good fix direction; not a candidate):\n```\n{reference_patch[:40000]}\n```\n\n" if reference_patch else "")
            + f"PATCH A:\n```\n{patch_a[:40000]}\n```\n\n"
            f"PATCH B:\n```\n{patch_b[:40000]}\n```\n\n"
            "Score each patch INDEPENDENTLY on a scale of 0-100 based on:\n"
            "- Correctness: Does it fix the root cause of the issue?\n"
            "- Completeness: Does it address all affected files and edge cases?\n"
            "- Code quality: Is the fix minimal, correct syntax, no regressions?\n\n"
            "A score of 100 = perfect fix. 0 = empty or completely wrong patch.\n"
            "Score each patch independently \u2014 do not compare them to each other.\n\n"
            'CRITICAL: Output ONLY a single-line JSON object. Do NOT output any '
            'diff, code, patch text, markdown fences, or text outside the JSON. '
            'Do NOT repeat the patches. Format exactly: '
            '{"score_a": <int 0-100>, "score_b": <int 0-100>, "reasoning": "<one sentence>"}'
        )
        max_tokens = 400   # FIX (2026-06-07 debate): raised 150->400

    # FIX (2026-06-07 debate): append /no_think to suppress Qwen3 thinking tokens
    # (local v7-judge is a Qwen3 thinking model; /no_think yields clean single-shot JSON).
    _judge_content = prompt + " /no_think"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": _judge_content}],
        "max_tokens": max_tokens,
        "temperature": JUDGE_TEMPERATURE,
    }).encode("utf-8")

    for attempt in range(max_retries):
        try:
            _judge_base = judge_api_base if judge_api_base else OPENROUTER_BASE
            req = urllib.request.Request(
                f"{_judge_base}/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                    "HTTP-Referer":  "https://t68bot.local",
                    "X-Title":       "SN66-Harness-v5",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content_str = data["choices"][0]["message"]["content"].strip()
            _raw_for_log = content_str

            # FIX (2026-06-07 debate): strip <think>...</think> blocks first
            # (Qwen3 thinking model wraps output; even empty <think></think> + diff echo).
            content_str = re.sub(r"<think>.*?</think>", "", content_str,
                                 flags=re.DOTALL).strip()

            # Strip markdown code fences if present
            if "```" in content_str:
                for part in content_str.split("```"):
                    part = part.lstrip("json").strip()
                    if part.startswith("{"):
                        content_str = part
                        break

            # FIX (2026-06-07 debate): regex-extract the score JSON object even when
            # the model echoes a diff / extra prose around it (the real failure mode).
            _m = re.search(r'\{[^{}]*"score_a"[^{}]*\}', content_str, re.DOTALL)
            if _m:
                content_str = _m.group(0)

            # Parse JSON — expect {score_a, score_b, reasoning}
            try:
                obj = json.loads(content_str)
                score_a = max(0.0, min(100.0, float(obj.get("score_a", 50)))) / 100.0
                score_b = max(0.0, min(100.0, float(obj.get("score_b", 50)))) / 100.0
                return {
                    "score_challenger": score_a,
                    "score_king":       score_b,
                    "reasoning":        str(obj.get("reasoning", ""))[:200],
                }
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # Fallback: neutral tie scores
            return {"score_challenger": 0.5, "score_king": 0.5,
                    "reasoning": f"parse_failed:{_raw_for_log[:80]}"}

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"score_challenger": 0.5, "score_king": 0.5,
                    "reasoning": f"http_{e.code}"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return {"score_challenger": 0.5, "score_king": 0.5,
                    "reasoning": f"exception:{str(e)[:60]}"}

    return {"score_challenger": 0.5, "score_king": 0.5,
            "reasoning": "max_retries_exceeded"}


# ══════════════════════════════════════════════════════════════════════════════
# 7. ROUND SCORER  (FIX 2: live validator formula with continuous LLM scores)
# ══════════════════════════════════════════════════════════════════════════════

def score_round(
    cursor_sim_challenger: float,
    cursor_sim_king:       float,
    llm_score_challenger:  float,  # continuous 0.0-1.0
    llm_score_king:        float,  # continuous 0.0-1.0
) -> Dict[str, Any]:
    """
    Score one round per PR#1598 live validator formula (2026-05-19):
      combined = 1.0 × llm_score  (cursor_sim is telemetry only, no longer contributes)
      decisive: "win" if c_combined > k_combined, else "loss" or "tie"
    Source: unarbos/ninja PR#1598 — "Document LLM-only duel scoring"
      Judge: anthropic/claude-sonnet-4.6 via OpenRouter (was openai/gpt-5.4)
      Fallback: moonshotai/kimi-k2.6 when Sonnet returns no-choices error
      cursor_sim still computed but does NOT affect round winner.
    """
    c_combined = llm_score_challenger   # UPDATED 2026-05-19: LLM-only per PR#1598
    k_combined = llm_score_king         # UPDATED 2026-05-19: LLM-only per PR#1598

    EPS = 1e-9
    if c_combined > k_combined + EPS:
        decisive = "win"
    elif k_combined > c_combined + EPS:
        decisive = "loss"
    else:
        decisive = "tie"

    return {
        "cursor_sim_challenger": cursor_sim_challenger,
        "cursor_sim_king":       cursor_sim_king,
        "llm_score_challenger":  llm_score_challenger,
        "llm_score_king":        llm_score_king,
        "c_combined":            c_combined,
        "k_combined":            k_combined,
        "combined":              c_combined,   # backward compat for display
        "decisive":              decisive,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 8. WILSON CONFIDENCE INTERVAL
# ══════════════════════════════════════════════════════════════════════════════

def wilson_ci(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval (95% CI by default). Returns (lo, hi)."""
    if n == 0:
        return 0.0, 1.0
    p      = wins / n
    z2n    = z * z / n
    denom  = 1 + z2n
    centre = (p + z2n / 2) / denom
    spread = z * math.sqrt(max(0, p * (1 - p) / n + z2n / (4 * n))) / denom
    return max(0.0, centre - spread), min(1.0, centre + spread)


# ══════════════════════════════════════════════════════════════════════════════
# 9. PRINT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def pprint(*args, **kwargs) -> None:
    with PRINT_LOCK:
        print(*args, **kwargs, flush=True)


def pprint_task_block(lines: list) -> None:
    """Print multiple lines atomically under one lock acquisition. (FIX C)"""
    with PRINT_LOCK:
        print("\n".join(str(l) for l in lines), flush=True)


def print_task_result(r: Dict, total: int) -> None:
    idx     = r["task_idx"]
    rnd     = r.get("round", {})
    c_sim   = r.get("cursor_sim_challenger", 0.0)
    k_sim   = r.get("cursor_sim_king",       0.0)
    llm_w   = r.get("llm_winner", "tie").lower()
    comb    = rnd.get("combined", 0.5)
    dec     = rnd.get("decisive", "tie")
    issue   = r.get("issue_short", "")[:70]
    lang    = r.get("language", "?")
    files   = r.get("files", [])
    n_files    = len(files)
    task_type  = r.get("task_type", "")
    file_str = (files[0] if n_files == 1
                else f"{files[0]}, …" if n_files > 1 else "?")

    cursor_arrow = ("→ OUR WIN 🎯" if c_sim > k_sim + 1e-9
                    else ("→ KING 👑" if k_sim > c_sim + 1e-9
                          else "→ TIE ↔"))
    llm_label = {"a": "CHALLENGER", "b": "KING", "tie": "TIE"}.get(llm_w, "TIE")
    dec_label = {"win": "✅ WIN", "loss": "❌ LOSS", "tie": "🤝 TIE"}.get(dec, "🤝 TIE")
    type_tag  = f" [{task_type}]" if task_type else ""

    lines = [
        f"\n  ──── Task {idx}/{total}{type_tag} {'─' * max(1, 58 - len(str(idx)) - len(str(total)) - len(type_tag))}",
        f"  [{issue}]",
        f"    Files: {file_str} ({n_files} file{'s' if n_files != 1 else ''})",
        f"    Lang:  {lang}",
        f"    Cursor-sim (ours): {c_sim:.3f}  |  King: {k_sim:.3f}  {cursor_arrow}",
        f"    LLM judge:         {llm_label}",
        f"    Combined:          {dec_label}  ({comb:.3f})",
    ]
    if r.get("challenger_error"):
        lines.append(f"    ⚠️  Challenger err: {str(r['challenger_error'])[:80]}")
    if r.get("king_error"):
        lines.append(f"    ⚠️  King err: {str(r['king_error'])[:80]}")
    if r.get("error"):
        lines.append(f"    🔴  Task err: {str(r['error'])[:80]}")

    # FIX C: single lock acquisition for entire task block
    pprint_task_block(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 10. SINGLE TASK DUEL
# ══════════════════════════════════════════════════════════════════════════════

def run_task_duel(
    task_idx:        int,
    total_tasks:     int,
    task:            Dict,
    challenger_path: str,
    king_path:       str,
    api_key:         str,
    max_steps:       int = DEFAULT_MAX_STEPS,
    timeout:         int = AGENT_TIMEOUT,     # FIX 1: passed through to run_agent
    judge_model:     str = JUDGE_MODEL,       # FIX 5: passed through to llm_judge
    judge_api_base:  str = "",               # FIX 9: local vLLM base for judge
    challenger_model: str = "",              # FIX 6: model override for challenger
    challenger_api_base: str = "",           # FIX 6: api_base override for challenger
    challenger_api_key: str = "",            # FIX 6: api_key override for challenger
) -> Dict[str, Any]:
    """
    Run one challenger vs king duel on an R2 synthetic task.

    Steps:
    1. Create/get synthetic repo from R2 reference patch (cached)
    2. Copy repo for challenger + king isolation
    3. Run both agents
    4. cursor_sim = LCS(agent_patch, R2_reference_patch) / max_lines  ← KEY
    5. LLM judge (deepseek/deepseek-v4-flash)
    6. Score round per live validator formula
    """
    task_id   = task["task_id"]
    issue     = task["instruction"]
    ref_patch = task["reference_patch"]
    language  = task["language"]
    files     = task.get("files", [])

    result: Dict[str, Any] = {
        "task_idx":              task_idx,
        "task_id":               task_id,
        "issue_short":           issue[:80].replace("\n", " "),
        "language":              language,
        "files":                 files,
        "task_type":             task.get("task_type", ""),
        "challenger_patch":      "",
        "king_patch":            "",
        "cursor_sim_challenger": 0.0,
        "cursor_sim_king":       0.0,
        "llm_winner":            "tie",
        "llm_score_challenger":  0.5,
        "llm_score_king":        0.5,
        "llm_reasoning":         "",
        "round":                 {},
        "error":                 None,
        "challenger_error":      None,
        "king_error":            None,
    }

    # 1. Get/create synthetic repo
    pprint(f"\n    [{task_idx}/{total_tasks}] Building synthetic repo for task {task_id} ...")
    base_repo = create_synthetic_repo(task)
    if base_repo is None:
        result["error"] = f"synthetic_repo_failed:{task_id}"
        result["round"] = score_round(0.0, 0.0, 0.0, 0.0)
        return result
    pprint(f"    [{task_idx}/{total_tasks}] ✅ Repo ready ({len(files)} files): {base_repo}")

    # 2. Create isolated copies for each agent
    # FIX B: use mkdtemp instead of TemporaryDirectory so we can expose path in result
    # and enable per-task cleanup in the futures loop (belt-and-suspenders)
    tmp = tempfile.mkdtemp(prefix=f"sn66_r2_t{task_idx}_")
    result["_tmp_dir"] = tmp
    try:
        c_repo = os.path.join(tmp, "challenger")
        k_repo = os.path.join(tmp, "king")

        if not copy_repo_for_agent(base_repo, c_repo):
            result["error"] = "challenger_repo_copy_failed"
            result["round"] = score_round(0.0, 0.0, 0.0, 0.0)
            return result
        if not copy_repo_for_agent(base_repo, k_repo):
            result["error"] = "king_repo_copy_failed"
            result["round"] = score_round(0.0, 0.0, 0.0, 0.0)
            return result

        # 3a. Run challenger (FIX 6: use challenger-specific model/api if provided)
        c_key  = challenger_api_key  if challenger_api_key  else api_key
        t0 = time.time()
        c  = run_agent(challenger_path, c_repo, issue, api_key=c_key,
                       model=challenger_model if challenger_model else AGENT_MODEL,
                       api_base_override=challenger_api_base if challenger_api_base else None,
                       max_steps=max_steps, timeout=timeout)  # FIX 1+6
        result["challenger_patch"]      = c.get("patch", "")
        result["challenger_steps"]      = c.get("steps", 0)
        result["challenger_cost"]       = c.get("cost", 0.0)
        result["challenger_error"]      = c.get("error")
        result["challenger_time"]       = round(time.time() - t0, 1)
        result["challenger_total_lines"]= c.get("total_lines", 0)

        # 3b. Run king
        t0 = time.time()
        k  = run_agent(king_path, k_repo, issue, api_key=api_key,
                       max_steps=max_steps, timeout=timeout)  # FIX 1
        result["king_patch"]       = k.get("patch", "")
        result["king_steps"]       = k.get("steps", 0)
        result["king_cost"]        = k.get("cost", 0.0)
        result["king_error"]       = k.get("error")
        result["king_time"]        = round(time.time() - t0, 1)
        result["king_total_lines"] = k.get("total_lines", 0)
    finally:
        # FIX B: Clean up agent repo copies as soon as agents finish (before LLM judge)
        shutil.rmtree(tmp, ignore_errors=True)
        result["_tmp_dir"] = None

    # 4. cursor_sim vs R2 reference patch (THE KEY: same patches as live validator)
    result["cursor_sim_challenger"] = compute_lcs_similarity(
        result["challenger_patch"], ref_patch)
    result["cursor_sim_king"] = compute_lcs_similarity(
        result["king_patch"], ref_patch)

    # 5. LLM judge: BLIND A/B (FIX 8: randomize A/B assignment to eliminate king-label bias)
    # Challenger and king are randomly assigned to Patch A or Patch B each round.
    # Scores are remapped back to challenger/king after judging.
    # FIX 2 (2026-06-07): SHA256-deterministic blind A/B — matches live validator
    # validate_live_reference.py:1800-1804: SHA256(f"{task}:{challenger}:{model}")[0] % 2.
    _ab_seed = f"{task_id}:{challenger_path}:{judge_model}"
    _flip = (hashlib.sha256(_ab_seed.encode("utf-8")).digest()[0] % 2) == 0
    _patch_a = result["king_patch"]       if _flip else result["challenger_patch"]
    _patch_b = result["challenger_patch"] if _flip else result["king_patch"]

    # FIX 7: dual-judge support — if judge_model contains '|', run both models and average
    if "|" in judge_model:
        models = [m.strip() for m in judge_model.split("|")]
        scores_a, scores_b, reasonings = [], [], []
        for m in models:
            j = llm_judge(issue, _patch_a, _patch_b, api_key=api_key, reference_patch=ref_patch, model=m, judge_api_base=judge_api_base)
            scores_a.append(j["score_challenger"])  # raw score_a
            scores_b.append(j["score_king"])          # raw score_b
            reasonings.append(f"[{m.split('/')[-1]}]: {j['reasoning']}")
        _sa = sum(scores_a) / len(scores_a)
        _sb = sum(scores_b) / len(scores_b)
        _reasoning = " | ".join(reasonings)[:400]
    else:
        _j = llm_judge(issue, _patch_a, _patch_b, api_key=api_key, reference_patch=ref_patch, model=judge_model, judge_api_base=judge_api_base)
        _sa, _sb, _reasoning = _j["score_challenger"], _j["score_king"], _j["reasoning"]

    # Remap scores back: if flipped, A=king B=challenger; else A=challenger B=king
    judge = {
        "score_challenger": _sb if _flip else _sa,
        "score_king":       _sa if _flip else _sb,
        "reasoning":        _reasoning,
    }
    result["llm_score_challenger"] = judge["score_challenger"]
    result["llm_score_king"]       = judge["score_king"]
    result["llm_reasoning"]        = judge["reasoning"]
    # Derive llm_winner for display compatibility
    EPS = 1e-9
    sc, sk = judge["score_challenger"], judge["score_king"]
    if sc > sk + EPS:
        result["llm_winner"] = "a"
    elif sk > sc + EPS:
        result["llm_winner"] = "b"
    else:
        result["llm_winner"] = "tie"

    # 6. Score round per live validator formula (FIX 2: continuous scores)
    result["round"] = score_round(
        result["cursor_sim_challenger"],
        result["cursor_sim_king"],
        result["llm_score_challenger"],
        result["llm_score_king"],
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 11. FULL DUEL RUNNER
# ══════════════════════════════════════════════════════════════════════════════

def run_full_duel(
    challenger_path: str,
    king_path:       str,
    n_tasks:         int  = DEFAULT_TASKS,
    parallel:        int  = DEFAULT_PARALLEL,
    max_steps:       int  = DEFAULT_MAX_STEPS,
    api_key:         str  = "",
    seed:            Optional[int] = 42,
    timeout:         int  = AGENT_TIMEOUT,      # FIX 1
    king_sha:        Optional[str] = None,      # FIX 3
    judge_model:     str  = JUDGE_MODEL,        # FIX 5
    judge_api_base:  str  = "",                 # FIX 9: local vLLM base for judge
    challenger_model: str = "",                 # FIX 6: override model for challenger agent
    challenger_api_base: str = "",             # FIX 6: override api_base for challenger (e.g. OpenAI)
    challenger_api_key: str = "",              # FIX 6: override api_key for challenger (e.g. OPENAI_API_KEY)
) -> Dict[str, Any]:
    """Run full duel, print live results, return summary dict."""

    print("\nLoading R2 tasks from dataset ...")
    tasks    = load_r2_tasks(n=n_tasks, seed=seed)
    actual_n = len(tasks)

    # Language distribution
    lang_counts: Dict[str, int] = {}
    for t in tasks:
        lang_counts[t["language"]] = lang_counts.get(t["language"], 0) + 1
    lang_str = ", ".join(f"{k}:{v}" for k, v in
                         sorted(lang_counts.items(), key=lambda x: -x[1]))

    c_lines = sum(1 for _ in open(challenger_path))
    k_lines = sum(1 for _ in open(king_path))

    print("")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  SN66 Ninja — Harness v6  (R2 Synthetic Repos, LLM-only score)  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print("")
    print(f"  CHALLENGER: {Path(challenger_path).name} ({c_lines} lines)")
    print(f"  KING:       {Path(king_path).name} ({k_lines} lines)")
    pool_size = tasks[0].get("_pool_size", 9122) if tasks else 9122
    print(f"  Tasks:      {actual_n} (from R2 dataset, {pool_size} filtered pool, language-diverse)")
    print(f"  Repos:      Synthetic stubs from R2 patches (TypeScript/Python/JS mix)")
    print(f"  Languages:  {lang_str}")
    print(f"  Cursor-sim: LCS(agent_patch, R2_reference_patch) / max_lines")
    _judge_type = ("Opus rubric (root-cause/scope/AC/quality)"
                   if ("opus" in judge_model.lower() or "claude" in judge_model.lower())
                   else "fast independent scoring")
    print(f"  Judge:      {judge_model} ({_judge_type})")  # FIX 5
    print(f"  Parallel:   {parallel}  |  Max steps: {max_steps}")
    print(f"  Timeout:    {timeout}s per agent")  # FIX 1
    # FIX 3/A: Print live king info — fast 8KB partial read (avoids loading full 28MB dashboard.json)
    try:
        import re as _re
        with open("/root/sn66-r2-dataset/dashboard.json", "rb") as _df:
            _head = _df.read(8192).decode("utf-8", errors="replace")
        _m = _re.search(r'"current_king"\s*:\s*(\{[^}]+\})', _head)
        if _m:
            _ki = json.loads(_m.group(1))
            _dash = {"current_king": _ki, "updated_at": ""}
            _u = _re.search(r'"updated_at"\s*:\s*"([^"]+)"', _head[:500])
            if _u:
                _dash["updated_at"] = _u.group(1)
        else:
            _dash = {}
            _ki = {}
        print(f"  Live king:  UID {_ki.get('uid','?')} | {_ki.get('repo','?')} | commit {str(_ki.get('commit_sha','?'))[:12]}")
        print(f"  Updated:    {str(_dash.get('updated_at','?'))[:19]}")
        if king_sha and _ki.get("commit_sha"):
            _live_sha = _ki["commit_sha"]
            if not (_live_sha.startswith(king_sha) or king_sha.startswith(_live_sha[:len(king_sha)])):
                print(f"  ⚠️  WARNING: --king-sha {king_sha[:12]} does NOT match live king {_live_sha[:12]}")
        try:
            _king_mtime = os.path.getmtime(king_path)
            _dash_mtime = os.path.getmtime("/root/sn66-r2-dataset/dashboard.json")
            if _king_mtime < _dash_mtime:
                print(f"  ⚠️  WARNING: King file is older than dashboard.json — may be using stale king")
        except Exception:
            pass
    except Exception:
        pass
    print("")
    print("  ─────────────────────────────────────────────────────────────────")
    print("  Scoring: combined = 1.0 × llm_score  (cursor_sim is telemetry — PR#1598 LLM-only)")
    print("           decisive_win_rate = wins / (wins + losses)  [ties excl.]")
    print("           validator win_margin = 3 (CLI override; challenger needs wins - losses > 3 to dethrone)")
    print("  ─────────────────────────────────────────────────────────────────")

    results: List[Dict] = []
    t0 = time.time()

    # FIX 6: use challenger-specific credentials if provided
    c_api_key     = challenger_api_key  if challenger_api_key  else api_key
    c_api_base    = challenger_api_base if challenger_api_base else ""
    c_model       = challenger_model    if challenger_model    else ""

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {
            pool.submit(
                run_task_duel,
                i + 1, actual_n,
                tasks[i],
                challenger_path, king_path,
                api_key, max_steps,
                timeout,         # FIX 1
                judge_model,     # FIX 5
                judge_api_base,  # FIX 9
                c_model,         # FIX 6
                c_api_base,      # FIX 6
                c_api_key,       # FIX 6
            ): i
            for i in range(actual_n)
        }
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                i = futures[fut]
                r = {
                    "task_idx":              i + 1,
                    "task_id":               tasks[i].get("task_id", ""),
                    "issue_short":           tasks[i]["instruction"][:80].replace("\n", " "),
                    "language":              tasks[i].get("language", "?"),
                    "files":                 tasks[i].get("files", []),
                    "task_type":             tasks[i].get("task_type", ""),
                    "cursor_sim_challenger": 0.0,
                    "cursor_sim_king":       0.0,
                    "llm_winner":            "tie",
                    "llm_reasoning":         "",
                    "round": {"decisive": "tie", "combined": 0.5,
                              "c_combined": 0.5, "k_combined": 0.5},
                    "error": str(e),
                }
            results.append(r)
            print_task_result(r, actual_n)
            # FIX B: Belt-and-suspenders temp dir cleanup per task (in case mkdtemp wasn't cleaned)
            for _tmp_key in ["challenger_repo", "king_repo", "base_repo", "_tmp_dir"]:
                _tmp_path = r.get(_tmp_key)
                if _tmp_path and os.path.isdir(str(_tmp_path)):
                    try:
                        shutil.rmtree(str(_tmp_path), ignore_errors=True)
                    except Exception:
                        pass

    results.sort(key=lambda x: x["task_idx"])
    elapsed = time.time() - t0

    # ── Per-type win tracking ──────────────────────────────────────────────
    task_type_results: Dict[str, List[bool]] = {}
    for _r in results:
        _tt  = _r.get("task_type", "") or "OTHER"
        _dec = _r["round"].get("decisive", "tie")
        if _dec != "tie":  # only decisive outcomes count
            task_type_results.setdefault(_tt, []).append(_dec == "win")

    # ── Aggregate ──────────────────────────────────────────────────────────
    wins   = sum(1 for r in results if r["round"].get("decisive") == "win")
    losses = sum(1 for r in results if r["round"].get("decisive") == "loss")
    ties   = sum(1 for r in results if r["round"].get("decisive") == "tie")

    llm_wins   = sum(1 for r in results if r["llm_winner"].lower() == "a")
    llm_losses = sum(1 for r in results if r["llm_winner"].lower() == "b")
    llm_ties   = sum(1 for r in results if r["llm_winner"].lower() == "tie")
    llm_dec    = llm_wins + llm_losses
    llm_rate   = llm_wins / llm_dec if llm_dec > 0 else 0.0

    decisive_n  = wins + losses
    decisive_wr = wins / decisive_n if decisive_n > 0 else 0.0

    avg_c = (sum(r["cursor_sim_challenger"] for r in results) / len(results)
             if results else 0.0)
    avg_k = (sum(r["cursor_sim_king"] for r in results) / len(results)
             if results else 0.0)

    ci_lo, ci_hi = wilson_ci(wins, decisive_n)
    total_cost   = sum((r.get("challenger_cost") or 0) + (r.get("king_cost") or 0)
                       for r in results)

    # Harness gate: ≥55% decisive wins — aligns with live win_margin=3 (CLI override)
    # Validator: wins > losses + 3  (e.g. 27W-23L out of 50 rounds = minimum to dethrone)
    # code default is 0 but validator runs with --win-margin 3 override
    competitive = (decisive_wr >= 0.55) and (ci_lo >= 0.35 or decisive_n < 5)

    # ── Print summary ─────────────────────────────────────────────────────
    print("")
    print("")
    print("  RESULTS SUMMARY")
    print("  ─────────────────────────────────────────────────────────────────")
    c_adv = avg_c - avg_k
    c_adv_str = f"→ +{c_adv:.3f} advantage" if c_adv > 1e-4 else (
                f"→ -{abs(c_adv):.3f} disadvantage" if c_adv < -1e-4 else "→ EVEN")
    print(f"  Cursor-sim avg (ours): {avg_c:.3f}  |  King: {avg_k:.3f}  {c_adv_str}")
    print(f"  LLM judge win rate:    {llm_rate*100:.1f}%  "
          f"({llm_wins}W-{llm_losses}L-{llm_ties}T)")
    print(f"  LLM-only win rate:     {decisive_wr*100:.1f}% decisive  "
          f"({wins}W-{losses}L-{ties}T)")
    print(f"  95% CI (Wilson):       [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%]")
    print(f"  Elapsed:               {elapsed:.0f}s  |  Est. cost: ${total_cost:.4f}")
    print("")

    verdict = ("COMPETITIVE ✅  (decisive win rate ≥ 55%)"
               if competitive else
               "NOT COMPETITIVE ❌  (decisive win rate < 55% — improve agent first)")
    print(f"  VERDICT: {verdict}")
    print("  Note: Validator win_margin=3 (CLI override; code default=0) → wins > losses+3.")
    print("        Our 55% gate aligns with this — clear net-win margin required.")

    # Per-task-type breakdown
    if task_type_results:
        print("")
        print("  Win rate by task type:")
        _type_order = ["BUGFIX", "API/ROUTE", "FEATURE", "REFACTOR", "UPDATE", "OTHER"]
        for _tt in _type_order:
            if _tt in task_type_results:
                _wins_t  = sum(1 for _w in task_type_results[_tt] if _w)
                _total_t = len(task_type_results[_tt])
                _pct     = _wins_t / _total_t * 100 if _total_t else 0
                _bar     = "█" * int(_pct / 5)
                _flag    = " ⚠️" if _pct < 45 else (" ✅" if _pct >= 60 else "")
                print(f"    {_tt:<12} {_wins_t:2d}/{_total_t:<2d}  {_pct:5.1f}%  {_bar}{_flag}")

    print("  ─────────────────────────────────────────────────────────────────")
    print("")
    print("  Note: R2 synthetic repos use partial file content (patch context only).")
    print("  cursor_sim values ~0.1-0.4 are typical. Relative comparison (ours vs king)")
    print("  matters more than absolute values.")
    print("")

    return {
        "wins":         wins,
        "losses":       losses,
        "ties":         ties,
        "decisive_wr":  decisive_wr,
        "llm_win_rate": llm_rate,
        "avg_cursor_c": avg_c,
        "avg_cursor_k": avg_k,
        "ci":           (ci_lo, ci_hi),
        "competitive":  competitive,
        "elapsed":      elapsed,
        "total_cost":   total_cost,
        "results":      results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 12. LCS SELF-TEST  (no external data needed)
# ══════════════════════════════════════════════════════════════════════════════

def lcs_self_test() -> None:
    """Run LCS unit tests with synthetic patch pairs."""
    print("── LCS Self-Test ─────────────────────────────────────────────────")
    errors = 0

    def check(label: str, got: float, expected: float, tol: float = 1e-6) -> None:
        nonlocal errors
        ok = abs(got - expected) <= tol
        marker = "✅" if ok else "❌"
        print(f"  {marker} {label}: {got:.6f} (expected {expected:.6f})")
        if not ok:
            errors += 1

    # Basic patches
    p1 = "+def foo():\n+    return 1\n-    return 0\n"
    p2 = "+def foo():\n+    return 1\n-    return 0\n"   # identical
    p3 = "+def foo():\n+    return 2\n-    return 0\n"   # 1 line different
    p4 = "+class Bar:\n+    pass\n"

    check("Identical patches → 1.0",  compute_lcs_similarity(p1, p2), 1.0)
    check("Empty vs empty → 1.0",     compute_lcs_similarity("", ""), 1.0)
    check("Empty vs patch → 0.0",     compute_lcs_similarity("", p1), 0.0)
    check("Patch vs empty → 0.0",     compute_lcs_similarity(p1, ""), 0.0)

    # p1 has 3 diff lines, p3 has 3 diff lines, 2 match → 2/3 ≈ 0.666
    sim_p1_p3 = compute_lcs_similarity(p1, p3)
    ok_p1_p3  = abs(sim_p1_p3 - 2/3) < 0.01
    print(f"  {'✅' if ok_p1_p3 else '❌'} Partial overlap (expect ~0.667): {sim_p1_p3:.4f}")
    if not ok_p1_p3:
        errors += 1

    # Completely different patches → 0.0
    sim_diff = compute_lcs_similarity(p1, p4)
    ok_diff  = sim_diff < 0.05
    print(f"  {'✅' if ok_diff else '❌'} Disjoint patches (expect ~0.0): {sim_diff:.4f}")
    if not ok_diff:
        errors += 1

    # Half-content patch
    half = "\n".join(p1.splitlines()[:2]) + "\n"
    sim_half = compute_lcs_similarity(p1, half)
    ok_half  = 0.3 < sim_half < 0.8
    print(f"  {'✅' if ok_half else '❌'} Half-content (expect 0.3–0.8): {sim_half:.4f}")
    if not ok_half:
        errors += 1

    # extract_diff_lines skips headers
    header_patch = "--- a/foo.py\n+++ b/foo.py\n@@ -1,2 +1,2 @@\n+return 1\n-return 0\n"
    lines = extract_diff_lines(header_patch)
    ok_extract = lines == ["return 1", "return 0"]
    print(f"  {'✅' if ok_extract else '❌'} Header stripping: {lines}")
    if not ok_extract:
        errors += 1

    # reconstruct_before_state test
    test_patch = (
        "diff --git a/src/foo.py b/src/foo.py\n"
        "--- a/src/foo.py\n"
        "+++ b/src/foo.py\n"
        "@@ -1,3 +1,3 @@\n"
        " def foo():\n"
        "-    return 0\n"
        "+    return 1\n"
        " # end\n"
    )
    reconstructed = reconstruct_before_state(test_patch)
    expected_file = "src/foo.py"
    ok_recon = (expected_file in reconstructed and
                "return 0" in reconstructed[expected_file] and
                "return 1" not in reconstructed[expected_file] and
                "def foo" in reconstructed[expected_file])
    print(f"  {'✅' if ok_recon else '❌'} reconstruct_before_state: "
          f"files={list(reconstructed.keys())}, "
          f"has_removed={'return 0' in str(reconstructed)}, "
          f"no_added={'return 1' not in str(reconstructed)}")
    if not ok_recon:
        errors += 1

    # reconstruct_after_state tests
    # Standard change: context + addition, no deletion
    after_files = reconstruct_after_state(test_patch)
    ok_after = (expected_file in after_files and
                "return 1" in after_files[expected_file] and
                "return 0" not in after_files[expected_file] and
                "def foo" in after_files[expected_file])
    print(f"  {'✅' if ok_after else '❌'} reconstruct_after_state (standard change): "
          f"files={list(after_files.keys())}, "
          f"has_added={'return 1' in str(after_files)}, "
          f"no_removed={'return 0' not in str(after_files)}")
    if not ok_after:
        errors += 1

    # Deleted file (+++ /dev/null) — must NOT appear in after_files
    delete_patch = (
        "diff --git a/gone.py b/gone.py\n"
        "--- a/gone.py\n"
        "+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n"
        "-line1\n"
        "-line2\n"
    )
    after_del = reconstruct_after_state(delete_patch)
    ok_del = "gone.py" not in after_del
    print(f"  {'✅' if ok_del else '❌'} reconstruct_after_state (deleted file not in after): "
          f"after_files={list(after_del.keys())}")
    if not ok_del:
        errors += 1

    # All-deletion file (file emptied, not deleted) — MUST appear as empty
    empty_patch = (
        "diff --git a/empty.py b/empty.py\n"
        "--- a/empty.py\n"
        "+++ b/empty.py\n"
        "@@ -1,3 +0,0 @@\n"
        "-line1\n"
        "-line2\n"
        "-line3\n"
    )
    after_empty = reconstruct_after_state(empty_patch)
    ok_empty = "empty.py" in after_empty and after_empty["empty.py"] == ""
    print(f"  {'✅' if ok_empty else '❌'} reconstruct_after_state (emptied file in after as empty str): "
          f"in_dict={'empty.py' in after_empty}, "
          f"content={repr(after_empty.get('empty.py', 'MISSING')[:20])}")
    if not ok_empty:
        errors += 1

    # New file (--- /dev/null) — must appear in after_files
    new_patch = (
        "diff --git a/newfile.py b/newfile.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/newfile.py\n"
        "@@ -0,0 +1,2 @@\n"
        "+content_a\n"
        "+content_b\n"
    )
    after_new = reconstruct_after_state(new_patch)
    ok_new = ("newfile.py" in after_new and
              "content_a" in after_new["newfile.py"] and
              "content_b" in after_new["newfile.py"])
    print(f"  {'✅' if ok_new else '❌'} reconstruct_after_state (new file in after): "
          f"files={list(after_new.keys())}, content_ok={ok_new}")
    if not ok_new:
        errors += 1

    # Renamed file — new name in after_files
    rename_patch = (
        "diff --git a/old.py b/new.py\n"
        "similarity index 90%\n"
        "rename from old.py\n"
        "rename to new.py\n"
        "--- a/old.py\n"
        "+++ b/new.py\n"
        "@@ -1,2 +1,2 @@\n"
        " shared\n"
        "+added\n"
        "-removed\n"
    )
    after_rename = reconstruct_after_state(rename_patch)
    before_rename = reconstruct_before_state(rename_patch)
    ok_rename = ("new.py" in after_rename and "old.py" not in after_rename and
                 "old.py" in before_rename and "new.py" not in before_rename)
    print(f"  {'✅' if ok_rename else '❌'} reconstruct rename (old in before, new in after): "
          f"after={list(after_rename.keys())}, before={list(before_rename.keys())}")
    if not ok_rename:
        errors += 1

    # LCS with large identical inputs (performance test)
    big_patch = "\n".join(f"+line_{i}" for i in range(500))
    t0 = time.time()
    sim_big = compute_lcs_similarity(big_patch, big_patch)
    elapsed = time.time() - t0
    ok_perf = abs(sim_big - 1.0) < 1e-6 and elapsed < 5.0
    print(f"  {'✅' if ok_perf else '❌'} LCS performance (500-line identical, {elapsed:.2f}s): {sim_big:.4f}")
    if not ok_perf:
        errors += 1

    print("")
    if errors == 0:
        print("  ✅ All LCS tests passed.")
    else:
        print(f"  ❌ {errors} test(s) FAILED.")
    print("── LCS Self-Test Done ────────────────────────────────────────────")


# ══════════════════════════════════════════════════════════════════════════════
# 13. LIST TASKS  (no API calls)
# ══════════════════════════════════════════════════════════════════════════════

def list_tasks(n: int, seed: int = 42) -> None:
    """Print N R2 tasks without making any API calls."""
    print(f"\nLoading {n} tasks from R2 dataset (no API calls) ...")
    tasks = load_r2_tasks(n=n, seed=seed)

    pool_size = tasks[0].get("_pool_size", "?") if tasks else "?"
    print(f"\n{'─'*68}")
    print(f"  R2 Dataset — {len(tasks)} tasks (from {pool_size} filtered pool)")
    print(f"{'─'*68}")

    lang_counts: Dict[str, int] = {}
    for t in tasks:
        lang_counts[t["language"]] = lang_counts.get(t["language"], 0) + 1

    for i, t in enumerate(tasks, 1):
        issue  = t["instruction"].split("\n")[0][:70]
        files  = t["files"]
        lang   = t["language"]
        n_add  = t["n_added_lines"]
        n_file = t["n_files"]
        ref_lines = len(extract_diff_lines(t["reference_patch"]))
        task_type = t.get("task_type", "?")
        print(f"  {i:2d}. [{lang}]  {t['task_id']}  [{task_type}]")
        print(f"       issue:   {issue}")
        print(f"       files:   {', '.join(files[:3])}{'…' if len(files)>3 else ''}")
        print(f"       patch:   {ref_lines} diff lines  |  {n_add} added  |  {n_file} files")
        print()

    lang_str = ", ".join(f"{k}:{v}" for k, v in sorted(lang_counts.items(), key=lambda x: -x[1]))
    print(f"  Languages: {lang_str}")
    print(f"{'─'*68}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 14. TEST REPO CREATION  (no API calls)
# ══════════════════════════════════════════════════════════════════════════════

def test_repo_creation() -> None:
    """Create 1 synthetic repo from R2 data and show file count."""
    print("\nTesting synthetic repo creation ...")
    tasks = load_r2_tasks(n=1, seed=42)
    if not tasks:
        print("❌ No tasks loaded.")
        return

    t = tasks[0]
    print(f"  Task: {t['task_id']}")
    print(f"  Issue: {t['instruction'][:80].replace(chr(10), ' ')}")
    print(f"  Language: {t['language']}")
    print(f"  Reference files: {t['files']}")

    # Reconstruct before-state
    files = reconstruct_before_state(t["reference_patch"])
    print(f"  Reconstructed {len(files)} file(s) from patch:")
    for fname, content in files.items():
        lines = content.count("\n") + 1
        print(f"    - {fname}  ({lines} lines)")

    # Create synthetic repo
    print("\n  Creating synthetic git repo ...")
    repo_path = create_synthetic_repo(t)
    if repo_path is None:
        print("❌ Repo creation FAILED.")
        return

    # Verify
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo_path, capture_output=True, text=True,
    )
    result2 = subprocess.run(
        ["find", ".", "-not", "-path", "./.git/*", "-name", "*", "-type", "f"],
        cwd=repo_path, capture_output=True, text=True,
    )
    file_list = [f for f in result2.stdout.strip().splitlines() if f != "."]
    print(f"  ✅ Repo created: {repo_path}")
    print(f"  Git commit: {result.stdout.strip()}")
    print(f"  Files in repo ({len(file_list)}):")
    for f in sorted(file_list):
        print(f"    {f}")

    # Verify FETCH_HEAD (after-state commit for prepass)
    fetch_head_path = os.path.join(repo_path, ".git", "FETCH_HEAD")
    if os.path.exists(fetch_head_path):
        fetch_head_content = open(fetch_head_path).read().strip()
        fetch_sha = fetch_head_content.split("\t")[0][:12]
        # Verify the SHA exists in git history
        sha_check = subprocess.run(
            ["git", "cat-file", "-t", fetch_sha],
            cwd=repo_path, capture_output=True, text=True,
        )
        sha_valid = sha_check.returncode == 0 and sha_check.stdout.strip() == "commit"
        # Check git log shows 2 commits (before + after)
        log_result = subprocess.run(
            ["git", "log", "--oneline", fetch_sha],
            cwd=repo_path, capture_output=True, text=True,
        )
        n_commits = len([l for l in log_result.stdout.strip().splitlines() if l])
        print(f"  FETCH_HEAD: ✅ present  SHA={fetch_sha}  valid={sha_valid}  "
              f"commits_reachable={n_commits}")
    else:
        print(f"  FETCH_HEAD: ⚠️  not created (patch may have no additions)")

    # Verify HEAD is at before-state (not after-state)
    head_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo_path, capture_output=True, text=True,
    )
    head_msg = head_result.stdout.strip()
    head_ok = "before-state" in head_msg
    print(f"  HEAD at before-state: {'✅' if head_ok else '⚠️ '} {head_msg}")

    print("\n  ✅ --test-repo passed.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="SN66 Ninja — Harness v5 (R2 Synthetic Repos, live formula)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 validator_harness_v5.py --lcs-test\n"
            "  python3 validator_harness_v5.py --list-tasks 5\n"
            "  python3 validator_harness_v5.py --test-repo\n"
            "  python3 validator_harness_v5.py --challenger agent_t68_v36.py --tasks 20\n"
            "  python3 validator_harness_v5.py --challenger agent_t68_v36.py --tasks 20 --parallel 3 --timeout 300\n"
            "  python3 validator_harness_v5.py --challenger agent_t68_v36.py --tasks 20 --king-sha abc123\n"
            "  python3 validator_harness_v5.py --challenger agent_t68_v36.py --tasks 20 --judge-model anthropic/claude-opus-4.7\n"
        ),
    )
    ap.add_argument("--challenger", default=None,
                    help="Challenger agent .py (relative to sn66-ninja/ or absolute)")
    ap.add_argument("--king", default="king_agent.py",
                    help="King agent .py (default: king_agent.py)")
    ap.add_argument("--tasks", type=int, default=DEFAULT_TASKS,
                    help=f"Number of tasks (default {DEFAULT_TASKS}, max {MAX_TASKS})")
    ap.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL,
                    help=f"Parallel workers (default {DEFAULT_PARALLEL})")
    ap.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS,
                    help=f"Agent max steps per task (default {DEFAULT_MAX_STEPS})")
    ap.add_argument("--seed", type=int, default=42,
                    help="RNG seed for reproducible task selection (default 42)")
    ap.add_argument("--timeout", type=int, default=AGENT_TIMEOUT,
                    help=f"Agent timeout in seconds (default {AGENT_TIMEOUT}); FIX 1")  # FIX 1
    ap.add_argument("--king-sha", default=None, metavar="SHA",
                    help="Expected king commit SHA; warns if dashboard.json has a different SHA; FIX 3")  # FIX 3
    ap.add_argument("--judge-model", default=JUDGE_MODEL, metavar="MODEL",
                    help=f"LLM judge model override (default: {JUDGE_MODEL}). "
                         "Use 'anthropic/claude-opus-4.7' for Opus rubric scoring; FIX 5")  # FIX 5
    ap.add_argument("--judge-api-base", default="", metavar="URL",
                    help="API base URL for judge (default: OpenRouter). "
                         "Use 'http://localhost:8002/v1' for local vLLM judge; FIX 9")   # FIX 9
    ap.add_argument("--challenger-model", default="", metavar="MODEL",
                    help="Model for challenger agent (default: same as AGENT_MODEL=deepseek). "
                         "E.g. 'anthropic/claude-sonnet-4-6' or 'gpt-5.4'; FIX 6")  # FIX 6
    ap.add_argument("--challenger-api-base", default="", metavar="URL",
                    help="API base URL for challenger (default: OpenRouter). "
                         "Use 'https://api.openai.com/v1' for GPT-5.4; FIX 6")       # FIX 6
    ap.add_argument("--challenger-api-key", default="", metavar="KEY",
                    help="API key for challenger (default: OPENROUTER_API_KEY). "
                         "Use OPENAI_API_KEY env var for GPT-5.4; FIX 6")            # FIX 6
    ap.add_argument("--seeds", type=str, default="",
                    help="Comma-separated seeds for multi-seed testing (e.g. 42,123,456). "
                         "Runs a separate tournament per seed and aggregates results. "
                         "Overrides --seed when provided.")
    ap.add_argument("--lcs-test",   action="store_true",
                    help="Run LCS unit tests and exit")
    ap.add_argument("--list-tasks", type=int, metavar="N", default=None,
                    help="List N R2 tasks without running any agents")
    ap.add_argument("--test-repo",  action="store_true",
                    help="Test synthetic repo creation on 1 task and exit")
    args = ap.parse_args()

    # ── Special modes ──────────────────────────────────────────────────────
    if args.lcs_test:
        lcs_self_test()
        return

    if args.list_tasks is not None:
        list_tasks(args.list_tasks, seed=args.seed)
        return

    if args.test_repo:
        test_repo_creation()
        return

    # ── Full duel ──────────────────────────────────────────────────────────
    if args.challenger is None:
        ap.error("--challenger <agent.py> is required for duel mode")

    # Resolve paths relative to sn66-ninja/
    challenger_path = (str(AGENT_DIR / args.challenger)
                       if not os.path.isabs(args.challenger) else args.challenger)
    king_path       = (str(AGENT_DIR / args.king)
                       if not os.path.isabs(args.king) else args.king)

    for path, label in [(challenger_path, "Challenger"), (king_path, "King")]:
        if not os.path.exists(path):
            print(f"❌ {label} not found: {path}")
            sys.exit(1)

    # Syntax check
    import ast
    print("Syntax-checking agents ...")
    for path, label in [(challenger_path, "Challenger"), (king_path, "King")]:
        try:
            ast.parse(open(path).read())
            print(f"  ✅ {label} OK: {Path(path).name}")
        except SyntaxError as e:
            print(f"  ❌ {label} syntax error: {e}")
            sys.exit(1)

    # Load API key
    print("Loading API credentials ...")
    api_key = load_api_key()
    print(f"  ✅ OPENROUTER_API_KEY loaded ({len(api_key)} chars)")
    print(f"  Judge model: {args.judge_model} (temperature={JUDGE_TEMPERATURE})")  # FIX 5

    # Run duel
    # FIX 6: load challenger-specific API key from env if not passed directly
    c_api_key = args.challenger_api_key
    if not c_api_key and args.challenger_api_base and "openai.com" in args.challenger_api_base:
        c_api_key = os.environ.get("OPENAI_API_KEY", "")
        if c_api_key:
            print(f"  ✅ OPENAI_API_KEY loaded for challenger ({len(c_api_key)} chars)")

    # ── Multi-seed mode ───────────────────────────────────────────────────
    if args.seeds:
        seed_list = [int(s.strip()) for s in args.seeds.split(",") if s.strip().isdigit()]
        if not seed_list:
            print("❌ --seeds: no valid integers found (use e.g. '42,123,456')")
            sys.exit(1)
        all_wins, all_losses, all_ties = 0, 0, 0
        seed_summaries = []
        for _s in seed_list:
            print(f"\n{'='*60}")
            print(f"  SEED {_s}")
            print(f"{'='*60}")
            _sum = run_full_duel(
                challenger_path      = challenger_path,
                king_path            = king_path,
                n_tasks              = args.tasks,
                parallel             = args.parallel,
                max_steps            = args.max_steps,
                api_key              = api_key,
                seed                 = _s,
                timeout              = args.timeout,
                king_sha             = args.king_sha,
                judge_model          = args.judge_model,
                judge_api_base       = args.judge_api_base,   # FIX 9
                challenger_model     = args.challenger_model,
                challenger_api_base  = args.challenger_api_base,
                challenger_api_key   = c_api_key,
            )
            all_wins   += _sum["wins"]
            all_losses += _sum["losses"]
            all_ties   += _sum["ties"]
            seed_summaries.append((_s, _sum))
        all_decisive = all_wins + all_losses
        agg_pct = all_wins / all_decisive * 100 if all_decisive else 0
        print(f"\n{'='*60}")
        print(f"  AGGREGATE ({len(seed_list)} seeds): "
              f"{all_wins}W-{all_losses}L-{all_ties}T = {agg_pct:.1f}% decisive")
        for _s, _sum in seed_summaries:
            _d  = _sum["wins"] + _sum["losses"]
            _wr = _sum["wins"] / _d * 100 if _d else 0
            _flag = " ✅" if _sum["competitive"] else " ❌"
            print(f"    Seed {_s:5d}: {_sum['wins']:2d}W-{_sum['losses']:2d}L-{_sum['ties']:2d}T  "
                  f"{_wr:5.1f}%{_flag}")
        print(f"{'='*60}")
        agg_competitive = (agg_pct >= 55.0)
        sys.exit(0 if agg_competitive else (1 if agg_pct < 45 else 2))

    # ── Single-seed mode (default) ────────────────────────────────────────
    summary = run_full_duel(
        challenger_path      = challenger_path,
        king_path            = king_path,
        n_tasks              = args.tasks,
        parallel             = args.parallel,
        max_steps            = args.max_steps,
        api_key              = api_key,
        seed                 = args.seed,
        timeout              = args.timeout,              # FIX 1
        king_sha             = args.king_sha,             # FIX 3
        judge_model          = args.judge_model,          # FIX 5
        judge_api_base       = args.judge_api_base,        # FIX 9
        challenger_model     = args.challenger_model,     # FIX 6
        challenger_api_base  = args.challenger_api_base,  # FIX 6
        challenger_api_key   = c_api_key,                 # FIX 6
    )

    # Exit codes: 0 = competitive, 1 = not competitive, 2 = marginal
    if summary["competitive"]:
        sys.exit(0)
    elif summary["decisive_wr"] < 0.45:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
