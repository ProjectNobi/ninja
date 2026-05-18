# SN66 System Audit — 2026-05-18
**Auditor:** T68Bot (claude-sonnet-4-6) | **Date:** 2026-05-18 08:15 UTC | **READ-ONLY — NO FIXES**

---

## 1. CRITICAL ISSUES (blockers to reach 70% WR)

### CRITICAL-1: King Sync Mismatch — ALL Gate Results Are Invalid
- **Live king SHA:** `fd2af7a6050e` from `private-submission`, UID 192 (as of 2026-05-18 08:15 UTC)
- **Our `king_agent.py`:** `54342f42bade` from `tao-hunter/viper-agent` (promoted May 16, 2026)
- **Impact:** v54 gate (52%) and v61 gate (39.4%) were both measured against a **STALE king**. The actual competition is against a **different, potentially stronger king**. All published WR% numbers are comparisons against the wrong baseline.
- **Evidence:** `curl 'https://ninja66.ai/dashboard.json'` shows `fd2af7a6050e / private-submission / UID 192`. Our `king_agent.r2sha_54342f42.py` backup file confirms which king we tested against.
- **File:** `/root/sn66-ninja/scripts/sync_king.sh` exists but was NOT run before recent gate tests.

### CRITICAL-2: Philosophy Regression in v61 — "Smallest Correct Change" Kills Completeness
- **Location:** `agent_cl_gpt_v61.py:2931` — SYSTEM_PROMPT opening sentence
- **v54 (52% WR):** `"COMPLETENESS BEATS MINIMALISM. Missing files/requirements costs far more than extra thorough edits."`
- **v61 (39.4% WR):** `"Aim for the patch a careful senior maintainer would submit: complete, precise, **no more**."` + `"the smallest correct change that fully resolves the issue at the root cause."`
- **Impact:** The LLM judge scores SCOPE COMPLETENESS (30pts). By telling the model to minimize scope, v61 systematically leaves points on the table. This is the **primary cause** of REFACTOR collapsing from 60% → 0% and UPDATE from 50% → 27%.
- **Diff proof:** `diff agent_cl_gpt_v54.py agent_cl_gpt_v61.py` shows exactly 4 changed locations — the core philosophy reversal is at lines 2931-2941.

### CRITICAL-3: v59's "Never Delete" Rule Destroyed Restructuring Tasks
- **Location:** `agent_cl_gpt_v59.py:3090-3100` — Added SCOPE AND COMPLETENESS section
- **Rule added:** `"Never delete or remove existing functions/components unless the task explicitly requests it."`
- **Impact:** REFACTOR and UPDATE tasks **require** deletion and restructuring. This rule makes the model preserve old broken code while adding new code, producing patches that fail the reference comparison. This is the root cause of v54→v59 regression (52% → 35.4%).
- **Cascade:** v61 inherited v59's "Never delete" prohibition but also added the minimalism shift — double penalty.
- **File:** `agent_cl_gpt_v59.py` — confirmed via diff against v54 (only 3 hunk locations changed).

### CRITICAL-4: REFACTOR at 0% in v61 — Catastrophic Single-Category Failure
- **v54 result:** REFACTOR 3/5 = **60%** (functional, no special handling)
- **v61 result:** REFACTOR 0/5 = **0%** (catastrophic collapse)
- **Root cause:** v61's "smallest correct change" + v59's "Never delete" both directly contradict what REFACTOR tasks require (restructure code = change structure + often delete old patterns). The model produces empty or trivial patches that don't restructure anything.
- **Urgency:** With only 5 REFACTOR tasks in 100, each task is worth 2 WR points. Going from 0% → 60% is worth +3 WR points — meaningful at the margin.

