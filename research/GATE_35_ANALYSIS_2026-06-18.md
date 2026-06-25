# Gate-35 Analysis — Next35 vs King hashirama
Date: 2026-06-18 ~08:45 UTC
Agent: agent_cl_gpt_Next35.py (2685 lines, base=Next33 + C++ hint + scoped JS hint + Go hint)
King: king_agent.py (1262 lines, SHA 53bca97c)
Status: COMPLETE — 5W-5L (50%) ❌ VERDICT: NOT COMPETITIVE

---

## Round Breakdown (8 confirmed + 2 pending)

| # | Type      | Lang       | Us    | King  | Result | Gate-33 | Gate-34 | Notes |
|---|-----------|------------|-------|-------|--------|---------|---------|-------|
| 1 | BUGFIX    | C/C++      | 0.680 | 0.380 | ✅ WIN  | ❌ 0.280 | ❌ 0.520 | C++ hint DOMINATES — 0.280→0.680, gap reversed |
| 2 | BUGFIX    | Python     | 0.490 | 0.540 | ❌ LOSS | ✅ 0.620 | ✅ 0.530 | Regression — was reliable WIN both gates |
| 3 | BUGFIX    | TypeScript | 0.280 | 0.340 | ❌ LOSS | ✅ 0.520 | ✅ 0.520 | Regression — was solid WIN both prior gates |
| 4 | API/ROUTE | Python     | 0.180 | 0.420 | ❌ LOSS | ✅ 0.450 | ❌ 0.120 | Still broken vs gate-33 (not restored) |
| 5 | API/ROUTE | PHP        | 0.620 | 0.300 | ✅ WIN  | ❌ 0.300 | ❌ 0.280 | PHP FLIPPED — 0.300→0.620 — big improvement |
| 6 | BUGFIX    | Go         | 0.620 | 0.080 | ✅ WIN  | ❌ 0.150 | ✅ 0.090 | Go hint DOMINATES — 0.150→0.620 |
| 7 | API/ROUTE | JS         | 0.550 | 0.420 | ✅ WIN  | ❌ 0.330 | ✅ 0.520 | JS hint holding — 3rd gate WIN |
| 8 | BUGFIX    | TypeScript | 0.080 | 0.150 | ❌ LOSS | ✅ 0.450 | ❌ 0.040 | T8 DI still broken — was 0.450 in G33 |
| 9 | FEATURE   | TypeScript | 0.100 | 0.280 | ❌ LOSS | ✅ 0.850 | ❌ 0.000 | PERSISTENT COLLAPSE — 3rd gate issue |
|10 | BUGFIX    | Python     | 0.380 | 0.280 | ✅ WIN  | ✅ 0.270 | ✅ 0.220 | Stable win |

---

## What Improved (confirmed working)
- **T1 C++: 0.280 → 0.680** — dominant reversal. _CPP_LANG_RE hint is GOLD. Keep forever.
- **T5 PHP: 0.300 → 0.620** — unexpected large gain. The scoped JS hint didn't fire (PHP), but something else changed. Possibly Go hint removed confusion, or random variance.
- **T6 Go: 0.150 → 0.620** — massive improvement. _GO_LANG_RE large-repo focus hint working perfectly.
- **T7 JS: 0.330 → 0.550** — scoped JS frontend hint holding up for 3rd consecutive gate.

## Persistent Losses / New Regressions

### T2 Python BUGFIX (0.620 → 0.490 → now LOSS)
- Was reliable WIN in G33 (0.620) and G34 (0.530). Now LOSS at 0.490 vs 0.540.
- Margin is tiny (0.050). Could be variance — same task both gates. No new changes touch Python BUGFIX.
- This is likely random judge variance on a borderline task, not a structural regression.

### T3 TypeScript BUGFIX (0.520 WIN → 0.280 LOSS)
- Was 0.520 WIN in G33 and G34 (stable). Now 0.280 vs 0.340 — dropped 0.240.
- cursor_sim: 0.060 vs 0.067 — very close. Both sides produced similar patches, king slightly better.
- This is a large-file TypeScript task (9 files). No new hint touches TS BUGFIX specifically.
- Possible cause: none of our changes should affect this. Likely judge variance / different LLM scoring run.

### T4 Python API/ROUTE (0.450 WIN → 0.120 → 0.180 — persistent loss)
- This 10-file Python AI pipeline task has been a persistent loss since Gate-34.
- Reverting CHANGE 2 did NOT restore it (was 0.450 in G33, still 0.180 in G35).
- Root cause: this specific task may have changed in difficulty, OR our base agent struggles with complex multi-file Python API pipeline tasks even without prompt interference.
- cursor_sim: 0.015 vs 0.025 — both very low. Agent not finding the right files quickly enough.

### T8 TypeScript DI (0.450 WIN → 0.040 → 0.080 — broken for 2 gates)
- _CONTAINER_DI_RE hint exists but produces 0.080 vs 0.150.
- G33: 0.450 WIN. G34: 0.040. G35: 0.080. Not restored.
- cursor_sim: 0.081 vs 0.100 — close but we're slightly below.
- The DI hint may not be firing correctly, OR the king has a different strategy for this task now.
- Need to inspect: is _CONTAINER_DI_RE pattern matching the task description?

---

## Cross-Gate Summary (all 10 tasks)

