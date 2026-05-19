# SN66 MINING PIPELINE — FORMAL INSTRUCTIONS
*James directive 2026-05-18 | T68Bot standing operating procedure*
*Last updated: 2026-05-19 — Judge mechanism update + v66 build*

---

## 🏛️ SN66 SCORING MECHANISM — LLM JUDGES (James directive 2026-05-19)

### Phase 1 — CURRENT (live since PR#1598, 2026-05-19 01:43 UTC)
| Field | Value |
|-------|-------|
| **Judge** | `anthropic/claude-sonnet-4.6` via OpenRouter |
| **Scoring** | 100% LLM judge — cursor_sim is telemetry ONLY (no weight) |
| **Temperature** | 0 (deterministic) |
| **Reasoning** | Adaptive |
| **Output cap** | 16,000 tokens |
| **Caching** | OpenRouter Anthropic prompt caching on task + reference context |
| **Fallback judge** | `moonshotai/kimi-k2.6` when Sonnet returns no-choices error |
| **Win condition** | challenger_wins - challenger_losses > 3 (win_margin=3) |

**What Sonnet 4.6 rewards:**
- Root cause identification (not symptom fixes)
- Idiomatic, architecturally consistent code
- Proper error types (not generic wrappers)
- Completeness without churn
- Code that would pass a senior engineer's code review

**Training target for Phase 1:** `sonnet_winner` field in DPO pairs

---

### Phase 2 — COMING NEXT WEEK (SN66 team upgrade)
| Field | Value |
|-------|-------|
| **Judges** | `anthropic/claude-sonnet-4.6` + `openai/gpt-5.4` (dual) |
| **Scoring** | Consensus of both judges |
| **Win condition** | Must win or tie against BOTH judges |

**Training target for Phase 2:** `consensus=True` DPO pairs (both judges agree)

**Our data advantage:** ALL our DPO pairs already contain BOTH judge fields:
- `sonnet_winner` / `sonnet_rationale` — Sonnet 4.6 preference
- `gpt54_winner` / `gpt54_score_chosen` / `gpt54_score_rejected` — GPT-5.4 preference
- `consensus` — True when both judges agree = highest quality training signal

**Action when Phase 2 launches:**
1. Filter DPO training data to `consensus=True` pairs only
2. Rebuild agent version targeting dual-judge consensus wins
3. Gate test with both judges

---

### Harness v6 Judge Config (updated 2026-05-19)
- JUDGE_MODEL: `anthropic/claude-sonnet-4.6` (Phase 1 — matches live validator)
- JUDGE_MODEL_FALLBACK: `moonshotai/kimi-k2.6`
- Scoring formula: `c_combined = llm_score_challenger` (no cursor_sim)
- **Rule: Always keep harness judge in sync with live validator after any PR merge**

---

## TWO-STAGE ARCHITECTURE

| Stage | Engine | Data Used | Goal |
|-------|--------|-----------|------|
| **Stage 1 (NOW)** | Opus 4.7 builds agents informed by data | DPO pairs + gold patches + duel history | Win ≥60% WR, beat king, earn emissions |
| **Stage 2 (SOON)** | Dedicated fine-tuned M2.7 as offline dev tool | All Stage 1 data + new duel DPO + Stage 1 results | Near-unlimited iterations at $0, dominate long-term |

---

## PRE-FLIGHT DATA CHECK (Both Stages)
Before any pipeline run: verify `training_unified_gold.jsonl` and DPO files are readable and record counts are non-zero.
```bash
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl
wc -l /root/sn66-ninja/training_data/*dpo*.jsonl | tail -1
```
If any file is empty or missing → STOP and investigate before proceeding.

---

## STAGE 1 — DATA-INFORMED PROMPT PIPELINE (CURRENT)

### Data Assets Available
| Dataset | Location | Records | Use |
|---------|----------|---------|-----|
| Unified gold patches | Hetzner1: training_data/training_unified_gold.jsonl | 297,215 | Understand how models solve tasks |
| Unified gold (AnonServer) | AnonServer: training_data/training_unified_gold.jsonl | 327,180 | Larger set, more models |
| DPO pairs (full matrix) | training_data/full_matrix_dpo_pairs.jsonl | 30,632 | Judge preferences across all task types |
| DPO pairs (UPDATE tasks) | training_data/update_task_dpo_pairs.jsonl | 32,263 | What judge rewards for UPDATE (68% of all tasks) |
| DPO pairs (reference) | training_data/reference_dpo_pairs.jsonl | 7,530 | Reference patch vs model — ground truth |
| DPO pairs (self-play) | training_data/self_play_dpo_pairs.jsonl | 2,848 | M2.7 vs itself, judge rationale |
| Live duel DPO (today) | training_data/dpo/2026-05-18.jsonl | 776 | Real competition duels |
| King history | training_data/king_history/ | 21 kings | All past kings' patterns |
| SFT records | training_data/sft/ | 873 | Live duel SFT training pairs |
| Harness v6 | validator_harness_v6.py | 1,842L | Local gate testing |
| R2 task dataset | hf_dataset_cache.jsonl | 9,122 tasks | Gate test pool (identical to live validator) |

