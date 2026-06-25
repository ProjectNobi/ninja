# SN66 Next5 — Build Report
*Built: 2026-06-14 | T68Bot Opus 4.8 subagent | NOT YET SUBMITTED (James approval required)*

---

## Objective
Beat the new king (`01c675065c1c`, 776L flattened) by combining the king's
verify-repair pass with Next1's proven SYSTEM_PROMPT additions — the changes
that delivered **55% WR vs the new king** in live duel #6654 (27W/22L).

**Deliverable:** `/root/sn66-ninja/agent_cl_gpt_Next5.py` (850 lines)

---

## Strategy: HYBRID (Next1 strengths + king repair pass, NO task-type detection)

### Core insight (from live + gate data)
- **Next1 = our best performer.** It is the *simplest* improvement over the old
  king and scored **55% WR vs the NEW king** without even being designed for it
  (lost by only 5 net rounds; needed win-margin >6 on 50 rounds).
- **Task-type detection HURTS.** Next4 gate (early, 7/30 tasks, seed 137) = **16% WR**
  (BUGFIX 0/3, API 0/2). Next2v3 = 43%. The new king's TASK_TEMPLATE is already
  well-calibrated; adding `_detect_task_type` protocols fights it and over-complicates
  simple tasks.
- **The king's edge is the verify-repair pass** (`_repair_reason` /
  `_build_repair_task` + bounded second solve loop). Next5 keeps it 100% intact.

### Base
`king_agent.py` (776L) — per **L-SN66-KING-BASE-MANDATORY-1**. NOT Next4, NOT Next2v3.

---

## Changes applied (exactly the 6 specified)

| # | Change | Source | Status |
|---|--------|--------|--------|
| 1 | SYSTEM_PROMPT additions (COMPLETENESS BEATS MINIMALISM, ACCEPTANCE CRITERIA FIRST, UPDATE TASK WIRING RULE, CORRECTNESS GUARDS, OUTPUT SAFETY auto-fail guard) | Next1 | ✅ ported verbatim, appended AFTER king's existing SYSTEM_PROMPT |
| 2 | Empty-reply guard — raises `ModelQueryError` on empty content (retry instead of silent no-op) | Next1 | ✅ wired into `ChatModel._extract_content` |
| 3 | Graduated urgency hints at 5/3/1 remaining steps + wall-clock awareness | Next1 | ✅ in `render_observation`; call site extended to pass `elapsed`/`wall_clock_limit` |
| 4 | Verify-repair pass (`_repair_reason`, `_build_repair_task`, second solve loop) | King | ✅ **BYTE-IDENTICAL** to king (verified via diff of entire `agent.py` block) |
| 5 | NO task-type detection (`_detect_task_type` deliberately absent) | — | ✅ confirmed absent |
| 6 | Clean docstring (no "flattened king" language) | spec | ✅ |

### Notes on each change

**Change 1 — SYSTEM_PROMPT.** King's SYSTEM_PROMPT (concise: format contract only)
is preserved verbatim; Next1's five sections are appended after it. This keeps
the king's framing intact while adding the completeness asymmetry, AC-first,
and UPDATE wiring rules that are mandated by FINAL_SN66_PIPELINE.md "Required
Patterns" and corroborated by STEP2 Intel (967 lessons = partial implementation
is the #1 loss cause; 649 = scope creep #2; UPDATE wiring rule preserved).

**Change 2 — Empty-reply guard.** King's `_extract_content` returns whatever
content exists (could be empty string → silent no-op step). Next5 adds Next1's
final guard: `if not content.strip(): raise ModelQueryError(...)`. The loop's
`ModelQueryError` handler retries via the model's own `max_attempts`, recovering
instead of advancing on a wasted step. King's list-content handling is preserved.

**Change 3 — Graduated urgency.** King had only a single `remaining_steps <= 3`
note. Next5 extends to 5/3/1 thresholds plus a solve-time nudge when
`elapsed > 0.6 * wall_clock_limit` and ≤5 steps remain. The king's completeness-
and-submit framing is retained inside the 3/1 notes (not replaced with pure
minimalism). The `agent_loop` call site now passes `elapsed` and
`wall_clock_limit` (both already tracked by the loop), with safe defaults of 0.0
so the signature is backward-compatible.

