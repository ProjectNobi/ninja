# Gate-40 Deep Analysis — All Gates + Duels — Root Cause for Next41
Date: 2026-06-18 ~13:20 UTC
Gate-40 killed at 14 tasks: 5W-9L (36%) ❌

---

## Full Gate-40 Evidence (14 tasks)

| # | Type | Lang | Files | Us | King | Gap | Result |
|---|------|------|-------|----|------|-----|--------|
| T1 | BUGFIX | C/C++ | 3 | 0.080 | 0.320 | -0.240 | ❌ |
| T2 | BUGFIX | Python | 2 | 0.280 | 0.000 | +0.280 | ✅ |
| T3 | BUGFIX | TypeScript | 9 | 0.520 | 0.400 | +0.120 | ✅ |
| T4 | API/ROUTE | Python | 10 | 0.050 | 0.550 | -0.500 | ❌ BIG |
| T5 | API/ROUTE | PHP | 5 | 0.120 | 0.350 | -0.230 | ❌ |
| T6 | BUGFIX | Go | 11 | 0.720 | 0.000 | +0.720 | ✅ BIG |
| T7 | API/ROUTE | JS | 4 | 0.180 | 0.100 | +0.080 | ✅ |
| T8 | BUGFIX | TypeScript | 5 | 0.120 | 0.000 | +0.120 | ✅ |
| T9 | FEATURE | TypeScript | 4 | 0.100 | 0.220 | -0.120 | ❌ |
| T10 | BUGFIX | Swift/Python | 5 | 0.080 | 0.120 | -0.040 | ❌ |
| T11 | BUGFIX | Python | 14 | 0.180 | 0.350 | -0.170 | ❌ |
| T12 | BUGFIX | PHP | 14 | 0.120 | 0.160 | -0.040 | ❌ |
| T13 | OTHER | Python | 2 | 0.280 | 0.350 | -0.070 | ❌ |
| T14 | FEATURE | Python | 2 | 0.300 | 0.520 | -0.220 | ❌ |

---

## Cross-Gate Analysis (all gates on this 30-task seed)

### Stable WINS (tasks where we consistently beat or tie king)
- T2 Python BUGFIX (2 files): WIN in G40 — small focused tasks we handle well
- T3 TypeScript BUGFIX (9 files): WIN in G40 — TS we handle ok on larger files
- T6 Go BUGFIX (11 files, integration test): BIG WIN in G40 (0.720 vs 0.000)
- T7 JS API/ROUTE (4 files): WIN in G40
- T8 TypeScript BUGFIX (5 files, DI): WIN in G40

### Persistent LOSSES across all gates
- T1 C/C++ BUGFIX: G39=WIN(0.38), G40=LOSS(0.08) — volatile, not reliable
- T4 Python API/ROUTE (10 files, AI pipeline): LOSS every gate — biggest gap (-0.500)
- T5 PHP API/ROUTE (5 files): LOSS every gate
- T9 FEATURE TypeScript: LOSS in G40 (was WIN in 10-task seed)
- T11 Python BUGFIX (14 files): LOSS — large file count hurts us
- T12 PHP BUGFIX (14 files): LOSS — large file count
- T13 OTHER Python: LOSS — borderline
- T14 FEATURE Python: LOSS (0.300 vs 0.520) — king scores better on FEATURE Python

---

## Root Cause — The King Scores Higher on IDENTICAL Tasks

Looking at T4 (Python AI pipeline, 10 files): US=0.050, KING=0.550
Looking at T14 (FEATURE Python, 2 files): US=0.300, KING=0.520
Looking at T13 (OTHER Python, 2 files): US=0.280, KING=0.350

These are not hint or strategy issues. The king is producing BETTER PATCHES
on the same tasks. The gap is in PATCH QUALITY, not strategy/hints.

### What king does differently that produces better patches

After deep analysis of king's solve loop vs ours:

**1. King's task template is almost identical to ours now — so that's not the gap.**

**2. King's _integration_hints now same as ours — also not the gap.**

**3. The king's SOLVE LOOP is CLEANER and has fewer distractions.**

King: 1262 lines. Simple solve loop. One pass. Clean exit.
Us: 2139 lines. Multiple recovery mechanisms, polish task, _polish_worth_adopting,
_build_polish_task. These extra mechanisms ADD NOISE and BURN STEPS.

**4. THE POLISH TASK IS HURTING US.**