### STEP-BY-STEP PIPELINE (James directive 2026-05-18)

---

#### PRE-STEP: King Sync (MANDATORY before every pipeline run)
```bash
cd /root/sn66-ninja && git fetch --all
git show <latest-commit>:agent.py > king_agent.py
wc -l king_agent.py   # Verify line count changed
```
Check: `curl -s https://ninja66.ai/dashboard.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['current_king']['commit_sha'][:16])"`

---

#### STEP 1a — PR/Source Check (Opus 4.7, ~10min)
**Task:** Check unarbos/ninja for any new merges since last pipeline run. Extract changes to validate.py, harness, scoring formula.
**Input:** `git log origin/main --oneline -20` + `git diff HEAD..origin/main -- validate.py`
**Output:** `research/PR_CHANGES_SN66_vNEXT.md`
**Question to answer:** Did scoring formula, judge model, or task distribution change?

---

#### STEP 1b — King Code Analysis (Opus 4.7, ~15min)
**Task:** Deep-study king_agent.py. Extract:
- SYSTEM_PROMPT full text + length
- MAX_STEPS, MAX_COMMANDS_PER_RESPONSE
- Multi-shot refinement logic (any candidate generation + selection)
- Dynamic per-turn injections
- Language-specific rules
- What the king does for UPDATE vs BUGFIX vs FEATURE vs REFACTOR tasks
**Input:** `/root/sn66-ninja/king_agent.py` only
**Output:** `research/KING_ANALYSIS_SN66_vNEXT.md`

---

#### STEP 1c — Scoring Mechanism Validation (Opus 4.7, ~10min)
**Task:** Verify current scoring formula from live harness. Confirm judge model = gpt-5.4, win_margin=3, scoring = 0.5×cursor_sim + 0.5×llm_judge.
**Input:** `/root/sn66-ninja/validator_harness_v6.py` (search for JUDGE_MODEL, _DIFF_JUDGE_WEIGHT, win_margin)
**Output:** `research/SCORING_FORMULA_SN66_vNEXT.md`
**Critical:** Any change here invalidates all previous gate results.

---

#### STEP 1d — Live Duel API Pull (automated, ~5min)
**Task:** Fetch all duel data for our active hotkeys from dashboard.json and compute our actual WR in live competition.
```bash
python3 -c "
import json
with open('/tmp/dashboard_sn66.json') as f: d = json.load(f)
# Find our duels by hotkey prefix
our_hotkeys = ['5FecE3QZ', '5Dqabiz8']
for duel in d['duels']:
    if any(duel.get('challenger_hotkey','').startswith(h) for h in our_hotkeys):
        print(duel)
"
```
**Output:** `research/LIVE_DUEL_STATE_SN66_vNEXT.md`

---

#### STEP 1e — Harness + Task Selection (local, ~10min)
**Task:** Ensure harness v6 is up to date. Select 50 diverse tasks for gate test covering UPDATE/FEATURE/BUGFIX/REFACTOR in proportion matching live distribution (68/19/7/6%).
```bash
python3 validator_harness_v6.py --list-tasks 100 --seed 42
```
**Output:** Gate test task list saved to `research/GATE_TASKS_SN66_vNEXT.txt`

---

#### STEP 2a — DPO Pair Deep Dive (Opus 4.7, ~20min)
**Task:** Analyze 500 DPO pairs, specifically:
- 300 UPDATE pairs from `update_task_dpo_pairs.jsonl`
- 100 FEATURE pairs from `full_matrix_dpo_pairs.jsonl`  
- 100 BUGFIX pairs from `full_matrix_dpo_pairs.jsonl`

**For each type, extract:** What does gpt-5.4 reward vs penalize? Give 5 concrete examples per task type.

**Key questions to answer:**
- For UPDATE: does judge care more about completeness or surgical precision?
- For FEATURE: does judge reward end-to-end wiring or targeted implementation?
- For BUGFIX: does judge care about addressing root cause or fixing symptoms?
- What specific phrases/patterns appear in chosen (winning) rationale but not rejected?

**Input:** First 300 lines of `training_data/update_task_dpo_pairs.jsonl` + first 200 lines of `training_data/full_matrix_dpo_pairs.jsonl`
**Output:** `research/DPO_INTEL_SN66_vNEXT.md`