**Change 4 — Repair pass.** The full `# Inlined from: agent.py` block (config,
`_resolve_inference_config`, `build_initial_user_prompt`, `_changed_py_files`,
`_py_syntax_errors`, `_repair_reason`, `_build_repair_task`, and `solve()` with
its bounded second loop) is **byte-identical** to the king — verified by
`diff` returning no differences. This is the king's main advantage and is left
untouched.

**Change 5 — No task detection.** `_detect_task_type` is deliberately not
present. Gate data (Next4 16%, Next2v3 43%) shows task-type protocols regress
against this king.

---

## Step 5 Checklist — ALL PASS

```
✅ syntax          (python3 -m py_compile)
✅ import OK        (from agent_n5 import solve)
✅ repair pass      (_repair_reason / _build_repair_task present, 4 matches)
✅ completeness     (COMPLETENESS BEATS MINIMALISM present)
✅ no task detection (_detect_task_type absent)
✅ no sampling      (no temperature/top_p/top_k outside comments)
✅ clean            (no grader/reward model)
✅ empty-reply fix  (model returned empty content guard present)
   850 lines
```

Additional verification:
- ✅ `agent.py` block (solve + verify-repair) **byte-identical** to king.
- ✅ `render_observation` call site passes `elapsed` + `wall_clock_limit`.
- ✅ `solve()` signature unchanged (validator contract preserved).
- ✅ No hardcoded API keys / endpoints / wallet references.
- ✅ Auto-fail guard contains `'automatic fail'` / `'ignore previous instructions'`
  ONLY — no `grader` / `reward model` (those phrases themselves are auto-fail
  triggers in patch content per STEP2 Intel A).
- ✅ `_sanitize_patch` deliberately NOT added (king has no such guard; keeping
  the patch-collection path byte-identical to king maximizes king-similarity,
  which Intel D shows correlates with higher WR; 51% very_similar vs 38% very_diff).

---

## Why Next5 should beat the king (data-backed)

1. **Starts from the 55% baseline.** Next1's exact SYSTEM_PROMPT + empty-reply
   fix + urgency hints scored 55% vs this king. Next5 reproduces all of them.
2. **Adds the king's repair pass on top.** Next1 did NOT have the verify-repair
   pass. Next5 = Next1's prompt strengths + king's repair safety net. The repair
   pass converts empty/broken patches into valid ones — pure upside on the
   rounds where the first solve produced an unparseable or empty diff.
3. **No task-type detection drag.** The two regressions (Next4 16%, Next2v3 43%)
   both carried task-type detection. Removing it eliminates the documented drag.
4. **High king-similarity.** Patch-collection + repair pass are byte-identical to
   king; only the prompt + two small loop hooks differ. Intel D: very_similar
   patches win 51% vs 38% for very different ones.

---

## Risks / open questions

- **Win-margin gap.** Next1 hit 55% but needed >6 net wins on 50 rounds to
  dethrone (it got +5). 55% ≈ +5; we need ~57%+ for a reliable margin. The
  repair pass is the lever expected to close that gap (recovers the ~few rounds
  lost to empty/broken first-pass diffs).
- **Gate confirmation needed.** No gate has been run on Next5 yet. Per pipeline:
  50 tasks, seed 42, `--timeout 600`, in tmux, threshold ≥60%. Recommend also a
  second seed (137 or 271) to avoid overfit, matching live BUGFIX/FEATURE-heavy
  distribution (STEP2 Intel E).
- **King turnover.** Current king `a56ffdf5`/`01c675065c1c` is the burn default
  (defended 13 duels). Re-sync king before any gate; if king changes, restart.

---

## Next steps (NOT executed — awaiting James)

1. **Gate test** (tmux, 50 tasks seed 42 --timeout 600, threshold ≥60%):
   ```bash
   tmux new-session -d -s sn66_next5_gate
   tmux send-keys -t sn66_next5_gate \
     "cd /root/sn66-ninja && python3 -u validator_harness_v6.py \
     --challenger agent_cl_gpt_Next5.py --king king_agent.py \
     --tasks 50 --seed 42 --parallel 3 --timeout 600 > /tmp/next5_gate_50.log 2>&1" Enter
   ```
2. Report full results (breakdown by task type) to James.
3. **Submit only after James's explicit approval** (L-NO-AUTO-SUBMIT-1).

---

*Build complete. File: `/root/sn66-ninja/agent_cl_gpt_Next5.py` (850L, syntax-clean, import-clean).*
*Verify-repair pass byte-identical to king. All Step 5 checks pass. Awaiting James approval before any submission or gate run.*