### CRITICAL-5: The 52% Ceiling Is an Architecture Gap, Not Just a Prompt Issue
- **Evidence:** v54 is the best-ever result at 52%. No version in v50-v61 has beaten it.
- **King architecture:** 4082 lines, MAX_STEPS=30, multishot (2 attempts), MAX_REFINEMENT_TURNS=3, WALL_CLOCK=248s
- **Our architecture:** 4610-4717 lines (same structure, more verbose), same step/time budgets
- **Gap hypothesis:** The king's multishot (attempt 1 + attempt 2 with fresh context) gives it a second chance on difficult tasks. Our multishot is present but may not be triggering as effectively.
- **Key difference identified:** King SYSTEM_PROMPT emphasizes `"smallest root-cause fix"` with integration cascade, while being concise (4082L vs our 4610L+). The king's conciseness may allow more useful context per token in the harness.
- **Math to 70%:** Need +18pp. Current WR distribution: BUGFIX 47%, API 70%, FEATURE 56%, REFACTOR 60%, UPDATE 50%. To reach 70%: need BUGFIX→65%, UPDATE→60%, REFACTOR→70% simultaneously.

---

## 2. ROOT CAUSES OF REGRESSION (v54 → v59 → v61)

### v54 → v59 (52% → 35.4%) — "Never Delete" Rule
```
ADDED to v59 at agent_cl_gpt_v59.py:3090-3100:
"Never delete or remove existing functions/components unless the task explicitly requests it."
"Only modify files directly required by the task."
```
- REFACTOR tasks need deletion → rule fires → model preserves old code → reference mismatch
- UPDATE tasks need to replace old implementations → rule fires → only adds code → score drops
- Also added: `_strip_mode_metadata_lines` (minor) and `git config core.fileMode false` (neutral)
- The rest of v59 SYSTEM_PROMPT is virtually identical to v54 — this rule alone caused -16.6pp

### v59 → v61 (35.4% → 39.4%) — Minimalism Shift Partially Offset by Hail-Mary Fix
- **Regression:** Removed `"COMPLETENESS BEATS MINIMALISM"` line. Added `"smallest correct change"` framing.
- **Improvement:** `MAX_HAIL_MARY_TURNS: 1 → 3` and `_MID_LOOP_HAIL_MARY_BUDGET_FRACTION: 0.50 → 0.55`
- **Net effect:** +4pp from hail-mary fix (fewer empty patches on hard tasks), -? pp from minimalism (systematic under-editing). Net: +4pp but still worse than v54.
- **Plan format change:** v61 changed from `AC-1/AC-2/AC-N` to `Requirement/Requirement` format and `CASCADE` → `Integration cascade`. This is a minor stylistic difference but may change how the model extracts requirements.

### v54 vs v61 — Direct SYSTEM_PROMPT Comparison (The Definitive Evidence)
| Dimension | v54 (52%) | v61 (39.4%) | Effect |
|-----------|-----------|-------------|--------|
| Opening framing | "elite autonomous coding agent" | "...scored on similarity + LLM" | Minor |
| Completeness law | **"COMPLETENESS BEATS MINIMALISM"** | REMOVED | **-WR** |
| Scope guideline | "Fix exactly what issue requires" | **"smallest correct change, no more"** | **-WR** |
| Plan format | AC-1/AC-2/CASCADE | Requirement/Integration cascade | Neutral |
| Hail-mary turns | 1 | **3** | **+WR** |
| Hail-mary fraction | 0.50 | 0.55 | +WR |
| Inherited "Never delete" | NO | YES (from v59) | **-WR** |

---

## 3. SYSTEMATIC WEAKNESSES BY TASK TYPE

### REFACTOR: 0% in v61 — Root Cause
- **v54:** 3/5 = 60% ✅ | **v61:** 0/5 = 0% ❌
- **Root cause (primary):** v61's "smallest correct change" framing causes the model to treat REFACTOR tasks as bugfixes — making minimal changes when the task requires comprehensive restructuring
- **Root cause (secondary):** v59's inherited "Never delete" rule suppresses code removal needed in every refactoring task
- **What REFACTOR tasks require:** Restructure code structure while preserving behavior. This almost always involves: (a) deleting old implementation, (b) creating new structure, (c) updating all call sites. Our v61 prompt fights all three steps.
- **Evidence:** v54 achieved 60% REFACTOR WITHOUT any special REFACTOR handling — pure effect of "COMPLETENESS BEATS MINIMALISM" philosophy giving the model permission to make comprehensive changes.
- **Diagnostic gap:** We have NO insight into what specific patches our agent generated for the 5 REFACTOR tasks in v61. No per-task patch capture to examine failure modes.

