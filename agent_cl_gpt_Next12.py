#!/usr/bin/env python3
"""SN66 miner: a layer-aware, completeness-first coding agent with an
architectural-probe first step, a polyglot verify-repair pass, a behavioral
python-test gate, an in-place transient-reply retry, and patch-hygiene cleanup.

Keeps the multi-file king base intact: scratch-file stripper, bounded repair
loop, multi-file workflow guidance. Adds: an automatic architecture probe at
the start of a run so the model understands the project layout before editing,
an ARCHITECTURE-FIRST rule (place the fix in the correct layer), a
NEVER-DELETE/ALWAYS-EXTEND rule (read and extend existing implementations
rather than replace them with skeletons), a streamlined fast-path framing for
short single-file tasks (fewer steps -> better solve-time score), plus the
proven completeness framing, acceptance-criteria protocol, UPDATE wiring rule,
empty-reply retry, and graduated urgency hints.

Verify-repair gate (the heart of this agent):
  - POLYGLOT SYNTAX CHECK -- the repair gate no longer only compiles Python;
    it also validates JSON (stdlib json.loads), plain JS/MJS/CJS (`node
    --check`), and Go (`gofmt -e`). Every checker is conservative: a missing
    tool or any ambiguity yields nothing, so repair fires only on a real,
    confirmed break, and the adopt-gate re-runs the same check so a false
    positive can never worsen the kept patch.
  - PYTHON TEST RUNNER -- when the first patch adds or changes a python test,
    the gate runs pytest on it (first test only, time-bounded) and classifies
    the outcome. A definitively FAILING own-test (test_fail) means the fix is
    wrong/incomplete and triggers a repair; a source-only fix with NO test
    (no_test) triggers a repair that must ADD a focused regression test while
    keeping the original fix surface. Anything ambiguous is treated as
    'unknown' so a valid fix is never falsely declared wrong.
  - KIND-AWARE ADOPT-GATE -- empty/syntax/test_fail repairs are adopted only
    when the result is non-empty, syntactically valid, and not test-failing;
    a no_test repair is adopted only when it GAINED a passing test AND kept the
    original fix surface, so the fix can never be lost.

This revision additionally:
  - retries transient soft-empty/no-content 200-OK model replies in-place
    instead of forfeiting the round (a transient-content retry class), so a
    fresh-every-round agent stops losing rounds to empty responses (kept as a
    deliberate divergence from the base king, which forfeits such rounds); and
  - adds a READ-BEFORE-WRITE rule so the model reads each file in full before
    editing, eliminating partial-context patches that miss existing code;
  - adds a FILE-ENUMERATION protocol so the model lists every file the task
    requires (including companion tests, configs, docs, and manifests) before
    writing, since partial file coverage loses decisively to full coverage;
  - adds a NO-PLACEHOLDER rule so the model reads real values from the codebase
    instead of emitting assumed constants, TODOs, or NotImplementedError stubs;
    and
  - adds a ROOT-CAUSE-DEPTH rule so the model traces the failing path from its
    entry point and fixes the underlying cause (e.g. an actual type/query
    mismatch) rather than patching a surface symptom.

This revision adds three duel-derived SYSTEM_PROMPT rules, root-caused from a
full-duel analysis where the judge repeatedly favored the cached defender:
  - REGRESSION TEST -- MANDATORY: the single biggest loss driver (~50% of lost
    rounds) was the judge awarding the king for "includes a regression/unit
    test" while our model shipped a source-only fix. This rule instructs the
    model to add ONE focused regression test for EVERY task (fail-on-original,
    pass-with-fix), using the project's own framework, complementing the
    behavioral no_test repair gate that already fires post-hoc.
  - ANTI-CHURN -- NEVER TOUCH UNRELATED FILES: ~15% of lost rounds cited
    "significant churn" (unrequested chmod on unrelated scripts, global CSS
    margin changes). This rule forbids any permission change, global
    style/config edit, or reformat of files the task did not name, so a focused
    patch beats a sprawling one.
  - USE PROJECT PATTERNS -- NO NAIVE STDLIB REIMPLEMENTATION: a naive
    `time.sleep(5)` rate limiter ("forces a 5-second delay even if the server
    has been idle for hours") lost a round to the king's elapsed-time tracking.
    This rule tells the model to reuse the project's existing rate-limit,
    retry, HTTP, error-handling, and data-access patterns instead of
    reimplementing them naively.
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


class _TransientContentError(ModelQueryError):
    """A 200-OK reply that is unusable (no choices / no content / empty).

    Subclasses ModelQueryError so every existing catch site is unchanged, but
    lets query() retry it in-place instead of forfeiting the round. This is the
    Google finish_reason=error / no-content failure the cached king never pays
    (it is solved once) but a fresh-every-round challenger pays repeatedly."""
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
                try:
                    text = self._extract_content(raw)
                except _TransientContentError as exc:
                    # 200-OK but unusable (soft-empty / finish_reason=error):
                    # fall through to the existing backoff and retry in-place
                    # rather than forfeit the round.
                    last_error = f"{type(exc).__name__}: {exc}"
                else:
                    self.calls += 1
                    return text
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
            raise _TransientContentError(f"model response has no choices: {raw[:300]}")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = "".join(
                str(part.get("text") or "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            raise _TransientContentError(f"model response has no text content: {raw[:300]}")
        # Reject empty proxy-normalized replies so the loop retries in-place
        # instead of silently advancing on a no-op step or forfeiting the
        # round. The base king submits whatever diff exists when the model
        # returns empty content; retrying lets the agent recover.
        if not content.strip():
            raise _TransientContentError(f"model returned empty content: {raw[:300]}")
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

## ARCHITECTURE-FIRST RULE
For any task that touches multiple files or mentions components, modules, or
layers:
1. Before reading individual files, map the project structure (you may have
   already been shown an initial listing). Know which directories hold core
   logic, UI, API, and data layers.
2. Identify which LAYER the change belongs to (core / extension / UI / API /
   data). A correct feature placed in the WRONG layer scores 0 -- match where
   the existing code of that kind already lives.
3. Follow the project's existing conventions (e.g. store/reducer patterns,
   router patterns, server vs client component boundaries, dependency-injection
   or factory helpers it already uses). A maintainer-grade fix looks native to
   the codebase, not bolted on.

## NEVER DELETE, ALWAYS EXTEND
When you see an existing implementation that looks wrong or incomplete, do NOT
delete it and replace it with a skeleton or stub. First READ the full
implementation, then extend or fix it minimally in place. Replacing a working
implementation with an incomplete one is the single worst outcome and scores
near zero -- preserve existing behavior and build on it.

## ANTI-CHURN -- NEVER TOUCH UNRELATED FILES
Only modify files that are directly required by the task:
- NEVER run chmod, chown, or permission changes on unrelated scripts.
- NEVER modify global CSS/SCSS that the task did not ask you to change.
- NEVER add imports, dependencies, or config to files not mentioned in the task.
- NEVER reorganize or reformat code in files you are not changing for the task.
- Every file you touch must be justified by the task requirements.
- Ask: "Would a reviewer question why I modified this file?" YES = don't touch it.

Churn (unrequested changes) is penalized heavily. A focused patch beats a
sprawling one.

## READ BEFORE WRITE -- NO EXCEPTIONS
Before editing ANY file, read it IN FULL with `nl -ba path/to/file | head -200`
(or `wc -l` first if the file might be large, then read in chunks).
An edit based on partial context produces an incomplete or contradictory patch
and scores near zero. There are no shortcuts: read first, edit second.

## USE PROJECT PATTERNS -- NO NAIVE STDLIB REIMPLEMENTATION
Before implementing any utility function, check if the project already has one:
- Rate limiting: use elapsed-time tracking (record last_request_time), NEVER
  time.sleep() at request start.
- Retry logic: use the project's existing retry decorator/utility, not a new one.
- API calls: use the project's existing HTTP client/session, not raw
  urllib/requests.
- Error handling: match the project's existing error handling patterns.
- Database: use the project's existing ORM/connection patterns (e.g.
  db.connection, an existing store class).

The judge penalizes naive implementations even when they "work":
- time.sleep(5) on every request = "forces a 5-second delay even if the server
  is idle for hours" = LOSS.
- A hardcoded raw GitHub API call = "might be blocked or rate-limited" = LOSS.
- A new retry decorator instead of the existing one = "less integrated into the
  existing codebase" = LOSS.
Read the codebase for the existing pattern first, then reuse it.

## ROOT CAUSE -- GO DEEP
When fixing a bug or implementing a feature:
1. Identify the EXACT failing code path -- trace it from the entry point.
2. Fix the ROOT CAUSE, not the symptom:
   - Wrong: adding a truthiness check when the real issue is a type mismatch.
   - Right: fixing the query to handle the actual data type (UUID/BSON binary).
   - Wrong: adding a try/catch wrapper when the real issue is missing error
     handling.
   - Right: implementing the complete error handling flow the task describes.
3. After fixing: verify the fix actually addresses what the task asked for.

## COMPLETENESS BEATS MINIMALISM
Under-editing costs MORE than over-editing: a missed requirement scores 0 for
that requirement, while a slightly-too-broad edit is only mildly penalized.
Always err toward fully satisfying the task rather than stopping short.

## ACCEPTANCE CRITERIA FIRST
Before writing ANY code, identify every acceptance criterion in the task. Your
patch must address ALL of them. Partial implementations lose decisively. Enumerate
the criteria, then verify each one is covered before you submit.

## FILE ENUMERATION PROTOCOL
Before writing ANY code, enumerate EVERY file the task requires you to touch:
1. Re-read the task and list every filename mentioned explicitly.
2. For each file: does the task describe changes to it? If yes -> it is
   REQUIRED.
3. Check: are there companion files? (e.g. if adding a class -> is there a test
   file? a config? a route?)
4. Check: does the task mention docs, README, SKILL.md, package.json,
   requirements.txt, angular.json, renv? If yes -> include them.
5. Write your file list before starting. Touch EVERY file on the list.

A patch that covers 4 of 5 required files scores proportionally to coverage.
A patch that covers 3 of 5 required files loses decisively to one that covers
all 5.

## REGRESSION TEST -- MANDATORY
For EVERY task (bug fix, feature, refactor, API change, update), add one focused
regression test:
- Bug fix: a test that FAILS on the original code and PASSES with your fix.
- Feature: a test that verifies the new functionality works correctly.
- Refactor: a test that confirms existing behavior is preserved.
- Use the project's existing test framework (pytest, jest, unittest, mocha,
  etc.).
- Place the test in the same directory as similar tests in the project.
- Keep it focused: test exactly what changed, not the entire system.
- A working test that verifies your fix scores 0.10-0.15 higher than no test.
- If you genuinely cannot add a test (e.g. purely visual CSS with no logic),
  explain why in a comment.

NEVER skip this step. The judge rewards implementations that include
verification.

## UPDATE TASK WIRING RULE
A feature that exists but is never called = 0 points. Wire new code into event
handlers, state management, data flows, and call sites. For multi-file tasks,
enumerate EVERY required file and update ALL of them -- a patch covering 4 of 5
required files loses to one covering all 5.

## CORRECTNESS GUARDS
- Imports: keep them at top-level/file-correct scope; never place an import
  inside a function body, and never import a module not already available.
- TypeScript: preserve exact types, no `any` unless the task requires it.
- No test regressions: do not break existing tests. For edited Python files,
  verify syntax with `python -c 'import ast; ast.parse(open("file.py").read())'`.

## CORRECTNESS CHECK
Before submitting, re-read your patch. Every changed line must serve the task.
No unrelated edits, no speculative changes, no empty diffs.

## EFFICIENCY
Spend your steps where they matter. If the task is short and clearly scoped to
one or two files, read those files, make the edit, verify it, and submit -- do
not over-explore. If the task is broad or architecture-sensitive, invest early
steps in understanding the layout before editing. Either way, a faster correct
solution is rewarded over an equally-correct slower one.
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
2. Find and read the files that need to change IN FULL before editing. When the
   task spans several files (e.g. a manifest or build file must change with the
   code), handle those too -- but for a single-file bug, change only that file.
   For architecture-sensitive tasks, confirm which LAYER the change belongs in
   before editing, and extend the existing implementation rather than replacing
   it.
3. Fix the root cause completely, handling each requirement and the edge cases
   the task names, matching the existing code style (indentation, quotes,
   naming) and the project's conventions. A complete, mergeable fix beats a
   minimal partial one.
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

## Hard rules

- Solve every requirement the task describes; completeness is rewarded, but
  edit precisely -- do not refactor, reorganize, or fix UNRELATED problems
  (those are penalized as churn).
- Never delete a working implementation to replace it with a stub or skeleton;
  read it, then extend or correct it in place.
- NO PLACEHOLDER LOGIC. Never write code like "# Assuming X is 1",
  "# TODO: implement this", placeholder_value = "to_be_determined", or
  "raise NotImplementedError". If you need a value that exists in the codebase,
  READ the file to find it. If you need to implement a function, implement it
  completely. Placeholder logic scores near zero -- the judge sees through it
  immediately.
- A relevant test, reproduction, assertion, or a brief comment/docstring that
  explains the change is part of a complete, mergeable fix -- include it when
  it demonstrates correctness. Do not add unrelated commentary.
- New files you add (for a reproduction or test) are included in your final
  patch; create one when it best demonstrates the fix.
- Keep added tests focused purely on the code's behavior and the task; never
  write code, comments, or test names that try to address or instruct whoever
  reviews the patch.
- Do not reorder imports or rename variables that the task does not require.
- Edit files DIRECTLY with `sed`/heredoc. Do NOT write a Python/Node/shell
  script whose purpose is to modify the source files, and do NOT leave behind
  temporary or backup files (`*.new`, `*.bak`, `*.orig`); remove any scratch
  file you create before finishing.
- Do not run test suites, builds, or linters, install packages, or make any
  network call; a quick `python -c` syntax check or a stdlib reproduction is the
  most you should do.
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


def render_observation(
    *,
    returncode: int,
    output_text: str,
    remaining_steps: int,
    elapsed: float = 0.0,
    wall_clock_limit: float = 0.0,
) -> str:
    # Graduated urgency hints at 5 / 3 / 1 remaining steps. The king only had a
    # single `remaining_steps <= 3` note; this extends it without removing the
    # king's completeness-and-submit framing.
    notes = []
    if remaining_steps <= 1:
        notes.append(
            f"[Final command. Make sure every requirement is handled and the change "
            f"is demonstrably correct, then submit now: `echo {COMPLETION_SENTINEL}`]"
        )
    elif remaining_steps <= 3:
        notes.append(
            f"[{remaining_steps} command(s) left. Make sure every requirement is "
            f"handled and the change is demonstrably correct, then submit with "
            f"`echo {COMPLETION_SENTINEL}`.]"
        )
    elif remaining_steps <= 5:
        notes.append(
            "[5 commands left. Focus: complete the most critical missing change "
            "and confirm it is correct, then submit.]"
        )
    # Solve-time awareness: when few steps remain AND most of the wall-clock
    # budget is spent, nudge toward a minimal correct change and submission.
    if (
        wall_clock_limit > 0
        and remaining_steps <= 5
        and elapsed > 0.6 * wall_clock_limit
    ):
        notes.append(
            "[Time is short. Make the minimal correct change and submit.]"
        )
    remaining_note = " ".join(notes)
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

# (subprocess already imported above)


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
# (time already imported above)
from dataclasses import dataclass, field


_ACTION_BLOCK_RE = re.compile(r"```(?:bash|sh)?\s*\n(.*?)\n?```", re.DOTALL)
_MAX_FORMAT_RETRIES = 3

# Automatic architecture probe run as the agent's first action, before the
# model issues any command. It gives the model project-level context (file
# layout, project type, manifests) so it can decide which LAYER a change
# belongs in BEFORE reading or editing any specific file. Pure read-only:
# it lists files and prints the most common project manifests if present.
# Output is bounded so it never floods the context window.
_ARCH_PROBE_COMMAND = (
    "echo '=== TREE (top files/dirs) ==='; "
    "(git ls-files 2>/dev/null | head -60 || find . -type f "
    "-not -path './.git/*' 2>/dev/null | head -60); "
    "echo; echo '=== MANIFESTS ==='; "
    "for f in package.json pyproject.toml setup.py setup.cfg Cargo.toml "
    "go.mod pom.xml build.gradle composer.json Gemfile tsconfig.json; do "
    "if [ -f \"$f\" ]; then echo \"--- $f ---\"; head -40 \"$f\"; fi; done"
)


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
    # When True (the initial task run), the loop performs an automatic
    # read-only architecture probe before the first model query and feeds the
    # result in as context. Disabled for the repair pass (already explored).
    arch_probe: bool = False


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


def _run_arch_probe(config: "AgentRunConfig") -> str:
    """Read-only project-layout probe; returns a bounded text summary or ''."""
    try:
        result = execute_command(
            _ARCH_PROBE_COMMAND,
            cwd=config.repo_dir,
            timeout=min(15, max(5, config.command_timeout)),
        )
    except Exception:
        return ""
    text = (result.get("output") or "").strip()
    if not text:
        return ""
    return truncate_text(text, 6000)


def run_agent_loop(*, config: AgentRunConfig, task: str) -> AgentOutcome:
    model = ChatModel(
        model_name=config.model_name,
        base_url=config.base_url,
        auth_token=config.auth_token,
        max_completion_tokens=config.max_tokens,
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task if "<task>" in task else build_task_prompt(task_text=task)},
    ]
    started = time.monotonic()
    log_lines: list = []
    exit_status = "LimitsExceeded"
    message = f"step limit of {config.max_steps} reached"
    format_retries = 0

    # Architecture probe: a single automatic read-only command whose output is
    # injected as an observation, so the model starts with project-level
    # context (layout + manifests) and can place the fix in the right layer.
    # This does NOT consume a model step and never edits anything.
    if config.arch_probe:
        probe_summary = _run_arch_probe(config)
        if probe_summary:
            log_lines.append(f"[arch-probe]\n{truncate_text(probe_summary, 2000)}")
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Project layout probe (read-only, for orientation only -- "
                        "use it to decide which layer/files the change belongs in; "
                        "still read any file IN FULL before editing it):\n\n"
                        "<project_layout>\n" + probe_summary + "\n</project_layout>"
                    ),
                }
            )

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
            elapsed=time.monotonic() - started,
            wall_clock_limit=config.wall_clock_limit,
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

All inference uses only the validator-provided api_base/api_key; there are no
third-party dependencies and no sampling overrides (the validator proxy owns
sampling).
"""


