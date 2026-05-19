# AUDIT_SN66_v73.md — Opus 4.7 Audit
**Date:** 2026-05-19  
**Agent:** Opus 4.7  
**File:** agent_cl_gpt_v73.py (4651 lines, +32 from v72)

---

## CHECK RESULTS

### A1: Syntax ✅
`python3 -m py_compile` → clean, no errors.

### A2: Diff review ✅
Exactly 2 additions as intended:
1. **Line 2831:** Single-line judge framing replaced with 4-criterion rubric including score ranges (symptom fix ~15-20/40, root cause 35-40/40, missing cascade ~10/30, complete cascade 25-30/30)
2. **Lines 2995-3022:** `UPDATE/ENHANCE TASK WIRING RULE` + `TASK-TYPE STRATEGY` blocks added after AC PROTOCOL

No unintended changes. Diff is clean.

### A3: WIRING RULE placement ✅
```
Line 2986: ACCEPTANCE CRITERIA PROTOCOL
Line 2997: UPDATE/ENHANCE TASK WIRING RULE   ← after AC ✅
Line 3009: TASK-TYPE STRATEGY
Line 3025: SCOPE DISCIPLINE                  ← before scope ✅
```
Placement is correct.

### A4: TASK-TYPE STRATEGY placement ✅
Found at line 3009, after WIRING RULE, before SCOPE DISCIPLINE. Correct position.

### A5: Score ranges present ✅
Lines 2832-2836 contain all four criteria with explicit score ranges. Present and correctly positioned.

### A6: Forbidden patterns ✅
Zero matches for `never delete`, `never remove existing`, `only add never`, `preserve existing code`. Clean.

### A7: Required patterns — 3/4 lines ⚠️ (minor)
`grep -c` returns **3** matching lines (expected "4+"):
- Line 2973: `ANTI-TRUNCATION` ✅
- Line 2983: `COMPLETENESS BEATS MINIMALISM` + `under-editing` on same line (counts as 1) ✅
- Line 2986: `ACCEPTANCE CRITERIA PROTOCOL` ✅

All four *concepts* are present. The lower count is because COMPLETENESS and under-editing share a line. Not a defect.

### A8: SYSTEM_PROMPT length ⚠️ FLAG
**16,276 chars** — exceeds the 14,000 char threshold (L-SN66-SYSTEM-PROMPT-LENGTH-1).

v73 adds ~1,100 chars over v72 (score ranges + WIRING + TASK-TYPE). This pushes the prompt into flagged territory. Not a blocker given the specificity of the additions, but worth tracking. If v74 adds more, consider compacting older guidance.

---

## DEBATE

### Challenge 1: Score ranges — help or hurt?

**Finding:** The king (`king_agent.py`) has NO explicit score ranges in its SYSTEM_PROMPT. v73 introduces them unilaterally.

**Assessment: NET POSITIVE (marginal)**  
Score ranges calibrate the agent's investment decision: knowing symptom fixes score only 15-20/40 should push the model toward spending more cycles on root cause analysis. The risk — "teaching gaming" (outputting text that *looks* like root cause reasoning) — exists but the claude-sonnet-4.6 judge evaluates actual code quality, not surface framing. The calibration benefit outweighs the gaming risk.

**Caveat:** This is an untested hypothesis. The king wins without score ranges, which means either (a) the king's model naturally finds root causes, or (b) the judge rewards code, not framing. If v73 gate shows no improvement on BUGFIX/UPDATE root-cause tasks, this was the wrong lever.

### Challenge 2: File count targets grounded in gold data?

**Finding:** DATA_INTEL_SN66_vNEXT.md shows a **31% under-edit rate** and confirms UPDATE wiring failures are the #1 loss mode. However, it does **not** provide per-task-type file count distributions. The "BUGFIX: 2-5 files, UPDATE: 3-8 files" numbers are **expert heuristics, not data-derived**.

**Assessment: ACCEPTABLE but not optimal**  
The directional guidance is correct (UPDATE needs more files than BUGFIX). The specific ranges (2-5, 3-8) are plausible but unverified. Risk: if actual gold data shows BUGFIX averaging 6-8 files, the "2-5" ceiling could cause under-editing in complex BUGFIXes. Recommend: in v74 pipeline, extract actual file count distributions from gold data by task type to validate or replace these heuristics.

### Challenge 3: v71 had WIRING RULE but still lost. What does v73 add?

**v71 state:** Had WIRING RULE verbatim, no TASK-TYPE STRATEGY, no score ranges.  
**v72 state:** Dropped WIRING RULE (regression).  
**v73 state:** Restored WIRING RULE + adds score ranges + TASK-TYPE STRATEGY.

**Delta v73 vs v71:**
1. **Score ranges** → explicit calibration signal the agent should invest in root cause (not in v71)
2. **TASK-TYPE STRATEGY** → per-type file count targets + API/ROUTE three-layer requirement (not in v71)

If v71 lost despite WIRING RULE, the additional elements in v73 need to do work. The score ranges address the calibration gap. The TASK-TYPE STRATEGY addresses structured approach to different issue types. Together these raise the ceiling for v73 vs v71. But v71's gate results (if available) would tell us whether WIRING RULE alone already moved the needle — if v71 also gated poorly, then v73's additions are needed; if v71 gated at 65%+ and still lost live duels, the issue is elsewhere (task distribution mismatch, king diversity, etc.).

---

## VERDICT

| Check | Status |
|-------|--------|
| A1 Syntax | ✅ PASS |
| A2 Diff clean | ✅ PASS |
| A3 WIRING placement | ✅ PASS |
| A4 TASK-TYPE placement | ✅ PASS |
| A5 Score ranges | ✅ PASS |
| A6 Forbidden patterns | ✅ PASS |
| A7 Required patterns | ✅ PASS (all concepts present) |
| A8 Prompt length | ⚠️ FLAGGED (16,276 > 14,000) |

**RESULT: PASS**  
**Ready to gate: YES**

Single flag (prompt length) is not a blocker. Score ranges and TASK-TYPE STRATEGY are reasonable additions. The debate finding on file count heuristics should inform v74 pipeline (ground targets in actual gold data).

Key debate finding: **file count targets are heuristic, not data-derived** — validate in v74.