---

#### STEP 2b — M2.7 Gold Pattern Analysis (Opus 4.7, ~15min)
**Task:** Analyze 1000 M2.7 gold patches from `gold_patches/gold_patches_minimax_minimax-m2_7.jsonl`.

**Extract:**
- Average patch size (lines changed) by task type
- Files changed per task
- Does M2.7 tend to under-edit or over-edit?
- What patterns does M2.7 use successfully? What does it miss?
- How does M2.7's output compare to the reference patch?

**Why:** In live competition, M2.7 generates our patches. Our agent's SYSTEM_PROMPT must compensate for M2.7's blind spots.

**Input:** First 100 records from `training_data/gold_patches/gold_patches_minimax_minimax-m2_7.jsonl`
**Output:** `research/M27_PATTERNS_SN66_vNEXT.md`

---

#### STEP 3 — Full Analysis + Debate (Opus 4.7 → Opus 4.7, ~30min)
**Task A (Opus):** Synthesize all research outputs into a single decision doc:
- King strengths/weaknesses → what our agent must match or beat
- M2.7 patterns → what SYSTEM_PROMPT must explicitly override
- gpt-5.4 rewards → what behaviors to emphasize per task type
- Top 5 changes for next version, with expected WR impact

**Input:** All `research/*_SN66_vNEXT.md` files
**Output:** `research/ROOT_CAUSE_SN66_vNEXT.md`

**Task B (second Opus — debate):** Challenge every finding in ROOT_CAUSE with data:
- Is this supported by the DPO data?
- Does this contradict any known forbidden patterns?
- What's the WR risk of each proposed change?
**Output:** `research/DEBATE_ROOT_CAUSE_SN66_vNEXT.md`

---

#### STEP 4 — Build Next Version (Opus 4.7, ~30min)
**Task:** Read ROOT_CAUSE + DEBATE + king_agent.py + agent_cl_gpt_v54.py → build next version.

**Mandatory rules for the build:**
- Start from v54 as base (best at 52.1%)
- Match king's budget: MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25
- Add multi-shot refinement if it doesn't regress UPDATE performance
- Apply language-specific completeness rules from king
- Implement UPDATE-specific functional connectivity requirement
- Keep: COMPLETENESS BEATS MINIMALISM + asymmetry (under-edit costs more)
- NEVER add: "never delete or remove existing functions/components" pattern
- NEVER remove the COMPLETENESS asymmetry statement

**Input:** `research/ROOT_CAUSE_SN66_vNEXT.md` + `research/DEBATE_ROOT_CAUSE_SN66_vNEXT.md` + king_agent.py + agent_cl_gpt_v54.py
**Output:** `agent_cl_gpt_vNEXT.py` (named with actual version number)

**Audit (second Opus):** Audit the new version for:
- Forbidden patterns (check PIPELINE_CONTEXT_vNEXT.md forbidden list)
- Budget settings (verify MAX_STEPS=50, MAX_COMMANDS=25)
- COMPLETENESS asymmetry present
- No "never delete" pattern

**Output:** `research/AUDIT_SN66_vNEXT.md`

**Debate (second Opus):** Challenge every audit finding with data.
**Output:** `research/DEBATE_AUDIT_SN66_vNEXT.md`

---

#### STEP 5 — Submission Checklist Alignment
Before gate test, verify all items:
```
[ ] MAX_STEPS=50 (matches king)
[ ] MAX_COMMANDS_PER_RESPONSE=25 (matches king)
[ ] COMPLETENESS BEATS MINIMALISM present
[ ] Under-editing asymmetry present  
[ ] Language-specific completeness rules present
[ ] "Never delete" pattern NOT present
[ ] UPDATE functional connectivity rule present
[ ] No hardcoded API keys, endpoints, or wallet references
[ ] solve() function signature unchanged
[ ] File is syntactically valid Python
```
```bash
python3 -c "import agent_cl_gpt_vNEXT; print('syntax OK')"
```

---

#### STEP 6 — Gate Test (tmux, report to James)
```bash
# ALWAYS in tmux
tmux new-session -d -s sn66_vnext_gate50
tmux send-keys -t sn66_vnext_gate50 "cd /root/sn66-ninja && python3 validator_harness_v6.py --challenger agent_cl_gpt_vNEXT.py --king king_agent.py --tasks 50 --seed 42 --parallel 3 --timeout 300 > /tmp/vnext_gate_50.log 2>&1" Enter

# Monitor
tmux attach -t sn66_vnext_gate50
# Or: tail -f /tmp/vnext_gate_50.log
```

**Threshold: ≥60% decisive WR on 50 tasks**

**If PASS (≥60%):**
→ Report full results to James → ask for explicit submission approval → submit