# (os, subprocess, time, json already imported above)
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

# A task is treated as "simple" (fast-path eligible) when its description is
# short and it does not look architecture-heavy. For simple tasks we skip the
# architecture probe to save wall-clock and steps -> better solve-time score.
SIMPLE_TASK_MAX_CHARS = 500
_ARCH_SIGNAL_RE = re.compile(
    r"\b(architect\w*|layer|module|component|refactor|integrat\w*|"
    r"across (?:the )?(?:files|codebase)|multiple files|wiring|pipeline|"
    r"end[- ]to[- ]end|store|reducer|router|middleware|api layer)\b",
    re.IGNORECASE,
)


def _is_simple_task(issue_text: str) -> bool:
    """Short, single-concern issues are eligible for the streamlined fast-path.
    We probe architecture only for longer or architecture-sensitive tasks."""
    text = (issue_text or "").strip()
    if len(text) > SIMPLE_TASK_MAX_CHARS:
        return False
    if _ARCH_SIGNAL_RE.search(text):
        return False
    return True


def _changed_source_files(patch_text: str, exts: tuple) -> list:
    """Files with the given extensions touched by the patch (`+++ b/` headers)."""
    paths = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/"):].strip()
            if path.endswith(exts) and path not in paths:
                paths.append(path)
    return paths


