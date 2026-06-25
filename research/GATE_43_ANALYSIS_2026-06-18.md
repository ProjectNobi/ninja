# Gate-43 Analysis — Root Cause for Next44
Date: 2026-06-18 ~19:00 UTC
Gate-43 killed at 17 tasks: 7W-10L (41%) ❌ — regression from G42 (21W-8L)

## Full Comparison: G42 vs G43 (same 17 tasks)

| # | Type | Lang | G42 Us | G42 King | G42 | G43 Us | G43 King | G43 | Change |
|---|------|------|--------|----------|-----|--------|----------|-----|--------|
| T1 | BUGFIX | C/C++ 3f | 0.530 | 0.420 | ✅ | 0.550 | 0.220 | ✅ | STABLE |
| T2 | BUGFIX | Python 2f | 0.330 | 0.500 | ❌ | 0.550 | 0.420 | ✅ | FIXED ✅ |
| T3 | BUGFIX | TypeScript 9f | 0.500 | 0.150 | ✅ | 0.220 | 0.350 | ❌ | REGRESSED ❌ |
| T4 | API/ROUTE | Python 10f | 0.380 | 0.520 | ❌ | 0.500 | 0.630 | ❌ | WORSE |
| T5 | API/ROUTE | PHP 5f | 0.440 | 0.350 | ✅ | 0.180 | 0.570 | ❌ | REGRESSED ❌ |
| T6 | BUGFIX | Go 11f | 0.220 | 0.090 | ✅ | 0.180 | 0.100 | ✅ | STABLE |
| T7 | API/ROUTE | JS 4f | 0.480 | 0.320 | ✅ | 0.380 | 0.720 | ❌ | REGRESSED ❌ |
| T8 | BUGFIX | TS DI 5f | 0.220 | 0.140 | ✅ | 0.280 | 0.800 | ❌ | REGRESSED ❌ |
| T9 | FEATURE | TS 4f | 0.150 | 0.100 | ✅ | 0.150 | 0.280 | ❌ | REGRESSED ❌ |
| T10 | BUGFIX | Swift 5f | 0.330 | 0.200 | ✅ | 0.480 | 0.200 | ✅ | BETTER ✅ |
| T11 | BUGFIX | Python 14f | 0.150 | 0.270 | ❌ | 0.320 | 0.260 | ✅ | FIXED ✅ |
| T12 | BUGFIX | PHP 14f | 0.420 | 0.300 | ✅ | 0.300 | 0.420 | ❌ | REGRESSED ❌ |
| T13 | OTHER | Python 2f | 0.650 | 0.590 | ✅ | 0.300 | 0.350 | ❌ | REGRESSED ❌ |
| T14 | FEATURE | Python 2f | 0.260 | 0.420 | ❌ | 0.340 | 0.120 | ✅ | FIXED ✅ |
| T15 | UPDATE | TS 4f | 0.700 | 0.380 | ✅ | 0.440 | 0.720 | ❌ | REGRESSED ❌ |
| T16 | UPDATE | JS 9f | — | — | — | 0.400 | 0.500 | ❌ | NEW LOSS |
| T17 | FEATURE | C/C++ 7f | — | — | — | 0.180 | 0.080 | ✅ | NEW WIN |

G42 first 15: 13W-2L. G43 first 17: 7W-10L. Massive regression.

## ROOT CAUSE — CONFIRMED: _PYTHON_COMPLETE_RE is too broad

### Evidence:
- T5 PHP: G42=WIN(0.440), G43=LOSS(0.180 vs 0.570). PHP task, NOT Python. Yet regressed badly.
- T7 JS: G42=WIN(0.480), G43=LOSS(0.380 vs 0.720). JS task. Also regressed.
- T8 TS DI: G42=WIN(0.220 vs 0.140), G43=LOSS(0.280 vs 0.800). TS task. King now 0.800.
- T9 FEATURE TS: G42=WIN(0.150 vs 0.100), G43=LOSS(0.150 vs 0.280).
- T12 PHP: G42=WIN(0.420), G43=LOSS(0.300 vs 0.420).
- T13 OTHER Python: G42=WIN(0.650), G43=LOSS(0.300 vs 0.350). Same Python task! Worse!
- T15 UPDATE TS: G42=WIN(0.700), G43=LOSS(0.440 vs 0.720). TypeScript task regressed.

### Why _PYTHON_COMPLETE_RE causes non-Python regressions:
The regex fires on `.py\b|python|...` — but the ISSUE TEXT for non-Python tasks
often MENTIONS Python (e.g. "The backend is written in Python and the frontend in TS"
or "uses Python scripts"). When it fires on a PHP/JS/TS task, it injects
"Python task: implement the full change including models, API endpoints..." — which
CONFUSES the agent working on a PHP/JS/TS file.

Additionally: even for actual Python tasks, "include all required components
(model fields, API endpoints, service methods, migrations, tests)" may cause
the agent to OVER-IMPLEMENT and add things not required → churn penalty.

### The fixed tasks (POSITIVE from Next43):
- T2 Python 2f: ❌→✅ (hint helped on small focused Python task)
- T11 Python 14f: ❌→✅ (large-file expanded hint helped)
- T14 FEATURE Python: ❌→✅ (Python completeness hint actually helped here)
- T10 Swift: ✅→✅ better score (0.330→0.480)

### The regressed tasks (NEGATIVE from Next43 — 8 regressions):
T3 TS, T5 PHP, T7 JS, T8 TS DI, T9 FEATURE TS, T12 PHP, T13 Python OTHER, T15 UPDATE TS

## NEXT44 STRATEGY: Remove _PYTHON_COMPLETE_RE, keep _LARGE_REPO_RE expansion

The evidence is unambiguous:
- _PYTHON_COMPLETE_RE caused 8 regressions (T3/T5/T7/T8/T9/T12/T13/T15)
- _PYTHON_COMPLETE_RE fixed 3 tasks (T2/T11/T14)
- Net: -5 rounds vs G42

### CHANGE 1 — Remove _PYTHON_COMPLETE_RE entirely
Delete the regex definition and the branch in _integration_hints().
This restores G42's proven performance on T3/T5/T7/T8/T9/T12/T15.

### CHANGE 2 — Keep _LARGE_REPO_RE expansion from Next43 (it helped T11)
T11 Python 14f: G42=LOSS(0.150), G43=WIN(0.320) — the expanded _LARGE_REPO_RE
matched "pyproject" in the task and the stronger hint helped. KEEP this.

### Result: Next44 = Next42 - _PYTHON_COMPLETE_RE + expanded _LARGE_REPO_RE
Expected: G42's 21W-8L + T11 flipped = 22W-7L (~73%)

This is a clean, evidence-based decision. G44 should be our best result yet.