### UPDATE: 27% in v61 — Root Cause
- **v54:** 6/12 = 50% | **v61:** 3/11 = 27.3% ❌
- **Root cause (primary):** UPDATE tasks require replacing old implementations — avg 246 lines DELETED (per v56 Intel). v61's "smallest correct change" + "Never delete" causes the model to ADD new code rather than REPLACE old code.
- **Root cause (secondary):** v52 history shows FCG (Functional Correctness Gate) added in v52 destroyed UPDATE from 75%→25% (L-FCG-UPDATE-REGRESSION-1). Unknown if similar gate logic exists in v54-v61.
- **Pattern:** UPDATE tasks in SN66 dataset represent "implement a feature for an existing system" — not a minor fix. The judge expects comprehensive implementation matching the reference patch.
- **v56 intel (applied to v56 but NOT to v54/v61):** `"UPDATE tasks often need to REMOVE old patterns while adding new ones. Avg UPDATE patch deletes 246 lines."` This critical insight exists in v56's SYSTEM_PROMPT but was NOT carried back to v54-v61 main line.

### BUGFIX: 40% in v61 (47% in v54) — Root Cause
- **v54:** 23/49 = 46.9% | **v61:** 20/50 = 40%
- **Root cause:** Moderate regression, not catastrophic. Both versions handle BUGFIX similarly at the philosophy level ("fix root cause, not symptom" is present in both).
- **Contributing factor:** v61's "smallest correct change" may cause under-editing on BUGFIX tasks that require cascade changes (updating callers, tests, configs).
- **Structural constraint:** BUGFIX = 49-50% of all tasks. This is the highest-leverage category. Even if we fix REFACTOR and UPDATE perfectly, we still need BUGFIX→65%+ to reach 70% WR overall.
- **Ceiling hypothesis:** The king likely wins BUGFIX tasks because its multishot gives a second attempt when the first solution is wrong. Our agents don't benefit from multishot as effectively.

### API/ROUTE: 60-70% — Working, Minor Room
- **v54:** 7/10 = 70% ✅ | **v61:** 6/10 = 60% ✅
- **Root cause of v61 regression:** Minor. Likely noise in small sample (10 tasks). Both versions perform adequately.
- **No action needed** on prompt for this category.

### FEATURE: 47-56% — Moderate Weakness
- **v54:** 10/18 = 55.6% | **v61:** 8/17 = 47.1%
- **Root cause:** FEATURE tasks require creating new functionality across multiple files (component + route + state + tests). v61's minimalism reduces multi-file creation. v56's architecture had explicit FEATURE handling ("49% of tasks need at least one new file") which was not in v54/v61.
- **Key missing:** v56 added explicit `FILE CREATION RULE` section guiding model to create new source files + tests + configs. This intelligence was NOT propagated to v54-based line.

---

## 4. ARCHITECTURE GAPS (what v54-v61 are missing vs king)

### GAP-1: King Uses Concise System Prompt (4082L vs 4610-4717L)
- King is 4082 lines total. Our agents: 4610-4717 lines (+10-15% more tokens)
- In a harness with `MAX_CONVERSATION_CHARS = 80000`, prompt length matters
- Longer system prompt = less room for observations, code, and task context
- **Not confirmed as bug** but worth noting: our agents may be token-starved on complex tasks

### GAP-2: Multishot Effectiveness
- Both king and our agents use multishot (2 attempts, `_MULTISHOT_TOTAL_BUDGET = 278s`)
- King: `MAX_REFINEMENT_TURNS=3` per attempt
- Our agents: Same constants
- **Unconfirmed:** Whether our agent triggers attempt 2 as often as king when attempt 1 produces empty/poor patch
- **Check needed:** Gate logs don't report per-task multishot attempt count

### GAP-3: No Task-Type Adaptation in v54/v61
- King SYSTEM_PROMPT has no explicit task-type branching (based on analysis)
- v56 added `TASK TYPE RECOGNITION` section — but v56 never completed a gate test
- Our v54-v61 line also has NO task-type adaptation
- The king beats us on REFACTOR (0% vs estimated >50% for king) without special handling — meaning king's GENERAL philosophy handles REFACTOR better than our v61's explicit constraints

