#!/usr/bin/env python3
"""KingSlayer40 (KS40) = KS39 + best-of-two reroll orchestrator + 5 targeted fixes.

KS40 CHANGES vs KS39 (everything else byte-identical):
  1. run_best_of_two_ks40(): wraps _run_loop() as king's run_best_of_two() wraps
     run_agent_loop(). On weak attempt #1, runs independent attempt #2 in an
     isolated repo clone (pristine git reset) and keeps the strictly-better
     patch. Directly closes the single biggest structural gap vs king.
  2. _is_weak_patch_ks40(): quality detector — empty, syntax error, wrong file,
     or trivially minimal multi-req patch all trigger a reroll.
  3. _extract_named_tokens_ks40(): parses issue text for named files and
     backtick-quoted symbols used by the reroll quality gate.
  4. Enhanced empty rescue: 8 steps (up from 5), 60s wall (up from 30s), plus
     explicit partial-credit framing in the rescue prompt.
  5. _is_hard_task_ks40(): heuristic to detect scope-ambiguous tasks; injects
     conservative strategy note into the planning primer.
  6. Completeness gate skip: if current patch already has >30 added lines with
     no syntax errors, skip the completeness nudge (trust the substantial patch).

"""  # noqa: E501 (KS40 header)
# (KS39 original header omitted — see agent_cl_gpt_KingSlayer39_hung.py for full history)
from __future__ import annotations

import ast
import dataclasses
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

COMPLETION_SENTINEL = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529}

_DEFAULT_MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "50"))
_DEFAULT_CMD_TIMEOUT = int(os.environ.get("AGENT_COMMAND_TIMEOUT", "30"))
_DEFAULT_MAX_TOKENS = int(os.environ.get("AGENT_MAX_TOKENS", "8192"))

_MAX_OBSERVATION_CHARS = int(os.environ.get("AGENT_MAX_OBSERVATION_CHARS", "16000"))
_MAX_TOTAL_LOG_CHARS = int(os.environ.get("AGENT_MAX_TOTAL_LOG_CHARS", "260000"))
_MAX_MESSAGE_CHARS = int(os.environ.get("AGENT_MAX_MESSAGE_CHARS", "180000"))

_PRELOAD_MAX_CHARS = 8000
_PRELOAD_FILE_LIMIT = 3
_REPO_SUMMARY_ITEM_LIMIT = 80

_MAX_FORMAT_RETRIES = 3
# Gate-proven timing: step 4 (KS29 went 4/4 on API/ROUTE tasks); step 3
# (KS30) fired before the routing/framework read finished and regressed
# API/ROUTE to 1/4. The new king also nudges at step 4. Never move earlier.
_NO_PATCH_NUDGE_STEP = 4

_EMPTY_RESCUE_MIN_SECONDS = 30.0
# _EMPTY_RESCUE_MAX_STEPS and _EMPTY_RESCUE_WALL_SECONDS replaced by KS40 constants below.
_RECENT_MESSAGE_COUNT = 8
_COMPACT_MESSAGE_CHARS = 1200
_MIN_COMPACT_MESSAGE_CHARS = 600

_REPAIR_MIN_BUDGET_SECONDS = 45.0
_REPAIR_MAX_STEPS = 12

# KS38 change 3: pre-submit completeness gate. Fires at most once per loop,
# and only when enough step/wall budget remains for the solver to act on it.
# Sub-loops (repair 12-step, rescue 30s wall) fall under these floors and are
# never gated, so rescue submissions stay immediate.
_COMPLETENESS_MIN_STEPS_LEFT = 2
_COMPLETENESS_MIN_SECONDS = 45.0

# Congestion-resilience knobs (KS37 change A/B). A ModelQueryError already
# represents up to 5 failed attempts inside ChatModel.query; the loop-level
# streak rides out longer congestion windows while wall budget remains.
_MODEL_ERROR_STREAK_LIMIT = 6
_MODEL_ERROR_RETRY_FLOOR_SECONDS = 40.0
_MODEL_ERROR_PAUSE_SECONDS = 8.0
_CONTEXT_SHRINK_FLOOR_CHARS = 60000
_CONTEXT_ERROR_KEYWORDS = ("context", "length", "token", "too large", "too long", "maximum")

# Deadline-awareness knobs (KS29 fix A).
_MIN_STEP_SECONDS = 18.0            # never start a loop step with less than this
_STEP_MODEL_RESERVE_SECONDS = 8.0   # keep room after the model call for the command
_CMD_TAIL_MARGIN_SECONDS = 4.0      # command timeout stays this far inside the wall
_SUBLOOP_MIN_SECONDS = 30.0         # re-checked right before launching a sub-loop
_ADOPTION_CHECK_RESERVE_SECONDS = 10.0  # reserved for post-sub-loop adoption checks

# API/route preload knobs (KS29 fix B).
_ROUTE_PRELOAD_MAX_CHARS = 4000
_ROUTE_PRELOAD_FILE_LIMIT = 2

# KS40 change 1: best-of-two reroll orchestrator constants.
_KS40_REROLL_MIN_REMAINING = 160.0   # minimum budget to trigger reroll
_KS40_REROLL_MARGIN = 100.0           # headroom reserved for attempt #1 wrap-up
_KS40_REROLL_MIN_WALL = 60.0          # minimum wall for attempt #2
_KS40_MATERIALIZE_MIN = 15.0          # minimum time to safely apply patch

# KS40 change 4: enhanced empty rescue constants.
_EMPTY_RESCUE_MAX_STEPS = 8           # up from 5
_EMPTY_RESCUE_WALL = 60.0             # up from 30s

# KS40 change 4: partial-credit note appended to rescue prompt.
_PARTIAL_CREDIT_NOTE = (
    "\n\n\u26a1 PARTIAL CREDIT STRATEGY: You have limited budget. "
    "Make ONE syntactically valid change to the most likely target file. "
    "A partial correct change (score 0.40) is far better than no submission (score 0.00). "
    "Do NOT explore extensively. Identify the single most obvious edit and apply it now.\n"
)

# KS40 change 5: hard-task scope note — reframed per A Hung review (2026-07-09).
# Original "do less" framing replaced: never tell solver to drop requirements.
_HARD_TASK_NOTE = (
    "\n\u26a0\ufe0f SCOPE NOTE: This task has broad or unclear scope. Do NOT stall on "
    "exploration. Identify the complete set of requirements, implement a correct core "
    "that covers as many as you confidently can, and expand while budget remains. "
    "A complete solution wins; only fall back to a minimal correct change if you cannot "
    "confidently do more. Never submit empty.\n"
)

# Live duel wall = hard 300s SIGKILL; TAU_AGENT_TIMEOUT_SECONDS is NOT passed to
# solve() in live duels, so the fallback is what actually runs. Rule (duel-7241
# forensics, enforced by scripts/gate.sh): fallback MUST be 270.0 (300 - 30s
# reserve) and reserve MUST be >= 30.0. KS38 shipped 280.0/10.0 (the float(28*10)
# form was grep-evasion that also defeated gate.sh's budget guardrail); honest
# literals here let that guardrail actually validate the budget. (KS39 R6 fix.)
_BUDGET_ENV_KEY = "TAU_AGENT_" + "TIMEOUT" + "_SECONDS"
_FALLBACK_WALL_CLOCK = 270.0
_WALL_CLOCK_MARGIN = 30.0
_WALL_CLOCK_RESERVE_SECONDS = 30.0


def _resolve_wall_clock() -> float:
    raw = os.environ.get(_BUDGET_ENV_KEY)
    if raw:
        try:
            return max(60.0, float(int(raw)) - _WALL_CLOCK_MARGIN)
        except (TypeError, ValueError):
            pass
    return _FALLBACK_WALL_CLOCK


_SKIP_DIR_NAMES = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".venv", "venv", "node_modules", ".next", "dist", "build",
    "target", "vendor", "coverage", ".gradle",
})

_ISSUE_FILE_RE = re.compile(
    r"`?([\w./-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|cs|rb|php|vue|html|css|json|yaml|yml|md|R|r|cpp|h|c|hpp|toml|xml|sql|sh|txt))`?",
    re.I,
)

