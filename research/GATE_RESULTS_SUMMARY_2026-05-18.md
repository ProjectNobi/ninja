# SN66 Gate Test Results — Consolidated Summary
**Generated:** 2026-05-18  
**⚠️ IMPORTANT:** All results below were measured against OLD king (commit 54342f42, 4082L).  
Real king as of 2026-05-18: **fd2af7a6050e (4408L, tao-hunter/viper-agent)**  
Results are still valuable as relative agent progression data, but WR% cannot be compared to live validator.

---

## Win Rate Progression (vs old king)

| Version | Tasks | WR% | BUGFIX | API/ROUTE | FEATURE | REFACTOR | UPDATE | Verdict |
|---------|-------|-----|--------|-----------|---------|----------|--------|---------|
| v47 | 25 | ~33% | — | — | — | — | — | NOT COMPETITIVE |
| v48 | 25 | ~36% | — | — | — | — | — | NOT COMPETITIVE |
| v50 | 25 | ~40% | — | — | — | — | — | NOT COMPETITIVE |
| v51 | 25 | ~40% | — | — | — | — | — | NOT COMPETITIVE |
| v52 | 25 | ~48% | — | — | — | — | — | NOT COMPETITIVE |
| v53 | 25 | ~52% | — | — | — | — | — | NOT COMPETITIVE |
| v53 | 100 | ~50% | — | — | — | — | — | NOT COMPETITIVE |
| **v54** | **100** | **52.1%** | 46.9% | **70%** ✅ | 55.6% | **60%** ✅ | 50% | NOT COMPETITIVE |
| v54 | 25 | 40.0% | 50% | 50% | 50% | — | 0% | NOT COMPETITIVE |
| v55 | 100 | incomplete | — | — | — | — | — | incomplete |
| v56 | 100 | incomplete | — | — | — | — | — | incomplete |
| v57 | 100 | incomplete | — | — | — | — | — | incomplete |
| v58 | 100 | incomplete | — | — | — | — | — | incomplete |
| **v59** | **100** | **35.4%** | — | — | — | — | — | NOT COMPETITIVE (regression) |
| v60 | 100 | incomplete | — | — | — | — | — | incomplete |
| **v61** | **100** | **39.4%** | 40% | 60% ✅ | 47.1% | **0%** ❌ | 27.3% ❌ | NOT COMPETITIVE |

---

## Key Observations

### v54 = Best Performer (52.1%)
- Strong REFACTOR (60%) and API/ROUTE (70%) — completeness-first philosophy working
- UPDATE (50%) solid — no "never delete" rule contamination
- Root cause of being best: explicit "COMPLETENESS BEATS MINIMALISM" statement

### v59 Regression (35.4% — sharp drop from 52.1%)
- Root cause: added "Never delete or remove existing functions/components unless the task explicitly requests it" (v59:3096)
- This single rule destroyed REFACTOR and UPDATE capabilities
- **Lesson: L-SN66-NEVER-DELETE-RULE-1**

### v61 Partial Recovery (39.4%) but REFACTOR stays at 0%
- Removed the "never delete" rule
- But replaced "COMPLETENESS BEATS MINIMALISM" with minimalism-first framing
- REFACTOR stayed at 0% — asymmetry statement is required explicitly
- **Lesson: L-SN66-MINIMALISM-FRAMING-1**

---

## Target Gap Analysis

- **Threshold for submission approval:** ≥70% WR (100-task, win_margin=3)
- **Best achieved:** 52.1% (v54, vs old king)
- **Gap to close:** ~18 percentage points
- **Path:** Prompt-only ceiling ~52%. Dedicated fine-tuned LLM required to reach 70%+.
- **King execution budget:** 50 steps, 25 commands/turn (vs our 30/15 = 67% gap)

---

## What's Next

1. **Wait for dedicated SN66 LLM** (this week) — fine-tuned on 215K gold + 85K SFT + 32K DPO
2. **Re-gate all versions against new king** (fd2af7a6050e, 4408L)
3. **v62 build** = v54 base + king execution budget (50 steps, 25 cmd/turn) + forbidden rules removed
4. Raw logs archived: `/root/sn66-ninja/research/gate_logs/`