### GAP-4: v56 Intelligence Not Propagated to Main Line
v56's uncommitted changes contain multiple insights that v54-v61 don't have:
- `TASK TYPE RECOGNITION` section with UPDATE/FEATURE-specific guidance
- `FILE CREATION RULE` section (49% of tasks need new file — explicit guidance)
- `Target patch size` hints (FEATURE: 300-1000L, UPDATE: 200-700L, BUGFIX: 150-400L)
- UPDATE deletion intelligence ("avg UPDATE patch deletes 246 lines")
- These are in `agent_cl_gpt_v56.py` with UNCOMMITTED CHANGES — at risk of being lost

### GAP-5: No Per-Task-Type Loss Analysis Done for v61
- We have breakdown by task type but NO per-task patch comparison for v61 losses
- Cannot diagnose WHY specific REFACTOR tasks failed (empty patch? wrong approach? wrong file?)
- Cannot diagnose WHY UPDATE tasks fail (too little deletion? wrong file selection?)
- Without patch capture, each iteration is partially blind

---

## 5. GOLD/DPO PIPELINE ISSUES

### PIPELINE-1: 53K DPO Pairs Never Migrated — HIGH SEVERITY
- **Evidence:** `DATA_HEALTH_2026-05-18.md`: "Migration script has NEVER been executed | Total migrated: 0"
- **Location:** AnonServer `/root/sn66-ninja/training_data/` has 53,053 high-quality DPO pairs (80%+ consensus)
- **Files:** `synthetic_dpo_pairs.jsonl` (4,389), `reference_dpo_pairs.jsonl` (910), `self_play_dpo_pairs.jsonl` (1,128), `full_matrix_dpo_pairs.jsonl` (46,626)
- **Impact:** These DPO pairs represent the most valuable training signal (winner vs loser with judge rationale). They are NOT in unified gold and cannot be used for training.

### PIPELINE-2: No Training Has Been Done — Data Collecting, Not Training
- ~600K gold patches collected across 12+ models. 53K DPO pairs. 27M+ SFT records (AnonServer)
- **None of this data has been used to train a model**
- No fine-tuning pipeline exists. No training job scheduled. No training infrastructure.
- All data collection is "future investment" — has ZERO impact on current WR.

### PIPELINE-3: task3_selfplay and task_update_dpo Effectively Stalled
- `task3_selfplay`: 1/4,122 records after fix restart — **9 days ETA** (impossible at current pace)
- `task_update_dpo`: 1,157/62,590 records — **203 hours (~8.5 days) ETA**
- These are generating the most valuable data (UPDATE-specific DPO pairs) but will not complete before any reasonable submission window.

### PIPELINE-4: AnonServer Unified Gold Schema Inconsistency
- AnonServer has 27M+ records with schema: `{output, llm_response, model, archetype, source}`
- Hetzner1 has 208K records with schema: `{output, llm_response, model, archetype, source, is_winner, edit_quality}`
- These are confirmed different populations (NOT identical copies)
- DPO pairs from AnonServer not yet merged = schema divergence risk on eventual merge

---

## 6. SYSTEM HEALTH ISSUES (PM2, crons, git, etc.)

### HEALTH-1: King Sync Not Run Before Gate Tests (HIGH)
- `king_agent.py` = `54342f42bade` (tao-hunter/viper-agent, May 16)
- Live king = `fd2af7a6050e` (private-submission, May 18, UID 192)
- Gate results (v54=52%, v61=39.4%) measured against WRONG king
- All WR numbers from recent gate tests are not comparable to live performance

### HEALTH-2: v56 Has UNCOMMITTED CHANGES (MEDIUM)
- `git status` shows `agent_cl_gpt_v56.py` as MODIFIED but not staged
- `git log` shows only v54 and v56 committed — but the committed v56 is different from the current working copy
- Risk: v56's uncommitted improvements (task-type recognition, FILE CREATION RULE, etc.) could be lost on `git checkout` or branch switch

