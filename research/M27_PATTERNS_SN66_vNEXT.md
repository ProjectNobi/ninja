# M2.7 Gold Patch Analysis & Live Duel Intelligence — SN66 vNEXT
**Generated:** 2026-05-19 UTC  
**Data sources:** 9,037 M2.7 gold patches + 385 live DPO (today) + 1,040 live DPO (yesterday)

---

## Part A — M2.7 Gold Patch Analysis

### 1. Dataset Overview
- **Total gold patches:** 9,037 (all from R2 dataset)
- **Archetype distribution:**
  | Archetype | Count | % |
  |-----------|-------|---|
  | FEATURE_BUILD | 6,744 | 74.6% |
  | REFACTOR | 1,228 | 13.6% |
  | MIGRATION | 625 | 6.9% |
  | BUG_FIX | 440 | 4.9% |

### 2. Patch Size: M2.7 vs Reference
- **M2.7 avg lines added:** 334.8 | **median:** 368.0
- **Reference avg lines added:** 724.2 | **median:** 256.0
- **Critical insight:** Mean reference is 2.16x larger than M2.7's output, BUT the median reference (256) is actually SMALLER than M2.7's median (368). This is due to a **fat tail** in reference patches (some tasks have very large references e.g. 19,778 lines) pulling the mean up.

**LLM/Ref ratio distribution (sample n=500):**
| Ratio band | Count | % |
|------------|-------|---|
| < 0.25 (severe under-edit) | 61 | 12.2% |
| 0.25–0.50 (major under-edit) | 46 | 9.2% |
| 0.50–0.75 (moderate under-edit) | 44 | 8.8% |
| 0.75–1.00 (slight under-edit) | 61 | 12.2% |
| 1.00–1.50 (slight over-edit) | 97 | 19.4% |
| > 1.50 (significant over-edit) | 191 | 38.2% |

**Key finding:** M2.7 is actually a **heavy over-editor** in most cases (57.6% over-edit). Only 21.4% severely under-edit. The "avg ratio" numbers above mislead because MIGRATION archetype skews reference sizes massively (avg ratio 4.92x = M2.7 produces 4.9x more than reference on MIGRATION tasks).

### 3. Files Changed Per Patch
- **Average files per patch:** 4.5
- **Median files per patch:** 4.0
- **Max observed:** 39 files in one patch

### 4. By Archetype: M2.7 Editing Behaviour
| Archetype | M2.7 avg lines | Ref avg lines | Ratio | Severe under (< 50%) |
|-----------|---------------|---------------|-------|----------------------|
| BUG_FIX | 239.6 | 480.8 | 0.50x | 18% |
| FEATURE_BUILD | 349.2 | 722.7 | 0.48x | 24% |
| MIGRATION | 310.4 | 677.4 | 0.46x | 23% |
| REFACTOR | 296.1 | 479.0 | 0.62x | 17% |

**REFACTOR is M2.7's best archetype** — highest ratio (0.62x), lowest severe under-edit (17%).

### 5. M2.7 Consistent Patterns (Top 5)
1. **Multi-file cascade coverage:** avg 4.5 files per patch — M2.7 proactively touches related files, not just the primary file.
2. **Over-editing bias:** 57.6% of patches exceed reference size. M2.7 tends to add MORE than required — which aligns well with the completeness asymmetry rule.
3. **REFACTOR strength:** M2.7 handles refactors best (62% ratio vs ref) — good at structural reorganisation.
4. **Moderate time budget:** avg 75.7s, median 61.8s — M2.7 takes time to think (not just speed-running).
5. **Consistent patch format:** Clean unified diff format, proper context lines, handles imports consistently.

### 6. M2.7 Consistent Weaknesses
1. **FEATURE_BUILD under-editing (24% severe):** Large feature implementations sometimes get truncated — complex new file creation gets cut short.
2. **MIGRATION tasks:** While ratio looks good (4.92x), the large reference sizes mean migrations often require massive file rewrites that M2.7 produces at 46% completion.
3. **Fat-tail reference tasks:** When references are >1000 lines, M2.7 reliably under-edits. The model appears to have a natural output ceiling around 400–500 lines.
4. **Missing cascade files:** In cases where severity is high (< 0.25 ratio), the likely cause is entire files being skipped rather than individual lines — M2.7 picks the wrong files to edit.

---

## Part B — Live Duel Data (2026-05-19)

### 1. Task Type Distribution in Recent Duels
**Today (385 records, 18 duels):**
| Task Type | Count | % |
|-----------|-------|---|
| BUGFIX | 281 | 73% |
| FEATURE | 47 | 12% |
| API | 33 | 9% |
| UPDATE | 24 | 6% |

**Yesterday (1,040 records, ~40 duels):**
| Task Type | Count | % |
|-----------|-------|---|
| BUGFIX | 500 | 48% |
| FEATURE | 367 | 35% |
| UPDATE | 103 | 10% |
| API | 70 | 7% |

