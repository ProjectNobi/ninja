# M2.7 BUGFIX Patterns — SN66 v67 Intelligence
*Generated: 2026-05-19 | Analyst: T68Bot subagent*

---

## Part A — M2.7 BUGFIX-Specific Analysis

### Patch Size vs Reference
| Metric | M2.7 (LLM) | Reference | Sonnet 4.6 |
|--------|-----------|-----------|------------|
| Avg lines added | 262.8 | 490.0 | 237.2 |
| Median lines added | 271.5 | 136.5 | 278.5 |
| Under-edit rate (<50% of ref) | **17.0%** (34/200) | — | **30.0%** (30/100) |

**Key interpretation:**
- M2.7 median (271.5) >> reference median (136.5) → **M2.7 chronically over-edits typical BUGFIX tasks**
- Reference mean (490.0) >> M2.7 mean (262.8) → on large BUGFIX tasks, M2.7 under-edits
- **M2.7 under-edits LESS than Sonnet 4.6** (17% vs 30%) — size is NOT M2.7's core problem

### Blind Spots (from judge rationales on BUGFIX losses)
Analyzed 189/404 BUGFIX duels where challenger lost to king. Top failure patterns:

| Failure Pattern | Frequency | Rate |
|----------------|-----------|------|
| Critical errors | 87/189 | **46%** |
| Error/syntax/compilation | 84/189 | **44%** |
| Bug introduced | 74/189 | **39%** |
| Missing requirements | 75/189 | **39%** |
| Wrong logic/implementation | 51/189 | **26%** |
| Unrelated code added | 28/189 | **15%** |
| Duplicate elements | 29/189 | **15%** |
| Incomplete fix | 24/189 | **13%** |
| Regression introduced | 23/189 | **12%** |

### Root Causes of M2.7 BUGFIX Failures

**1. Correctness failures (top issue, 44-46%)**
M2.7 generates syntactically plausible patches that contain semantic bugs: wrong function signatures, incorrect variable names, corrupted syntax, invalid language constructs (e.g. `var*` in Zig). The LLM "looks like" it fixed the bug but the fix is broken.

**2. Cascading / missing fixes (39%)**
M2.7 addresses the primary bug but misses cascading requirements — doesn't update all affected files, leaves inconsistent state, or only fixes the symptom not the root cause.

**3. Scope creep causing regressions (15-26%)**
M2.7 adds extra, unrelated, or duplicate code while fixing. This introduces regressions (12%) and creates "dual rendering" or duplicate behavior bugs (15% duplicate rate). The model is trying to "be thorough" but overshoots.

**4. Wrong-file targeting (15%)**
M2.7 edits the wrong file or wrong function within a file. The judge explicitly calls out cases where "challenger incorrectly targets file X when fix belongs in file Y."

### Sample Failure Rationales

> "challenger has a critical structural bug: it renders the new premium header card AND then immediately renders a separate component, producing duplicate back navigation. This is a clear regression."

> "challenger patch contains a fatal Zig syntax error (`var*`) that prevents compilation, and also fails to implement the Mask.apply empty-input fix while adding tests that depend on it."

> "challenger incorrectly embeds callStormAPI inside client component (wrong architectural placement)."

---

## Part B — Sonnet 4.6 BUGFIX Approach (New Judge Model)

| Metric | Sonnet 4.6 |
|--------|-----------|
| Avg patch size | 237.2 lines |
| Median patch size | 278.5 lines |
| Under-edit rate | 30.0% |

**How Sonnet 4.6 differs from M2.7 on BUGFIX:**
1. **More conservative** — Sonnet generates smaller patches on average (237 vs 262)
2. **Under-edits more often** (30% vs 17%) — Sonnet takes a surgical approach; sometimes too surgical
3. **Pattern:** Sonnet tends to fix exactly what's asked, even if that means leaving related issues untouched. M2.7 tries to fix everything it sees, sometimes breaking things it shouldn't touch.