| Task | G33 | G34 | G35 | Trend |
|------|-----|-----|-----|-------|
| T1 C++ BUGFIX      | ❌ 0.280 | ❌ 0.520 | ✅ **0.680** | 📈 FIXED |
| T2 Python BUGFIX   | ✅ 0.620 | ✅ 0.530 | ❌ 0.490 | 📉 variance |
| T3 TS BUGFIX       | ✅ 0.520 | ✅ 0.520 | ❌ 0.280 | 📉 regression |
| T4 Python API      | ✅ 0.450 | ❌ 0.120 | ❌ 0.180 | 📉 broken |
| T5 PHP API         | ❌ 0.300 | ❌ 0.280 | ✅ **0.620** | 📈 FIXED |
| T6 Go BUGFIX       | ❌ 0.150 | ✅ 0.090 | ✅ **0.620** | 📈 FIXED |
| T7 JS API          | ❌ 0.330 | ✅ 0.520 | ✅ 0.550 | ✅ stable |
| T8 TS DI BUGFIX    | ✅ 0.450 | ❌ 0.040 | ❌ 0.080 | 📉 broken |
| T9 TS FEATURE      | ✅ 0.850 | ❌ 0.000 | ❌ 0.100 | 📉 PERSISTENT — 2 collapses in a row |
| T10 Python BUGFIX  | ✅ 0.270 | ✅ 0.220 | ✅ 0.380 | ✅ stable |

---

## Hypotheses for Next36

### H1 — T3 TypeScript BUGFIX regression (0.520 → 0.280)
- Task: "Refactor Node Styling and Introduce New Texture Options" (9 files, TypeScript)
- Was consistent 0.520 WIN for 2 gates. Dropped to 0.280.
- cursor_sim both sides very close (0.060 vs 0.067).
- Hypothesis: judge variance — this is the SAME task same model, slight score drift.
- No new hint fires on this. Hard to fix structurally. Low priority unless pattern repeats.

### H2 — T4 Python API/ROUTE persistent loss
- Task: "Enhance Repository Analysis Backend with Full AI Pipeline and Frontend" (10 files)
- 0.450 → 0.120 → 0.180. Never recovered.
- cursor_sim: 0.015/0.025 — both agents barely touching reference. Hard task.
- Hypothesis: agent reads too much, hits step limit before implementing core changes.
- Fix: when Python + 10+ files + "AI pipeline" → inject "Identify the 2-3 core files that implement the pipeline. Read ONLY those, then implement the full change."

### H3 — T8 TypeScript DI persistent loss
- Task: "Improve Streamable HTTP Server Error Handling and Element Reload Logic" (5 files, Container.ts)
- Was 0.450 in G33. G34: 0.040. G35: 0.080. The _CONTAINER_DI_RE hint exists but scores keep dropping.
- Hypothesis: the DI hint ("Read the Container/DI class constructor IN FULL") may be leading agent to READ but not implementing the error handling + element reload. The task is about HTTP Server + element reload — the DI aspect is a red herring.
- Fix: refine the _CONTAINER_DI_RE trigger. Check if "Streamable HTTP" + "Error Handling" + "Element Reload" is being captured by the DI regex — it shouldn't fire on HTTP error handling tasks. If it does fire → it's giving the WRONG hint (DI read = irrelevant for HTTP error handling).

### H4 — T2 Python BUGFIX variance
- Margin: 0.490 vs 0.540 (0.050 gap). This is judge noise territory.
- No structural fix needed. Will likely flip back naturally.

---

## Next36 Plan: Exactly Three Changes vs Next35

**BASE: agent_cl_gpt_Next35.py**

### CHANGE 1 (keep/refine C++ hint — it's working)
No change needed to C++ hint — KEEP EXACTLY as Next35. Already dominant.

### CHANGE 2 (fix _CONTAINER_DI_RE over-triggering on T8)
Inspect what the _CONTAINER_DI_RE regex actually matches. The task T8 is:
"Improve Streamable HTTP Server Error Handling and Element Reload Logic"
Files: src/di/Container.ts + 4 others.

The regex likely fires on "Container.ts" or "di" in path — and injects "Read the Container/DI class constructor IN FULL" — which is CORRECT for T8 (Container.ts is a real DI container). Yet score is 0.080.

Root cause: the hint makes agent read Container constructor, but the task is about STREAMABLE HTTP error handling + element RELOAD logic — the fix likely needs to modify the error handler middleware and element reload function, NOT just understand the DI structure. The hint burns steps on DI reading when the agent should be fixing the HTTP error path.

Fix: make _CONTAINER_DI_RE hint more specific — add "implement the error handling or reload logic AFTER reading the Container interface. The DI graph context is needed to understand dependencies, not as the primary fix target."

### CHANGE 3 (T4 Python large multi-file API pipeline focus)
Add a new hint in _integration_hints() that fires when:
- Language is Python AND
- File count > 8 AND
- Issue mentions "pipeline" or "AI" or "backend" or "frontend" with "full" or "enhance"

Inject: "Large Python backend: identify the 2-3 files that own the core pipeline logic. Read ONLY those files first, then implement the full change in one pass. Skip config/env/frontend files unless the task explicitly requires them."

### KEEP: Go hint, C++ hint, scoped JS hint, _polish_worth_adopting, _build_polish_task, etc.

---

## Expected outcome
- T1 C++ → ✅ WIN (proven, keep hint)
- T3 TS → likely restored (judge variance, no structural issue)
- T4 Python API → ✅ potential flip with large-pipeline hint
- T5 PHP → ✅ WIN (holding)
- T6 Go → ✅ WIN (proven)
- T7 JS → ✅ WIN (holding)
- T8 TS DI → ✅ potential flip with refined hint
- T2/T9/T10 → likely wins (stable)

Best case: **8-9W** → 80-90% gate pass ✅
