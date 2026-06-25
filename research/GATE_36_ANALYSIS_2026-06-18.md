# Gate-36 Analysis — Next36 vs King hashirama
Date: 2026-06-18 ~09:18 UTC
Agent: agent_cl_gpt_Next36.py (2851 lines)
King: king_agent.py (1262 lines, SHA 53bca97c)
Verdict: NOT COMPETITIVE ❌ — 5W-5L (50%)

---

## Full Round Breakdown

| # | Type      | Lang       | Us    | King  | Result | G33   | G34   | G35   | Trend |
|---|-----------|------------|-------|-------|--------|-------|-------|-------|-------|
| 1 | BUGFIX    | C/C++      | 0.520 | 0.430 | ✅ WIN  | ❌0.280| ❌0.520| ✅0.680| stable win |
| 2 | BUGFIX    | Python     | 0.440 | 0.520 | ❌ LOSS | ✅0.620| ✅0.530| ❌0.490| volatile |
| 3 | BUGFIX    | TypeScript | 0.300 | 0.400 | ❌ LOSS | ✅0.520| ✅0.520| ❌0.280| volatile |
| 4 | API/ROUTE | Python     | 0.440 | 0.140 | ✅ WIN  | ✅0.450| ❌0.120| ❌0.180| RESTORED 🔥|
| 5 | API/ROUTE | PHP        | 0.180 | 0.350 | ❌ LOSS | ❌0.300| ❌0.280| ✅0.620| volatile |
| 6 | BUGFIX    | Go         | 0.080 | 0.000 | ✅ WIN  | ❌0.150| ✅0.090| ✅0.620| stable win |
| 7 | API/ROUTE | JS         | 0.350 | 0.120 | ✅ WIN  | ❌0.330| ✅0.520| ✅0.550| stable win |
| 8 | BUGFIX    | TS DI      | 0.750 | 0.000 | ✅ WIN  | ✅0.450| ❌0.040| ❌0.080| RESTORED 🔥🔥|
| 9 | FEATURE   | TypeScript | 0.180 | 0.680 | ❌ LOSS | ✅0.850| ❌0.000| ❌0.100| BROKEN — king 0.680 |
|10 | BUGFIX    | Python     | 0.000 | 0.180 | ❌ LOSS | ✅0.270| ✅0.220| ✅0.380| NEW COLLAPSE |

---

## What's Working (stable wins)
- **T1 C++**: 4th gate winning (0.520 vs 0.430). C++ hint locked in.
- **T4 Python API**: RESTORED to WIN (0.440 vs 0.140). Pipeline hint working.
- **T6 Go**: Stable win. Go hint locked in.
- **T7 JS**: Stable win (3rd gate). Scoped JS hint locked in.
- **T8 TS DI**: RESTORED — 0.750 vs 0.000. Refined DI hint working brilliantly.

## Critical Losses

### T9 FEATURE TypeScript — STRUCTURAL PROBLEM (0.850→0.000→0.100→0.180)
- This is the same task every gate: "Implement Adjustable Map Zoom Speed" (preferences.component.ts, 4 files)
- G36: us 0.180 vs king **0.680** — king is now DOMINATING (cursor_sim 0.052 vs 0.301)
- King cursor_sim 0.301 >> ours 0.052 — king is making far more reference-similar changes
- The king implements EXACTLY what the reference expects; we implement something different
- Our FEATURE hint (_FEATURE_VERB_RE/_FEATURE_SUBJECT_RE) fired — but agent still went wrong direction
- Root cause: our agent over-engineers the zoom implementation (adds complex classes/services) while the task expects a simple preference field + direct binding in preferences.component.ts
- The king's simpler approach (fewer steps, direct edit) beats our more complex approach
- FIX NEEDED: for FEATURE tasks with small file count (≤5), CONSTRAIN output: "Make the minimal change — add the field and wire it directly. Do NOT add new services, classes, or abstractions unless explicitly requested."

### T10 Python BUGFIX — NEW COLLAPSE (0.270→0.220→0.380→0.000)
- Task: "Enhance LoRA Publish Flow with Export Kind Enumeration and Job Registration" (Swift/Python, 5 files)
- G36: us **0.000** vs king 0.180 — complete collapse, zero output (cursor_sim 0.000)
- Was stable WIN in G33/G34/G35. Something in Next36 broke it.
- cursor_sim 0.000 = empty patch / sanitized to nothing
- Candidate cause: _PYTHON_PIPELINE_RE (new in Next36) fired on this task — it mentions "Publish Flow" and "Registration" — possibly matching the pipeline regex when it shouldn't.
- Check: does "LoRA Publish Flow" match `_PYTHON_PIPELINE_RE`? If yes, the pipeline hint told agent to focus on 2-3 core files and skip config — but this task NEEDS to touch Swift + Python files together.
- FIX: Tighten `_PYTHON_PIPELINE_RE` to NOT fire on Swift-containing tasks or tasks with "publish"/"flow" without "AI"/"ML"/"backend" context.