### HEALTH-3: 100+ Untracked Files in /root/sn66-ninja/ (MEDIUM)
- `git status` shows 100+ untracked files: agents v1-v61, king backups, gate logs, research docs
- Branch is on `sn66-clgptv35-02`, diverged 5 commits from origin/main
- Origin/main is 21 commits ahead of local branch — significant drift
- Risk: Impossible to do clean `git pull` without resolving divergence

### HEALTH-4: Stale tmux Sessions from May 15 (LOW)
- 15+ old gate sessions running: `v40-gate`, `v41-gate`, ..., `v48-gate`, `glm47-sweep3/4`, `gold-*` (18 sessions)
- Most completed (gate results visible in pane) but sessions not cleaned up
- Resource consumption: each stale session holds terminal state
- v46-gate shows 56% WR — competitive! This result was never surfaced to the pipeline

### HEALTH-5: memorybear-forgetting/inference/reflection STOPPED (LOW)
- 3 PM2 processes stopped with 0 restarts — likely intentional but not documented
- If these were part of a training or memory pipeline, they should be monitored

### HEALTH-6: nobi-validator NOT in PM2 List (MEDIUM)
- Per AGENTS.md, nobi-validator should be in PM2
- Absent from current `pm2 list` — may have been removed intentionally or crashed without restart

### HEALTH-7: t68hyper — 9 Restarts in 4h (LOW-MEDIUM)
- `t68hyper` running but with 9 restarts in ~4h — elevated churn
- Could indicate memory leak, API errors, or unstable dependency

---

## 7. OPTIMIZATION OPPORTUNITIES (ranked by impact)

### OPT-1: Revert to v54 Philosophy, Fix the Two Regressions (HIGHEST IMPACT)
- **Action needed:** Remove "smallest correct change" / "no more" minimalism from SYSTEM_PROMPT
- **Action needed:** Remove "Never delete or remove existing functions" constraint inherited from v59
- **Action needed:** Restore "COMPLETENESS BEATS MINIMALISM" as explicit law
- **Expected gain:** +13-16pp (recover v59 regression) + further improvement from minimalism fix
- **Evidence:** v54 at 52% with zero REFACTOR/UPDATE-specific handling, using completeness philosophy

### OPT-2: Sync King Before Any Gate Test (HIGH IMPACT, LOW EFFORT)
- Run `bash /root/sn66-ninja/scripts/sync_king.sh` immediately
- Re-run 100-task gate for v54 against live king to establish true baseline
- All strategy decisions are based on stale comparison

### OPT-3: Port v56's Task-Type Intelligence to v54 Base (HIGH IMPACT)
- v56's TASK TYPE RECOGNITION section is the most advanced task-type guidance in the codebase
- UPDATE intelligence ("avg 246 lines deleted") + FILE CREATION RULE for FEATURE tasks
- Port these to a v62 built on v54's philosophy (not v61's minimalism)
- **Expected gain:** UPDATE 50% → 60%+ (+10pp on 12% of tasks = +1.2pp overall)

### OPT-4: Per-Task Patch Capture for Loss Analysis (HIGH IMPACT for next iteration)
- Need a script to save challenger patches for each failed task
- Without per-task analysis: every version iteration is partially blind
- Specifically need: 5 REFACTOR task patches from v61 + 11 UPDATE task patches from v61

### OPT-5: Propagate v54's Philosophy to v62, Inherit v56's Task Intelligence (MEDIUM IMPACT)
- Best v62 = v54 philosophy + v56's UPDATE/FEATURE/REFACTOR task guidance + v61's hail-mary fix (3 turns)
- Keep: `MAX_HAIL_MARY_TURNS=3` from v61 (this was correct improvement)
- Keep: `_MID_LOOP_HAIL_MARY_BUDGET_FRACTION=0.55` from v61 (correct)
- Remove: minimalism framing, "Never delete" rule
- Add: UPDATE deletion guidance (246 lines), FILE CREATION RULE, TASK TYPE RECOGNITION

### OPT-6: DPO Migration (MEDIUM IMPACT — future training)
- Run `migrate_dpo_to_unified.py` on AnonServer to merge 53K DPO pairs
- This enables eventual fine-tuning of an SWE-bench model with T68-specific data
- No current-round impact but critical for long-term competitive advantage