**If FAIL (<60%):**
→ Send James the gate results with breakdown by task type
→ Ask James to restart pipeline from Step 3 (Analysis) with new insights
→ Document failure analysis in `research/GATE_FAIL_SN66_vNEXT.md`

---

## STAGE 2 — DEDICATED FINE-TUNED M2.7 PIPELINE

### Trigger Conditions
- T68-S2 DGX Spark arrives and NVLink bridge set up (242GB unified RAM)
- All gold + DPO data collection complete (target: 9,122 tasks × all models)
- Stage 1 has produced ≥3 submitted versions with live duel results

**Fallback:** If fine-tuning fails or M2.7 judge simulation unreliable → return to Stage 1 pipeline immediately and notify James.

---

### The Three Roles of the Dedicated Fine-Tuned M2.7

| Role | What it does | Replaces |
|------|-------------|---------|
| **🛠️ Role 1 — Patch Generator** | Generates winning patches natively for any SN66 task. Trained on 297K+ gold examples from 20+ models. Knows exactly what gpt-5.4 rewards. | External API calls (OR/Chutes, ~$0.30/task) |
| **⚖️ Role 2 — Judge Simulator** | Predicts gpt-5.4's decision for any patch pair (ours vs king). Trained on 86K+ DPO pairs with full judge rationale. Returns predicted winner + confidence. | Running real gpt-5.4 judge (~$0.10/duel) |
| **🔬 Role 3 — Offline Dev Tool** | Powers rapid iteration: Opus 4.7 writes improved SYSTEM_PROMPT → M2.7 generates patches → M2.7 simulates judge → score instantly. Full build-test cycle at near-$0. | 50-task gate test (~$15-30/run) |

**Net result:** 50-100 build-test cycles per day vs 1-2 today. Self-improving flywheel.

---

### Training Data (collected by Final Unified Collector, running 24/7)

| Dataset | Location | Records | Trains Role |
|---------|----------|---------|-------------|
| Unified gold patches | training_unified_gold.jsonl | 297K+ | Role 1 — SFT phase |
| DPO full matrix | full_matrix_dpo_pairs.jsonl | 30K+ | Roles 1+2 — DPO phase |
| UPDATE task DPO | update_task_dpo_pairs.jsonl | 32K+ | Role 1 — UPDATE specialization |
| Reference DPO | reference_dpo_pairs.jsonl | 7.5K | Role 2 — ground truth alignment |
| Self-play DPO | self_play_dpo_pairs.jsonl | 2.8K | Role 2 — preference refinement |
| Live duel SFT | sft/ (daily, growing) | 800+ | Roles 1+2 — real competition signal |
| King history | training_data/king_history/ | 21 kings | Role 1 — "what wins" patterns |

### Fine-Tune Config
- **Base:** MiniMax-M2.7-base (NVFP4, ~115GB — already on T68-S1 at /home/t68/models/minimax-m2.7-base/)
- **Method:** QLoRA (LoRA rank 64, alpha 128, targets: q/k/v/o projections)
- **Hardware:** T68-S1 + T68-S2 NVLinked = 242GB unified RAM, SGLang TP=2
- **Phase 1 — SFT:** (issue + repo_context) → winning_patch using 297K gold records
- **Phase 2 — DPO:** (issue, chosen_patch, rejected_patch, judge_rationale) → preference alignment
- **Deployment:** LiteLLM proxy port 4000, model alias `t68-sn66-m27`

---

### Stage 2 Pipeline Steps

#### PRE-STEP: King Sync (same as Stage 1 — mandatory)

---

#### STEP 1 — Task Sampling (automated, 5min)
**M2.7 role:** None.
Select 50 diverse tasks from R2 dataset matching live distribution (68% UPDATE, 19% FEATURE, 7% API, 6% BUGFIX).

---

#### STEP 2 — Patch Generation (M2.7 Role 1, ~30min, $0)
Run fine-tuned M2.7 offline (SGLang on T68-S1+S2) against all 50 tasks.
Generate **3 candidate patches per task** at temperatures 0.7 / 1.0 / 1.3.
```bash
python3 run_m27_candidates.py --tasks gate_tasks.txt --candidates 3 --model t68-sn66-m27
```
Output: 150 candidate patches

---

#### STEP 3 — Judge Simulation + Best Pick (M2.7 Role 2, ~10min, $0)
Fine-tuned M2.7 scores each candidate vs king — simulates gpt-5.4 decision.
Selects highest-scoring candidate per task. Returns predicted WR estimate.
```bash
python3 simulate_judge.py --candidates candidates.jsonl --king king_agent.py --judge t68-sn66-m27-judge
```
Output: best_patches.jsonl + predicted_wr.txt

---