**Trend:** BUGFIX is dominating today's task distribution (73% vs 48% yesterday). FEATURE dropped significantly. This is live task sampling — task distribution can vary substantially day to day.

### 2. Win/Loss Patterns (Today's Challenger SHAs)
Overall today: King wins **201/385 (52.2%)**, Challenger wins **184/385 (47.8%)** — very competitive split.

Scores from today's duels:
| Task Type | Challenger win rate | Avg chosen score | Avg rejected score |
|-----------|--------------------|-----------------|--------------------|
| BUGFIX | ~50% (est) | 0.596 | 0.305 |
| FEATURE | ~50% (est) | 0.604 | 0.314 |
| API | ~50% (est) | 0.613 | 0.329 |
| UPDATE | ~50% (est) | 0.623 | 0.338 |

**Note:** The `is_winner` field is always True in DPO records — it marks whether that record is the "chosen" (winning) side, not whether our agent won. True duel win rate requires duel-level aggregation.

**Overall 2-day win rate:**
- Total across both days: King 784 round-wins (55.0%), Challenger 641 (45.0%)
- Avg rounds per duel: 24.6 (most go full distance)
- Score gap is large: avg 0.305 point gap — very few close battles

### 3. Judge Rationale Patterns (What Claude Sonnet 4.6 Rewards/Penalises)

**When KING wins — challenger failure modes:**
| Failure | Count (sample 100) |
|---------|-------------------|
| Breaking change / error / TypeScript bug | 68 |
| Missing files/requirements | 61 |
| Crash / functional failure | 32 |
| Unnecessary churn (unrelated edits) | 27 |
| Duplicate code/logic | 20 |
| Incomplete implementation | 12 |

**When CHALLENGER wins — king failure modes:**
| Failure | Count (sample 100) |
|---------|-------------------|
| Breaking change / error | 83 |
| Missing files/requirements | 56 |
| Crash / functional failure | 34 |
| Unnecessary churn | 22 |
| Duplicate code/logic | 18 |
| Incomplete implementation | 15 |

**Critical insight:** The #1 differentiator in BOTH directions is **breaking changes / errors**. Code that compiles and runs correctly beats complete-but-broken code every time. #2 is **missing files/requirements** — completeness still matters heavily. **Unnecessary churn** (unrelated edits, reformatting) is the #3 penalty — the judge explicitly calls this out.

### 4. High-Score Pattern (score ≥ 0.8)
334 of 1,040 yesterday's records scored ≥ 0.80. Key patterns from rationales:
- Correct import paths (breaking the opponent on wrong relative imports)
- Removing the correct OLD code alongside adding NEW code (full refactor)
- Edge case coverage in tests
- No chmod churn or unrelated whitespace changes
- Matches reference structure (file organisation, naming)

---

## Actionable Intelligence for vNEXT Agent

### Priority 1: CORRECTNESS OVER COMPLETENESS
The data is clear: breaking errors kill scores more than missing files. M2.7 needs to prioritise **compilable, runnable patches** above everything.

### Priority 2: ANTI-CHURN RULES
Unrelated edits (chmod, formatting, unnecessary imports) appear in 22-27% of losing cases. The agent must be explicitly told: **only touch what the task requires**.

### Priority 3: M2.7 OVER-EDITING IS ACTUALLY AN ASSET
57.6% of M2.7 gold patches exceed reference size — this is GOOD given the completeness asymmetry rule. The risk is the 21.4% severe under-edit cases (< 50% of reference). The agent needs to push M2.7 to cover cascade files when it would naturally stop short.

### Priority 4: BUGFIX TASK DOMINANCE
73% of today's duels are BUGFIX. The agent's system prompt should have strong BUGFIX-specific rules: trace the bug to root cause, fix ALL affected call sites, don't just patch the symptom.

### Priority 5: UPDATE TASK WEAKNESS (Based on yesterday)
UPDATE tasks have the highest score gap opportunity (avg chosen 0.623 vs rejected 0.338 = 0.285 gap). The judge rationale for UPDATE losses repeatedly mentions: "incomplete", "missing Phase B features", "only partial refactor". UPDATE tasks require the agent to implement the COMPLETE feature described, not just the minimal change.

### Priority 6: IMPORT PATH CORRECTNESS
Multiple high-score examples explicitly penalise wrong relative imports. M2.7 should double-check import paths, especially when moving files between directories.

---

## Summary Statistics
| Metric | Value |
|--------|-------|
| M2.7 gold patches analysed | 9,037 |
| M2.7 median patch size | 368 lines |
| M2.7 over-editing rate | 57.6% |
| M2.7 severe under-editing rate | 21.4% |
| M2.7 avg files per patch | 4.5 |
| Live duels analysed (2 days) | 1,425 records |
| King 2-day win rate | 55.0% |
| Avg score gap (winner vs loser) | 0.305 |
| #1 loss cause (both sides) | Breaking errors |
| #2 loss cause | Missing files |
| #3 loss cause | Unnecessary churn |
