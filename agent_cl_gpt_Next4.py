#!/usr/bin/env python3
"""SN66 Ninja miner — Next4.

Built on new king (01c675065c1c): verify-repair pass intact.

Changes over Next2-v3:
- Removed conflicting SYSTEM_PROMPT additions (completeness/AC framing conflicts with king TASK_TEMPLATE).
- Kept only BUGFIX minimal-change rule (targeted, non-conflicting).
- Added correctness-demonstration nudge to task-type protocols.
- Extended TASK_TEMPLATE Workflow with prioritised 5-step process.
- Improved task-type detection: added REFACTOR type, tightened UPDATE keywords.
"""

from __future__ import annotations


# ============================================================
# Inlined from: agent/environment.py
# ============================================================

"""Local bash execution environment. Each action runs in a fresh subshell
at the repository root with merged stdout/stderr."""

import os
import subprocess

_QUIET_TOOL_DEFAULTS = {
    "PAGER": "cat",
    "MANPAGER": "cat",
    "LESS": "-R",
    "PIP_PROGRESS_BAR": "off",
    "TQDM_DISABLE": "1",
    "NO_COLOR": "1",
    "GIT_PAGER": "cat",
    # Keep verification runs from leaving __pycache__/*.pyc behind, which
    # repo_diff could otherwise sweep into the final patch as binary churn.
    "PYTHONDONTWRITEBYTECODE": "1",
}


def execute_command(command: str, *, cwd: str, timeout: int) -> dict:
    env = os.environ.copy()
    env.update(_QUIET_TOOL_DEFAULTS)
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, int(timeout)),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": completed.stdout or "", "returncode": completed.returncode}
    except subprocess.TimeoutExpired as exc:
        partial = exc.output or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        return {
            "output": f"{partial}\n[command timed out after {timeout} seconds]",
            "returncode": 124,
        }
    except (OSError, ValueError) as exc:
        return {"output": f"[command could not be executed: {exc}]", "returncode": -1}


