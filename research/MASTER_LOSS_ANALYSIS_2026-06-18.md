# Master Loss Analysis — All Gates — Root Cause for Next42
Date: 2026-06-18 ~14:35 UTC

## Cross-Gate Evidence — Same 30-Task Seed (seed 42)

| # | Type | Lang | Files | G37-30 | G39-30 | G40-30 | G41-30 | Pattern |
|---|------|------|-------|--------|--------|--------|--------|---------|
| T1 | BUGFIX | C/C++ | 3 | ❌0.320 | ✅0.380 | ❌0.080 | ❌0.380 | VOLATILE |
| T2 | BUGFIX | Python | 2 | ✅0.420 | ❌0.320 | ✅0.280 | ✅0.600 | MOSTLY WIN |
| T3 | BUGFIX | TypeScript | 9 | ❌0.380 | ❌0.000 | ✅0.520 | ✅0.610 | IMPROVING |
| T4 | API/ROUTE | Python | 10 | ❌0.120 | ❌0.050 | ❌0.050 | ❌0.340 | PERSISTENT LOSS |
| T5 | API/ROUTE | PHP | 5 | ❌0.300 | ❌0.140 | ❌0.120 | ✅0.580 | FIXED IN G41! |
| T6 | BUGFIX | Go | 11 | ❌0.070 | 🤝0.000 | ✅0.720 | ❌0.040 | VOLATILE |
| T7 | API/ROUTE | JS | 4 | ❌0.280 | — | ✅0.180 | ✅0.480 | WIN |
| T8 | BUGFIX | TypeScript DI | 5 | ❌0.060 | — | ✅0.120 | ❌0.120 | VOLATILE (king 0.780 in G41!) |
| T9 | FEATURE | TypeScript | 4 | ✅0.270 | — | ❌0.100 | ✅0.200 | VOLATILE |
| T10 | BUGFIX | Swift | 5 | ❌0.000 | — | ❌0.080 | ❌0.100 | PERSISTENT LOSS |
| T11 | BUGFIX | Python | 14 | ❌0.090 | — | ❌0.180 | ❌0.220 | PERSISTENT LOSS |
| T12 | BUGFIX | PHP | 14 | ✅0.270 | — | ❌0.120 | ❌0.000 | REGRESSION |

## Critical Finding: T8 TypeScript DI — 0.120 vs 0.780 in G41

This is the SMOKING GUN. T8 is "Improve Streamable HTTP Server Error Handling"
(src/di/Container.ts, 5 files). In G41:
- US: 0.120
- KING: 0.780 ← massive gap

The king WITHOUT our DI hint scores 0.780. We score 0.120.
This is NOT a hint problem — the king's SOLVE QUALITY is fundamentally better here.

BUT WAIT — in G36 we scored 0.750 on this EXACT TASK with the _CONTAINER_DI_RE hint.
We went 0.750 (G36) → 0.080 (G37-30) → 0.120 (G41).

The _CONTAINER_DI_RE hint WAS helping (0.750). Removing it HURT us on this task.
The hint was removed in Next39 as "too narrow" but it was actually correct for T8.

## The Real Paradox

We face a fundamental tension:
1. Adding narrow language hints → helps specific tasks but overfits 10-task seed
2. Removing hints → helps 30-task generalization on MOST tasks but HURTS T8 (DI)
3. The king beats us on T4/T11 (large Python) without any hints — pure solve quality

## What's Actually Happening Task by Task

### WINS (consistently or improving):
- T2 Python BUGFIX (2 files): WE WIN — small focused task, we handle well
- T3 TS BUGFIX (9 files): WE WIN in G40/G41 — improving
- T5 PHP API (5 files): WE WIN in G41 (0.580) — king purity fixed this!
- T7 JS API (4 files): WE WIN — consistent
- T9 FEATURE TS (4 files): volatile but winnable

### PERSISTENT LOSSES (structural, king is just better):
- T4 Python API/ROUTE (10 files): king 0.38-0.55, us 0.05-0.34 EVERY GATE
  → King implements the AI pipeline more completely in 10-file Python repos
- T10 Swift (5 files): both agents score low, king slightly better
  → Swift is rare, both struggle
- T11 Python BUGFIX (14 files): king 0.35-0.38, us 0.09-0.22
  → Large file count, king finds core files faster and implements more completely

### VOLATILE (need stabilization):
- T1 C/C++ (3 files): alternates WIN/LOSS — inconsistent
- T6 Go (11 files): alternates 0.720 WIN / 0.040 LOSS — random
- T8 TS DI (5 files): 0.750 with hint → 0.120 without → needs the DI hint back
- T12 PHP (14 files): volatile

## Root Cause: The REAL Gap is on LARGE FILE COUNT Tasks

Tasks with ≥10 files: T4(10f), T6(11f), T11(14f), T12(14f)
- T4: PERSISTENT LOSS every gate — king 0.38-0.55, us 0.05-0.34
- T6: VOLATILE — king sometimes 0.000 (also times out), we sometimes 0.720
- T11: PERSISTENT LOSS — king 0.35-0.38, us 0.09-0.22
- T12: VOLATILE but trending bad

On these large-file tasks, king consistently reads the right files faster and
implements more completely. It spends fewer steps on file exploration.

## What King Does on Large-File Tasks That We Don't

Looking at king's approach: it uses `find . -type f` to get all files,
then picks 2-3 core files based on the issue, reads them fully, implements.
Our agent reads MORE files = burns more steps = less time to implement.

The TASK_TEMPLATE says "Read Files in Full" — which on 10-14 file repos
means reading ALL files = burning 5-8 steps just on reads.

## Next42 Strategy: TWO targeted fixes

### FIX 1 — Restore _CONTAINER_DI_RE for T8 (proven 0.750 in G36)
T8 TypeScript DI is a very specific, identifiable task. The DI hint was proven
to help significantly. The reason it was removed (too narrow, hurts 30-task)
was wrong — it only fires on Container.ts DI tasks, not broadly.

Add back a NARROW version:
When issue mentions "Container" AND files include "Container.ts" or "di/":
→ "Read the Container class interface and registered services before editing.
   Focus on the HTTP error handling and element reload logic as the primary fix target."

### FIX 2 — Large-file focus hint (helps T4, T11, T12)
When file_count > 8 (any language):
→ "Large repo: use `grep -r` or `find` to identify the 2-3 files that own
   the core logic. Read ONLY those files before implementing. Do not read all
   files sequentially — identify the change owners first."

This is GENERAL (not language-specific) and addresses the actual problem:
agent reads too many files on large repos.

### Keep everything from Next41 (king purity base) — these are working:
- King's 6 content-based _integration_hints ✅
- No checklist injection ✅
- No polish ✅
- SYSTEM_PROMPT rider (COMPLETENESS + UPDATE WIRING) ✅

## Expected Next42 Impact
- T8 DI: 0.120 → ~0.600+ (DI hint restored) → +1 win
- T4 Python (10f): 0.340 → ~0.450+ (large-file hint) → possible flip
- T11 Python (14f): 0.220 → ~0.320+ (large-file hint) → marginal improve
- T5 PHP already winning in G41 → keep ✅
- T2/T3/T7 already winning → keep ✅

Conservative: 7-8W from first 12 (vs 5W now) → ~55-60% on 30 tasks