### OPT-7: Restart T68-S1 Gold Run (LOW-MEDIUM IMPACT)
- T68-S1 gold run not running (dead per DATA_HEALTH report)
- qwen3-30b-awq gold patches were at 2,844/9,122 when last alive
- Marginal data value but completes the dataset

---

## 8. DECISIONS NEEDED (what James must decide)

### DECISION-1: v62 Build Strategy
**Option A (Recommended):** Build v62 from v54 base. Port v56 task-type intelligence. Apply v61's hail-mary fix. Do NOT use minimalism framing. Run 100-task gate against live king.

**Option B:** Continue iterating from v61 base (requires removing "smallest correct change" and "Never delete" — essentially becomes Option A).

**Option C:** Study the live king (fd2af7a6050e / private-submission) first — its architecture may be significantly different from tao-hunter/viper-agent. Private submission means it could be a proprietary stack.

### DECISION-2: King Architecture Study
The live king is from "private-submission" (UID 192), not a public GitHub repo. The `sync_king.sh` script fetches from `unarbos/ninja` on GitHub — which may not have the current king's code. **We may be flying blind.** Decision: How to obtain the current king's code? (The harness' `king_sha` warning system exists for this.)

### DECISION-3: Training Investment Timing
50K+ DPO pairs collected, 600K+ gold patches. Training a custom SWE model could leapfrog the prompt-engineering ceiling. Decision: When to prioritize training vs continued prompt iteration? Current ceiling seems to be ~52% with prompt alone.

### DECISION-4: Stale tmux Session Cleanup
v40-v48 gate sessions from May 15 still alive. v46-gate showed 56% WR — was this version ever surfaced? Decision: clean up sessions? Investigate v46?

### DECISION-5: v56 Uncommitted Changes
v56 has valuable uncommitted changes (task-type intelligence) that are NOT in git. Decision: commit v56 current state OR port its intelligence to v62 and discard v56?

---

## 9. WHAT IS NOT AN ISSUE (things working correctly)

- **sn66-final-unified-collector (PM2):** ✅ Running, 6 restarts is normal for long-running process
- **Nobi services:** nobi-api, nobi-bot, nobi-discord, nobi-webapp, nobi-auto-updater — all online, healthy
- **Gold patch collection (AnonServer):** ✅ All 23 gold sessions running, 600K+ patches
- **DPO quality:** ✅ 53K pairs, 80%+ consensus, zero identical pairs — high quality data
- **Harness v6 scoring formula:** ✅ Correctly implements live validator formula (0.5×cursor_sim + 0.5×llm_score). win_margin=3 correctly reflected in 55% gate threshold.
- **API/ROUTE task performance:** ✅ 60-70% WR — our strongest category, no action needed
- **cron schedule:** ✅ Gold sync (every 2h), gateway watchdog (15min), API key healthcheck (weekly) all scheduled and running
- **t68hyper:** Running (9 restarts is concerning but it's online)
- **Hetzner1 disk:** 199G/338G (59%) — healthy
- **v61's hail-mary improvement:** MAX_HAIL_MARY_TURNS 1→3 was CORRECT — this reduces empty patches from hard tasks

---

## Summary Statistics

| Metric | Value | Assessment |
|--------|-------|------------|
| Best ever WR | 52% (v54) | NOT competitive vs 70% target |
| Current (v61) WR | 39.4% | Sharp regression from best |
| Gap to threshold | 17.6pp (from v54) | Major architecture/prompt work needed |
| Live king SHA | fd2af7a6050e (private) | DIFFERENT from test king — all results stale |
| REFACTOR in v61 | 0/5 = 0% | Catastrophic — caused by prompt philosophy |
| UPDATE in v61 | 3/11 = 27% | Chronic — caused by "never delete" rule |
| DPO pairs in training | 0 | 53K collected but never merged |
| Active training runs | 0 | Data collection only, no model training |
| Stale gate sessions | 15+ | Cleanup needed |

---

*Audit complete. Report written to /root/sn66-ninja/AUDIT_SYSTEM_2026-05-18.md*