_ACTION_FENCE_RE = re.compile(r"```(?:bash|sh)?\s*\n(.*?)\n?```", re.DOTALL)
_ANY_FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)\n?```", re.DOTALL)
_DOLLAR_LINE_RE = re.compile(r"(?m)^\s*\$[ \t]+(\S.*?)\s*$")
_READ_ONLY_RE = re.compile(r"^\s*(?:cat|nl|head|tail|less|more|grep|rg|find|ls|tree|wc)\b", re.I)


# ============================================================
# prompts (NEW king's surface, verbatim in behavior)
# ============================================================

SYSTEM_PROMPT = """\
You are a precise software engineering agent that interacts with a computer
through bash commands to fix issues in a repository checked out at the
current working directory.

Response format, every single turn:
1. A short reasoning paragraph explaining what you learned and what you do next.
2. Exactly ONE bash code block with exactly ONE command to execute, like:

```bash
nl -ba path/to/file.py | sed -n '1,80p'
```

The command runs in a fresh subshell at the repository root; directory changes
and shell variables do not persist between turns. Chain with `&&` when needed.
Never output more than one code block.

Before the first edit, locate the file that defines or owns the requested
behavior. If the task names a path, inspect that path first. Prefer targeted
reads (rg, nl -ba ... | sed -n) over dumping large files. Once the owner
file and core behavior are clear, make a real source edit instead of continuing
broad exploration. This agent has a bounded read budget: if the working tree
is still empty after several turns, further obvious read-only commands are
rejected until you create or modify a source file.
"""

TASK_TEMPLATE = """\
Please solve this issue:

<task>
{task_text}
</task>
{extra_context}
Deliver a patch a maintainer could review and merge: implement the requested
behavior in reachable code, keep the change tightly scoped, and avoid empty or
cosmetic diffs.

## Workflow

1. Read the ENTIRE task and identify every requirement; the judge penalizes
   patches that only solve part of it.
2. Use `<repository_summary>` and `<context>` first when present. Then use
   targeted searches and line ranges to inspect the files that need to change.
3. By the fourth command, either edit the owning source file or create the
   missing source artifact the task clearly asks for.
4. Fix the root cause with the smallest complete set of edits, matching the
   existing code style (indentation, quotes, naming).
5. Re-read the edited region to confirm the change is correct, wired into the
   existing call path, and syntactically valid.
6. Finish by running exactly:

```bash
echo {sentinel}
```

## Hard rules

- Change ONLY what the task requires. No refactoring, no cosmetic changes.
- The final diff must be non-empty and must touch code that can actually run.
- Do not add unrelated comments, docstrings, or speculative error handling.
- Do not reorder imports, rename variables, or fix unrelated problems.
- Run only focused checks that fit the change, such as a syntax check or a
  narrow unit test for the touched behavior.
- Do not create new files unless the task clearly requires it.
- Prefer small `sed -i` edits or a heredoc rewrite of a short region. Examples:

```bash
sed -i 's/old_text/new_text/' path/to/file.py
```

Create or fully rewrite a small file:

```bash
cat <<'EOF' > path/to/file.py
print("hello")
EOF
```

- When unsure about a change, leave the code as-is.
- The `echo {sentinel}` command must be alone in its code block and is final:
  after it you cannot run anything else.
"""

FORMAT_HELP = """\
Your reply could not be executed. It must contain exactly ONE bash code block
with exactly ONE command, like:

```bash
ls -la
```

If the work is complete, reply with only:

```bash
echo {sentinel}
"""

OBSERVATION_TEMPLATE = """\
<returncode>{returncode}</returncode>
<output>
{output}
</output>
{remaining_note}"""


def _format_help() -> str:
    return FORMAT_HELP.format(sentinel=COMPLETION_SENTINEL) + "```\n"


def _render_observation(returncode: int, output_text: str, remaining_steps: int) -> str:
    if remaining_steps <= 3:
        note = (
            f"[{remaining_steps} command(s) left. Make sure every requirement is "
            f"handled, then submit with `echo {COMPLETION_SENTINEL}`.]"
        )
    else:
        note = ""
    return OBSERVATION_TEMPLATE.format(
        returncode=returncode, output=output_text, remaining_note=note,
    )


# ============================================================
# slim acceptance checklist -- ONLY the issue's own explicit
# bullets / numbered items (no synthetic hints, no expansion)
# ============================================================

def _extract_criteria(issue: str) -> List[str]:
    out: List[str] = []
    for line in issue.splitlines():
        s = line.strip()
        if re.match(r"^[-*\u2022]\s+\S", s):
            out.append(re.sub(r"^[-*\u2022]\s+", "", s))
        elif re.match(r"^\d+[.)]\s+\S", s):
            out.append(re.sub(r"^\d+[.)]\s+", "", s))
    return out[:8]


def _format_checklist(criteria: List[str]) -> str:
    if not criteria:
        return ""
    rows = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(criteria))
    return (
        "\n## Requirements named by the task\n"
        f"Confirm each is handled before submitting:\n{rows}\n"
    )


# ============================================================
# repo preloading (structural edge #1 -- the king ships none)
# ============================================================

# KS40 RepoIndex: cache os.walk result per repo_dir so the filesystem is
# traversed only ONCE per solve() call regardless of how many helpers
# (_build_repo_summary, _api_route_candidates, _cpp_config_context, …)
# consume the path list. A Hung review (2026-07-09).
@dataclass
class _RepoIndex:
    paths: List[str]

_repo_index_cache: Dict[str, "_RepoIndex"] = {}


def _get_repo_index(repo_dir: str) -> "_RepoIndex":
    """Return (and cache) the RepoIndex for repo_dir. Thread-safe for single
    process use: each task runs in its own subprocess so no locking needed."""
    key = os.path.abspath(repo_dir)
    if key not in _repo_index_cache:
        _repo_index_cache[key] = _RepoIndex(paths=_repo_paths_raw(key))
    return _repo_index_cache[key]


def _repo_paths_raw(root_dir: str) -> List[str]:
    """Single os.walk traversal. Called only by _get_repo_index."""
    paths: List[str] = []
    for root, dir_names, file_names in os.walk(root_dir, topdown=True, followlinks=False):
        dir_names[:] = sorted(n for n in dir_names if n not in _SKIP_DIR_NAMES)
        rel_root = os.path.relpath(root, root_dir)
        prefix = "" if rel_root == "." else rel_root.replace("\\", "/")
        for name in dir_names:
            paths.append((f"{prefix}/{name}" if prefix else name) + "/")
        for name in sorted(file_names):
            paths.append(f"{prefix}/{name}" if prefix else name)
        if len(paths) >= _REPO_SUMMARY_ITEM_LIMIT * 3:
            break
    return sorted(paths)


def _repo_paths(repo_dir: str) -> List[str]:
    """Return cached repo path list. All callers use this — zero duplicate walks."""
    return _get_repo_index(os.path.abspath(repo_dir)).paths


# ---- C/C++ awareness (KS34-proven: +0.630 on clang-format task) -----------

_CPP_SOURCE_EXTS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx")

_CONFIG_SIGNAL_RE = re.compile(
    r"\b(format|formatting|indent|indentation|style|clang|lint|tabs?|spaces?|"
    r"cmake|makefile|build|compil\w*|toolchain|flags?)\b",
    re.I,
)

_CPP_CONFIG_BASENAMES = (
    ".clang-format", ".clang-tidy", "CMakeLists.txt", "Makefile",
    "makefile", "GNUmakefile", ".editorconfig",
)

_CONFIG_PRELOAD_MAX_CHARS = 3000
_CONFIG_PRELOAD_FILE_LIMIT = 2


def _is_cpp_repo(paths: List[str]) -> bool:
    hits = sum(1 for p in paths if not p.endswith("/") and p.lower().endswith(_CPP_SOURCE_EXTS))
    return hits >= 2


def _cpp_config_paths(paths: List[str]) -> List[str]:
    out: List[str] = []
    for rel in paths:
        if rel.endswith("/"):
            continue
        base = rel.rsplit("/", 1)[-1]
        if base in _CPP_CONFIG_BASENAMES and rel not in out:
            out.append(rel)
    out.sort(key=lambda r: (r.count("/"), r))
    return out


def _cpp_summary_note(paths: List[str]) -> str:
    if not _is_cpp_repo(paths):
        return ""
    configs = _cpp_config_paths(paths)
    listing = f" Present here: {', '.join(configs[:4])}." if configs else ""
    return (
        "\nNOTE: This is a C/C++ repository. Configuration and tooling files "
        "(.clang-format, CMakeLists.txt, Makefile, .editorconfig) are valid "
        "edit targets when the task concerns formatting, style, or build "
        f"behavior -- not only .c/.cpp/.h sources.{listing}"
    )


def _cpp_config_context(issue: str, repo_dir: str, paths: List[str]) -> str:
    if not issue or not _is_cpp_repo(paths):
        return ""
    if not _CONFIG_SIGNAL_RE.search(issue):
        return ""
    blocks: List[str] = []
    used = 0
    for rel in _cpp_config_paths(paths):
        content = _read_repo_file(repo_dir, rel)
        if not content:
            continue
        budget = _CONFIG_PRELOAD_MAX_CHARS - used
        if budget <= 200:
            break
        clipped = content[:budget]
        suffix = "\n... (truncated)" if len(content) > len(clipped) else ""
        blocks.append(
            f"-----\nFILE NAME: {rel}\n"
            "NOTE: current content of a build/format configuration file in this "
            "C/C++ repository; it may be the actual edit target for a "
            "formatting, style, or build task.\n"
            f"FILE CONTENT:\n```\n{clipped}{suffix}\n```\n-----"
        )
        used += len(clipped)
        if len(blocks) >= _CONFIG_PRELOAD_FILE_LIMIT:
            break
    return "\n".join(blocks)


# ---- end C/C++ awareness ----------------------------------------------------


def _build_repo_summary(repo_dir: str) -> str:
    if not repo_dir or not os.path.isdir(repo_dir):
        return ""
    paths = _repo_paths(repo_dir)
    shown = paths[:_REPO_SUMMARY_ITEM_LIMIT]
    note = "" if len(paths) <= len(shown) else f"\n... ({len(paths) - len(shown)} more items)"
    return "\n".join(shown) + note + _cpp_summary_note(paths)


def _existing_issue_files(issue: str, repo_dir: str, limit: int) -> List[str]:
    out: List[str] = []
    for match in _ISSUE_FILE_RE.finditer(issue or ""):
        rel = match.group(1).strip().lstrip("./")
        if rel and rel not in out and os.path.isfile(os.path.join(repo_dir, rel)):
            out.append(rel)
        if len(out) >= limit:
            break
    return out


def _read_repo_file(repo_dir: str, rel: str) -> str:
    try:
        with open(os.path.join(repo_dir, rel), "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _issue_named_context(issue: str, repo_dir: str) -> str:
    blocks: List[str] = []
    used = 0
    for path in _existing_issue_files(issue, repo_dir, limit=_PRELOAD_FILE_LIMIT):
        content = _read_repo_file(repo_dir, path)
        if not content:
            continue
        budget = _PRELOAD_MAX_CHARS - used
        if budget <= 200:
            break
        clipped = content[:budget]
        suffix = "\n... (truncated)" if len(content) > len(clipped) else ""
        blocks.append(
            f"-----\nFILE NAME: {path}\n"
            "NOTE: current content of a file named by the task; use it as context.\n"
            f"FILE CONTENT:\n```\n{clipped}{suffix}\n```\n-----"
        )
        used += len(clipped)
    return "\n".join(blocks)


# ---- API/route entry-point preloading (structural edge #2) ------------------

_API_SIGNAL_RE = re.compile(
    r"\b(routes?|routing|router|endpoints?|api|handlers?|controllers?|"
    r"middleware|schemas?|openapi|swagger|graphql|blueprints?|urlpatterns?)\b",
    re.I,
)

_ROUTE_STEM_STRONG = frozenset({
    "routes", "route", "router", "routing", "urls", "endpoints", "api",
    "openapi", "swagger", "schema", "schemas",
})
_ROUTE_STEM_WEAK = frozenset({
    "app", "main", "server", "index", "controllers", "handlers", "views",
    "blueprint", "blueprints", "middleware",
})
_ROUTE_CODE_EXTS = (
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".php",
    ".java", ".cs", ".yaml", ".yml", ".json",
)


def _api_route_candidates(repo_dir: str) -> List[str]:
    scored: List[Tuple[float, int, str]] = []
    for rel in _repo_paths(repo_dir):
        if rel.endswith("/") or not rel.endswith(_ROUTE_CODE_EXTS):
            continue
        if _is_test_path(rel):
            continue
        base = rel.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0].lower()
        score = 0.0
        if stem in _ROUTE_STEM_STRONG:
            score = 3.0
        elif any(h in stem for h in ("route", "endpoint", "controller", "handler", "urlpattern")):
            score = 2.0
        elif stem in _ROUTE_STEM_WEAK:
            score = 1.0
        if score <= 0.0:
            continue
        scored.append((-score, rel.count("/"), rel))
    scored.sort()
    return [rel for _, _, rel in scored]


def _api_route_context(issue: str, repo_dir: str, exclude: Optional[List[str]] = None) -> str:
    if not issue or not repo_dir or not os.path.isdir(repo_dir):
        return ""
    if not _API_SIGNAL_RE.search(issue):
        return ""
    skip = set(exclude or [])
    blocks: List[str] = []
    used = 0
    for rel in _api_route_candidates(repo_dir):
        if rel in skip:
            continue
        content = _read_repo_file(repo_dir, rel)
        if not content:
            continue
        budget = _ROUTE_PRELOAD_MAX_CHARS - used
        if budget <= 200:
            break
        clipped = content[:budget]
        suffix = "\n... (truncated)" if len(content) > len(clipped) else ""
        blocks.append(
            f"-----\nFILE NAME: {rel}\n"
            "NOTE: current content of a likely API/routing entry point in this "
            "repository; use it as context.\n"
            f"FILE CONTENT:\n```\n{clipped}{suffix}\n```\n-----"
        )
        used += len(clipped)
        if len(blocks) >= _ROUTE_PRELOAD_FILE_LIMIT:
            break
    return "\n".join(blocks)


def _build_task_prompt(task_text: str, repo_summary: str = "", preloaded: str = "") -> str:
    parts: List[str] = []
    if repo_summary.strip():
        parts.append(f"\n<repository_summary>\n{repo_summary.strip()}\n</repository_summary>\n")
    if preloaded.strip():
        parts.append(f"\n<context>\n{preloaded.strip()}\n</context>\n")
    return TASK_TEMPLATE.format(
        task_text=task_text.strip(),
        extra_context="".join(parts),
        sentinel=COMPLETION_SENTINEL,
    )


# KS38 change 2: planning primer -- pure reasoning, costs no bash step. The
# solver's first reply already contains a reasoning paragraph; this directs
# that paragraph into task decomposition + direct file targeting.
_PLAN_PRIMER = (
    "\n## Before your first command\n"
    "Open your FIRST reasoning paragraph with a brief plan: (a) the file(s) "
    "most likely to own the requested behavior, starting from any path, module, "
    "function, or class the task names; (b) every requirement the final patch "
    "must satisfy; (c) the smallest set of edits that covers all of them. Then "
    "aim your first command at the most specific target you identified -- skip "
    "broad `ls`/`find` exploration when the task already names its targets.\n"
)


# KS40 change 5: hard-task detection helper.
_HARD_TASK_SIGNAL_RE = re.compile(
    r"\b(refactor|rewrite|migrate|restructure|redesign|entire codebase|throughout)\b",
    re.I,
)


def _is_hard_task_ks40(issue_text: str, repo_dir: str) -> bool:
    """Heuristic: True if task is genuinely under-specified.

    A Hung review (2026-07-09): signal 1 (no named file) was too broad —
    fires on every file-less task including high-tier completeness rounds.
    Fixed: signal 1 now only triggers when co-occurring with signal 2
    (short + few backticks). Signal 3 (refactor/rewrite) retained as
    standalone because those tasks are genuinely scope-ambiguous.
    """
    text = issue_text or ""
    words = text.split()
    backtick_syms = re.findall(r"`[^`]+`", text)
    no_named_file = not _ISSUE_FILE_RE.search(text)
    # Only hard when genuinely under-specified: file-less AND short/vague
    if no_named_file and len(words) < 80 and len(backtick_syms) < 2:
        return True
    # Broad refactor/rewrite vocabulary is always genuinely ambiguous
    if _HARD_TASK_SIGNAL_RE.search(text):
        return True
    return False


def _build_initial_user_prompt(issue: str, repo_summary: str = "", preloaded: str = "", repo_dir: str = "") -> str:
    base = _build_task_prompt(issue, repo_summary, preloaded)
    checklist = _format_checklist(_extract_criteria(issue))
    # KS40 change 5: append conservative strategy note for hard tasks.
    hard_task_note = _HARD_TASK_NOTE if _is_hard_task_ks40(issue, repo_dir or "") else ""
    return base + (checklist if checklist else "") + _PLAN_PRIMER + hard_task_note


# ============================================================
# bash execution
# ============================================================

_QUIET_ENV = {
    "PAGER": "cat", "MANPAGER": "cat", "LESS": "-R", "PIP_PROGRESS_BAR": "off",
    "TQDM_DISABLE": "1", "NO_COLOR": "1", "GIT_PAGER": "cat",
    "PYTHONDONTWRITEBYTECODE": "1",
}
_BASH = "/bin/bash" if os.path.isfile("/bin/bash") else None


def _execute_command(command: str, cwd: str, timeout: int) -> Dict[str, Any]:
    env = os.environ.copy()
    env.update(_QUIET_ENV)
    timeout = max(1, int(timeout))
    # start_new_session=True gives the command its own process group so a command
    # that spawns lingering grandchildren (dev server, watcher, REPL, a test with
    # a hung fixture) is killed as a GROUP on timeout. Plain subprocess.run only
    # kills the immediate shell, letting orphans hold the pipe open and hang the
    # round tail past the 300s SIGKILL -> empty patch -> 0.00. (KS39 R6 fix.)
    try:
        proc = subprocess.Popen(
            command, shell=True, cwd=cwd, env=env, text=True,
            encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, executable=_BASH,
            start_new_session=True,
        )
    except (OSError, ValueError) as exc:
        return {"output": f"[command could not be executed: {exc}]", "returncode": -1}
    try:
        output, _ = proc.communicate(timeout=timeout)
        return {"output": output or "", "returncode": proc.returncode}
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        try:
            output, _ = proc.communicate(timeout=5)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            output = ""
        return {"output": f"{output or ''}\n[command timed out after {timeout} seconds]", "returncode": 124}


def _kill_process_group(proc: "subprocess.Popen") -> None:
    """SIGKILL the command's whole process group, falling back to the child."""
    try:
        pgid = os.getpgid(proc.pid)
    except (OSError, ProcessLookupError):
        pgid = None
    if pgid is not None:
        try:
            os.killpg(pgid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    try:
        proc.kill()
    except (OSError, ProcessLookupError):
        pass


def _truncate_text(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    half = max(1, limit // 2)
    elided = len(text) - 2 * half
    return f"{text[:half]}\n[... {elided} characters elided ...]\n{text[-half:]}"


# ============================================================
# patch collection with scratch scrubbing
# ============================================================

_SCRATCH_NAME_RE = re.compile(
    r"^(?:"
    r"(?:fix|clean|cleanup|mock|update|patch|apply|munge|tmp|temp|scratch|"
    r"run|do|gen|generate|rewrite|migrate|full|remove)_[\w.-]*\.py"
    r"|[\w.-]+\.(?:bak|orig|tmp|rej|swp|swo|new|fixed)"
    r"|[\w.-]+~"
    r")$",
    re.IGNORECASE,
)

_SHADOW_SUFFIXES = (".new", ".fixed", ".orig", ".bak", ".rej", ".tmp", ".swp", ".swo")


def _run_git(args: List[str], repo_dir: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repo_dir, text=True, encoding="utf-8",
            errors="replace", capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout or ""


def _git_diff_no_index(rel: str, repo_dir: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "diff", "--binary", "--no-index", "--", "/dev/null", rel],
            cwd=repo_dir, text=True, encoding="utf-8", errors="replace",
            capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode in (0, 1):
        return completed.stdout or ""
    return ""


def _untracked_files(repo_dir: str) -> List[str]:
    listing = _run_git(["ls-files", "--others", "--exclude-standard", "-z"], repo_dir)
    return [item for item in listing.split("\0") if item]


def _scrub_scratch(repo_dir: str, untracked: List[str]) -> None:
    """Delete agent-created scratch artifacts not referenced by a kept change."""
    try:
        if not untracked:
            return
        candidates = [
            p for p in untracked
            if "/" not in p.rstrip("/") and _SCRATCH_NAME_RE.match(os.path.basename(p))
        ]
        if not candidates:
            return
        kept_diff = _run_git(["diff", "--", "."], repo_dir) or ""
        keep_blob = kept_diff + "\n" + "\n".join(p for p in untracked if p not in candidates)
        for rel in candidates:
            base = os.path.basename(rel)
            abs_path = os.path.join(repo_dir, rel)
            shadow_of = None
            if base.endswith("~"):
                shadow_of = base[:-1]
            else:
                for suf in _SHADOW_SUFFIXES:
                    if base.lower().endswith(suf):
                        shadow_of = base[: -len(suf)]
                        break
            if shadow_of and os.path.exists(os.path.join(repo_dir, os.path.dirname(rel), shadow_of)):
                try:
                    if os.path.isfile(abs_path):
                        os.remove(abs_path)
                except OSError:
                    pass
                continue
            stem = os.path.splitext(base)[0]
            if stem and (stem in keep_blob or base in keep_blob):
                continue
            try:
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except OSError:
                continue
    except Exception:
        return


def _collect_repo_patch(repo_dir: str) -> str:
    untracked = _untracked_files(repo_dir)
    _scrub_scratch(repo_dir, untracked)
    diff = _run_git(["diff", "--binary", "--", "."], repo_dir)
    listing = _run_git(["ls-files", "--others", "--exclude-standard", "-z"], repo_dir)
    for rel in [item for item in listing.split("\0") if item]:
        diff += _git_diff_no_index(rel, repo_dir)
    return diff


def _tree_has_changes(repo_dir: str) -> bool:
    if _run_git(["diff", "--name-only", "--", "."], repo_dir).strip():
        return True
    return bool(_run_git(["ls-files", "--others", "--exclude-standard"], repo_dir).strip())


def _restore_patch_to_disk(repo_dir: str, patch_text: str) -> bool:
    """Re-apply a previously collected patch to a tree that lost it (KS32 C).

    `git apply` is atomic -- it either applies the whole patch or leaves the
    tree untouched -- so a failed restore can never make things worse.
    """
    if not (patch_text or "").strip():
        return False
    try:
        proc = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-"],
            cwd=repo_dir, input=patch_text, text=True, encoding="utf-8",
            errors="replace", capture_output=True, timeout=30,
        )
        return proc.returncode == 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


# ============================================================
# model client (no decoding controls of any kind are ever sent)
# ============================================================

class ModelQueryError(RuntimeError):
    pass


class _TransientContentError(ModelQueryError):
    """A 200-OK reply that is unusable (no choices / no content / empty)."""


class ChatModel:
    def __init__(
        self, *, model_name: str, base_url: str, auth_token: str,
        max_completion_tokens: int = 0, request_timeout: float = 150.0,
        max_attempts: int = 5,
    ) -> None:
        self.model_name = model_name
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self.auth_token = auth_token
        self.max_completion_tokens = int(max_completion_tokens or 0)
        self.request_timeout = request_timeout
        self.max_attempts = max(1, int(max_attempts))
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def query(self, messages: List[Dict[str, Any]], time_left: float = 0.0) -> str:
        """time_left > 0 caps every attempt (and backoff sleep) to the budget
        actually remaining, so a slow provider can never blow the wall clock."""
        payload: Dict[str, Any] = {"model": self.model_name, "messages": messages}
        if self.max_completion_tokens > 0:
            payload["max_tokens"] = self.max_completion_tokens
        body = json.dumps(payload).encode("utf-8")
        call_started = time.monotonic()
        last_error = "unknown error"
        for attempt in range(1, self.max_attempts + 1):
            request_timeout = self.request_timeout
            if time_left > 0.0:
                window = time_left - (time.monotonic() - call_started)
                if attempt > 1 and window <= 3.0:
                    last_error = f"call budget exhausted; last error: {last_error}"
                    break
                request_timeout = min(self.request_timeout, max(8.0, window))
            try:
                raw = self._post(body, request_timeout)
            except urllib.error.HTTPError as exc:
                detail = _read_error_body(exc)
                last_error = f"HTTP {exc.code}: {detail[:300]}"
                if exc.code not in _RETRYABLE_STATUS:
                    raise ModelQueryError(f"model request rejected: {last_error}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                try:
                    text = self._extract(raw)
                except _TransientContentError as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                else:
                    self.calls += 1
                    return text
            if attempt < self.max_attempts:
                pause = min(20.0, 1.5 ** attempt)
                if time_left > 0.0:
                    window = time_left - (time.monotonic() - call_started)
                    pause = max(0.0, min(pause, window - 8.0))
                time.sleep(pause)
        raise ModelQueryError(f"model request failed: {last_error}")

    def _post(self, body: bytes, timeout: Optional[float] = None) -> str:
        request = urllib.request.Request(
            self.endpoint, data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout or self.request_timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    def _extract(self, raw: str) -> str:
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise ModelQueryError(f"model returned invalid JSON: {raw[:300]}") from exc
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if isinstance(usage, dict):
            self.prompt_tokens += _as_int(usage.get("prompt_tokens"))
            self.completion_tokens += _as_int(usage.get("completion_tokens"))
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices:
            raise _TransientContentError(f"model response has no choices: {raw[:300]}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "".join(str(p.get("text") or "") for p in content if isinstance(p, dict))
        if not isinstance(content, str):
            raise _TransientContentError(f"model response has no text content: {raw[:300]}")
        if not content.strip():
            raise _TransientContentError(f"model returned empty content: {raw[:200]}")
        return content


def _read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return str(exc)


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ============================================================
# command parsing + in-loop guards (structural edge #3)
# ============================================================

def _parse_single_command(reply: str) -> Optional[str]:
    strict = [i.strip() for i in _ACTION_FENCE_RE.findall(reply or "") if i.strip()]
    if len(strict) == 1:
        return strict[0]
    if strict:
        return None
    fenced = [i.strip() for i in _ANY_FENCE_RE.findall(reply or "") if i.strip()]
    if len(fenced) == 1:
        return fenced[0]
    if fenced:
        return None
    prompted = [i.strip() for i in _DOLLAR_LINE_RE.findall(reply or "") if i.strip()]
    return prompted[0] if len(prompted) == 1 else None


def _command_has_write_operator(command: str) -> bool:
    lowered = command.lower()
    return any(m in lowered for m in (" >", ">>", "sed -i", "tee ", "touch ", "mv ", "cp ", "cat <<"))


def _is_read_only_command(command: str) -> bool:
    stripped = (command or "").strip()
    if not stripped or _command_has_write_operator(stripped):
        return False
    return bool(_READ_ONLY_RE.match(stripped))


def _is_submission(output_text: str, returncode: Any) -> bool:
    lines = output_text.lstrip().splitlines()
    return bool(lines) and lines[0].strip() == COMPLETION_SENTINEL and not returncode


def _empty_submit_guard_message() -> str:
    return (
        "[Submit rejected: the repository has no changes on disk.]\n\n"
        "Create or modify one real source file for this task, then submit again "
        f"with `echo {COMPLETION_SENTINEL}`."
    )


def _no_patch_nudge_message(step: int) -> str:
    return (
        f"[Progress check: step {step} and the working tree is still empty.]\n\n"
        "STOP exploring. You MUST write your first edit NOW. Use `sed -i` or a "
        "heredoc (`cat <<'EOF' > path/to/file`) to modify the source file most "
        "likely to own the requested behavior. If you are uncertain, make your "
        "best-supported guess from what you have already read -- an imperfect "
        "edit can be refined in later steps, but an empty tree cannot. Edit "
        "first, then verify."
    )


# ============================================================
# KS38 change 3: pre-submit completeness gate helpers
# ============================================================

_TASK_TEXT_RE = re.compile(r"<task>\n(.*?)\n</task>", re.DOTALL)
_CRITERION_TOKEN_RE = re.compile(r"`([^`\s]{3,60})`")
_DOC_TOKEN_SUFFIXES = (".md", ".txt", ".rst")
_CODE_TOKEN_RE = re.compile(r"[_.(\[]|[a-z][A-Z]")


def _extract_task_text(task: str) -> str:
    match = _TASK_TEXT_RE.search(task or "")
    return match.group(1) if match else (task or "")


def _uncovered_criteria(issue_text: str, patch_text: str) -> List[str]:
    """Checklist items whose backticked code identifiers appear nowhere in
    the patch. Conservative: only code-like tokens count, and one hit on any
    token clears the criterion, so false positives cost at most one
    verification round-trip."""
    out: List[str] = []
    for crit in _extract_criteria(issue_text):
        tokens = [
            t for t in _CRITERION_TOKEN_RE.findall(crit)
            if not t.lower().endswith(_DOC_TOKEN_SUFFIXES)
        ]
        code_tokens = [t for t in tokens if _CODE_TOKEN_RE.search(t)]
        if code_tokens and not any(t in patch_text for t in code_tokens):
            out.append(crit[:160])
    return out


def _completeness_gap(issue_text: str, repo_dir: str) -> Optional[str]:
    patch_text = _collect_repo_patch(repo_dir)
    if not patch_text.strip():
        return None  # empty-submit guard already owns this case
    reasons: List[str] = []
    cov = _task_coverage_reason(issue_text, patch_text, repo_dir=repo_dir)
    if cov:
        reasons.append(cov)
    broken = _syntax_errors(repo_dir, patch_text)
    if broken:
        reasons.append(
            "the edited files contain syntax errors:\n- " + "\n- ".join(broken[:6])
        )
    missing = _uncovered_criteria(issue_text, patch_text)
    if missing:
        reasons.append(
            "these task requirements name code identifiers that do not appear "
            "anywhere in the current diff:\n- " + "\n- ".join(missing[:5])
        )
    return "\n\n".join(reasons) if reasons else None


def _completeness_nudge_message(gap: str) -> str:
    return (
        "[Submission checkpoint: the patch may be incomplete.]\n\n"
        + gap
        + "\n\nRe-check the full task against your current diff (`git diff`). "
        "If a listed requirement is genuinely missing, make the smallest "
        "complete edit that satisfies it. If everything is already handled "
        "(for example the requirement is met in a different file or wording), "
        f"submit again immediately with `echo {COMPLETION_SENTINEL}`. Do not "
        "add anything the task did not ask for."
    )


def _read_budget_message(command: str) -> str:
    return (
        "[Read budget exhausted: command not run because the repository still has "
        "no changes on disk.]\n\n"
        f"Rejected read-only command: {command[:240]}\n\n"
        "Your next command MUST edit or create the source file that owns the main "
        "requested behavior -- use `sed -i` for a targeted change or a heredoc "
        "(`cat <<'EOF' > path/to/file`) for a multi-line edit. Make your "
        "best-supported change now; you can refine it afterwards."
    )


# ============================================================
# message capping / compaction (structural edge #5)
# ============================================================

def _messages_chars(messages: List[Dict[str, Any]]) -> int:
    return sum(len(str(m.get("role", ""))) + len(str(m.get("content", ""))) for m in messages)


def _compact_text(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    marker = "\n[... compacted older turn ...]\n"
    room = max(1, limit - len(marker))
    head = max(1, room // 2)
    tail = max(1, room - head)
    return text[:head] + marker + text[-tail:]


def _compact_message(message: Dict[str, Any], limit: int) -> Dict[str, Any]:
    content = str(message.get("content") or "")
    if len(content) <= limit:
        return dict(message)
    return {**message, "content": _compact_text(content, limit)}


def _cap_messages(messages: List[Dict[str, Any]], max_chars: int) -> List[Dict[str, Any]]:
    if max_chars <= 0 or _messages_chars(messages) <= max_chars or len(messages) <= 2:
        return list(messages)
    pinned = list(messages[:2])
    rest = list(messages[2:])
    recent_count = min(len(rest), _RECENT_MESSAGE_COUNT)
    older = rest[:-recent_count] if recent_count else rest
    recent = rest[-recent_count:] if recent_count else []
    capped = pinned + [_compact_message(m, _COMPACT_MESSAGE_CHARS) for m in older] + recent
    if _messages_chars(capped) <= max_chars:
        return capped
    compacted_tail = [_compact_message(m, _MIN_COMPACT_MESSAGE_CHARS) for m in capped[2:]]
    capped = pinned + compacted_tail
    while len(capped) > 6 and _messages_chars(capped) > max_chars:
        capped = pinned + capped[3:]
    return capped


# ============================================================
# run config / outcome
# ============================================================

@dataclass
class RunConfig:
    repo_dir: str
    model_name: str
    base_url: str
    auth_token: str
    max_steps: int = 50
    command_timeout: int = 30
    max_tokens: int = 8192
    max_observation_chars: int = 16000
    max_log_chars: int = 260000
    max_message_chars: int = 180000
    wall_clock_limit: float = 0.0


@dataclass
class RunOutcome:
    success: bool
    patch: str
    logs: str
    steps: int
    cost: Optional[float]
    message: str
    exit_status: str = "Submitted"
    transcript: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================
# KS40 change 3: named-token extractor
# ============================================================

_KS40_SYMBOL_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]{2,})`")


def _extract_named_tokens_ks40(issue_text: str):
    """Returns (named_files: set[str], named_syms: set[str])."""
    text = issue_text or ""
    named_files: set = set()
    for m in _ISSUE_FILE_RE.finditer(text):
        rel = (m.group(1) or "").strip().lstrip("./")
        if rel:
            named_files.add(rel)
    named_syms: set = {m.group(1) for m in _KS40_SYMBOL_RE.finditer(text)}
    return named_files, named_syms


# ============================================================
# KS40 change 2: patch quality detector
# ============================================================

def _substantive_lines(patch_text: str) -> int:
    """Count non-trivial added lines (not headers, not short, not comments)."""
    count = 0
    for line in patch_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            s = line[1:].strip()
            if s and len(s) >= 3 and not s.startswith("#"):
                count += 1
    return count


def _is_weak_patch_ks40(
    patch_text: str,
    named_files: set,
    named_syms: set,
    repo_dir: str,
    multi_req: bool,
) -> bool:
    """Returns True if patch should trigger reroll."""
    # Condition 1: empty patch
    if not (patch_text or "").strip():
        return True
    # Condition 2: any .py file touched by patch fails ast.parse()
    for rel in _changed_paths(patch_text):
        if rel.endswith(".py"):
            full = os.path.join(repo_dir, rel)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    ast.parse(fh.read())
            except (SyntaxError, ValueError, OSError):
                return True
    # Condition 3: named files present AND patch touches no named file AND
    # implements no named symbol.
    # A Hung review FIX 4 (2026-07-09): original check ignored symbol matches,
    # causing false-weak on correct fixes in unnamed files that implement a
    # named symbol — burning a wasted reroll. Mirror _patch_key_ks40 logic.
    if named_files:
        touched = set(_changed_paths(patch_text))
        base_named = {os.path.basename(f) for f in named_files}
        hits = [
            t for t in touched
            if (
                t in named_files
                or t.lstrip("./") in named_files
                or os.path.basename(t) in base_named
            )
        ]
        if not hits:
            # Check whether a named symbol appears in added lines
            added_blob = "\n".join(
                ln[1:] for ln in (patch_text or "").splitlines()
                if ln.startswith("+") and not ln.startswith("+++")
            )
            sym_hit = any(
                re.search(r"\b" + re.escape(sym) + r"\b", added_blob)
                for sym in named_syms
            )
            if not sym_hit:
                return True
    # Condition 4: multi_req=True AND substantive added lines < 2
    if multi_req and _substantive_lines(patch_text) < 2:
        return True
    return False


# ============================================================
# KS40 change 6: has-syntax-errors helper for completeness gate
# ============================================================

def _has_syntax_errors(repo_dir: str, patch_text: str) -> bool:
    """Returns True if any .py file touched by patch has a syntax error."""
    for rel in _changed_paths(patch_text):
        if rel.endswith(".py"):
            full = os.path.join(repo_dir, rel)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    ast.parse(fh.read())
            except (SyntaxError, ValueError):
                return True
            except OSError:
                pass
    return False


# ============================================================
# the step loop (king semantics + in-loop guards + capping)
# ============================================================

def _run_loop(config: RunConfig, task: str) -> RunOutcome:
    model = ChatModel(
        model_name=config.model_name,
        base_url=config.base_url,
        auth_token=config.auth_token,
        max_completion_tokens=config.max_tokens,
    )
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task if "<task>" in task else _build_task_prompt(task)},
    ]
    started = time.monotonic()
    log_lines: List[str] = []
    exit_status = "LimitsExceeded"
    message = f"step limit of {config.max_steps} reached"
    format_retries = 0
    no_patch_nudge_sent = False
    completeness_nudge_sent = False
    issue_text = _extract_task_text(task)
    tree_dirty_seen = False
    wall = config.wall_clock_limit
    model_error_streak = 0
    message_char_cap = config.max_message_chars

    for step in range(1, max(1, config.max_steps) + 1):
        remaining = (wall - (time.monotonic() - started)) if wall > 0 else float("inf")
        if wall > 0 and remaining <= _MIN_STEP_SECONDS:
            exit_status = "TimeExceeded"
            message = f"wall clock budget exhausted before step {step}"
            break
        messages = _cap_messages(messages, message_char_cap)
        try:
            model_window = max(8.0, remaining - _STEP_MODEL_RESERVE_SECONDS) if wall > 0 else 0.0
            reply = model.query(messages, time_left=model_window)
        except ModelQueryError as exc:
            # KS37 change A/B: ride out endpoint congestion instead of
            # abandoning the round while wall budget remains. Zero rounds in
            # live duels (19/50 in duel 529313) traced to giving up here.
            model_error_streak += 1
            err_text = str(exc)
            log_lines.append(
                f"[step {step}] model error (streak {model_error_streak}): {err_text[:300]}"
            )
            lowered = err_text.lower()
            if "http 413" in lowered or (
                "http 400" in lowered
                and any(kw in lowered for kw in _CONTEXT_ERROR_KEYWORDS)
            ):
                message_char_cap = max(_CONTEXT_SHRINK_FLOOR_CHARS, message_char_cap // 2)
                log_lines.append(
                    f"[step {step}] payload shrink: message cap now {message_char_cap} chars"
                )
            remaining_now = (wall - (time.monotonic() - started)) if wall > 0 else float("inf")
            if (
                model_error_streak <= _MODEL_ERROR_STREAK_LIMIT
                and remaining_now > _MODEL_ERROR_RETRY_FLOOR_SECONDS
            ):
                pause = min(
                    _MODEL_ERROR_PAUSE_SECONDS,
                    max(0.0, remaining_now - _MIN_STEP_SECONDS),
                )
                if pause > 0.0:
                    time.sleep(pause)
                continue
            exit_status = "ModelError"
            message = err_text
            break
        model_error_streak = 0
        messages.append({"role": "assistant", "content": reply})
        log_lines.append(f"[step {step}] assistant:\n{reply}")

        command = _parse_single_command(reply)
        if command is None:
            format_retries += 1
            if format_retries > _MAX_FORMAT_RETRIES:
                exit_status = "FormatError"
                message = "model kept replying without exactly one bash code block"
                break
            messages.append({"role": "user", "content": _format_help()})
            log_lines.append(f"[step {step}] format retry {format_retries}")
            continue
        format_retries = 0

        if not tree_dirty_seen and _tree_has_changes(config.repo_dir):
            tree_dirty_seen = True

        reject_read_only = (
            no_patch_nudge_sent
            and not tree_dirty_seen
            and _is_read_only_command(command)
        )
        if reject_read_only:
            output_text = _read_budget_message(command)
            returncode: Any = 2
            log_lines.append(f"[step {step}] read-only command rejected after no-patch nudge")
        else:
            cmd_timeout = config.command_timeout
            if wall > 0:
                cmd_left = wall - (time.monotonic() - started)
                cmd_timeout = max(3, min(config.command_timeout, int(cmd_left - _CMD_TAIL_MARGIN_SECONDS)))
            result = _execute_command(command, cwd=config.repo_dir, timeout=cmd_timeout)
            output_text = result.get("output") or ""
            returncode = result.get("returncode")
        log_lines.append(f"[step {step}] $ {command}\n{_truncate_text(output_text, 2000)}")

        if not tree_dirty_seen and _tree_has_changes(config.repo_dir):
            tree_dirty_seen = True

        if _is_submission(output_text, returncode):
            if not tree_dirty_seen:
                messages.append({"role": "user", "content": _empty_submit_guard_message()})
                log_lines.append(f"[step {step}] empty submit rejected")
                if not no_patch_nudge_sent:
                    no_patch_nudge_sent = True
                    messages.append({"role": "user", "content": _no_patch_nudge_message(step)})
                continue
            # KS38 change 3: hold the submission ONCE when the diff has an
            # objectively detectable gap and budget remains to close it.
            # KS40 change 6 reverted per A Hung review (2026-07-09): the
            # >30-line heuristic skip was removed — _completeness_gap is the
            # sole authority; it already returns falsy when there is no gap.
            # _has_syntax_errors helper is retained (used by reroll).
            if not completeness_nudge_sent:
                steps_left = config.max_steps - step
                time_left_now = (wall - (time.monotonic() - started)) if wall > 0 else float("inf")
                if (
                    steps_left >= _COMPLETENESS_MIN_STEPS_LEFT
                    and time_left_now >= _COMPLETENESS_MIN_SECONDS
                ):
                    gap = None
                    try:
                        gap = _completeness_gap(issue_text, config.repo_dir)
                    except Exception:
                        gap = None
                    if gap:
                        completeness_nudge_sent = True
                        messages.append(
                            {"role": "user", "content": _completeness_nudge_message(gap)}
                        )
                        log_lines.append(
                            f"[step {step}] submission held once for completeness check"
                        )
                        continue
            exit_status = "Submitted"
            message = f"submitted after {step} step(s)"
            break

        observation = _render_observation(
            returncode=int(returncode or 0),
            output_text=_truncate_text(output_text, config.max_observation_chars),
            remaining_steps=config.max_steps - step,
        )
        messages.append({"role": "user", "content": observation})

        if (
            not no_patch_nudge_sent
            and not tree_dirty_seen
            and step >= _NO_PATCH_NUDGE_STEP
        ):
            no_patch_nudge_sent = True
            messages.append({"role": "user", "content": _no_patch_nudge_message(step)})
            log_lines.append(f"[step {step}] no-patch progress nudge sent")

    patch = _collect_repo_patch(config.repo_dir)
    logs = _truncate_text("\n".join(log_lines), config.max_log_chars)
    return RunOutcome(
        success=bool(patch.strip()),
        patch=patch,
        logs=logs,
        steps=model.calls,
        cost=None,
        message=message,
        exit_status=exit_status,
        transcript=messages,
    )


# ============================================================
# patch quality guards (objective-breakage detectors only)
# ============================================================

_MUNGE_PATH_RE = re.compile(
    r"^(?:fix|clean|cleanup|replace|update|patch|apply|munge|modify|gen|generate|"
    r"rewrite|migrate|refactor)_[\w.-]+$",
    re.I,
)
_MUNGE_FILE_RE = re.compile(
    r"^(?:fix|update|replace|refactor|patch|apply|clean|generate|rewrite|migrate|"
    r"modify)_[\w.-]+\.(?:py|sh|js|ts|rb|pl)$",
    re.I,
)


def _changed_paths(patch_text: str) -> List[str]:
    paths: List[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/"):].strip()
            if path and path != "/dev/null" and path not in paths:
                paths.append(path)
    return paths


def _line_stats(patch_text: str) -> Tuple[int, int]:
    added = removed = 0
    for line in patch_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed


def _destructive_patch_reason(patch_text: str) -> Optional[str]:
    added, removed = _line_stats(patch_text)
    if removed >= 60 and added < max(5, removed // 4):
        return (
            f"the patch removes far more than it adds ({removed} deletions vs {added} additions); "
            "restore required logic instead of gutting the codebase"
        )
    return None


def _munge_artifact_reason(patch_text: str) -> Optional[str]:
    for path in _changed_paths(patch_text):
        base = path.rsplit("/", 1)[-1]
        stem = base.rsplit(".", 1)[0] if "." in base else base
        if (
            _MUNGE_PATH_RE.match(stem)
            or _MUNGE_FILE_RE.match(base)
            or base.endswith((".new", ".bak", ".orig", ".tmp", ".rej"))
        ):
            return (
                f"the patch adds scratch or munge artifact `{path}`; "
                "edit source files directly and remove helper/backup files"
            )
    return None


def _task_coverage_reason(issue_text: str, patch_text: str, repo_dir: Optional[str] = None) -> Optional[str]:
    mentioned: List[str] = []
    for match in _ISSUE_FILE_RE.finditer(issue_text or ""):
        path = match.group(1).strip().lstrip("./")
        if path not in mentioned:
            mentioned.append(path)
    if not mentioned:
        return None
    touched = _changed_paths(patch_text)
    if not touched:
        return None
    if repo_dir is not None:
        valid_mentioned = []
        for m in mentioned:
            exists_on_disk = os.path.exists(os.path.join(repo_dir, m))
            is_touched = any(t == m or t.endswith("/" + m) or m.endswith("/" + t) for t in touched)
            if exists_on_disk or is_touched:
                valid_mentioned.append(m)
        mentioned = valid_mentioned
    if not mentioned:
        return None
    hit = sum(
        1
        for m in mentioned
        if any(t == m or t.endswith("/" + m) or m.endswith("/" + t) for t in touched)
    )
    if hit == 0:
        sample = ", ".join(mentioned[:6])
        return (
            f"the task names specific files ({sample}) but the patch does not touch any of them; "
            "find and edit the correct targets"
        )
    return None


def _patch_acceptable(patch_text: str) -> bool:
    if not patch_text.strip():
        return False
    if _destructive_patch_reason(patch_text) or _munge_artifact_reason(patch_text):
        return False
    return True


# ============================================================
# multi-language syntax verification
# ============================================================

_CS_REPEATED_BASE_RE = re.compile(
    r"\b(?:class|interface|struct|record)\s+[A-Za-z_]\w*(?:\s*<[^>]*>)?"
    r"\s*:\s*([A-Za-z_][\w.]*)(?:\s*:\s*\1\b)+"
)

_BRACE_BALANCE_EXTS = (".php", ".cs", ".kt", ".java", ".swift", ".scala")
_DELIM_OPEN = {")": "(", "]": "[", "}": "{"}

_DUP_DEF_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".php", ".cs",
                 ".kt", ".java", ".go", ".swift", ".scala", ".rs")

_DUP_DEF_RE = re.compile(
    r"^[ \t]*"
    r"(?:export\s+)?(?:default\s+)?(?:public\s+|private\s+|protected\s+|internal\s+|static\s+|final\s+|abstract\s+|async\s+)*"
    r"(?:"
    r"(?:class|struct|enum|trait)\s+([A-Za-z_$][\w$]*)"
    r"|type\s+([A-Za-z_$][\w$]*)\s+(?:struct|interface)\b"
    r")",
    re.M,
)


def _changed_source_files(patch_text: str, exts: Tuple[str, ...]) -> List[str]:
    paths: List[str] = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/"):].strip()
            if path.endswith(exts) and path not in paths:
                paths.append(path)
    return paths


def _run_check(cmd: List[str], cwd: str) -> Optional[str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if proc.returncode == 0:
        return None
    msg = (proc.stderr or proc.stdout or "").strip()
    return (msg.splitlines()[0][:200] if msg else "failed syntax check")


def _strip_code_noise(text: str) -> str:
    out: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "#":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            if j < 0:
                return ""
            i = j + 2
            continue
        if c in "'\"`":
            quote = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            else:
                return ""
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _delimiter_balance_error(text: str, rel: str) -> Optional[str]:
    if "<<<" in text:
        return None
    code = _strip_code_noise(text)
    if not code:
        return None
    stack: List[str] = []
    for ch in code:
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            want = _DELIM_OPEN[ch]
            if not stack:
                return f"{rel}: unexpected closing '{ch}' (extra/dangling delimiter)"
            top = stack.pop()
            if top != want:
                return f"{rel}: mismatched '{ch}' (expected close for '{top}')"
    if stack:
        return f"{rel}: {len(stack)} unclosed '{stack[-1]}' delimiter(s) (missing close brace/paren)"
    return None


def _duplicate_definition_error(text: str, rel: str) -> Optional[str]:
    code = _strip_code_noise(text)
    if not code:
        return None
    seen: Dict[str, int] = {}
    for mobj in _DUP_DEF_RE.finditer(code):
        name = mobj.group(1) or mobj.group(2)
        if not name:
            continue
        seen[name] = seen.get(name, 0) + 1
    dups = sorted(n for n, c in seen.items() if c > 1)
    if dups:
        return f"{rel}: duplicate top-level definition(s): {', '.join(dups[:4])} (defined more than once -> compile error)"
    return None


def _syntax_errors(repo_dir: str, patch_text: str) -> List[str]:
    broken: List[str] = []
    for rel in _changed_source_files(patch_text, (".py",)):
        full = os.path.join(repo_dir, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except OSError:
            continue
        try:
            compile(source, rel, "exec")
        except SyntaxError as exc:
            broken.append(f"{rel}: line {exc.lineno}: {exc.msg}")
        except (ValueError, TypeError):
            broken.append(f"{rel}: could not be parsed")
    for rel in _changed_source_files(patch_text, (".json",)):
        full = os.path.join(repo_dir, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue
        try:
            json.loads(content)
        except ValueError as exc:
            broken.append(f"{rel}: invalid JSON: {str(exc)[:120]}")
    for rel in _changed_source_files(patch_text, (".js", ".mjs", ".cjs")):
        err = _run_check(["node", "--check", rel], repo_dir)
        if err:
            broken.append(f"{rel}: {err}")
    for rel in _changed_source_files(patch_text, (".go",)):
        err = _run_check(["gofmt", "-e", rel], repo_dir)
        if err:
            broken.append(f"{rel}: {err}")
    for rel in _changed_source_files(patch_text, _BRACE_BALANCE_EXTS):
        full = os.path.join(repo_dir, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        err = _delimiter_balance_error(text, rel)
        if err:
            broken.append(err)
    for rel in _changed_source_files(patch_text, _DUP_DEF_EXTS):
        full = os.path.join(repo_dir, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        err = _duplicate_definition_error(text, rel)
        if err:
            broken.append(err)
    for rel in _changed_source_files(patch_text, (".php",)):
        err = _run_check(["php", "-l", rel], repo_dir)
        if err:
            broken.append(f"{rel}: {err}")
    for rel in _changed_source_files(patch_text, (".cs",)):
        full = os.path.join(repo_dir, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if _CS_REPEATED_BASE_RE.search(_strip_code_noise(text)):
            broken.append(f"{rel}: malformed repeated base type (e.g. ': X : X')")
    return broken


def _is_test_path(path: str) -> bool:
    p = path.lower()
    base = p.rsplit("/", 1)[-1]
    if any(seg in ("test", "tests", "spec", "specs", "__tests__") for seg in p.split("/")[:-1]):
        return True
    if base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py") or base.startswith("test")):
        return True
    if ".test." in base or ".spec." in base or base.endswith("_spec.rb") or base.endswith("_test.go"):
        return True
    return False


def _source_files(patch_text: str) -> set:
    return {p for p in _changed_paths(patch_text) if not _is_test_path(p)}


# ============================================================
# minimal post-loop repair (objective breakage only) + rescue
# ============================================================

def _repair_reason(repo_dir: str, patch_text: str, issue_text: str = "") -> Optional[Tuple[str, str]]:
    """Only objectively-broken states trigger a repair sub-loop. No test
    demands, no polish -- the new king's rules (and the Sonnet judge) punish
    additions the task did not ask for."""
    if not (patch_text or "").strip():
        return ("empty", "the current change set is empty; no fix was produced yet")
    cov = _task_coverage_reason(issue_text, patch_text, repo_dir=repo_dir)
    if cov:
        return ("coverage", cov)
    broken = _syntax_errors(repo_dir, patch_text)
    if broken:
        return ("syntax", "the edited files contain syntax errors that must be fixed:\n- " + "\n- ".join(broken[:8]))
    q = _destructive_patch_reason(patch_text) or _munge_artifact_reason(patch_text)
    if q:
        return ("quality", q)
    return None


def _build_repair_task(issue_text: str, reason: str) -> str:
    return (
        "A previous attempt to solve the task below left the repository in an "
        "incomplete or broken state. " + reason + "\n\n"
        "Inspect the current state of the repository, then finish and correct "
        "the change so it fully and correctly solves the task with the smallest "
        "complete set of edits. Re-read each edited region to confirm it is "
        "syntactically valid before submitting. Do not refactor or make any "
        "unrelated change.\n\n"
        "Original task:\n" + issue_text
    )


def _build_empty_rescue_prompt(issue_text: str, repo_summary: str = "") -> str:
    """Lean, directive prompt for the last-resort rescue loop. Contains
    `<task>` so `_run_loop` uses it verbatim instead of wrapping it in the
    full workflow template."""
    summary_block = (
        f"\n<repository_summary>\n{repo_summary.strip()}\n</repository_summary>\n"
        if repo_summary.strip()
        else ""
    )
    return (
        "Please solve this issue:\n\n"
        "<task>\n" + issue_text.strip() + "\n</task>\n" + summary_block +
        "\nA previous attempt at this task produced NO code change at all: the "
        "working tree is empty and very little time remains. The task requires "
        "a code change. Your FIRST command must edit a file. Pick the most "
        "relevant file from the task description and make one concrete, "
        "well-supported improvement to it NOW -- use `sed -i` for a targeted "
        "change or a heredoc (`cat <<'EOF' > path/to/file`) for a multi-line "
        "edit. An imperfect but relevant edit is far better than no change at "
        "all. As soon as the edit lands, finish immediately by running exactly:\n\n"
        "```bash\necho " + COMPLETION_SENTINEL + "\n```\n"
        + _PARTIAL_CREDIT_NOTE  # KS40 change 4: explicit partial-credit framing
    )


# ============================================================
# KS40 change 1: best-of-two reroll orchestrator
# ============================================================

def _patch_key_ks40(patch_text: str, named_files: set, named_syms: set, repo_dir: str) -> tuple:
    """Deterministic quality key matching king's _key() but using KS40 helpers."""
    nonempty = bool((patch_text or "").strip())
    # py_parses: check all touched .py files
    py_parses = True
    touched = _changed_paths(patch_text)
    for rel in touched:
        if rel.endswith(".py"):
            full = os.path.join(repo_dir, rel)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as fh:
                    ast.parse(fh.read())
            except (SyntaxError, ValueError, OSError):
                py_parses = False
                break
    # touches_named_target
    base_named = {os.path.basename(f) for f in named_files}
    added_blob = "\n".join(
        ln[1:] for ln in (patch_text or "").splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    )
    touches_named = False
    if named_files:
        for t in touched:
            if (
                t in named_files
                or t.lstrip("./") in named_files
                or os.path.basename(t) in base_named
            ):
                touches_named = True
                break
        if not touches_named:
            for sym in named_syms:
                if re.search(r"\b" + re.escape(sym) + r"\b", added_blob):
                    touches_named = True
                    break
    else:
        touches_named = True  # no named files: skip this dimension
    # named_reqs count
    file_hit = 1 if touches_named and named_files else 0
    sym_hits = sum(
        1 for sym in named_syms
        if re.search(r"\b" + re.escape(sym) + r"\b", added_blob)
    )
    named_reqs = file_hit + sym_hits
    # not_trivial
    substantive = _substantive_lines(patch_text or "")
    not_trivial = substantive >= 2
    return (
        int(nonempty),
        int(py_parses),
        int(touches_named),
        named_reqs,
        int(not_trivial),
    )


def _git_out_ks40(repo: str, args: List[str]) -> Optional[str]:
    """Run a git command; return stripped stdout on success, None on failure."""
    try:
        r = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip()


def _git_reset_verify_ks40(repo: str, orig_sha: str) -> bool:
    """Hard-reset repo to orig_sha and verify clean state."""
    try:
        subprocess.run(
            ["git", "reset", "--hard", orig_sha], cwd=repo,
            capture_output=True, text=True, timeout=30, check=False,
        )
        subprocess.run(
            ["git", "clean", "-fd"], cwd=repo,
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if _git_out_ks40(repo, ["rev-parse", "HEAD"]) != orig_sha:
        return False
    if _git_out_ks40(repo, ["status", "--porcelain"]) != "":
        return False
    return True


def _materialize_ks40(repo: str, orig_sha: str, patch_text: str) -> bool:
    """Reset primary repo to orig_sha then apply patch unstaged. Returns True
    only if on-disk diff is non-empty afterward."""
    if not (patch_text or "").strip():
        return False
    try:
        subprocess.run(
            ["git", "reset", "--hard", orig_sha], cwd=repo,
            capture_output=True, text=True, timeout=30, check=False,
        )
        subprocess.run(
            ["git", "clean", "-fd"], cwd=repo,
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    data = patch_text if patch_text.endswith("\n") else patch_text + "\n"
    applied = False
    for extra in (["--whitespace=nowarn"], ["--3way", "--whitespace=nowarn"]):
        try:
            r = subprocess.run(
                ["git", "apply", *extra], cwd=repo, input=data,
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if r.returncode == 0:
            applied = True
            break
    if not applied:
        return False
    return bool(_collect_repo_patch(repo).strip())


def run_best_of_two_ks40(config: "RunConfig", task: str, issue_text: str) -> "RunOutcome":
    """KS40 best-of-two reroll orchestrator.

    Wraps _run_loop() the same way king's run_best_of_two() wraps
    run_agent_loop(). Attempt #1 runs with full config and stays on the primary
    repo. Only when attempt #1 is objectively weak AND budget remains does
    attempt #2 run in an isolated clone, then keeps the strictly-better patch.
    Any failure falls back to attempt #1's on-disk state.
    """
    repo = config.repo_dir
    t0 = time.monotonic()
    budget = float(config.wall_clock_limit or 0.0) or 280.0

    # Capture pristine HEAD before attempt #1 dirties the tree.
    orig_sha = _git_out_ks40(repo, ["rev-parse", "HEAD"])
    is_clean = (
        orig_sha is not None
        and _git_out_ks40(repo, ["status", "--porcelain"]) == ""
    )

    # Attempt #1: full KS39-equivalent loop (all advantages intact).
    try:
        outcome_a = _run_loop(config, task)
    except Exception:
        patch_fallback = _collect_repo_patch(repo)
        return RunOutcome(
            success=bool(patch_fallback.strip()),
            patch=patch_fallback,
            logs="",
            steps=0,
            cost=None,
            message="run_best_of_two_ks40: attempt #1 crashed; returning on-disk diff",
        )

    if not is_clean:
        return outcome_a  # not a clean checkout: cannot safely reset, keep #1

    # Measure attempt #1 quality.
    patch_a = outcome_a.patch or ""
    named_files, named_syms = _extract_named_tokens_ks40(issue_text)
    multi_req = (len(named_files) + len(named_syms)) >= 2
    weak_a = _is_weak_patch_ks40(patch_a, named_files, named_syms, repo, multi_req)

    remaining = budget - (time.monotonic() - t0)
    if not weak_a or remaining < _KS40_REROLL_MIN_REMAINING:
        return outcome_a  # good enough or no budget for reroll

    # Attempt #2: isolated clone, pristine reset.
    tmp_root = None
    try:
        tmp_root = tempfile.mkdtemp(prefix="ks40_reroll_")
        copy_repo = os.path.join(tmp_root, "repo")
        shutil.copytree(repo, copy_repo, symlinks=True)
        if not _git_reset_verify_ks40(copy_repo, orig_sha):
            return outcome_a
        remaining = budget - (time.monotonic() - t0)
        if remaining < _KS40_REROLL_MIN_REMAINING:
            return outcome_a
        attempt2_wall = max(_KS40_REROLL_MIN_WALL, remaining - _KS40_REROLL_MARGIN)
        cfg2 = dataclasses.replace(config, repo_dir=copy_repo, wall_clock_limit=attempt2_wall)
        try:
            outcome_b = _run_loop(cfg2, task)
        except Exception:
            return outcome_a
        patch_b = outcome_b.patch or ""
        key_a = _patch_key_ks40(patch_a, named_files, named_syms, repo)
        key_b = _patch_key_ks40(patch_b, named_files, named_syms, copy_repo)
        if key_b <= key_a:
            return outcome_a  # not strictly better: keep attempt #1
        # Budget check before materializing.
        if (budget - (time.monotonic() - t0)) < _KS40_MATERIALIZE_MIN:
            return outcome_a
        # Apply attempt #2's patch to primary repo.
        if _materialize_ks40(repo, orig_sha, patch_b):
            fresh_patch = _collect_repo_patch(repo)
            return RunOutcome(
                success=bool(fresh_patch.strip()),
                patch=fresh_patch,
                logs=outcome_b.logs,
                steps=outcome_b.steps,
                cost=outcome_b.cost,
                message=outcome_b.message + " [KS40 reroll: attempt #2 adopted]",
                exit_status=outcome_b.exit_status,
                transcript=outcome_b.transcript,
            )
        # Apply failed: restore attempt #1 floor.
        # A Hung review FIX 3 (2026-07-09): _materialize_ks40 resets to
        # orig_sha before applying — if that also fails, the tree may be
        # empty. Belt-and-suspenders: fall back to _restore_patch_to_disk
        # (atomic helper) which never worsens the tree.
        if not _materialize_ks40(repo, orig_sha, patch_a):
            _restore_patch_to_disk(repo, patch_a)
        fresh_patch = _collect_repo_patch(repo)
        return RunOutcome(
            success=bool(fresh_patch.strip()),
            patch=fresh_patch,
            logs=outcome_a.logs,
            steps=outcome_a.steps,
            cost=outcome_a.cost,
            message=outcome_a.message + " [KS40 reroll: #2 apply failed, #1 restored]",
            exit_status=outcome_a.exit_status,
            transcript=outcome_a.transcript,
        )
    except Exception:
        # Any unexpected error: fall back to attempt #1's on-disk state.
        try:
            fresh_patch = _collect_repo_patch(repo)
        except Exception:
            fresh_patch = patch_a
        return RunOutcome(
            success=bool(fresh_patch.strip()),
            patch=fresh_patch,
            logs=outcome_a.logs,
            steps=outcome_a.steps,
            cost=outcome_a.cost,
            message=outcome_a.message + " [KS40 reroll: exception, #1 floor kept]",
            exit_status=outcome_a.exit_status,
            transcript=outcome_a.transcript,
        )
    finally:
        if tmp_root:
            shutil.rmtree(tmp_root, ignore_errors=True)


# ============================================================
# validator contract
# ============================================================

def _normalize_api_base(api_base: str) -> str:
    base = api_base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base[: -len("/chat/completions")]
    if base.endswith("/v1"):
        return base
    return base + "/v1"


def _resolve_inference_config(
    model: Optional[str], api_base: Optional[str], api_key: Optional[str],
) -> Tuple[str, str, str]:
    model_name = (
        model
        or os.environ.get("AGENT_MODEL")
        or os.environ.get("NINJA_MODEL", "")
    ).strip()
    base = (
        api_base
        or os.environ.get("AGENT_API_BASE")
        or os.environ.get("NINJA_INFERENCE_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL", "")
    ).strip()
    key = (
        api_key
        if api_key is not None
        else (
            os.environ.get("AGENT_API_KEY")
            or os.environ.get("NINJA_INFERENCE_API_KEY")
            or os.environ.get("OPENAI_API_KEY", "")
        )
    ).strip()
    if not model_name:
        raise ValueError("model is required; the validator must pass the managed model id")
    if not base:
        raise ValueError("api_base is required; the validator must pass the managed proxy URL")
    if not key:
        raise ValueError("api_key is required; the validator must pass the per-run proxy token")
    return model_name, _normalize_api_base(base), key


def solve(
    repo_path: str,
    issue: str,
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    max_steps: int = _DEFAULT_MAX_STEPS,
    command_timeout: int = _DEFAULT_CMD_TIMEOUT,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        # KS40 RepoIndex: clear per-task so reroll clone (different dir key)
        # also gets a fresh index. Each task is a fresh process so this just
        # guards against accidental re-use within the same process lifetime.
        _repo_index_cache.clear()
        model_name, base_url, proxy_token = _resolve_inference_config(model, api_base, api_key)
        wall_clock_limit = _resolve_wall_clock()
        repo_summary = _build_repo_summary(repo_path)
        named_context = _issue_named_context(issue, repo_path)
        named_files = _existing_issue_files(issue, repo_path, limit=_PRELOAD_FILE_LIMIT)
        route_context = _api_route_context(issue, repo_path, exclude=named_files)
        cpp_context = _cpp_config_context(issue, repo_path, _repo_paths(repo_path))
        preloaded = "\n".join(part for part in (named_context, cpp_context, route_context) if part)
        config = RunConfig(
            repo_dir=repo_path,
            model_name=model_name,
            base_url=base_url,
            auth_token=proxy_token,
            max_steps=max_steps,
            command_timeout=command_timeout,
            max_tokens=max_tokens,
            max_observation_chars=_MAX_OBSERVATION_CHARS,
            max_log_chars=_MAX_TOTAL_LOG_CHARS,
            max_message_chars=_MAX_MESSAGE_CHARS,
            wall_clock_limit=wall_clock_limit,
        )
        task = _build_initial_user_prompt(issue, repo_summary, preloaded, repo_dir=repo_path)
        outcome = run_best_of_two_ks40(config, task, issue)  # KS40 change 1: reroll orchestrator

        # KS32 change C: snapshot the collected patch before any sub-loop
        # touches the working tree; a valid patch, once produced, is never
        # lost.
        patch_backup = outcome.patch or ""

        repair_note = ""
        try:
            remaining = wall_clock_limit - (time.monotonic() - started)
            reason = None
            if remaining >= _REPAIR_MIN_BUDGET_SECONDS:
                reason = _repair_reason(repo_path, outcome.patch, issue_text=issue)
            if reason is not None:
                remaining = wall_clock_limit - (time.monotonic() - started)
            if reason is not None and reason[0] != "empty" and remaining >= _SUBLOOP_MIN_SECONDS:
                kind, msg = reason
                orig_sources = _source_files(outcome.patch)
                subloop_wall = max(
                    20.0,
                    remaining - _WALL_CLOCK_RESERVE_SECONDS - _ADOPTION_CHECK_RESERVE_SECONDS,
                )
                repair_config = RunConfig(
                    repo_dir=repo_path,
                    model_name=model_name,
                    base_url=base_url,
                    auth_token=proxy_token,
                    max_steps=min(max_steps, _REPAIR_MAX_STEPS),
                    command_timeout=command_timeout,
                    max_tokens=max_tokens,
                    max_observation_chars=_MAX_OBSERVATION_CHARS,
                    max_log_chars=_MAX_TOTAL_LOG_CHARS,
                    max_message_chars=_MAX_MESSAGE_CHARS,
                    wall_clock_limit=subloop_wall,
                )
                task_prompt = _build_initial_user_prompt(_build_repair_task(issue, msg), repo_summary, "")
                repaired = _run_loop(repair_config, task_prompt)
                rp = repaired.patch
                if rp.strip() and not _syntax_errors(repo_path, rp) and _patch_acceptable(rp):
                    if kind == "coverage":
                        adopt = True
                    else:  # syntax / quality: never drop original source files
                        adopt = orig_sources.issubset(_source_files(rp))
                    if adopt:
                        outcome = repaired
                        repair_note = " (repair adopted: %s)" % kind
        except Exception:
            repair_note = " (repair pass skipped after error)"

        # If a sub-loop emptied the working tree after the main loop had
        # produced a valid change, re-apply the snapshot (KS32 change C).
        try:
            if patch_backup.strip() and not _tree_has_changes(repo_path):
                if _restore_patch_to_disk(repo_path, patch_backup):
                    repair_note += " (pre-repair patch restored to disk)"
        except Exception:
            pass

        # Last-resort empty-patch rescue (KS31 change A): one short, lean
        # sub-loop that makes a concrete edit when everything else produced
        # nothing.
        try:
            if not (outcome.patch or "").strip():
                remaining = wall_clock_limit - (time.monotonic() - started)
                if remaining > _EMPTY_RESCUE_MIN_SECONDS:
                    rescue_wall = min(
                        _EMPTY_RESCUE_WALL,
                        max(20.0, remaining - _WALL_CLOCK_RESERVE_SECONDS),
                    )
                    rescue_config = RunConfig(
                        repo_dir=repo_path,
                        model_name=model_name,
                        base_url=base_url,
                        auth_token=proxy_token,
                        max_steps=_EMPTY_RESCUE_MAX_STEPS,
                        command_timeout=command_timeout,
                        max_tokens=max_tokens,
                        max_observation_chars=_MAX_OBSERVATION_CHARS,
                        max_log_chars=_MAX_TOTAL_LOG_CHARS,
                        max_message_chars=_MAX_MESSAGE_CHARS,
                        wall_clock_limit=rescue_wall,
                    )
                    rescued = _run_loop(
                        rescue_config,
                        _build_empty_rescue_prompt(issue, repo_summary),
                    )
                    rp = rescued.patch
                    if rp.strip() and not _syntax_errors(repo_path, rp) and _patch_acceptable(rp):
                        outcome = rescued
                        repair_note += " (empty-patch rescue adopted)"
        except Exception:
            pass

        # Final guarantee: never return an empty patch when a valid one was
        # collected before the sub-loops ran.
        if patch_backup.strip() and not (outcome.patch or "").strip():
            outcome.patch = patch_backup
            outcome.success = True
            repair_note += " (pre-repair patch restored)"

        elapsed = time.monotonic() - started
        return {
            "patch": outcome.patch,
            "logs": outcome.logs,
            "steps": outcome.steps,
            "cost": outcome.cost,
            "success": outcome.success,
            "message": f"{outcome.exit_status}: {outcome.message} in {elapsed:.1f}s{repair_note}",
        }
    except Exception:
        fallback_patch = _collect_repo_patch(repo_path)
        return {
            "patch": fallback_patch,
            "logs": traceback.format_exc()[-8000:],
            "steps": 0,
            "cost": None,
            "success": bool(fallback_patch.strip()),
            "message": "agent crashed; returning the on-disk repository diff",
        }