#### STEP 4 — Rapid Iteration (M2.7 Roles 1+2 + Opus 4.7, multiple cycles)
If predicted WR < 60%: Opus 4.7 reads failure analysis → improves SYSTEM_PROMPT → back to Step 2.
Each cycle: ~40min, near $0. Run until predicted WR ≥ 60%.
**Max 10 cycles per run. If threshold unmet after 10 cycles → escalate to James.**
**This is where Stage 2 dominates Stage 1:** 5-10 improvement cycles in one afternoon.

---

#### STEP 5 — Opus Audit + Debate (when predicted WR ≥ 60%)
Same as Stage 1 — two Opus sessions audit then debate the final version.
Output: `research/AUDIT_STAGE2_vNEXT.md` + `research/DEBATE_STAGE2_vNEXT.md`

---

#### STEP 6 — Real Gate Test (50 tasks, tmux, final confirmation)
Run actual harness v6 with fine-tuned M2.7 as execution model vs current king.
Threshold: ≥60% decisive WR. Always in tmux.
```bash
tmux new-session -d -s sn66_stage2_gate
python3 validator_harness_v6.py --challenger agent_vNEXT.py --king king_agent.py \
  --tasks 50 --seed 42 --model t68-sn66-m27 --parallel 5 --timeout 300
```

---

#### STEP 7 — Report to James + Submit (approval required, same rule as Stage 1)

---

### Data Flywheel (why Stage 2 wins long-term)

```
Live duel → gpt-5.4 judges → new DPO pair → nightly fine-tune update →
better M2.7 → better patch → win duel → repeat
```

Every win generates training data that makes the next version stronger.
Competitor agents without this loop fall behind exponentially.

Final Unified Collector (PM2: `sn66-final-unified-collector`, Hetzner1) feeds this flywheel 24/7.

---

## STANDING RULES (ALL PIPELINE RUNS)

### Forbidden (never add to SYSTEM_PROMPT)
❌ "Never delete or remove existing functions/components unless explicitly requested"
❌ "Preserve existing code structure" without completeness asymmetry
❌ Minimalism framing WITHOUT the asymmetry counterbalance

### Required (always verify before gate test)
✅ COMPLETENESS BEATS MINIMALISM (explicit header)
✅ "Under-editing costs MORE than over-editing" (explicit)
✅ MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25 (match king)
✅ Language-specific completeness rules
✅ King sync BEFORE every pipeline task

### Submission Rules
- Gate threshold: ≥60% decisive WR (50 tasks, seed 42)
- Gate ALWAYS in tmux session
- NEVER submit without James's explicit approval
- Always register new hotkey before submit (τ0.41-1.64 burn)
- Private repo: ProjectNobi/sn66-miners only

---

*Last updated: 2026-05-18 | By: T68Bot*

---

## SUBMISSION LOG — 2026-05-18

### ProjectNobi-v62 (James approved)
| Field | v62ci | v62b (fixed original) |
|-------|-------|----------------------|
| Hotkey | sn66-pnobi-v62 | sn66-pnobi-v62b |
| UID | 200 | 136 |
| CI Score | 78 | 74 |
| Strategy | King-base + UPDATE WIRING | Original v62 + 4 minimum fixes |
| Submission ID | 5CciPvx7G9VnCQ6j-e1a9728ff6f98ae0 | 5G6JxJQviH6w8i2F-270cb163a1a11b80 |
| Status | LIVE | LIVE |

### Key CI Lesson (L-SN66-CI-SUBMISSION-1)
James directive: always try minimum changes to original version first.
Never change base strategy. Only fix what the CI judge specifically flags.
See MINER_SUBMISSION_CHECKLIST.md Pre-Submission Fix Checklist for exact fixes.


---

## v63 — Built 2026-05-18 (James approved for pipeline)

### Description
**agent_cl_gpt_v63.py** (4608 lines) — King-base + UPDATE TASK WIRING + all new king features

Built from: king_agent.py (UID 64, d24c9d3, 4596L) — current king at time of build

### What v63 Has vs v62ci
| Feature | v62ci | v63 |
|---------|-------|-----|
| Base | king (d24c9d3) | king (d24c9d3) |
| UPDATE TASK WIRING rule | ✅ | ✅ |
| Ship blocker detection | ✅ (king's) | ✅ (king's) |
| Multi-shot with duel scoring | ✅ (king's) | ✅ (king's) |
| Smart test commands | ✅ (king's) | ✅ (king's) |
| Companion test timeout scaling | ✅ (king's) | ✅ (king's) |

v63 = v62ci (both are king-base + UPDATE WIRING). Functionally identical.
Confirmed: syntax OK, 50 steps, all king guards intact.

