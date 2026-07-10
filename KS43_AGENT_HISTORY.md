# SN66 Agent Full History — T68Bot / Project Nobi
**Branch:** `kingslayer/ks43-plan`
**Compiled:** 2026-07-10 08:30 UTC by T68Bot
**Purpose:** Complete intel for KS43 design — every agent, every live result, every lesson learned

---

## PART 1: SCORING SYSTEM CHANGES (CRITICAL CONTEXT)

| Era | Dethrone Mechanism | Notes |
|-----|--------------------|-------|
| Pre-Jul-01 | wins - losses > 3 (margin gate) | Primary + confirmation duel required |
| **Jul-01 onwards** | challenger_mean - king_mean ≥ 0.05 (mean delta) | Single 50-round duel, scoring_method=MEAN |

The scoring change is the most important context for all KS38+ agents.
Old era: win rate + margin. New era: **absolute mean score delta**.
This changes the optimal strategy: maximize your absolute mean, not just win rate.

---

## PART 2: KING LINEAGE

| # | Period | King SHA / UID | Architecture | Mean Score Era |
|---|--------|----------------|--------------|----------------|
| 1 | ~May 9 | PR#640 (5CfBJuxB...) | Single-shot | N/A |
| 2 | May 10 | PR#770 ninjaking66 | Multi-shot v28 | N/A |
| 3 | May 10 | PR#783 VladaWebDev (UID 249) | Multi-shot | N/A |
| 4 | May 10 | PR#784 victormorales9493 (UID 108) | Multi-shot + 9 refinement gates | N/A |
| 5 | May–Jun | PR#805 leec72991-a11y (UID 107) | anon-magician v28 + integration cascade | N/A |
| 6 | ~Jun | SHA 9272402e (adamninja PR#1551, 4106L) | Multi-shot 248/20s | N/A |
| 7 | Jun 14+ | SHA 733bd504 | Multi-shot, 15 defenses | Win/Loss era |
| 8 | ~Jun 23 | SHA 2cc758a5 | Multi-shot, Tie-heavy | Win/Loss era |
| 9 | ~Jun 25 | SHA 3afbc575 | Multi-shot + reroll.py | Win/Loss era |
| 10 | Jun 28+ | SHA 3ecc3307bb02 | Multi-file package agent | Win/Loss → Mean era |
| 11 | ~Jun 30 | SHA e8e025b7 (multi-file pkg) | Full package: agent/ modules | Win/Loss → Mean era |
| 12 | Jul 01+ | SHA 0f4615a → **53bca97cbfe6** (UID 130) | Package: agent.py+reroll+prompts+env | **MEAN era, ~0.68–0.75 mean** |
| 13 | **Jul 10** | **UID 215** `5HKauaiL71XiWn49` (private) | Unknown, private submission | **~0.4443 mean (NEW)** |

**Current King (as of 2026-07-10 08:30 UTC):**
- UID 215, hotkey `5HKauaiL71XiWn49q3PWPTb8BzcPVAmtT87UzrwXVRfS3sXc`
- Took throne: 2026-07-10T03:11:44 UTC (Duel 589408, delta +0.0832, 100 rounds)
- Dashboard SHA: still showing `53bca97cbfe6` — **NOT YET UPDATED**
- New King avg mean: **0.4443** (range 0.4012–0.5346 across 11 defenses)

---

## PART 3: AGENT HISTORY — COMPLETE RECORD

### Next-Series Agents (Pre-KS, Next66 era)
**Architecture:** Iterative improvements on a v6–v7 GPS/multi-shot base
**Approach:** Generate-Prune-Select, structured `<edit>` verb, GraphRAG context

| Agent | Lines | Key Feature | Gate Result |
|-------|-------|-------------|-------------|
| Next1–8 | ~900–1100L | Various GPS attempts | Mixed |
| Next9 | ~1100L | Root cause: api/route weakness | Gate passed |
| Next66 | ~1500L | Requirement-coverage approach | 15W-12L-3T margin+3 |
| Next71–85 | ~1500–1800L | Incremental tuning | Various |

**Fable-5 V1** (2026-06-09): 2277L, GPS + `<edit>` verb + GraphRAG + reference-alignment SYSTEM_PROMPT. Separate track from KS series. Has its own UIDs via sn66-fable5-v1/v2/v3 hotkeys.

---

### KS1 — KS3 (Late June 2026, Win/Loss era)
**Base:** King clone + targeted surgical changes
**Key insight from KS1–3:** Simpler is better. KS2 outperformed KS3-7. Minimalism wins.

| Agent | Key Change | Gate | Live Result |
|-------|-----------|------|-------------|
| KS1 | King clone baseline study | Gate run | Not submitted |
| KS2 | +named-file early nudge (small scope only) | Seed 42+99 run | Not submitted |
| KS3 | +scope note for ≥3 files | Regression vs KS2 | Not submitted |

---

### KS4 — KS6 (Jun 26+, vs SHA 733bd504 King)
**King:** SHA 733bd504, UID 35, 17 defenses before being dethroned
**Era:** Win/Loss scoring (wins - losses > 3 needed)
**Submission UID:** 35

**King weakness map (733bd504):**
- Win rate 22–71% depending on task draw
- Tie rate ~40% (only 60% contested rounds)
- Narrow loss gaps dominate (-0.06 to -0.10)
- King wins on QUALITY OF DIAGNOSIS, not code volume

| Agent | Live Duel | W/L/T | Margin | Result |
|-------|-----------|-------|--------|--------|
| KS4 | Duel #6662 | W30-L20-T0 | +10 | ❌ Missed threshold |
| KS4 | Duel #6667 | W29-L21-T0 | +8 | ❌ Missed |
| KS4 | Duel #6696 | W24-L13-T13 | +11 | ❌ Need margin >3 with confirmation |
| KS4 | Duel #6727 | W29-L19-T0 | +10 | ❌ Missed |
| KS4 | Duel #6769 | W29-L21-T0 | +8 | ❌ Missed |
| KS4+ | (17 total duels) | Various | Various | ❌ Never dethroned |
| KS8 | Duel #7454 | W22-L19 | +3 | ❌ Missed by 1 win! |

**KS4–8 lessons:**
- Narrow losses dominate — king wins by CONSISTENCY not brilliance
- Flip 3 narrow losses → +10% win rate
- Multi-shot / two-attempt architecture explains king's edge on narrow rounds
- KS8: missed throne by 1 win (W22-L19, needed margin+4 for confirmation)

---

### KS9 — KS13 (Late June, vs SHA 2cc758a5 / 3afbc575)
**King:** SHA 2cc758a5 → 3afbc575 (introduced reroll.py)
**Key discovery:** King's reroll.py — runs 2 attempts, picks better one

| Agent | Key Feature | Gate | Live |
|-------|------------|------|------|
| KS9 | Richer SYSTEM_PROMPT + FEATURE improvements | 74% tie rate gates | Not submitted |
| KS10 | Two-attempt reroll concept introduced | Seed 42+99 partial | Duel #7464: W12-L4-T33 WON primary ✅ |
| KS11 | Confirmation duel strategy | Seed 42+99 partial | Confirmation failed ❌ |
| KS12 | Architecture B: task-type specialist router | Partial gates | Not dethroned |
| KS13 | FEATURE breakthrough (67% on FEATURE) | Seed 42+99 partial | Not submitted |

**KS10 throne duel #7464:** W12-L4-T33/49, margin=+8 → WON primary but failed confirmation
**Critical discovery:** Tie rate 74% in some duels = only 26% contested rounds → margin+7 possible with just 6 decisive wins!

---

### KS14 — KS27 (Early July, vs SHA 53bca97cbfe6 King, MEAN era begins)
**King:** SHA `53bca97cbfe6` (UID 130) — full package agent with reroll.py
**New scoring:** MEAN delta ≥ 0.05 to dethrone (effective Jul 01 2026)
**King package structure:** agent.py + agent/reroll.py + agent/prompts.py + agent/model.py + agent/environment.py + agent/repo_diff.py

**King mean scores in defenses:** 0.68–0.75 (high quality era)

| Agent | Lines | Key Feature | Gate Result | Live |
|-------|-------|-------------|-------------|------|
| KS21 | 940L | Scope-aware nudge timing + `<scope>` note | Gate passed | Not submitted |
| KS22 | ~1000L | Nudge threshold retune | Regressed | Not submitted |
| KS27 | ~1400L | Multi-file scope fix | Partial gate | Not submitted |
| KS28 | 1518L | **Fable 5 lens** — first-principles king analysis, test-writing, 15s→40s timeout | Not gated | Not submitted |

**KS28 key insight (Fable 5 analysis):**
- King's TASK_TEMPLATE is rubric-aligned: correctness + completeness + alignment
- King includes regression tests IN the patch (NO_TEST = 50–66% of our losses)
- King: post-run verify+repair+polish pipeline
- Our gap: KS21/KS27 used OLD king prompt that suppressed tests
- King's edge: demonstrated fixes (with tests) vs our undemonstrated fixes

---

### KS38 — KS39 (Jul 7, vs 53bca97cbfe6)
**Base:** Deep king study, rebuild from first principles

**KS38** (1909L, 2026-07-07):
- TASK_TEMPLATE verbatim from king
- Planning primer (PLAN_PRIMER) — zero step cost
- Pre-submit completeness gate: coverage + syntax + requirements checks
- CI: pyflakes clean, all tests pass
- Gate: Not recorded in available logs

**KS39** (R6 resilience, ~1943L):
- Honest 270/30 wall-clock budget (fixes duel-7241 forensics rule)
- Process-group command kill
- **This is the LAST AGENT THAT BEAT THE KING**
- KS39 mean score vs king: **0.729** (king was ~0.68–0.75 era)
- KS39 won live against old king family

---

### KS40 (Jul 9, first reroll attempt)
**Base:** KS39 + best-of-two reroll orchestrator
**Lines:** 2220L (+277 vs KS39)
**Submission:** UID 225

**KS40 changes:**
1. `run_best_of_two_ks40()` — reroll orchestrator
2. `_is_weak_patch_ks40()` — quality detector
3. `_extract_named_tokens_ks40()` + backtick symbol parsing
4. Enhanced empty rescue (8 steps/60s, up from 5/30s)
5. `_is_hard_task_ks40()` + `_HARD_TASK_NOTE` scope injection
6. `_RepoIndex` cache

**KS40 live result:**
- Duel 251186: KS40 UID 225 vs King UID 130
- **W21-L22-T7 | KS40 mean=0.6988 | King mean=0.7176 | Δ=-0.0188 | LOST**
- Mean LOWER than KS39 (0.729) → regression of 0.030

**Root cause (KS41 post-mortem):**
- `_is_weak_patch_ks40()` has false positives → fires reroll on correct patches
- `_patch_key_ks40` measures structural coverage, NOT correctness
- False positive Case A: non-named-file fix → reroll fires → wrong file adopted
- False positive Case B: one-liner multi-req → reroll fires → bloated wrong patch adopted
- King's `_is_weak()` in reroll.py has LOWER false positive rate
- King ALSO upgraded to reroll (+0.033 mean), net swing: KS40 -0.030 + king +0.033 = 0.063 delta

---

### KS41 (Jul 9, king-faithful reroll)
**Base:** KS39 + king's reroll.py verbatim + A Hung fixes
**Lines:** 2362L
**A Hung contribution:** 8 audit fixes including crash fix, trace accuracy, budget comment

**KS41 changes vs KS39:**
- `run_best_of_two_ks41()` — king's reroll implementation (correct, low false-positive)
- A Hung's patches 1–8: crash fix, trace events, outer_exception handling, budget comment

**KS41 gate results (vs king 53bca97cbfe6):**

| Seed | Win Rate | W/L/T | Mean Delta | Verdict |
|------|----------|-------|-----------|---------|
| 42 | 60.0% | 30W-20L-0T | +0.0400 | ✅ Competitive, ❌ below dethrone |
| 7 | 60.0% | 30W-20L-0T | **+0.0538** | ✅ Competitive, ✅ **DETHRONE** |
| 99 | 62.5% | 30W-18L-2T | +0.0472 | ✅ Competitive, ❌ below dethrone |
| 123 | 46.9% | 23W-26L-1T | -0.0330 | ❌ NOT COMPETITIVE |

**Decision:** Not submitted. KS42 chosen instead (no reroll, test-gated repair).

---

### KS42 (Jul 9, submitted — KS39 + king repair/polish)
**Base:** KS39 + test-gated repair + polish pass (NO reroll)
**Lines:** 2074L
**Submission:** UID 177, on-chain as `ProjectNobi-KingSlayer42` (2026-07-09)

**KS42 changes vs KS39:**
1. `_python_test_outcome()` — test-gated repair adoption (only adopt repair if tests pass)
2. `_repair_reason()` gains `test_fail` + `no_test` branches (from king)
3. Polish pass — leftover budget refinement when patch is already clean

**Deliberately NOT carried:** reroll, `_RepoIndex`, hard-task note, weak-patch detector

**KS42 live result:**
- Duel 768292 (2026-07-10T02:29 UTC) vs King UID 130
- **King mean=0.4198 | KS42 mean=0.3754 | Δ=-0.0444 | LOST ❌**
- Rounds: 50 | W22-L24-T4

**Why KS42 lost (analysis):**
- KS42 scored 0.3754 — far below expected gate range of 0.65–0.70
- King UID 130 was also scoring lower (0.4198 vs historical 0.68–0.75)
- Both agents degraded → new task pool or scoring environment shifted
- Task seed variance: same agent can swing ±0.087 delta (gate seed 7 vs 123)
- KS42 gate: FEATURE 42.9% and UPDATE 42.9% weak — live may have drawn more of these
- Old King (UID 130) dethroned by UID 215 just 15 minutes after KS42's duel

---

## PART 4: FABLE-5 AGENT TRACK

Fable-5 is a separate agent architecture running on dedicated hotkeys:
- `sn66-fable5-v1` hotkey
- `sn66-fable5-v2` hotkey
- `sn66-fable5-v3` hotkey

**Fable-5 V1** (`fable5_v1_agent.py`, 2277L, 2026-06-09):
Architecture: GPS (Generate-Prune-Select) + `<edit>` verb + GraphRAG + reference-alignment
- 3-5 diverse candidates, best selected
- Coverage gate + criteria gate
- Anti-churn: whitespace/comment diffs stripped
- Hail-mary for empty patches
- Wall: 248s inner / 20s reserve

**Fable-5 KS28 study** (`agent_cl_gpt_KingSlayer28.py`, 1518L, 2026-07-04):
First-principles king study through Fable-5 lens:
- GPS + test-writing (15s→40s timeout so pytest can finish)
- 8192 token budget, 16K observations
- Acceptance checklist auto-extracted from issue
- Post-run verify+repair+polish
- NOT gated, NOT submitted (James requested waiting for A Hung direction)

**Note on "Use Fable-5 model for analysis" (A Hung request 2026-07-10):**
Fable-5 is our agent architecture, not an external model. The model used in gates is
`anthropic/claude-sonnet-4.6` (via OpenRouter/validator proxy). If A Hung means to use
Fable-5's architecture as the basis for KS43 analysis/design, that is noted here.

---

## PART 5: NEW KING (UID 215) — FULL PROFILE

| Field | Value |
|-------|-------|
| UID | 215 |
| Hotkey | `5HKauaiL71XiWn49q3PWPTb8BzcPVAmtT87UzrwXVRfS3sXc` |
| Repo | `private-submission/5HKauaiL71XiWn49` |
| Repo URL | None (private, no public access) |
| Took throne | 2026-07-10T03:11:44 UTC |
| Throne duel | 589408 (100 rounds, W51-L36-T13) |
| Winning delta | +0.0832 |
| Winning mean | 0.4738 vs old king 0.3906 |

**Defense record (11 duels, sorted by delta):**

| Duel | vs UID | King mean | Ch mean | Delta | Survived |
|------|--------|-----------|---------|-------|---------|
| 663650 | 43 | 0.4168 | 0.4180 | +0.0012 | ✅ |
| 820745 | 50 | 0.4148 | 0.4096 | -0.0052 | ✅ |
| 400017 | 83 | 0.4412 | 0.4392 | -0.0020 | ✅ |
| 974104 | 105 | 0.4584 | 0.4270 | -0.0314 | ✅ |
| 287019 | 207 | 0.4556 | 0.4120 | -0.0436 | ✅ |
| 286898 | 91 | 0.4042 | 0.4366 | +0.0324 | ✅ |
| 310762 | 61 | 0.4012 | 0.4352 | +0.0340 | ✅ |
| 936518 | 25 | 0.5346 | 0.5494 | +0.0148 | ✅ |
| 367614 | 224 | 0.4354 | 0.4830 | +0.0476 | ✅ |
| (UID 180) | 180 | ~0.41 | 0.4692 | +0.0618 | ✅ |
| (latest) | 224 | ~0.43 | 0.4830 | +0.0476 | ✅ |

**Statistical profile:**
- Mean score avg: **0.4443** (σ ≈ 0.044)
- Min: 0.4012 | Max: 0.5346
- Most vulnerable when scoring ~0.40 (3 defenses at that level)
- Closest challenge: UID 180 at +0.0618 delta — missed by ~0.01

**KS43 target:** need **≥0.494 mean** consistently to dethrone (0.4443 + 0.05 = 0.494)
Conservative design target: **0.50–0.52 mean**

---

## PART 6: SN66 ENVIRONMENT INTEL (2026-07-09)

1. **Task score cap:** Tasks scoring >70% will be removed from the pool (incoming)
   - Impact: high-performing tasks disappear, harder average task baseline
   - Our strong BUGFIX tasks may get culled

2. **Token efficiency incentive:** Within 5% quality → lower token count WINS
   - Major strategic shift: don't just be correct, be TOKEN-EFFICIENT
   - A correct but verbose patch loses to an equally correct but concise one
   - This favors leaner agent loops, not maximal multi-shot attempts

3. **MEAN scoring since Jul 01:** challenger_mean - king_mean ≥ 0.05
   - 50-round single duel (no confirmation required)
   - Both scored in [0.0, 1.0] by judge model

---

## PART 7: GATE INFRASTRUCTURE

**Gate script:** `scripts/gate.sh`
**Harness:** `validator_harness_v7.py`
**King sync:** `scripts/sync_king.sh` (fetches from dashboard.json → GitHub)
**Budget rule:** 270s/30s (wall/reserve) — duel-7241 forensics rule
**Judge models:** `anthropic/claude-sonnet-4.6` → `moonshotai/kimi-k2.6` (fallback)
**Dataset:** R2 dataset, 8227 filtered pool
**Blind A/B:** SHA256(task:challenger:model) % 2

**Gate thresholds (SN66_V7_ROOT_FIX_DEBATE_FINAL.md):**
- 10 tasks: ≥80% decisive win rate
- 30 tasks: ≥70% decisive win rate
- 100 tasks: ≥65% decisive win rate

**⚠️ Dashboard SHA lag:** Dashboard can lag hours/days behind actual live king.
Current: showing `53bca97cbfe6` but live king is UID 215 (private, no public SHA yet).
Must wait for dashboard refresh before `sync_king.sh` can pull new king.

---

## PART 8: OPEN QUESTIONS FOR KS43 DESIGN (A Hung)

1. **Why did KS42 score only 0.3754 live vs ~0.65–0.70 in gate?**
   - Task pool change? Model routing change? Agent timeout issue?
   - Need to check if there were timeouts in duel 768292 (like seed 123's 2 timeouts in gate)

2. **Should KS43 be based on KS42 (repair+polish) or KS41 (king-faithful reroll)?**
   - KS41 seed 7 hit dethrone delta (+0.0538) against OLD king
   - Old king scored 0.68–0.75; new king scores ~0.44 — different opponent profile

3. **Token efficiency: how to reduce tokens within 5% quality?**
   - Shorter prompts? Fewer steps? Concise patches?
   - New KS incentive could flip the optimal strategy

4. **Fable-5 architecture for KS43?**
   - GPS + test writing + reference alignment
   - A Hung requested Fable-5 analysis — does this mean KS43 should use Fable-5 base?

5. **Gate vs live gap investigation:**
   - Run a quick 10-task spot gate of KS42 vs NEW king once dashboard updates
   - Compare to KS42's live score to understand the gap

---

## PART 9: AGENT FILE LOCATIONS

| Agent | File | Lines | Status |
|-------|------|-------|--------|
| Fable-5 V1 | `fable5_v1_agent.py` | 2277L | Separate track |
| KS28 (Fable-5 lens) | `agent_cl_gpt_KingSlayer28.py` | 1518L | Not submitted |
| KS38 | `agent_cl_gpt_KingSlayer38.py` | 1909L | Not submitted |
| KS39 baseline | `agent_cl_gpt_KingSlayer39_hung.py` | ~1943L | Best baseline |
| KS40 | `agent_cl_gpt_KingSlayer40_submitted.py` | 2220L | UID 225, lost |
| KS41 (A Hung) | `agent_cl_gpt_KingSlayer41.py` | 2362L | Not submitted |
| **KS42 (live)** | `agent_cl_gpt_KingSlayer42.py` | 2074L | **UID 177, lost** |
| New king ref | `king_agent.py` | 268L | `53bca97cbfe6` (stale) |

---

*Compiled by T68Bot from gate logs, live duel API, git history, research docs, and build reports.*
*Awaiting A Hung's direction for KS43 design.*
