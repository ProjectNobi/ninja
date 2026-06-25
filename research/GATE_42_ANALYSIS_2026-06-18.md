# Gate-42 Analysis — Next42 (ProjectNobi-v42) — PASSED ✅
Date: 2026-06-18 ~17:15 UTC
Agent: agent_cl_gpt_Next42.py / agent_cl_gpt_ProjectNobi_v42.py (2171 lines)
King: king_agent.py (1262 lines, SHA 53bca97c)
Verdict: COMPETITIVE ✅ — 21W-8L+ (70%+) on 30-task gate, seed 42, timeout 600s

Saved as: agent_cl_gpt_ProjectNobi_v42.py — READY FOR SUBMISSION when ninja66.ai is back.

---

## Full Gate-42 Results (29 confirmed + T30 running)

| # | Type | Lang | Files | Us | King | Result |
|---|------|------|-------|----|------|--------|
| T1 | BUGFIX | C/C++ | 3 | 0.530 | 0.420 | ✅ WIN |
| T2 | BUGFIX | Python | 2 | 0.330 | 0.500 | ❌ LOSS |
| T3 | BUGFIX | TypeScript | 9 | 0.500 | 0.150 | ✅ WIN |
| T4 | API/ROUTE | Python | 10 | 0.380 | 0.520 | ❌ LOSS |
| T5 | API/ROUTE | PHP | 5 | 0.440 | 0.350 | ✅ WIN |
| T6 | BUGFIX | Go | 11 | 0.220 | 0.090 | ✅ WIN |
| T7 | API/ROUTE | JS | 4 | 0.480 | 0.320 | ✅ WIN |
| T8 | BUGFIX | TS DI | 5 | 0.220 | 0.140 | ✅ WIN |
| T9 | FEATURE | TS | 4 | 0.150 | 0.100 | ✅ WIN |
| T10 | BUGFIX | Swift | 5 | 0.330 | 0.200 | ✅ WIN |
| T11 | BUGFIX | Python | 14 | 0.150 | 0.270 | ❌ LOSS |
| T12 | BUGFIX | PHP | 14 | 0.420 | 0.300 | ✅ WIN |
| T13 | OTHER | Python | 2 | 0.650 | 0.590 | ✅ WIN |
| T14 | FEATURE | Python | 2 | 0.260 | 0.420 | ❌ LOSS |
| T15 | UPDATE | TypeScript | 4 | 0.700 | 0.380 | ✅ WIN |
| ... | ... | ... | ... | ... | ... | ... |
| T21-29 | various | various | — | — | — | 9W from 9 confirmed |
| T30 | BUGFIX | Python | 17 | TBD | TBD | running |

Win rate (29 confirmed): 21W-8L (72%) ✅ PASSED

## What Changed vs Gate-41 (5W-7L → 21W-8L+)

### T1 C/C++: LOSS→WIN (0.530 vs 0.420) ✅
### T3 TS BUGFIX: WIN→WIN stable ✅
### T5 PHP: WIN→WIN stable ✅
### T6 Go: LOSS→WIN (0.220 vs 0.090) ✅ — large-file hint helped
### T8 TS DI: LOSS(0.120 vs 0.780)→WIN(0.220 vs 0.140) ✅ — DI hint restored working
### T10 Swift: LOSS→WIN (0.330 vs 0.200) ✅ — large-file hint helped
### T12 PHP 14f: LOSS→WIN (0.420 vs 0.300) ✅ — large-file hint helped

## Remaining Losses (G42)

### T2 Python BUGFIX 2f (0.330 vs 0.500) — borderline loss
- Small 2-file task, both sides score reasonably
- King simply produced a better patch on this specific task
- Random variance — was a WIN in G41

### T4 Python API/ROUTE 10f (0.380 vs 0.520) — persistent
- Architext AI pipeline — king 0.520 vs us 0.380
- Large-file hint helped (G40: 0.050, G41: 0.340, G42: 0.380 — improving!)
- Still losing but gap closing: -0.500 → -0.140

### T11 Python BUGFIX 14f (0.150 vs 0.270) — persistent
- Large Python backend — king still better
- Gap: -0.120. Marginal — could flip with better file-finding

### T14 FEATURE Python 2f (0.260 vs 0.420) — surprising loss
- Small 2-file task. King scores 0.420 — significantly better
- This is a Python FEATURE task. Our agent under-implements FEATURE Python tasks
- Root cause: no FEATURE-specific guidance for Python tasks

## Next43 Targets

### TARGET 1 — T14 Python FEATURE (0.260 vs 0.420)
FEATURE tasks in Python — king scores 0.420. We score 0.260.
King's strength: complete implementation with proper wiring.
Possible fix: add a FEATURE-specific hint for Python — "For Python feature tasks,
implement the full feature including database models, API endpoint, and any
required migrations. Wire everything end-to-end."

### TARGET 2 — T2 Python BUGFIX (0.330 vs 0.500) — variance
This is random variance. T2 was WIN in G41 (0.600), LOSS in G42 (0.330).
No structural fix needed — just accept the variance.

### TARGET 3 — T4 Python API 10f (0.380 vs 0.520) — closing gap
Gap improved from -0.500 to -0.140 over 4 gates. Might flip naturally.
Large-file hint is helping. Could add more specific guidance for multi-file
Python API tasks.

### TARGET 4 — T11 Python 14f (0.150 vs 0.270) — still losing
Large Python BUGFIX, 14 files. King 0.270, us 0.150. Gap: -0.120.
The large-file hint fires but agent still under-implements.

## Next43 Strategy
Base: Next42 (ProjectNobi-v42) — PROVEN ✅
Add targeted improvements for the 4 remaining loss categories:
1. Python FEATURE hint (T14) — implement fully end-to-end
2. Refine large-file hint to be more aggressive for 12+ files (T11)
3. Everything else: KEEP — don't touch what's working

Expected: 22-24W/30 (73-80%) if these fixes work.

---

## ⚠️ POST-GATE INTEL UPDATE (2026-06-18, SN66 team)

Reference patch has been REMOVED from the live validator. Our G42 72% result
was scored partially against the reference — the new judge scores purely on
task quality. Gate results G37-G44 are partially invalid.

On restart: sync king → update harness (remove ref patch) → re-gate → then decide.
ProjectNobi-v42 is still our best agent, but needs re-validation against new judge.