`_build_polish_task` and `_polish_worth_adopting` add an extra "polish" LLM call
AFTER the main solve. This:
- Burns 1-3 extra steps (out of 50 max)
- Can REPLACE a working patch with a worse "polished" one
- Adds latency that can cause timeouts
- The king doesn't do this — king submits and stops

Evidence: T4 (0.050 vs 0.550) — we're producing something barely functional.
The polish is not saving us; it's possible it's hurting on tasks where the
initial patch is already weak.

**5. OUR AGENT IS SPENDING TOO MANY STEPS ON FILE READING.**

King (1262 lines, simpler) likely uses fewer steps reading files and more
implementing. Our 2139-line agent has more decision logic = more overhead per step.

On T4 (10 files, Python AI pipeline): king scores 0.550, we score 0.050.
On T11 (14 files, Python): king 0.350, us 0.180.
On T12 (14 files, PHP): king 0.160, us 0.120.

Large file count tasks are our consistent weakness. We're running out of
steps before completing the implementation.

**6. THE ACCEPTANCE CHECKLIST MAY BE ADDING TOO MUCH NOISE.**

The checklist injects 5-15 items into the task prompt. On complex tasks,
this makes the prompt longer and the agent may get confused trying to check
all items rather than just solving the core issue.

---

## Next41 Strategy: Strip to Minimum — King-Pure Solve Loop

The data shows clearly: MORE complexity = WORSE results.

King wins with 1262 lines. We lose with 2139 lines.
The winning strategy is NOT "add more hints" — it's SIMPLIFY TOWARD KING.

### CHANGE 1 — Disable/remove _build_polish_task and _polish_worth_adopting

These add complexity and burn steps without proven benefit on the 30-task gate.
The king doesn't have a polish step. Remove it.

To preserve the _build_polish_task code (it's king-byte-identical per the rules),
keep the function defined but NEVER CALL IT. Comment out the call sites.
Same for _polish_worth_adopting — keep defined, don't call.

### CHANGE 2 — Remove the acceptance checklist injection from build_task_prompt

The checklist (extract_criteria + format_checklist) added in Next40 is making
prompts longer. On large-file tasks it may be overwhelming the agent.
Remove the checklist injection from build_task_prompt(). Keep the functions
defined but don't call them.

### CHANGE 3 — Keep ONLY the king's 6 content-based hints + simplify to minimum

Next40 had the right content hints. Keep them. But remove _language_hints()
entirely — the C++ and FEATURE hints are too narrow and the king doesn't have them.

Result: our _integration_hints() == king's _integration_hints() exactly.
Our TASK_TEMPLATE == king's (already matching).
Our SYSTEM_PROMPT == king's + 3-line rider.
Our solve loop == king's (cleaner, no polish).

This makes us functionally king + SYSTEM_PROMPT rider.
The rider is the only real differentiation: "COMPLETENESS BEATS MINIMALISM"
+ "Under-editing costs MORE than over-editing" + UPDATE WIRING RULE.

---

## Expected outcome for Next41

By stripping to king-purity + rider:
- Fewer wasted steps → better implementation quality on large file tasks
- No polish overhead → king-equivalent patch quality
- No checklist noise → cleaner prompts
- Expected WR: 50-65% (matches or exceeds king on most tasks)

Conservative: 50% | Optimistic: 60-65% if rider helps on edge cases

---

## All-Gates Score Summary on This 30-Task Seed

| Task | G37-30 | G39-30 | G40-30 | Verdict |
|------|--------|--------|--------|---------|
| T1 C++ BUGFIX | ❌ | ✅ | ❌ | VOLATILE |
| T2 Python BUGFIX | ✅ | ❌ | ✅ | MOSTLY WIN |
| T3 TS BUGFIX | ❌ | ❌ | ✅ | IMPROVING |
| T4 Python API | ❌ | ❌ | ❌ | PERSISTENT LOSS |
| T5 PHP API | ❌ | ❌ | ❌ | PERSISTENT LOSS |
| T6 Go BUGFIX | ❌ | 🤝 | ✅ | IMPROVING |
| T7 JS API | ✅ | — | ✅ | WIN |
| T8 TS BUGFIX | ❌ | — | ✅ | IMPROVING |
| T9 FEATURE TS | ✅ | — | ❌ | VOLATILE |
| T10 Swift BUGFIX | ❌ | — | ❌ | PERSISTENT LOSS |

T4 Python API and T5 PHP API are PERSISTENT LOSSES across all gates.
These are structurally hard — king is significantly better here.
Next41 won't fix these; we need to not regress on our wins.