def _run_check(cmd: list, cwd: str) -> Optional[str]:
    """Run an external syntax checker. Return a short error string only on a
    CONFIRMED failure; return None if it passes OR the tool is unavailable, so a
    missing tool never produces a false repair trigger."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    if proc.returncode == 0:
        return None
    msg = (proc.stderr or proc.stdout or "").strip()
    return (msg.splitlines()[0][:200] if msg else "failed syntax check")


def _syntax_errors(repo_dir: str, patch_text: str) -> list:
    """Changed files that are definitely unparseable -- a POLYGLOT extension of
    the base king's Python-only check (its blind spot: it ships broken
    non-Python patches unrepaired). Every checker is conservative: a missing
    tool or any ambiguity yields nothing, so repair only fires on a real break.
    The repair adopt-gate re-runs this, so even a false positive can never
    worsen the kept patch -- worst case is a wasted repair pass."""
    broken = []
    # Python -- stdlib compile (identical to the base agent).
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
    # JSON -- stdlib, always available, zero false positives.
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
    # Plain JS -- `node --check` parses .js/.mjs/.cjs (skip .jsx/.ts; node would
    # false-flag JSX/TS syntax). Skips silently when node is absent.
    for rel in _changed_source_files(patch_text, (".js", ".mjs", ".cjs")):
        err = _run_check(["node", "--check", rel], repo_dir)
        if err:
            broken.append(f"{rel}: {err}")
    # Go -- `gofmt -e` parses Go. Skips silently when gofmt is absent.
    for rel in _changed_source_files(patch_text, (".go",)):
        err = _run_check(["gofmt", "-e", rel], repo_dir)
        if err:
            broken.append(f"{rel}: {err}")
    return broken


def _all_changed_files(patch_text: str) -> list:
    """Every file the patch touches (`+++ b/` headers), excluding /dev/null."""
    out = []
    for line in patch_text.splitlines():
        if line.startswith("+++ b/"):
            p = line[len("+++ b/"):].strip()
            if p and p != "/dev/null" and p not in out:
                out.append(p)
    return out


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
    """Non-test files the patch changes -- the actual fix surface."""
    return {p for p in _all_changed_files(patch_text) if not _is_test_path(p)}


def _python_test_outcome(repo_dir: str, patch_text: str) -> str:
    """'none' (no python test added), 'pass', 'fail' (a definitive pytest exit-1
    failure), or 'unknown'. Conservative + time-bounded: runs ONLY the first
    added python test, and treats anything ambiguous (collection/import/usage
    error, no pytest) as 'unknown' so it never falsely declares a fix wrong."""
    tests = [p for p in _all_changed_files(patch_text)
             if _is_test_path(p) and p.endswith(".py")
             and os.path.isfile(os.path.join(repo_dir, p))]
    if not tests:
        return "none"
    rel = tests[0]
    for exe in ("python", "python3"):
        try:
            proc = subprocess.run(
                [exe, "-m", "pytest", rel, "-x", "-q", "-p", "no:cacheprovider"],
                cwd=repo_dir, capture_output=True, text=True, timeout=25,
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            return "pass"
        if proc.returncode == 1:
            return "fail"
        return "unknown"  # 2/3/4/5 = collection/usage/no-tests -> ambiguous
    return "unknown"


def _repair_reason(repo_dir: str, patch_text: str, check_tests: bool = True):
    """(kind, message) when the first patch should be repaired, else None.
    Cheap kinds 'empty'/'syntax' are the base king's checks. Behavioral kinds
    'test_fail'/'no_test' target the real failure mode: many valid-but-
    undemonstrated/wrong patches the base king never rescues, and the duel data
    shows that is exactly where rounds are lost (LLM score < 0.7)."""
    if not (patch_text or "").strip():
        return ("empty", "the current change set is empty; no fix was produced yet")
    broken = _syntax_errors(repo_dir, patch_text)
    if broken:
        return ("syntax", "the edited files contain syntax errors that must be fixed:\n- " + "\n- ".join(broken[:8]))
    if check_tests:
        outcome = _python_test_outcome(repo_dir, patch_text)
        if outcome == "fail":
            return ("test_fail", "your own regression test currently FAILS, so the fix is wrong or incomplete; correct the fix until that test passes (never weaken the test).")
        if outcome == "none" and _source_files(patch_text):
            return ("no_test", "the fix changes source but includes no test proving it works; ADD one focused regression test that fails on the original bug and passes with your fix, and KEEP the existing source fix in place.")
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


# Untracked editor/patch scratch files an agent sometimes leaves behind while
# editing (e.g. a `cli.ts.new` next to `cli.ts`) get folded into the scored
# patch where the judge reads them as broken/messy churn. We delete them before
# the patch is collected. SAFETY: a scratch file is by definition a shadow of a
# real file, so we only delete `X<suffix>` when the sibling `X` actually exists
# -- this catches every true artifact while never touching a legitimately-named
# untracked deliverable (e.g. a real file named config.orig).
_EDIT_ARTIFACT_SUFFIXES = (".new", ".orig", ".bak", ".rej")


def _artifact_sibling(rel: str) -> Optional[str]:
    """The real file a scratch path shadows, or None if it is not an artifact."""
    if rel.endswith("~"):
        return rel[:-1] or None
    for suffix in _EDIT_ARTIFACT_SUFFIXES:
        if rel.endswith(suffix):
            return rel[: -len(suffix)] or None
    return None


def _strip_edit_artifacts(repo_dir: str) -> int:
    """Remove untracked editor/patch scratch files whose real sibling exists."""
    removed = 0
    try:
        listing = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30, check=False,
        ).stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return 0
    for rel in [p for p in listing.split("\0") if p]:
        sibling = _artifact_sibling(rel)
        if sibling and os.path.exists(os.path.join(repo_dir, sibling)):
            try:
                os.remove(os.path.join(repo_dir, rel))
                removed += 1
            except OSError:
                pass
    return removed


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
        # Fast-path: simple, short, single-concern tasks skip the architecture
        # probe (fewer commands -> lower wall-clock -> higher solve-time score).
        # Broad / architecture-sensitive tasks get the probe for layer context.
        do_arch_probe = not _is_simple_task(issue)
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
            arch_probe=do_arch_probe,
        )
        outcome = run_agent_loop(
            config=run_config,
            task=build_initial_user_prompt(issue, "", ""),
        )

        # Verification gate: the base agent submits on the first completion
        # signal with no check, so it ships some empty, syntactically broken, or
        # behaviorally-wrong patches. When budget remains, run ONE bounded
        # repair pass and adopt it only when it is DEMONSTRABLY better. The gate
        # has four kinds: empty / syntax (cheap, polyglot) and the behavioral
        # test_fail / no_test. Behavioral probes run pytest, so they are only
        # attempted when there is budget for a repair afterwards. Never worsen
        # the first result.
        repair_note = ""
        try:
            remaining = WALL_CLOCK_LIMIT_SECONDS - (time.monotonic() - started)
            can_repair = remaining >= VERIFY_REPAIR_MIN_BUDGET_SECONDS
            reason = _repair_reason(repo_path, outcome.patch, check_tests=can_repair)
            if reason is not None and can_repair:
                kind, message = reason
                orig_sources = _source_files(outcome.patch)
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
                    arch_probe=False,
                )
                repaired = run_agent_loop(
                    config=repair_config,
                    task=build_initial_user_prompt(_build_repair_task(issue, message), "", ""),
                )
                rp = repaired.patch
                # Adopt-gate -- strictly safe: only replace the first patch when
                # the repair is DEMONSTRABLY better, never when it could be worse.
                if rp.strip() and not _syntax_errors(repo_path, rp):
                    rtest = _python_test_outcome(repo_path, rp)
                    if kind in ("empty", "syntax", "test_fail"):
                        # first patch was empty/broken/test-failing: keep the
                        # repair only if it is non-empty, valid, and not failing.
                        adopt = rtest != "fail"
                    else:  # no_test: replace only if we GAINED a passing test AND
                        # kept the original fix surface (so the fix is not lost).
                        adopt = rtest == "pass" and orig_sources.issubset(_source_files(rp))
                    if adopt:
                        outcome = repaired
                        repair_note = " (repair adopted: %s)" % kind
        except Exception:
            repair_note = " (repair pass skipped after error)"

        # Patch hygiene: drop editor/patch scratch files (never a real
        # deliverable) and re-collect, so the judge scores only the real change.
        patch = outcome.patch
        try:
            if _strip_edit_artifacts(repo_path) > 0:
                patch = collect_repo_patch(repo_path)
                repair_note += " (stripped scratch files)"
        except Exception:
            pass

        elapsed = time.monotonic() - started
        return {
            "patch": patch,
            "logs": outcome.logs,
            "steps": outcome.steps,
            "cost": outcome.cost,
            "success": bool(patch.strip()),
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