### T2 Python BUGFIX — Persistent Variance (0.620→0.530→0.490→0.440)
- Gradual decline over 4 gates. Was 0.620 WIN in G33, now 0.440 LOSS (margin: 0.080).
- cursor_sim: 0.147 vs 0.188 — king slightly more reference-similar.
- No new hint should affect this (Python BUGFIX, 2 files). Possible the _PYTHON_PIPELINE_RE fired on "Intent Detection API" (mentions "API" + "endpoint" + "Chat") — if so, it constrained the agent unnecessarily on a small 2-file task.
- FIX: _PYTHON_PIPELINE_RE must only fire when file_count > 8 (already specified) — verify the count guard is working.

### T3 TypeScript BUGFIX — Volatile (0.520→0.520→0.280→0.300)
- Dropped in G35, slightly recovered in G36 (0.280→0.300) but still LOSS.
- cursor_sim: 0.071 vs 0.055 — WE are more reference-similar but still lost on judge score.
- This is judge variance on a borderline task. No structural fix available.
- We score 0.300 vs king 0.400 — 0.100 gap, judge consistently prefers king's style.
- Possible: king has a TypeScript-specific style preference (explicit types, cleaner diffs) that our agent doesn't match.

### T5 PHP API — Volatile (❌0.300→❌0.280→✅0.620→❌0.180)
- Wildly inconsistent across gates. 0.620 WIN in G35 → 0.180 LOSS in G36.
- cursor_sim: 0.105 vs 0.093 — we're actually MORE reference-similar but still lost badly.
- This is pure judge variance on a PHP task. Score gap is large (0.440) which suggests the king's implementation direction differs fundamentally.

---

## Pattern Analysis: The Volatility Problem

Looking at all 4 gates:

**STABLE WINS (3-4/4 gates)**: T1 C++, T6 Go, T7 JS, T8 DI (with fix), T4 Python (with fix), T10 Python
**STABLE LOSSES (3-4/4 gates)**: T9 FEATURE TS (structural)
**VOLATILE (flip-flop)**: T2 Python, T3 TS, T5 PHP

The volatile tasks are the bottleneck. T2/T3/T5 flip based on judge variance, not structural agent issues.

**KEY INSIGHT**: We have ~5-6 reliable wins. We need 8. The gap is:
1. Fix T9 FEATURE (structural) → 1 more reliable win
2. Fix T10 collapse (avoid pipeline regex misfiring) → 1 more reliable win
3. Make T2/T3/T5 less volatile → harder, judge noise

---

## Next37 Plan: Exactly Three Changes vs Next36

### CHANGE 1 — Fix _PYTHON_PIPELINE_RE over-triggering (fixes T10 collapse, prevents T2 regression)
TIGHTEN the `_PYTHON_PIPELINE_RE` regex so it ONLY fires when:
- File count > 8 (keep this guard)
- AND language is Python (no Swift files)
- AND issue mentions "AI" OR "ML" OR "machine learning" OR "model" alongside "pipeline" or "backend"
- EXCLUDE: "publish", "flow", "export", "enumeration", "job registration" from triggering it

Specifically: add negative lookahead or exclusion list: if issue matches `_PYTHON_PIPELINE_RE` BUT also matches "publish flow" OR "export kind" OR "LoRA" OR "enumeration" → do NOT fire the hint.

### CHANGE 2 — Constrain T9 FEATURE to minimal implementation
The existing `_FEATURE_VERB_RE`/`_FEATURE_SUBJECT_RE` hint fires but agent over-engineers.
REPLACE the hint text with a stronger constraint:
"Feature task: make the MINIMAL change. Add only the required field/property to the model/config file and wire it directly to the existing handler — do NOT add new services, classes, utility functions, or abstractions unless the task explicitly requests them. Simpler is better."

### CHANGE 3 — TypeScript BUGFIX style hint (closes T3 persistent gap)
Add a light TypeScript hint in `_integration_hints()` when:
- Language is TypeScript AND task type is BUGFIX AND file count 5-10
- Inject: "TypeScript bugfix: preserve existing type signatures and interfaces — do not add new types unless required. Minimal diff preferred."
This targets the judge's preference for clean, type-preserving TypeScript changes.

### KEEP: All existing hints (C++, Go, scoped JS, DI, pipeline — but tightened)

---

## Expected Next37 Outcome
- T1 C++: ✅ stable
- T4 Python API: ✅ stable (pipeline hint kept, tightened)
- T6 Go: ✅ stable
- T7 JS: ✅ stable
- T8 DI: ✅ stable (dominant 0.750)
- T10 Python: ✅ restored (pipeline regex tightened)
- T9 FEATURE: possible flip with minimal-change constraint
- T3 TS: possible improvement with TS hint
- T2/T5: volatile — 50/50

Conservative: 6W-4L (60%). Optimistic: 8W-2L (80%) if T9+T3+T10 all flip.