**Impact of Sonnet 4.6 as new judge (PR#1598, today):**
- LLM judge will penalize M2.7's "extra code" more harshly than old heuristic judge
- Sonnet 4.6 judge will recognize duplicate/regression patterns easily (same model family)
- M2.7's tendency to generate large patches with extra code = higher risk under Sonnet judge
- **Surgical correctness is now more valuable than coverage**

---

## Part C — Today's Live Duel Task Distribution

| Task Type | Count | % of Tasks | Challenger WR |
|-----------|-------|-----------|---------------|
| **BUGFIX** | 404 | **73.7%** | **53.2%** ✅ |
| FEATURE | 64 | 11.7% | 10.9% ❌ |
| API | 41 | 7.5% | 43.9% ⚠️ |
| UPDATE | 39 | 7.1% | 28.2% ❌ |
| **TOTAL** | **548** | 100% | **45.8%** ❌ |

**Total records today: 548 duels**

### Critical Insight: BUGFIX Is NOT the Main Problem
- Challenger wins BUGFIX at **53.2%** — actually above 50%
- The real drag: **FEATURE (10.9%)** and **UPDATE (28.2%)**
- Overall WR of 45.8% is being killed by non-BUGFIX tasks
- BUGFIX at 73.7% of duels × 53.2% WR = only contributes ~39 net wins
- FEATURE at 11.7% × 10.9% = near-zero, UPDATE at 7.1% × 28.2% = loss

### BUGFIX Score Differential
- avg `score_diff` (chosen-rejected) for BUGFIX: **0.297**
- Median: **0.260**
- These are decisive margins, not close fights — when challenger loses BUGFIX, it loses badly

---

## Key Questions Answered

**1. Does M2.7 under-edit BUGFIX patches vs reference?**
On typical (median) tasks: NO — M2.7 over-edits (271 vs 136 median). On large tasks: YES — M2.7 falls short of the 490-line average reference. The problem isn't size; it's correctness and scope.

**2. How many files does M2.7 touch for BUGFIX vs reference?**
File-count fields (`n_files_llm`, `n_files_ref`) are absent from gold_patches schema. Unable to compare directly.

**3. How does Sonnet 4.6's BUGFIX approach differ from M2.7?**
Sonnet is more surgical (smaller, more focused patches), under-edits more often (30% vs 17%), but avoids regressions and incorrect implementations. As the new judge, it will penalize M2.7's over-editing and correctness failures.

**4. What prompting changes would improve M2.7 BUGFIX?**
- **Add "verify your fix compiles/runs" instruction** — targets 44% syntax/compilation failure rate
- **Explicit "do not add code unrelated to the bug" rule** — targets 15% unrelated/duplicate issues
- **"Fix the root cause, not symptoms; update all affected files" rule** — targets 39% missing rate
- **Surgical edit instructions** — "prefer fewer correct changes over many speculative changes"
- Consider: the current SYSTEM_PROMPT lacks compilation verification guidance

---

## Summary for v67

**M2.7 BUGFIX blind spots:**
1. **Correctness failures dominate** (44-46%): M2.7 introduces new bugs, syntax errors, or wrong implementations while fixing the original issue
2. **Scope creep causes regressions** (15-26%): over-editing adds unrelated/duplicate code
3. **Cascading miss** (39%): fixes primary bug but misses cascading file updates

**Sonnet 4.6 judge impact:**
Sonnet 4.6 is surgical, penalizes extra/wrong code harshly. M2.7's over-editing style is misaligned with what the new judge rewards. Correctness >> coverage under Sonnet.

**CRITICAL: BUGFIX is performing OK (53.2%). The v66 50% gate failure is driven by FEATURE (10.9%) and UPDATE (28.2%).** v67 should prioritize improving FEATURE and UPDATE task handling, not BUGFIX.

---

*Data sources: gold_patches_minimax_minimax-m2_7.jsonl (9,037 records, 200 BUGFIX sampled) | gold_patches_anthropic_claude-sonnet-4_6.jsonl (9,122 records, 100 BUGFIX sampled) | dpo/2026-05-19.jsonl (548 live duels)*