### Gate Test
- Running: 50 tasks, seed 42, 50 steps, vs king UID 64 (d24c9d3)
- Log: /tmp/v63_gate_50steps.log
- Threshold: ≥60% decisive WR → report to James → submit

### Files
- Agent: /root/sn66-ninja/agent_cl_gpt_v63.py (4608L)
- King ref: /root/sn66-ninja/king_agent.py (4596L, d24c9d3)
- Harness: /root/sn66-ninja/validator_harness_v6.py

---

## 🏆 OFFICIAL BASELINE — v62 (James directive 2026-05-18)

**v62 is the current T68 SN66 baseline for all miners.**

| File | Description | CI Score | Gate WR |
|------|-------------|----------|---------|
| `agent_v62_submit.py` | Original v62 (raw) | 62 CI (fails) | ~56-68% vs king UID 64 |
| `agent_cl_gpt_v62_fix.py` | v62 + 4 min CI fixes | **74 CI ✅** | same |
| `baseline_sn66_v62.py` | Copy of original v62 | — | — |
| `baseline_sn66_v62_ci.py` | Copy of CI-passing v62 | **74 CI ✅** | — |

### v62 Key Strengths (preserve in all future versions)
- MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25 (matches king)
- COMPLETENESS BEATS MINIMALISM + under-editing asymmetry
- UPDATE TASK WIRING RULE (functional connectivity)
- Language-specific completeness rules
- CASCADE tracking (callers, importers, tests)

### v62 Submission Status (LIVE)
- sn66-pnobi-v62 (UID 200): king-base + UPDATE WIRING, CI 78 ✅
- sn66-pnobi-v62b (UID 136): v62 + 4 min fixes, CI 74 ✅

### Starting point for all future versions
All future agent versions build from v62 (CI-passing) as base.
Restore all king guard rails before submitting (see Pre-Submission Fix Checklist in MINER_SUBMISSION_CHECKLIST.md).

---

## SESSION LESSONS — 2026-05-18

### Pipeline Execution Rules (hardened from today)

**L-SN66-NO-PIPELINE-SHORTCUT-1** — Never shortcut any pipeline step. If build fails → retry the step, never substitute with a copy.

**L-SN66-CI-VBASE-MATTERS-1** — King-base → 74-78 CI on first attempt. v54-base → stuck at 62 after 9 attempts. Default to king-base for all CI submissions.

**L-SN66-CI-INCREMENTAL-FIXES-FAIL-1** — Stop after 3 failed CI attempts on same base. Switch to king-base approach.

**L-SN66-CI-ACCEPTED-CHECK-1** — Always verify acceptance via API after submission. Console parsing can miss accepted submissions.

**L-SN66-CI-HOTKEY-SPENT-1** — Each hotkey is consumed after first submission attempt (pass OR fail). Budget τ1.5+ before starting CI campaign.

**L-SN66-GATE-REGRESSION-1** — Gate WR peaks early, regresses as harder tasks come in. Report WR only after ≥40/50 tasks complete.

**L-SN66-AGENT-USERNAME-1** — Use `--agent-username ProjectNobi-vXX` flag for on-chain naming showing on dashboard.

### CI Submission Strategy (proven reliable)
1. Build from king_agent.py as base
2. Add ONE targeted improvement (e.g. UPDATE TASK WIRING rule)
3. Apply pre-submission fix checklist (4 items in MINER_SUBMISSION_CHECKLIST.md)
4. Submit with `--agent-username ProjectNobi-vXX`
5. Verify acceptance via API (not console)

---

## ProjectNobi-v62b Submission — 2026-05-19

### Hotkey Details
| Field | Value |
|-------|-------|
| Hotkey name | sn66-rsvd-2 |
| UID | 255 |
| SS58 | 5E9zKVRpZCreZmzBYVawHwznLssPasyVu9DJyEP3gw1nFtaS |
| Agent username | **ProjectNobi-v62b** |
| Submission ID | 5E9zKVRpZCreZmzB-e1a9728ff6f98ae0 |
| CI Score | **78/100 ✅ PASSED** |
| File | agent_cl_gpt_v62ci.py (king d24c9d3 + UPDATE WIRING only) |
| Status | LIVE — queued for duel |

### What v62b Is
- Base: current king_agent.py (commit d24c9d3, 4595L)
- Addition: UPDATE TASK WIRING RULE (functional connectivity for UPDATE/ENHANCE tasks)
- **One surgical change = CI 78** (proven approach per L-SN66-CI-VBASE-MATTERS-1)

### Previous v62b Duel (UID 136)
- Result: 26W/23L — net +3, **1 round short of dethroning** (win_margin=3 requires strictly >+3)
- James note: validator margin rule prevented win despite strong performance

