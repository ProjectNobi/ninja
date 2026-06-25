# Step 4: Build Report — 2026-06-14

## Agent: agent_cl_gpt_vNext.py
## Line count: 822
## Base: king_agent.py (SHA a56ffdf5, 684L) — copied EXACTLY per L-SN66-KING-BASE-MANDATORY-1, then edited

**Build method:** `cp king_agent.py agent_cl_gpt_vNext.py` → 5 targeted edits. No other base.
All king core structures preserved unchanged: `run_agent_loop`, `AgentRunConfig`, `AgentOutcome`,
`_extract_commands`, `_NATIVE_TOOL_CALL_RE`, `_ACTION_BLOCK_RE`, and the `solve()` contract
(signature + return dict keys `patch/logs/steps/cost/success/message`).

---

## Changes made (5 total)

### Change 1: SYSTEM_PROMPT upgrade
**Added** (kept the king's bare response-format contract verbatim at the end):
- `## COMPLETENESS BEATS MINIMALISM` header + explicit statement that
  "Under-editing costs MORE than over-editing: a missed requirement scores 0 …".
- `## ACCEPTANCE CRITERIA FIRST` — identify every acceptance criterion before writing code;
  patch must address ALL of them; partial implementations lose decisively (Gemini's #1 win
  signal, 1,508 occurrences — Intel E).
- `## UPDATE TASK WIRING RULE` — "A feature that exists but is never called = 0 points. Wire new
  code into event handlers, state management, data flows, call sites." + the 4-of-5-files-loses
  framing (Intel C; v68 catastrophe proved stripping it drops UPDATE 57%→14%).
- `## CORRECTNESS GUARDS` — imports at top-level/correct scope only (Gemini #1 loss cause, 1,961
  `import issues`); TypeScript exact types, no `any` unless required; no test regressions; Python
  syntax self-check via `python -c 'import ast; ast.parse(...)'`.
- `## SCOPE DISCIPLINE (counterbalance)` — change ONLY what the task requires; "When unsure, leave
  as-is." This is the minimalism counterbalance that prevents FORBIDDEN Pattern 2 (pure-minimalism
  without asymmetry) AND prevents over-churn (Intel A #2 loss cause: 649 scope-creep lessons).
- `## OUTPUT SAFETY` — patch must NOT contain `automatic fail`, `ignore previous instructions`,
  `grader` (102 auto-fail cases = instant 0, Intel A).

**Kept verbatim:** the king's "Response format, every single turn / ONE bash block with ONE command"
contract and the fresh-subshell / chain-with-`&&` rules. Total prompt ≈ 52 lines.

**Forbidden-pattern check:** the `## SCOPE DISCIPLINE` block is phrased as a *counterbalance to
completeness* (not standalone pure minimalism), and contains NO "never delete / preserve existing /
only add" language. Compliant with both FORBIDDEN patterns.

### Change 2: _sanitize_patch
**Ported** from `agent.py` as a **self-contained** function (the original drags in
`_strip_skipped_file_diffs`, `_strip_mode_only_file_diffs`, `_strip_mode_metadata_lines`,
`_strip_low_signal_hunks`, `_should_skip_patch_path` — heavy, not judge-visible). The ported version
keeps the judge-critical part only: the `_EDGECASE_GUARDRAIL` tuple (identical list to agent.py:937)
plus a header-aware content-line stripper. Diff headers (`diff/index/---/+++/@@/mode/rename/copy/
Binary/GIT binary patch`) are preserved; only non-header content lines containing a trigger are
dropped. Clean patches pass through byte-identical (early-return on no-trigger).
**Wired:** `collect_repo_patch()` now `return _sanitize_patch(diff)` — so EVERY patch (normal loop
return AND the `solve()` crash-fallback path, which also calls `collect_repo_patch`) is sanitized.
Keeping it self-contained preserves high king-similarity (Intel D: 51% WR for very-similar patches).

### Change 3: Empty-reply fix (`ae2158103232`)
**Changed `ChatModel._extract_content`:**
- List-shaped content parts now read from BOTH `text` and `content` keys
  (`part.get("text") or part.get("content") or ""`), and non-dict parts are stringified. The king
  only read `text`.
- **Added empty-reply rejection:** after assembling content, `if not content.strip(): raise
  ModelQueryError("model returned empty content: …")`. Because `query()`'s retry loop treats
  `ModelQueryError` from `_extract_content` as terminal (it's raised inside the `else` branch), an
  empty proxy reply now raises cleanly instead of silently feeding an empty assistant turn into the
  loop → the loop records a ModelError step rather than burning a no-op step. This matches upstream
  commit `ae2158103232` (newer than the king; king lacks it).

### Change 4: Solve-time awareness (5% live weight)
**In `render_observation`** (new optional `elapsed` + `wall_clock_limit` kwargs): when
`wall_clock_limit > 0 AND remaining_steps <= 5 AND elapsed > 0.6 * wall_clock_limit`, append
`[Time is short. Make the minimal correct change and submit.]`. **In `run_agent_loop`** the
observation call now passes `elapsed=time.monotonic() - started` and
`wall_clock_limit=config.wall_clock_limit`. MAX_STEPS, timeouts, and the wall-clock limit are
UNCHANGED — this is purely an in-context hint. Verified: fires at elapsed=200/limit=280, silent at
elapsed=50/limit=280.

### Change 5: Urgency refinement
**In `render_observation`**, graduated remaining-steps notes:
- `<= 5`: `[5 commands left. Focus: complete the most critical missing change, then submit.]`
- `<= 3`: kept the king's existing message verbatim (`[N command(s) left. Make the smallest useful
  edit, then submit with echo …]`).
- `<= 1`: `[Final command. Submit now: echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT]`.
The time-short note (Change 4) is appended alongside whichever step note applies.

---

## Step 5 Checklist Results

| # | Check | Result | Pass |
|---|-------|--------|------|
| 1 | `ast.parse` syntax | `syntax OK` | ✅ |
| 2 | `grep -c "def solve"` (==1) | `1` | ✅ |
| 3 | `grep "COMPLETENESS BEATS MINIMALISM"` | `1` match | ✅ |
| 4 | `grep "Under-editing costs MORE"` | `1` match | ✅ |
| 5 | `grep "automatic fail"` (guard present) | `2` (prompt guard + sanitizer list) | ✅ |
| 6 | `grep "WIRING RULE\|wire new code\|never called"` | `2` matches | ✅ |
| 7 | `grep "temperature\|top_p\|top_k\|seed"` (EMPTY) | no match (exit 1) | ✅ |
| 8 | `grep "_NATIVE_TOOL_CALL_RE\|_ACTION_BLOCK_RE"` (both) | `4` (defs + usages) | ✅ |
| 9 | `grep "_sanitize_patch\|sanitize"` | `2` matches | ✅ |
| 10 | `wc -l` line count | `822` | ✅ |

**Extra verifications (beyond the 10):**
- `python3 -m compileall -q` → OK
- `solve(` signature unchanged (line 776); return dict keys `patch/logs/steps/cost/success/message` intact
- No third-party imports (stdlib only: os, subprocess, json, time, re, urllib, traceback, dataclasses, typing, __future__)
- King core structures present: `run_agent_loop`, `AgentRunConfig`, `AgentOutcome`, `_extract_commands` (4/4)
- Runtime smoke test PASSED: render_observation graduated notes + time gate; _sanitize_patch strips
  triggers while keeping headers and leaves clean patches byte-identical; _extract_content joins
  list-shaped content (`'hello world'`) and rejects empty replies; _extract_commands parses BOTH
  bash blocks (`['ls -la']`) and native tool-call tokens (`['echo hi']`).

---

## Risk Assessment

- **Regression risk: LOW.** All edits are additive prompt text + 3 small code changes. The king's
  loop, parsers, budgets, and submit sentinel are untouched. King-similarity stays very high
  (Intel D best-WR band).
- **Change 2 (sanitizer):** simplified vs agent.py's full chain. It still removes the auto-fail
  phrases (the only judge-visible value). It will NOT strip mode-only/low-signal hunks the way
  agent.py did — acceptable, those are cosmetic and not loss drivers. Header-preservation verified so
  valid diffs are never corrupted.
- **Change 3 (empty-reply rejection):** could in theory raise on a legitimately empty assistant turn,
  but a truly empty content carries no command anyway → previously a wasted/no-op step. Net neutral-
  to-positive. Retry behavior unchanged (HTTP-level retries still apply; content-empty is terminal,
  same as the king's prior "no text content" raise).
- **Change 4/5 (hints):** pure in-context strings; cannot change patch content or break the loop.
- **CI expectation:** king-base + ~138-line additive delta → expected CI ~78 (king-base lane).
  No sampling tokens, no keys/endpoints/wallets, stdlib-only → passes the CI forbidden-pattern gate.
- **SCOPE DISCIPLINE counterbalance:** mitigates over-churn that the COMPLETENESS framing could
  otherwise induce; phrased to avoid FORBIDDEN Pattern 1 ("never delete") entirely.

---

## Gate command (ready to copy-paste)

> NOTE: judge model MUST be the live judge `google/gemini-3.1-flash-lite` (Step 3 mandate — all prior
> Sonnet-judged gate data is invalid). v6's local dataset is missing; if v6 errors on dataset, use the
> v7 harness with the R2 dataset.

```bash
cd /root/sn66-ninja
tmux new-session -d -s sn66_vNext_gate
tmux send-keys -t sn66_vNext_gate \
  "cd /root/sn66-ninja && bash scripts/sync_king.sh && wc -l king_agent.py && \
   python3 -u validator_harness_v6.py \
     --challenger agent_cl_gpt_vNext.py --king king_agent.py \
     --tasks 50 --seed 42 --parallel 3 --timeout 600 \
     --judge-model google/gemini-3.1-flash-lite \
     > /tmp/vNext_gate_50.log 2>&1" Enter
tail -f /tmp/vNext_gate_50.log
```

Fallback (v7 harness + R2 dataset, if v6 dataset missing):

```bash
cd /root/sn66-ninja
tmux new-session -d -s sn66_vNext_gate
tmux send-keys -t sn66_vNext_gate \
  "cd /root/sn66-ninja && python3 -u validator_harness_v7_upstream.py \
     --challenger agent_cl_gpt_vNext.py --king king_agent.py \
     --tasks 50 --seed 42 --judge-model google/gemini-3.1-flash-lite \
     > /tmp/vNext_gate_50.log 2>&1" Enter
tail -f /tmp/vNext_gate_50.log
```

**Threshold:** ≥57–60% decisive WR (need net >6 over 50 rounds, ≈28W/21L). Report WR only after
≥40/50 tasks (L-SN66-GATE-REGRESSION-1). Kill the tmux gate session when done
(L-SN66-GATE-CLEANUP-1). Then report to James — NEVER auto-submit (L-NO-AUTO-SUBMIT-1).
```