def truncate_text(text: str, limit: int) -> str:
    """Head/tail elision so long outputs keep their start and end visible."""
    if limit <= 0 or len(text) <= limit:
        return text
    half = max(1, limit // 2)
    elided = len(text) - 2 * half
    return f"{text[:half]}\n[... {elided} characters elided ...]\n{text[-half:]}"

# ============================================================
# Inlined from: agent/model.py
# ============================================================

"""Minimal OpenAI-compatible chat client.
Standard library only; the endpoint and token always come from the
validator-managed proxy configuration passed into agent.solve()."""

import json
import time
import urllib.error
import urllib.request

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class ModelQueryError(RuntimeError):
    pass


class ChatModel:
    def __init__(
        self,
        *,
        model_name: str,
        base_url: str,
        auth_token: str,
        max_completion_tokens: int = 0,
        request_timeout: float = 180.0,
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

    def query(self, messages: list) -> str:
        """Send the conversation and return the assistant message text."""
        payload = {"model": self.model_name, "messages": messages}
        if self.max_completion_tokens > 0:
            payload["max_tokens"] = self.max_completion_tokens
        body = json.dumps(payload).encode("utf-8")
        last_error = "unknown error"
        for attempt in range(1, self.max_attempts + 1):
            try:
                raw = self._post(body)
            except urllib.error.HTTPError as exc:
                detail = _read_error_body(exc)
                last_error = f"HTTP {exc.code}: {detail[:300]}"
                if exc.code not in _RETRYABLE_STATUS:
                    raise ModelQueryError(f"model request was rejected: {last_error}") from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                self.calls += 1
                return self._extract_content(raw)
            if attempt < self.max_attempts:
                time.sleep(min(20.0, 1.5 ** attempt))
        raise ModelQueryError(f"model request failed after {self.max_attempts} attempts: {last_error}")

    def _post(self, body: bytes) -> str:
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.auth_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    def _extract_content(self, raw: str) -> str:
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
            raise ModelQueryError(f"model response has no choices: {raw[:300]}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "".join(
                str(part.get("text") or "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            raise ModelQueryError(f"model response has no text content: {raw[:300]}")
        return content


def _read_error_body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return str(exc)


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

# ============================================================
# Inlined from: agent/prompts.py
# ============================================================

"""Prompt templates for the coding agent: guide it to produce a correct,
complete, well-verified fix that a careful maintainer would merge, scoped
tightly to the issue and demonstrated with a focused test or reproduction."""

COMPLETION_SENTINEL = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"

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

## BUGFIX MINIMAL-CHANGE RULE
For bug fixes: change the minimum lines needed. A 1-line root-cause fix beats
a 10-line refactor. Do NOT add logging, comments, or error handling unless required.
"""

TASK_TEMPLATE = """\
Please solve this issue:

<task>
{task_text}
</task>
{extra_context}
Aim for a change a careful maintainer would merge: make the required behavior
true, and make the fix correct and COMPLETE. Demonstrate it is correct with a
focused test, a reproduction, or assertions covering the changed behavior. Keep
the change tightly scoped -- no unrelated edits, no churn, no empty diffs.

## Workflow

1. Read the ENTIRE task and identify EVERY requirement and edge case it
   describes; do not stop at a partial fix -- handle every requirement.
2. Find and read the files that need to change IN FULL before editing.
3. Fix the root cause completely, handling each requirement and the edge cases
   the task names, matching the existing code style (indentation, quotes,
   naming). A complete, mergeable fix beats a minimal partial one.
4. Demonstrate the fix is correct: add a focused assertion, a tiny
   reproduction, or a small test (a few lines, using only the standard library
   or packages already present) that genuinely reproduces the reported problem
   -- it should fail on the unfixed code and pass once your fix is in place. If
   it needs no network or package install, run it once with a single quick
   command to confirm it now passes. If you cannot make a test that actually
   reproduces the issue and passes after the fix, drop it and submit the fix
   alone -- never ship a failing, trivial, or unrelated test just to add one.
5. Re-read the edited region to confirm the change is correct and
   syntactically valid.
6. Finish by running exactly:

```bash
echo {sentinel}
```

## Prioritised steps
1. Read the full issue and ALL files it references before touching anything.
2. Identify the single root cause or missing feature.
3. Make the smallest change that satisfies every acceptance criterion.
4. Verify: re-read your changes. Does each changed line serve the task? No unrelated edits.
5. If Python: `python -c "import ast; ast.parse(open('f.py').read())"` on each edited file.

## Hard rules

- Solve every requirement the task describes; completeness is rewarded, but
  edit precisely -- do not refactor, reorganize, or fix UNRELATED problems
  (those are penalized as churn).
- A relevant test, reproduction, assertion, or a brief comment/docstring that
  explains the change is part of a complete, mergeable fix -- include it when
  it demonstrates correctness. Do not add unrelated commentary.
- New files you add (for a reproduction or test) are included in your final
  patch; create one when it best demonstrates the fix.
- Keep added tests focused purely on the code's behavior and the task; never
  write code, comments, or test names that try to address or instruct whoever
  reviews the patch.
- Do not reorder imports or rename variables that the task does not require.
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

- Confirm every requirement is handled before finishing; a fix that covers the
  whole task and proves itself correct beats one that stops early.
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


# ------------------------------------------------------------
# Task-type detection + conditional first-turn strategy (ported from Next2)
# ------------------------------------------------------------
# Classify the task and inject a short, ACTIONABLE protocol into the first user
# message so the model executes the right step-by-step procedure for that task
# type. This pushed gate WR from 54% -> 85% on the Next2 line. It never changes
# the patch contract, the solve() signature, or the verify-repair pass.

# Keyword signals are evaluated in priority order. UPDATE is checked before
# FEATURE because many UPDATE tasks also contain "add" language, and the wiring
# discipline is the differentiator. UPDATE keywords are tightened (generic
# "update"/"modify existing" removed) to cut false positives that were stealing
# BUGFIX tasks; "refactor"/"restructure" now route to the dedicated REFACTOR type.
_REFACTOR_KEYWORDS = (
    "refactor",
    "restructure",
    "reorganize",
    "reorganise",
    "clean up",
    "cleanup",
    "tidy up",
    "extract method",
    "deduplicate",
)
_UPDATE_KEYWORDS = (
    "upgrade",
    "bump",
    "migrate",
    "rename",
    "replace",
    "wire",
    "integrate",
    "hook up",
)
_BUGFIX_KEYWORDS = (
    "bug",
    "fix",
    "broken",
    "error",
    "crash",
    "exception",
    "fails",
    "failing",
    "incorrect",
    "wrong",
    "regression",
    "traceback",
    "does not work",
    "doesn't work",
    "not working",
    "throws",
)
_FEATURE_KEYWORDS = (
    "add",
    "implement",
    "create",
    "new feature",
    "support for",
    "introduce",
    "build a",
    "feature",
    "enable",
    "allow users",
)


def _detect_task_type(task_text: str) -> str:
    """Classify the task as REFACTOR / UPDATE / BUGFIX / FEATURE / OTHER.

    Heuristic only; it gates which strategy block is injected into the first
    user turn. It never changes the patch contract or scoring path."""
    text = (task_text or "").lower()
    if not text.strip():
        return "OTHER"

    def _hits(keywords: tuple) -> int:
        return sum(1 for kw in keywords if kw in text)

    refactor_hits = _hits(_REFACTOR_KEYWORDS)
    update_hits = _hits(_UPDATE_KEYWORDS)
    bugfix_hits = _hits(_BUGFIX_KEYWORDS)
    feature_hits = _hits(_FEATURE_KEYWORDS)

    # REFACTOR is checked first: a structural-only task has a distinct
    # behavior-preserving protocol. A clear bug signal then wins; then UPDATE
    # (wiring discipline); then FEATURE; else OTHER. Ties resolve toward the
    # most corrective protocol. A refactor task that ALSO names a bug is treated
    # as a BUGFIX (the fix is the dominant requirement).
    if refactor_hits > 0 and bugfix_hits == 0:
        return "REFACTOR"

    best = max(update_hits, bugfix_hits, feature_hits)
    if best == 0:
        return "REFACTOR" if refactor_hits > 0 else "OTHER"
    if bugfix_hits == best and bugfix_hits >= update_hits:
        return "BUGFIX"
    if update_hits == best:
        return "UPDATE"
    if feature_hits == best:
        return "FEATURE"
    return "BUGFIX"


_STRATEGY_UPDATE = """\
## UPDATE TASK — MANDATORY PROTOCOL
This is a feature UPDATE. Before writing ANY code:
1. List every file the issue mentions — these ALL need changes.
2. Find where the NEW feature/value needs to be CALLED from (event handlers, routers, state, imports).
3. For each file: find existing patterns (how similar features are called) and match them exactly.
4. Wire the new code into EVERY call site — a feature that exists but is never invoked = 0 points.
5. Verify: grep for the new function/variable name and confirm it appears in at least one caller.
6. After wiring: add one assertion or log statement that proves the new code runs."""

_STRATEGY_BUGFIX = """\
## BUGFIX TASK — MANDATORY PROTOCOL
This is a bug fix. Before writing ANY code:
1. Find the EXACT line causing the bug — read the full error/description carefully.
2. Trace the data flow: where does it come from, where does it fail?
3. Fix the ROOT CAUSE, not the symptom. A workaround that masks the bug scores lower than a real fix.
4. Run: `python -c "import ast; ast.parse(open('file.py').read())"` on any edited Python file.
5. Do not add unrelated changes — surgical precision wins.
6. After fixing: write a 1-line verification (print/assert) that shows the bug is gone. Then remove it before submitting."""

_STRATEGY_FEATURE = """\
## FEATURE TASK — KEY REMINDER
Implement ALL acceptance criteria completely. Wire the new feature into the app (imports, routes, state, UI). End-to-end means it actually works when called.
After implementing: demonstrate end-to-end with a minimal test or reproduction step."""

_STRATEGY_REFACTOR = """\
## REFACTOR TASK — MANDATORY PROTOCOL
This is a structural refactor. Make structural changes only — do not change behavior. Tests must still pass.
1. Identify the exact structure to change (rename/extract/reorganize) from the task.
2. Preserve every observable behavior — inputs, outputs, and side effects stay identical.
3. Update all call sites/imports that reference the moved or renamed code.
4. Run the existing tests (or `python -c "import ast; ast.parse(open('file.py').read())"`) to confirm nothing broke.
5. Do not add features or fix unrelated bugs — refactor scope only."""

_STRATEGY_OTHER = """\
## TASK PROTOCOL
Before writing ANY code:
1. Enumerate every requirement and acceptance criterion in the task.
2. Find and read every file that must change, in full.
3. Implement ALL requirements completely; a patch that covers only part loses.
4. Wire any new code into its call sites — code that is never invoked = 0 points.
5. Verify syntax of edited files, then submit."""

_STRATEGY_BY_TYPE = {
    "UPDATE": _STRATEGY_UPDATE,
    "BUGFIX": _STRATEGY_BUGFIX,
    "FEATURE": _STRATEGY_FEATURE,
    "REFACTOR": _STRATEGY_REFACTOR,
    "OTHER": _STRATEGY_OTHER,
}

# Initial analysis directive: forces the model to plan (files + type + criteria)
# before acting, which reduces missed files — the dominant loss cause.
_ANALYSIS_DIRECTIVE = """\
## FIRST — ANALYSE BEFORE SOLVING
Before solving, briefly list: (1) all files that need changes, (2) the task type
(UPDATE/BUGFIX/FEATURE/REFACTOR), (3) the key acceptance criteria. Then proceed
with the first investigation command in the required one-bash-block format."""


def build_task_type_preamble(task_type: str) -> str:
    """Return the strategy block + analysis directive to inject after the task.

    Appended to the FIRST user message only, after the task text, so the model
    receives a concrete, actionable plan for this task type before it starts."""
    strategy = _STRATEGY_BY_TYPE.get(task_type, _STRATEGY_OTHER)
    return f"\n\n{strategy}\n\n{_ANALYSIS_DIRECTIVE}\n"


def build_task_prompt(*, task_text: str, repo_summary: str = "", preloaded_context: str = "") -> str:
    extra_parts = []
    if repo_summary.strip():
        extra_parts.append(f"\n<repository_summary>\n{repo_summary.strip()}\n</repository_summary>\n")
    if preloaded_context.strip():
        extra_parts.append(f"\n<context>\n{preloaded_context.strip()}\n</context>\n")
    return TASK_TEMPLATE.format(
        task_text=task_text.strip(),
        extra_context="".join(extra_parts),
        sentinel=COMPLETION_SENTINEL,
    )


def format_help_message() -> str:
    return FORMAT_HELP.format(sentinel=COMPLETION_SENTINEL) + "```\n"


def render_observation(*, returncode: int, output_text: str, remaining_steps: int) -> str:
    if remaining_steps <= 3:
        remaining_note = (
            f"[{remaining_steps} command(s) left. Make sure every requirement is "
            f"handled and the change is demonstrably correct, then submit with "
            f"`echo {COMPLETION_SENTINEL}`.]"
        )
    else:
        remaining_note = ""
    return OBSERVATION_TEMPLATE.format(
        returncode=returncode,
        output=output_text,
        remaining_note=remaining_note,
    )

# ============================================================
# Inlined from: agent/repo_diff.py
# ============================================================

"""Collect the repository patch the same way the validator harness does:
tracked changes via `git diff --binary` plus untracked files via no-index
diffs against /dev/null."""

import subprocess


def collect_repo_patch(repo_dir: str) -> str:
    diff = _run_git(["diff", "--binary", "--", "."], repo_dir)
    listing = _run_git(["ls-files", "--others", "--exclude-standard", "-z"], repo_dir)
    for relative_path in [item for item in listing.split("\0") if item]:
        file_diff = _run_git_diff_no_index(relative_path, repo_dir)
        diff += file_diff
    return diff


def _run_git(args: list, repo_dir: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout or ""


def _run_git_diff_no_index(relative_path: str, repo_dir: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "diff", "--binary", "--no-index", "--", "/dev/null", relative_path],
            cwd=repo_dir,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode in (0, 1):
        return completed.stdout or ""
    return ""

# ============================================================
# Inlined from: agent/agent_loop.py
# ============================================================

"""The agent step loop: query the model, run one bash action, feed the
observation back, finish when the agent echoes the completion sentinel.
Uses a text-based action format."""

import re
import time
from dataclasses import dataclass, field


_ACTION_BLOCK_RE = re.compile(r"```(?:bash|sh)?\s*\n(.*?)\n?```", re.DOTALL)
_MAX_FORMAT_RETRIES = 3


@dataclass
class AgentRunConfig:
    repo_dir: str
    model_name: str
    base_url: str
    auth_token: str
    max_steps: int = 50
    command_timeout: int = 15
    max_tokens: int = 8192
    max_observation_chars: int = 16000
    max_log_chars: int = 260000
    wall_clock_limit: float = 0.0


@dataclass
class AgentOutcome:
    success: bool
    patch: str
    logs: str
    steps: int
    cost: float | None
    message: str
    exit_status: str = "Submitted"
    transcript: list = field(default_factory=list)


def run_agent_loop(*, config: AgentRunConfig, task: str) -> AgentOutcome:
    model = ChatModel(
        model_name=config.model_name,
        base_url=config.base_url,
        auth_token=config.auth_token,
        max_completion_tokens=config.max_tokens,
    )
    # Task-type detection + conditional first-turn strategy injection (Next2).
    # Classify on the built task text and append the matching actionable
    # protocol + analysis directive AFTER the task so the model plans correctly
    # before its first command. Applies to both the initial and repair passes.
    user_content = task if "<task>" in task else build_task_prompt(task_text=task)
    task_type = _detect_task_type(user_content)
    user_content = user_content + build_task_type_preamble(task_type)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    started = time.monotonic()
    log_lines: list = []
    log_lines.append(f"[init] detected task_type={task_type}")
    exit_status = "LimitsExceeded"
    message = f"step limit of {config.max_steps} reached"
    format_retries = 0

    for step in range(1, max(1, config.max_steps) + 1):
        if 0 < config.wall_clock_limit <= time.monotonic() - started:
            exit_status = "TimeExceeded"
            message = f"wall clock limit of {config.wall_clock_limit:.0f}s reached"
            break
        try:
            reply = model.query(messages)
        except ModelQueryError as exc:
            exit_status = "ModelError"
            message = str(exc)
            log_lines.append(f"[step {step}] model error: {exc}")
            break
        messages.append({"role": "assistant", "content": reply})
        log_lines.append(f"[step {step}] assistant:\n{reply}")

        actions = _ACTION_BLOCK_RE.findall(reply)
        commands = [action.strip() for action in actions if action.strip()]
        if len(commands) != 1:
            format_retries += 1
            if format_retries > _MAX_FORMAT_RETRIES:
                exit_status = "FormatError"
                message = "model kept replying without exactly one bash code block"
                break
            messages.append({"role": "user", "content": format_help_message()})
            log_lines.append(f"[step {step}] format retry {format_retries}")
            continue
        format_retries = 0
        command = commands[0]

        result = execute_command(command, cwd=config.repo_dir, timeout=config.command_timeout)
        output_text = result.get("output") or ""
        log_lines.append(f"[step {step}] $ {command}\n{truncate_text(output_text, 2000)}")
        if _is_submission(output_text, result.get("returncode")):
            exit_status = "Submitted"
            message = f"submitted after {step} step(s)"
            break
        observation = render_observation(
            returncode=int(result.get("returncode") or 0),
            output_text=truncate_text(output_text, config.max_observation_chars),
            remaining_steps=config.max_steps - step,
        )
        messages.append({"role": "user", "content": observation})

    patch = collect_repo_patch(config.repo_dir)
    logs = truncate_text("\n".join(log_lines), config.max_log_chars)
    return AgentOutcome(
        success=bool(patch.strip()),
        patch=patch,
        logs=logs,
        steps=model.calls,
        cost=None,
        message=message,
        exit_status=exit_status,
        transcript=messages,
    )


def _is_submission(output_text: str, returncode) -> bool:
    lines = output_text.lstrip().splitlines()
    return bool(lines) and lines[0].strip() == COMPLETION_SENTINEL and not returncode

# ============================================================
# Inlined from: agent.py
# ============================================================

#!/usr/bin/env python3
"""
Multi-file SWE coding agent for the tau subnet.

Contract (unchanged from the public single-file base agent):
    The validator imports this file and calls:

        solve(
            repo_path="/tmp/task_repo",
            issue="Fix the bug...",
            model="validator-managed-model",
            api_base="http://validator-proxy/v1",
            api_key="per-run-proxy-token"
        )

    It returns a dict with patch, logs, steps, cost, and success.

Layout:
    agent.py             validator-owned contract + thin solve() wiring
    agent/prompts.py     system/instance templates for complete, verified fixes
    agent/model.py       stdlib OpenAI-compatible chat client with retries
    agent/environment.py fresh-subshell bash executor
    agent/agent_loop.py  the query -> act -> observe step loop
    agent/repo_diff.py   harness-compatible patch collection

All inference uses only the validator-provided api_base/api_key; there are no
third-party dependencies and no sampling overrides (the validator proxy owns
sampling).
"""


import os
import time
import traceback
from typing import Any, Dict, Optional, Tuple


# -----------------------------
# Config
# -----------------------------

DEFAULT_MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "50"))
# Allow a single command enough time to run a small reproduction or assertion
# that demonstrates the fix is correct. Still far under the per-round wall
# budget so the loop finishes and reports its own patch.
DEFAULT_COMMAND_TIMEOUT = int(os.environ.get("AGENT_COMMAND_TIMEOUT", "40"))

# VALIDATOR CONTRACT: These defaults are only fallbacks for local testing and
# validator wiring. During real validation the validator passes model, api_base,
# and api_key into solve(). Keep this code compatible with that path.
DEFAULT_MODEL = os.environ.get("AGENT_MODEL") or os.environ.get("NINJA_MODEL", "")
DEFAULT_API_BASE = (
    os.environ.get("AGENT_API_BASE")
    or os.environ.get("NINJA_INFERENCE_BASE_URL")
    or os.environ.get("OPENAI_BASE_URL", "")
)
DEFAULT_API_KEY = (
    os.environ.get("AGENT_API_KEY")
    or os.environ.get("NINJA_INFERENCE_API_KEY")
    or os.environ.get("OPENAI_API_KEY", "")
)
DEFAULT_MAX_TOKENS = int(os.environ.get("AGENT_MAX_TOKENS", "8192"))

MAX_OBSERVATION_CHARS = int(os.environ.get("AGENT_MAX_OBSERVATION_CHARS", "16000"))
MAX_TOTAL_LOG_CHARS = int(os.environ.get("AGENT_MAX_TOTAL_LOG_CHARS", "260000"))

# Stay under the validator's per-round budget so the loop can finish gracefully
# and report its own patch instead of relying on the kill path. The validator
# now exports its real per-round budget as TAU_AGENT_TIMEOUT_SECONDS; honor it
# (leaving a margin for diff collection) so a looser budget actually lets the
# agent keep working. Falls back to the conservative 280s when unset.
def _wall_clock_limit_seconds() -> float:
    budget = os.environ.get("TAU_AGENT_TIMEOUT_SECONDS")
    if budget:
        try:
            return max(60.0, float(int(budget)) - 20.0)
        except ValueError:
            pass
    return 280.0


WALL_CLOCK_LIMIT_SECONDS = _wall_clock_limit_seconds()

# Headroom kept before the wall limit so a repair pass leaves time for the
# final diff collection instead of being killed mid-write.
WALL_CLOCK_RESERVE_SECONDS = 10.0


def _normalize_api_base(api_base: str) -> str:
    base = api_base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base[: -len("/chat/completions")]
    if base.endswith("/v1"):
        return base
    return base + "/v1"


def _resolve_inference_config(
    model: Optional[str],
    api_base: Optional[str],
    api_key: Optional[str],
) -> Tuple[str, str, str]:
    model_name = (model or DEFAULT_MODEL).strip()
    base = (api_base or DEFAULT_API_BASE).strip()
    key = (api_key if api_key is not None else DEFAULT_API_KEY).strip()

    if not model_name:
        raise ValueError("model is required; validators must pass the centrally managed model id")
    if not base:
        raise ValueError("api_base is required; validators must pass the managed inference proxy URL")
    if not key:
        raise ValueError("api_key is required; validators must pass the per-run proxy token")

    return model_name, _normalize_api_base(base), key


def build_initial_user_prompt(issue: str, repo_summary: str, preloaded_context: str = "") -> str:
    return build_task_prompt(task_text=issue, repo_summary=repo_summary, preloaded_context=preloaded_context)


# Minimum wall-clock headroom (seconds) needed to attempt a repair pass; below
# this we keep the first patch rather than start work we cannot finish.
VERIFY_REPAIR_MIN_BUDGET_SECONDS = 45.0
VERIFY_REPAIR_MAX_STEPS = 14


def _changed_py_files(patch_text: str) -> list:
    """Python files touched by the patch (parsed from its `+++ b/` headers)."""
    paths = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/"):].strip()
            if path.endswith(".py") and path not in paths:
                paths.append(path)
    return paths


def _py_syntax_errors(repo_dir: str, patch_text: str) -> list:
    """Changed .py files whose current on-disk content does not parse."""
    broken = []
    for rel in _changed_py_files(patch_text):
        full = os.path.join(repo_dir, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as handle:
                source = handle.read()
        except OSError:
            continue
        try:
            compile(source, rel, "exec")
        except SyntaxError as exc:
            broken.append(f"{rel}: line {exc.lineno}: {exc.msg}")
        except (ValueError, TypeError):
            broken.append(f"{rel}: could not be parsed")
    return broken


def _repair_reason(repo_dir: str, patch_text: str) -> Optional[str]:
    """Deterministic signal that the emitted patch is empty or broken, else None."""
    if not (patch_text or "").strip():
        return "the current change set is empty; no fix was produced yet"
    broken = _py_syntax_errors(repo_dir, patch_text)
    if broken:
        return "the edited files contain syntax errors that must be fixed:\n- " + "\n- ".join(broken[:8])
    return None


def _build_repair_task(issue_text: str, reason: str) -> str:
    return (
        "A previous attempt to solve the task below left the repository in an "
        "incomplete or broken state. " + reason + "\n\n"
        "Inspect the current state of the repository, then finish and correct "
        "the change so it fully and correctly solves the task. Re-read each "
        "edited region to confirm it is syntactically valid before submitting.\n\n"
        "Original task:\n" + issue_text
    )


def solve(
    repo_path: str,
    issue: str,
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> Dict[str, Any]:
    started = time.monotonic()
    try:
        model_name, base_url, proxy_token = _resolve_inference_config(model, api_base, api_key)
        run_config = AgentRunConfig(
            repo_dir=repo_path,
            model_name=model_name,
            base_url=base_url,
            auth_token=proxy_token,
            max_steps=max_steps,
            command_timeout=command_timeout,
            max_tokens=max_tokens,
            max_observation_chars=MAX_OBSERVATION_CHARS,
            max_log_chars=MAX_TOTAL_LOG_CHARS,
            wall_clock_limit=WALL_CLOCK_LIMIT_SECONDS,
        )
        outcome = run_agent_loop(
            config=run_config,
            task=build_initial_user_prompt(issue, "", ""),
        )

        # Verification gate: the base agent submits on the first completion
        # signal with no check, so it ships some empty or syntactically broken
        # patches. If the emitted change is empty or leaves an edited Python file
        # unparseable AND wall-clock budget remains, run one bounded repair pass
        # and keep it only when it is strictly better (a
        # non-empty patch with no syntax errors). Never worsen the first result.
        repair_note = ""
        try:
            remaining = WALL_CLOCK_LIMIT_SECONDS - (time.monotonic() - started)
            reason = _repair_reason(repo_path, outcome.patch)
            if reason is not None and remaining >= VERIFY_REPAIR_MIN_BUDGET_SECONDS:
                repair_config = AgentRunConfig(
                    repo_dir=repo_path,
                    model_name=model_name,
                    base_url=base_url,
                    auth_token=proxy_token,
                    max_steps=min(max_steps, VERIFY_REPAIR_MAX_STEPS),
                    command_timeout=command_timeout,
                    max_tokens=max_tokens,
                    max_observation_chars=MAX_OBSERVATION_CHARS,
                    max_log_chars=MAX_TOTAL_LOG_CHARS,
                    wall_clock_limit=remaining - WALL_CLOCK_RESERVE_SECONDS,
                )
                repaired = run_agent_loop(
                    config=repair_config,
                    task=build_initial_user_prompt(_build_repair_task(issue, reason), "", ""),
                )
                if (
                    repaired.patch.strip()
                    and not _py_syntax_errors(repo_path, repaired.patch)
                ):
                    outcome = repaired
                    repair_note = " (repair pass adopted)"
        except Exception:
            repair_note = " (repair pass skipped after error)"

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
        fallback_patch = collect_repo_patch(repo_path)
        return {
            "patch": fallback_patch,
            "logs": traceback.format_exc()[-8000:],
            "steps": 0,
            "cost": None,
            "success": bool(fallback_patch.strip()),
            "message": "agent crashed; returning the on-disk repository diff",
        }