### CI Lesson Reinforced
- agent_cl_gpt_v62_fix.py (v62+4fixes): CI 62 ❌ — king changed, too much divergence now
- agent_cl_gpt_v62ci.py (king+WIRING): CI 78 ✅ — minimum change = highest CI
- Rule: L-SN66-CI-VBASE-MATTERS-1 always applies on fresh king

### Spent Hotkeys (2026-05-19)
| Hotkey | UID | CI | Outcome |
|--------|-----|----|---------|
| sn66-rsvd-1 | 157 | 62 ❌ | v62_fix submitted — rejected, hotkey spent |
| sn66-rsvd-2 | 255 | 78 ✅ | v62ci as ProjectNobi-v62b — LIVE |

---

## v65 Gate Failure Analysis (2026-05-19)

### Final Gate Result: FAIL ❌
- WR: 37.5% decisive (15W/25L/1T) — 50 tasks, seed 42
- Threshold: ≥60% required

### Breakdown by Task Type
| Type | WR | W/L | Status |
|------|-----|-----|--------|
| BUGFIX | **12%** | 2W/14L | 🔴 Root cause of failure |
| FEATURE | 45% | 5W/6L | ⚠️ Below par |
| UPDATE | 60% | 3W/2L | ✅ UPDATE WIRING working |
| REFACTOR | 100% | 1W/0L | ✅ |

### Root Cause
- v62 base underperforms vs king on BUGFIX under LLM-only scoring (Claude Sonnet 4.6)
- BUGFIX = 73% of today's live competition tasks
- The 5 micro-changes (hail-mary, anti-churn, correctness, security, error handling) did NOT fix BUGFIX

### James directive (2026-05-19)
Restart pipeline with **v62b (agent_cl_gpt_v62_fix.py) as baseline**. BUGFIX is the primary target.


---

## SN66 Validator Roadmap Intel (James directive 2026-05-19)

### Phase 1 — NOW (live since PR#1598, 2026-05-19)
- Single LLM judge: `anthropic/claude-sonnet-4.6`
- Scoring: 100% LLM-only
- Training target: `sonnet_winner` field in DPO pairs

### Phase 2 — NEXT WEEK (upgrade coming)
- Dual LLM judges: `anthropic/claude-sonnet-4.6` + `openai/gpt-5.4`
- Scoring: consensus of both judges
- Training target: `consensus=True` DPO pairs (both judges agree)
- **Our advantage:** dual-judge DPO data already collected with both fields

### Data Assets (already ready for Phase 2)
| Field | Use |
|-------|-----|
| `sonnet_winner` | Ground truth for Phase 1 |
| `gpt54_winner` | Ground truth for old scoring |
| `consensus=True` | **Ground truth for Phase 2** — win both judges |
| `sonnet_rationale` | What Sonnet rewards (Phase 1+2) |
| `judge_rationale` | What GPT-5.4 rewards (Phase 2) |

### Strategy
- v66 targets Sonnet 4.6 (Phase 1) — gate test running now
- When Phase 2 arrives: focus on `consensus` pairs — agents must satisfy BOTH judges
- Pre-train on consensus pairs NOW to be ready before Phase 2 launch

---

## v66 — Built 2026-05-19 (James approved — v62b baseline, BUGFIX focus)

### Description
**agent_cl_gpt_v66.py** (4,658 lines, +14 vs v62b) — v62b base + 5 BUGFIX-targeted surgical additions

Built from: agent_cl_gpt_v62_fix.py (original v62b, 4,644L) — per James directive

