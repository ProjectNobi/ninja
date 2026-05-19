# DPO + M2.7 Intelligence — SN66 v68
**Date:** 2026-05-19  
**Context:** v67ci at 59.0% WR (41/50), 1 win from 60% threshold. Judge: claude-sonnet-4.6 (LLM-only).

---

## STEP 2a — DPO Analysis (Sonnet 4.6 ground truth)

### Today's Live Duels (772 total rounds, 2026-05-19.jsonl)

| Task Type | Total | King Wins | Challenger Wins | Challenger WR |
|-----------|-------|-----------|-----------------|---------------|
| BUGFIX    | 564   | 265       | 299             | **53%** ✅    |
| FEATURE   | 92    | 79        | 13              | **14%** 🔴    |
| UPDATE    | 59    | 45        | 14              | **24%** 🔴    |
| API       | 57    | 32        | 25              | **44%** ⚠️   |
| **TOTAL** | 772   | 421 (54.5%) | 351 (45.5%) | 45.5%         |

**Current king SHA:** d24c9d30fa919115 (vs all challengers today)

**Key revelation:** Challengers are WINNING BUGFIX (53%) — the problem is FEATURE (14%) and UPDATE (24%) are catastrophically dragging the overall WR to 45.5%.

### Win Margins
- King wins: avg 0.310, median 0.270
- Challenger wins: avg 0.290, median 0.270
- Wins are decisive (not narrow) — **no "almost won" pattern**. Fix = get more correct, not be slightly better.

### Consensus Rate (full_matrix_dpo_pairs.jsonl): 79% (790/1000 sampled)

---

## Top 3 Sonnet 4.6 Signals — What Makes King Win

### Signal 1: FEATURE — "Missing all required components" (58.1% of FEATURE+UPDATE king wins)
Sonnet checks the full spec against what was delivered. King wins when it implements all N required files/components. Challenger loses when it implements N-1 or N-2 items, even if those items are better quality.

**Pattern:** "King correctly implements all four required files... Challenger omits X, Y, and Z"  
**v68 rule:** For FEATURE tasks, enumerate every deliverable upfront and verify completeness before finalizing.

### Signal 2: FEATURE/UPDATE — "Critical issues" (49.2%) + "Compile errors" (23.4%)
Sonnet immediately penalizes:
- Import of non-existent modules
- Undefined references, broken function signatures  
- Syntax errors (missing commas in object literals, unclosed blocks)
- Using wrong decorator/pattern that would fail at runtime

**Pattern:** "King has critical omissions: missing lib.rs registration, missing Python package exports... compilation errors"  
**v68 rule:** Do not add any code that references an undefined symbol. Verify all imports exist before including them.

### Signal 3: BUGFIX — "Logic bugs / regressions" (39.6%) + "Missing something" (34%)
When king wins on BUGFIX, it's overwhelmingly because challenger:
1. Introduced a duplicate/regression while fixing (22.6% of king BUGFIX wins)
2. Fixed wrong/incomplete file set (missing cascade)
3. Introduced syntax errors in the process of fixing

**Pattern:** "Challenger has critical structural bug: renders header AND then separate PageHeader, producing duplicate back navigation"  
**v68 rule:** For BUGFIX, verify the fix doesn't introduce visible regressions. Check that existing tests/patterns aren't broken.

---

## STEP 2b — M2.7 BUGFIX Blind Spots

### Size Analysis vs Sonnet 4.6

| Metric | M2.7 | Sonnet 4.6 |
|--------|------|-----------|
| Avg patch size | 271 lines | 261 lines |
| Median patch size | 276 lines | 302 lines |
| Over-edit (>1.5x ref) | **50.5%** | 51.8% |
| Under-edit (<0.5x ref) | **15.5%** | 20.1% |
| Multi-file tasks | 84.3% | 84.4% |
| LLM edits multi-file | **76.4%** | 73.3% |

**Finding:** M2.7 and Sonnet 4.6 are remarkably similar in BUGFIX patching behavior. M2.7 over-edits slightly less than Sonnet and under-edits less too. The size profiles are nearly identical.

### M2.7 BUGFIX Blind Spot: WRONG FILE SELECTION on Over-Edits

The 50.5% over-edit rate hides the real problem: M2.7 often edits **the wrong files** at the wrong entry point.

**Evidence from over-edit cases:**
- M2.7 edits `app.py` (entry point) when reference edits `main_window.py` (correct location)  
- M2.7 edits `Terminal.Gui/Views/MessageBox.cs` when reference edits `ChineseUI.cs` (completely different file)
- M2.7 edits `DealCard.tsx` (3.6x size) when reference edits `deal-value-display.helpers.ts` (different component)

**Pattern:** M2.7 identifies the symptom-level file (what displays the bug) instead of the source-level file (where the bug lives). It then over-edits that wrong file.

### M2.7 Missing Cascade Files (Under-edits)
- 68/440 BUGFIX patches under-edit severely
- Worst case: 1 file edited vs 4 required (missed test files, C source files)
- Multi-monorepo tasks: 12 files edited vs 62 required (missed 50 cascade files)
- M2.7 doesn't trace import trees to find all call sites

---

## v68 Must-Fix

### Priority 1 (CRITICAL): FEATURE task completeness
- Enumerate all N required deliverables at task start  
- Track completion against that list before finalizing
- FEATURE tasks average 79/92 king wins = 86% king WR — single biggest loss bucket

### Priority 2 (HIGH): UPDATE task full-scope wiring
- UPDATE tasks lose 76% of the time because challenger misses 1-2 required files in the chain  
- King wins by covering all four files in UPDATE tasks, not just the main one

### Priority 3 (MEDIUM): BUGFIX wrong-file selection
- M2.7 diagnoses bug at wrong layer (symptom vs source)
- Add explicit instruction: "Identify the ROOT CAUSE file, not the display/symptom file. Trace backwards from the symptom to find where the bug originates."

### What NOT to change on BUGFIX
- BUGFIX already wins 53% in live duels — do not add restrictive rules that break this
- Over-edit rate is fine (same as Sonnet 4.6 = validator-acceptable)
- The BUGFIX loss patterns (logic bugs, regressions) are random quality issues, not systematic

---

## Summary (under 150 words)

**Top 3 Sonnet 4.6 signals from today's live duels:**
1. **Completeness check** (58%): Missing any required file/component = immediate loss on FEATURE/UPDATE
2. **Compile/runtime errors** (49%): Any broken import, undefined reference, or syntax error = king wins
3. **Regression detection** (39% BUGFIX): Challenger introduces duplicate rendering or breaks existing behavior while fixing

**M2.7 BUGFIX blind spot v68 must address:**
M2.7 edits at the **symptom layer** instead of the **source layer** — it fixes `MessageBox.cs` when the bug is in `ChineseUI.cs`. This wrong-file selection (50.5% over-edit rate, often wrong files) costs us on precision. The fix: explicit root-cause tracing instruction ("trace backwards from symptom to source file before editing").

**The real v68 priority is FEATURE/UPDATE completeness (14%/24% WR), not BUGFIX.**
