# SN66 Next7 Build Report — 2026-06-14

**Builder:** Opus 4.8 subagent
**Deliverable:** `/root/sn66-ninja/agent_cl_gpt_Next7.py`
**Status:** ✅ Built, syntax/import verified, all checklist items pass. **NOT submitted — awaiting James approval.**

---

## Objective

Beat the NEW king (SHA `44a7cf7e0336`, 837L) by combining the king's two new
improvements with Next5's proven SYSTEM_PROMPT additions (75% gate WR).

---

## Base & Strategy

- **Base:** `king_agent.py` (837L, SHA `44a7cf7e0336`) — per L-SN66-KING-BASE-MANDATORY-1.
- `cp king_agent.py agent_cl_gpt_Next7.py`, then surgical edits only.
- Result: **907L**, **92-line diff vs king** (intentional, minimal).

### King base already contains (kept 100% intact)
- `_strip_edit_artifacts()` — removes untracked scratch files (`.new/.orig/.bak/.rej/~`) whose real sibling exists, AFTER first solve, BEFORE patch return.
- `_artifact_sibling()` + `_EDIT_ARTIFACT_SUFFIXES` tuple.
- Verify-repair pass: `_repair_reason`, `_build_repair_task`, `_py_syntax_errors`, `_changed_py_files`.
- Patch-hygiene re-collect in `solve()` (re-runs `collect_repo_patch` after stripping → "stripped scratch files" note).
- TASK_TEMPLATE multi-file awareness + anti-scratch-file rule + anti-test-runner rule.

---

## Changes applied (4 surgical edits, 92-line diff)

### 1. Clean docstring (CI safety)
Replaced king's `"""King SHA: 44a7cf7e..."""` with a neutral capability docstring.
**No** version numbers, **no** benchmark references (66%/80%/75%/SWE-bench), **no** "Next5"/"Next7".
*(CI repeatedly flags version/benchmark references — this docstring has none.)*

### 2. Empty-reply guard in `ChatModel._extract_content`
Ported verbatim from Next5: raise `ModelQueryError` on empty/whitespace content
so the loop retries instead of silently advancing on a no-op step. The base king
submits whatever diff exists when the model returns empty content; retrying lets
the agent recover. (Upstream fix ae2158103232.)

### 3. SYSTEM_PROMPT additions (ported verbatim from Next5)
Appended AFTER the king's existing SYSTEM_PROMPT closing line, 5 blocks:
- **COMPLETENESS BEATS MINIMALISM** — under-editing costs more than over-editing (required pattern + asymmetry).
- **ACCEPTANCE CRITERIA FIRST** — enumerate every criterion before coding.
- **UPDATE TASK WIRING RULE** — the #1 rule; feature never called = 0 points; multi-file enumeration.
- **CORRECTNESS GUARDS** — import scope, TS types, no test regressions / Python ast.parse check.
- **CORRECTNESS CHECK** — re-read patch, every line serves the task, no empty diffs.

### 4. Graduated urgency hints in `render_observation` (+ call-site wiring)
Replaced king's single `remaining_steps <= 3` note with Next5's graduated
5/3/1-step hints plus wall-clock awareness (nudge to minimal-correct-and-submit
when >60% of budget spent). Extended signature with `elapsed`/`wall_clock_limit`
(defaulted, backward compatible) and updated the single call site in the agent
loop to pass `time.monotonic() - started` and `config.wall_clock_limit`.

---

## Explicitly NOT added (per task spec)
- ❌ `_detect_task_type` (none present — verified).
- ❌ BUGFIX STRATEGY block.
- ❌ phrase-blacklist / OUTPUT SAFETY / automatic-fail guard text (CI flagged this in a prior version).
- ❌ benchmark references / version numbers in docstring or comments.
- ❌ sampling params (temperature/top_p/top_k).
- ❌ `grader`/`reward model` guardrail text.
- ✅ `solve()` signature unchanged (byte-identical to king).

---

## Step 5 Checklist — ALL PASS

| Check | Result |
|-------|--------|
| `py_compile` syntax | ✅ |
| `from agent import solve` | ✅ import OK |
| `_strip_edit_artifacts` / `_artifact_sibling` | ✅ present |
| `_repair_reason` / `_build_repair_task` | ✅ present |
| `COMPLETENESS BEATS MINIMALISM` | ✅ present |
| `_detect_task_type` | ✅ absent |
| `OUTPUT SAFETY` / phrase-blacklist / automatic fail / grader | ✅ clean |
| `temperature` / `top_p` / `top_k` | ✅ none |
| benchmark/version refs (next5/next7/v6x/v7x/66%/80%/75%/swe-bench) | ✅ none |
| empty-reply fix | ✅ present |
| urgency hints (Final / 5 commands left) | ✅ present |
| UPDATE TASK WIRING RULE | ✅ present |
| ACCEPTANCE CRITERIA FIRST | ✅ present |
| CORRECTNESS CHECK | ✅ present |
| anti-scratch / anti-test-runner TASK_TEMPLATE (king) | ✅ intact |
| `_EDIT_ARTIFACT_SUFFIXES` | ✅ intact |
| patch-hygiene re-collect ("stripped scratch files") | ✅ intact |
| `solve()` signature vs king | ✅ identical |
| diff vs king | 92 lines |
| line count | 907L |

---

## Why this should beat the new king

1. **Inherits both king wins**: scratch-file hygiene (no churn penalty) + repair loop (no empty/broken patches).
2. **Adds Next5's proven solver-quality framing** (75% gate WR): completeness asymmetry, AC-first enumeration, UPDATE wiring (fixes the historical UPDATE WR crisis), empty-reply retry, graduated urgency.
3. **CI-safe**: no version/benchmark refs, no phrase-blacklist, no sampling, king-base → expected CI ≥72.

---

## Next steps (NOT executed — require James approval)
1. King sync check (`bash scripts/sync_king.sh`) — confirm SHA still `44a7cf7e0336` before any gate.
2. Gate test in tmux: 50 tasks, seed 42, `--timeout 600`, `--parallel 3`. Threshold ≥60% decisive WR.
3. Report breakdown by task type → James approval → submit on new hotkey.

**Per L-NO-AUTO-SUBMIT-1: no submission without James's explicit approval.**