### Why v66 (motivation)
- v65 gate failed: 37.5% WR — BUGFIX 12% (2W/14L), catastrophic
- New judge: Claude Sonnet 4.6 (LLM-only scoring since PR#1598 2026-05-19)
- BUGFIX = 73% of live competition tasks
- Root cause: v62b lacked BUGFIX-specific root-cause tracing guidance

### 5 Changes Applied (minimum surgical, v62b base intact)
| # | Change | Location | Purpose |
|---|--------|----------|---------|
| 1 | BUGFIX SCOPE RULE — root-cause owner framing | After THOROUGHNESS section | Fix symptom-spraying pattern |
| 2 | ROOT CAUSE examples + anti-patterns (cache, CLI, delegation wrapper, result masking) | After existing parser example ~line 3033 | Concrete examples stop M2.7 from abstracting |
| 3 | Strategy line task-type branching | Plan template ~line 2996 | BUG FIX = smallest root-cause, UPDATE/FEATURE = complete wiring |
| 4 | Caller contract + error type sentences | ROOT CAUSE RULE section ~line 3041 | 80% of BUGFIX rejections = incomplete cascade fix |
| 5 | Sonnet 4.6 tie-break signal | SCOPE DISCIPLINE section ~line 3131 | Architectural fitness wins 17.5% of Sonnet disagreements |

### Preserved (untouched from v62b)
- UPDATE TASK WIRING RULE ✅
- COMPLETENESS BEATS MINIMALISM ✅
- Under-editing asymmetry ✅
- "Never delete" pattern: absent ✅

### Gate Test
- Running: 50 tasks, seed 42, parallel 3, timeout 300s
- Judge: claude-sonnet-4.6 (matches live validator)
- Log: /tmp/v66_gate_50.log | tmux: sn66_v66_gate50
- Threshold: ≥60% decisive WR → report to James → submit
- Expected: BUGFIX 12% → 35-40%, Overall 37.5% → 48-53%

### Validator Phase Intel (2026-05-19)
- Phase 1 (NOW): Single judge claude-sonnet-4.6, LLM-only scoring
- Phase 2 (next week): Dual judges sonnet-4.6 + gpt-5.4 → use consensus=True DPO pairs

### Files
- Agent: /root/sn66-ninja/agent_cl_gpt_v66.py
- Research: research/ROOT_CAUSE_SN66_v66.md, research/DEBATE_ROOT_CAUSE_SN66_v66.md
- King ref: /root/sn66-ninja/king_agent.py (d24c9d3)

---

## 🔑 HOTKEY REUSE RULE (James directive 2026-05-19 — VERIFIED)

**L-SN66-CI-HOTKEY-SPENT-1 CORRECTED:**

| CI Result | Score | Status | Hotkey State |
|-----------|-------|--------|-------------|
| CI passed | ≥ 72 | "passed" | **SPENT** — agent live in duel queue |
| CI failed | ≤ 62 | "failed" | **REUSABLE** — agent rejected, hotkey free |

**Rule:** After CI 62 "failed" → DO NOT register a new hotkey. Fix the agent and resubmit to the SAME hotkey.

**How to fix CI 62:** Switch to king-base + minimum additions (L-SN66-CI-VBASE-MATTERS-1). Never try v62b base again for CI submissions.

---

## 🏛️ KING-BASE MANDATORY RULE — ALL FUTURE VERSIONS (James directive 2026-05-19)

**L-SN66-KING-BASE-MANDATORY-1**

> **ALL submitted agents MUST use the current king's source code as base.**
> King-base + minimum targeted improvements = correct architecture.

### Why the CI system enforces this
The SN66 private submission CI judge compares your agent diff against the current king. Divergence = lower score:
- Minimal diff from king → CI 78 ✅
- Medium divergence (v62b + changes) → CI 72 ✅ (borderline)  
- High divergence (v62b + more changes) → CI 62 ❌ REJECTED

### Build pipeline (MANDATORY going forward)
```
Step 0: bash scripts/sync_king.sh        ← ALWAYS first
Step 1: cp king_agent.py vNext_ci.py     ← king as base
Step 2: Add targeted improvements         ← minimum additions
Step 3: Submit vNext_ci.py               ← guaranteed CI ≥ 72
```

### v62b role (clarified)
- v62b-based versions → gate testing only (local research, WR measurement)
- NOT for submission to the live competition
- The gate test results from v62b still give valid signal about which improvements work

### Also applies to: ALL future versions (v68, v69, etc.)

---

## 🏛️ L-SN66-KING-BASE-MANDATORY-1 — CORRECTION (James directive 2026-05-19, FINAL)

**CORRECTED RULE (replaces previous version above):**

> **ALWAYS start from the current latest king's source code as the initial baseline for the ENTIRE pipeline — research, gate testing, AND live submission.**

This applies to EVERY step in the SN66-Pipeline-Formal process:
- Step 1b (King code analysis) → read king, extract patterns
- Step 4 (Build) → `cp king_agent.py agent_vNext.py` as the FIRST action
- Gate testing → test your king-base version against the king
- CI submission → submit the king-base version

### There is NO "two-track" system
The previous note about "v62b for research, king for submission" is WRONG and REVOKED.

**ONE rule: king source = starting point for everything.**

Build = king + targeted improvements (minimum additions)
Gate test the king-based version
Submit the king-based version

### Why this is stronger than just "for CI"
1. The king is the current best agent — it already has everything working
2. Starting from king means you inherit all its strengths by default
3. You only need to add what the king lacks (your targeted improvements)
4. This minimizes risk of regression and maximizes CI score

### Pipeline Step 0 (mandatory, before Step 1a):
```bash
cd /root/sn66-ninja && bash scripts/sync_king.sh
wc -l king_agent.py  # Confirm king is updated
```
THEN: `cp king_agent.py agent_cl_gpt_vNext.py`

**This is the law for all future SN66 pipeline runs.**
