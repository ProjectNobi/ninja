# FINAL SN66 INTEL PIPELINE PROCESS
*Single source of truth — T68Bot | Consolidated 2026-05-19*
*Sources: DATA_INTEL_PIPELINE_SN66.md + SN66_PIPELINE_FORMAL.md*

---

## ⚡ QUICK REFERENCE

| Item | Value |
|------|-------|
| **King sync** | `cd /root/sn66-ninja && bash scripts/sync_king.sh && wc -l king_agent.py` |
| **Gate command** | `python3 -u validator_harness_v6.py --challenger AGENT.py --king king_agent.py --tasks 50 --seed 42 --parallel 3 --timeout 600` |
| **Gate threshold** | ≥60% decisive WR on 50 tasks |
| **Gate session** | ALWAYS in tmux — `tmux new-session -d -s sn66_vNEXT_gate` |
| **Judge (Phase 1)** | `anthropic/claude-sonnet-4.6` — 100% LLM, no cursor_sim weight |
| **Win margin** | challenger_wins - challenger_losses > 3 |
| **Base rule** | `cp king_agent.py agent_vNext.py` — ALWAYS start from king |
| **PR #40** | https://github.com/unarbos/tau/pull/40 (blind judge fix) |
| **Blind judge** | FIX 8 in harness v6 (commit 81289db) — labels "PATCH A/B" only |
| **Timeout** | --timeout 600 (king is multishot — never use 300s) |
| **CI submission** | King-base + minimum additions → CI 78. Any divergence lowers CI. |
| **Auto-submit** | NEVER — always get James's explicit approval first |
| **Private repo** | ProjectNobi/sn66-miners only |

### Key Thresholds (current)
- Gate: ≥60% WR (50 tasks, seed 42)
- CI: ≥72 to pass. King-base → 78. High divergence → 62 ❌
- Win margin: net > +3 rounds to dethrone king

### Critical Lessons (fast lookup)
- **L-SN66-KING-BASE-MANDATORY-1**: ALWAYS start from current `king_agent.py` — no exceptions
- **L-SN66-BLIND-JUDGE-1**: Blind A/B labels in harness (FIX 8) — never reveal king/challenger
- **L-SN66-NEVER-DELETE-RULE-1**: Never add "never delete existing functions" to SYSTEM_PROMPT
- **L-SN66-CI-VBASE-MATTERS-1**: King-base → CI 78; v62b divergence → CI 62
- **L-SN66-CI-HOTKEY-SPENT-1**: CI failed (≤62) = hotkey reusable; CI passed (≥72) = hotkey spent

### #1 Rule for UPDATE Tasks
> **UPDATE WIRING RULE** — A feature that exists but is never called = 0 points.
> Wire new code into: event handlers, state management, data flows, call sites.
> NEVER strip this rule. Stripping it: UPDATE WR 57% → 14% (v68 catastrophe).

### Forbidden Patterns (never add)
❌ "Never delete or remove existing functions/components unless explicitly requested"
❌ Pure minimalism framing WITHOUT the completeness asymmetry counterbalance

### Required Patterns (always verify)
✅ `COMPLETENESS BEATS MINIMALISM` (explicit header)
✅ "Under-editing costs MORE than over-editing" (explicit statement)
✅ UPDATE TASK WIRING RULE (functional connectivity)
✅ MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25 (match king)
✅ Language-specific completeness rules

---

## 🏛️ STAGE 1: DATA-INFORMED PIPELINE (NOW — Opus 4.7 builds)

*Use when: T68-S2 NVLink not yet set up. Opus 4.7 builds SYSTEM_PROMPT informed by DPO analysis.*

---

### Pre-Step: King Sync (MANDATORY before anything else)

```bash
cd /root/sn66-ninja && bash scripts/sync_king.sh
wc -l king_agent.py   # confirm line count changed if king updated
curl -s https://ninja66.ai/dashboard.json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d['current_king']['commit_sha'][:16])"
```

Also check PR status on unarbos/ninja. If a new PR was merged since last run, **restart from Step 1**.

Then immediately copy king as base for new version:
```bash
cp king_agent.py agent_cl_gpt_vNext.py
```

---

### Step 1: Source Intelligence (King + Scoring + PRs + Live Data)

**1a — PR/Source Check** (Opus 4.7, ~10min)
Check unarbos/ninja for any new merges since last pipeline run.
```bash
git log origin/main --oneline -20
git diff HEAD..origin/main -- validate.py
```
- Did scoring formula, judge model, or task distribution change?
- Did PR #40 (blind judge fix: https://github.com/unarbos/tau/pull/40) merge? If so: re-run all recent gate results.
- **Output:** `research/PR_CHANGES_SN66_vNEXT.md`

**1b — King Code Analysis** (Opus 4.7, ~15min)
Deep-study `king_agent.py`. Extract:
- SYSTEM_PROMPT full text + length
- MAX_STEPS, MAX_COMMANDS_PER_RESPONSE
- Multi-shot refinement logic (candidate generation + selection)
- Dynamic per-turn injections
- Language-specific completeness rules
- Task-type handling: UPDATE vs BUGFIX vs FEATURE vs REFACTOR
- **Output:** `research/KING_ANALYSIS_SN66_vNEXT.md`

**1c — King as Baseline (MANDATORY)**
> `cp king_agent.py agent_cl_gpt_vNext.py` — This is the law. No other base is acceptable.
> Confirmed: king-base → CI 78 on first attempt. v62b/other base → CI 62 ❌ after 9 attempts.

**1d — Scoring Mechanism Validation** (Opus 4.7, ~10min)
Verify current scoring formula from harness v6. Confirm: **single or dual LLM judges**, judge model(s), win_margin, formula.
```bash
grep -n "JUDGE_MODEL\|JUDGE_MODEL_2\|_DIFF_JUDGE_WEIGHT\|win_margin\|cursor_sim\|dual\|consensus" validator_harness_v6.py
```
- **Phase 1 (NOW):** Single judge — `anthropic/claude-sonnet-4.6`, win_margin=3, cursor_sim=telemetry only (PR#1598)
- **Phase 2 (next week):** Dual judges — `anthropic/claude-sonnet-4.6` + `openai/gpt-5.4`, consensus wins
- Check PR merges to confirm which phase is active before every pipeline run
- Any change to judge model or formula **invalidates all previous gate results**
- **Output:** `research/SCORING_FORMULA_SN66_vNEXT.md`

**1e — Live Duel API Pull** (~10min)
Pull ALL duels against the current King. Compute actual WR + loss patterns per task type.
```bash
curl -s https://ninja66.ai/dashboard.json > /tmp/dashboard_sn66.json
python3 -c "
import json
with open('/tmp/dashboard_sn66.json') as f: d = json.load(f)
# All our active hotkeys — update each pipeline run
our_hotkeys = ['5FecE3QZ', '5Dqabiz8', '5Dqabiz', '5FecE3']  # expand as needed
wins, losses = 0, 0
task_losses = {}
for duel in d.get('duels', []):
    chk = duel.get('challenger_hotkey','')
    if any(chk.startswith(h) for h in our_hotkeys):
        result = duel.get('result','')
        ttype = duel.get('task_type','unknown')
        if result == 'challenger_wins': wins += 1
        else:
            losses += 1
            task_losses[ttype] = task_losses.get(ttype,0) + 1
print(f'WR: {wins}/{wins+losses} ({100*wins//max(1,wins+losses)}%)')
print('Losses by task type:', sorted(task_losses.items(), key=lambda x: -x[1]))
"
```
Analyze: WR vs current king, which task types we lose most, round score patterns.
- **Output:** `research/LIVE_DUEL_STATE_SN66_vNEXT.md`

**1f — Harness + Task Selection** (~10min)
Update harness v6 if needed (after any PR merge). Select **100 diverse tasks** matching live duel distribution.

> ⚠️ **TASK POOL ROTATION — CRITICAL (James directive 2026-05-19)**
> Task pool rotates at 10 tasks/hour starting this week.
> Fixed task set testing is NO LONGER VALID.
>
> **3 key rules:**
> 1. Before every gate test, check live duel task type distribution from `dashboard.json` duel history.
> 2. Ensure **100-task** gate sample matches current BUGFIX/UPDATE/FEATURE/API ratios in live duels.
> 3. HuggingFace corpus (oldest 10 tasks/hour uploaded) = free training data — download weekly.

```bash
# Check current task type distribution in 100-task pool
python3 validator_harness_v6.py --list-tasks 100 --seed 42

# Use varied seeds each pipeline run to avoid overfitting
# e.g. seed 42, 137, 271 in rotation
# Gate command (always 100 tasks, always --timeout 600):
# python3 -u validator_harness_v6.py --challenger agent_vNext.py --king king_agent.py --tasks 100 --seed 42 --parallel 3 --timeout 600
```
- **Output:** `research/GATE_TASKS_SN66_vNEXT.txt`

---

### Step 2: Data Intelligence (Intel A–E)

**Pre-flight check:**
```bash
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl
wc -l /root/sn66-ninja/training_data/*dpo*.jsonl | tail -1
```
If any file is empty or missing → STOP and investigate.

---

#### Intel A: Task-Type Winning vs Losing Phrases (Opus 4.7, ~15min)

Extract 3-gram phrases from `sonnet_rationale` in consensus DPO pairs per task type.

```python
from collections import Counter
import json, re

def extract_phrases(text, n=3):
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

win_phrases = Counter()
lose_phrases = Counter()
with open('training_data/full_matrix_dpo_pairs.jsonl') as f:
    for line in f:
        r = json.loads(line)
        if not r.get('consensus'): continue
        rat = r.get('sonnet_rationale', r.get('judge_rationale',''))
        winner = r.get('sonnet_winner') or r.get('gpt54_winner')
        phrases = extract_phrases(rat[:300], n=3)
        if winner == 'A':
            win_phrases.update(phrases)
        else:
            lose_phrases.update(phrases)
```

**Verified findings (as of 2026-05-19):**

| Task | Top WIN signal | Top LOSE signal |
|------|----------------|-----------------|
| UPDATE | "patch more directly", "aligned with issue", "more directly addresses" | "appears incomplete truncated", "patch appears incomplete" |
| BUGFIX | "patch directly addresses", "aligned with issue", "patch closer issue" | "appears incomplete truncated", "patch better matches but" |
| FEATURE | "patch much closer", "acceptance criteria patch", "which aligns with" | "appears incomplete truncated", "only partially addresses" |

**→ SYSTEM_PROMPT rule**: "Your patch must directly address every stated acceptance criterion. Incomplete patches that trail off or partially implement features lose decisively. The judge explicitly checks for 'incompleteness' and 'truncation'."

---

#### Intel B: M2.7 Natural Success Patterns (Opus 4.7, ~15min)

Analyze M2.7 gold patches + reference DPO pairs (9,189 records).

```bash
# Source
training_data/gold_patches/gold_patches_minimax_minimax-m2_7.jsonl
training_data/reference_dpo_pairs.jsonl
```

**Verified findings (from 9,189 reference DPO pairs):**

| Type | M2.7 wins | M2.7 loses | Win rate |
|------|-----------|-----------|----------|
| UPDATE | 759 | 3,816 | 16.6% |
| FEATURE | 483 | 2,284 | 17.4% |
| BUGFIX | 163 | 721 | 18.4% |
| API | 153 | 810 | 15.9% |

- M2.7 wins most on **FEATURE tasks with substantial multi-file implementations**
- M2.7 line count when winning: median 368 vs losing: 362 — **LINE COUNT BARELY MATTERS**
- Root cause: M2.7 wins when it attempts the right architectural approach; loses when it stops short of full integration

**→ SYSTEM_PROMPT rule**: "M2.7 strength = recognizing the RIGHT code to change. Weakness = stopping before full wiring. Never stop at 'beginning to implement' — always complete the integration."

**For v72+:** Also analyze `gold_patches_minimax_minimax-m2_7.jsonl` — extract:
- Average patch size (lines changed) by task type
- Does M2.7 tend to under-edit or over-edit?
- What patterns does M2.7 use successfully?

---

#### Intel C: UPDATE Task Wiring Patterns (Opus 4.7, ~15min)

Extract wiring examples from 5,385 consensus pairs with explicit wiring language.

```python
with open('training_data/update_task_dpo_pairs.jsonl') as f:
    for line in f:
        r = json.loads(line)
        rat = r.get('judge_rationale', r.get('sonnet_rationale', '')).lower()
        if r.get('consensus') and \
           any(w in rat for w in ['wire', 'lifecycle', 'hook', 'state management']):
            # r['chosen_patch'] = example of winning wired implementation
            pass
```

**Concrete wiring patterns from rationale analysis (verified):**
1. "wires them into the chat store lifecycle: saving on message updates" — data persistence hooks
2. "wires a teacher-mode toggle through the app state and passes that mode into both TheorySection and TestCard" — state prop-drilling
3. "adding server-side developer token generation with origin aggregation" — backend+frontend bridge
4. "not only adds X but also wires them into the lifecycle" — the meta-pattern

**→ SYSTEM_PROMPT rule**: "A feature that exists but is never called = 0 points. Wire new code into: event handlers, state management, data flows, call sites."

**Data**: 62,589 records in `update_task_dpo_pairs.jsonl`; 5,385 (8.6%) have explicit wiring language — ground-truth examples for UPDATE SYSTEM_PROMPT improvements.

---

#### Intel D: Models That Beat M2.7 Most (Opus 4.7, ~10min)

| Model | Times beats M2.7 | Avg score gap |
|-------|-----------------|---------------|
| o3 | 2,808 | 0.392 |
| gpt-5.5 | 1,947 | 0.389 |
| claude-opus-4.7 | 1,501 | 0.383 |
| gemini-3.1-pro | 910 | 0.351 |
| qwen3.5-397b-tee | 643 | 0.301 |

**→ SYSTEM_PROMPT insight**: Models with highest gap (o3, gpt-5.5, opus-4.7) win by deep reasoning before coding.
They READ MORE CAREFULLY first, then implement completely.
→ Rule: "Before writing ANY code, run: `find . -type f | grep relevant_extension | head 50`. Read all files the issue references. Only then start editing."

---

#### Intel E: Data Quality Map (Which Intel to Trust Most)

| Task | Consensus % | Median gap | Trust level | Priority |
|------|------------|-----------|-------------|----------|
| BUGFIX | 79.3% | 0.350 | ⭐⭐⭐ HIGHEST | 3rd (currently ~52% WR — OK) |
| FEATURE | 78.9% | 0.340 | ⭐⭐⭐ HIGHEST | 2nd |
| UPDATE | 78.8% | 0.330 | ⭐⭐⭐ HIGH | **1st — 14% WR crisis** |
| API | 78.5% | 0.320 | ⭐⭐ HIGH | 4th |

All task types have excellent signal quality (consensus >78%, gap >0.3). **Trust ALL equally.** Prioritize UPDATE for SYSTEM_PROMPT improvements until WR normalizes.

---

#### DPO Pair Deep Dive Protocol (for each pipeline run)

Analyze 500 DPO pairs per run:
- 300 UPDATE pairs from `update_task_dpo_pairs.jsonl`
- 100 FEATURE pairs from `full_matrix_dpo_pairs.jsonl`
- 100 BUGFIX pairs from `full_matrix_dpo_pairs.jsonl`

For each type, extract (using `sonnet_winner` + `sonnet_rationale` — Phase 1 ground truth):
- For UPDATE: does judge care more about completeness or surgical precision?
- For FEATURE: does judge reward end-to-end wiring or targeted implementation?
- For BUGFIX: does judge care about root cause or symptom fixes?
- For Phase 2 readiness: where do `sonnet_winner` and `gpt54_winner` diverge?

**Output:** `research/DPO_INTEL_SN66_vNEXT.md`

---

### Step 3: Synthesis + Debate

**Task A (Opus 4.7):** Synthesize all Step 1 + Step 2 outputs into a single decision doc:
- King strengths/weaknesses → what our agent must match or beat
- M2.7 patterns → what SYSTEM_PROMPT must explicitly override or compensate for
- Judge rewards → what behaviors to emphasize per task type
- Top 5 changes for next version, with expected WR impact

**Input:** All `research/*_SN66_vNEXT.md` files from Steps 1 + 2
**Output:** `research/ROOT_CAUSE_SN66_vNEXT.md`

**Task B (second Opus — debate):** Challenge every finding in ROOT_CAUSE with data:
- Is this supported by the DPO data?
- Does this contradict any known forbidden patterns?
- What's the WR risk of each proposed change?
- Does this risk regression on currently strong task types?

**Output:** `research/DEBATE_ROOT_CAUSE_SN66_vNEXT.md`

---

### Step 4: Build + Audit + Debate

**Build (Opus 4.7, ~30min):**
Read ROOT_CAUSE + DEBATE + king_agent.py → build next version.

**Mandatory build rules:**
- Start from king_agent.py as base (L-SN66-KING-BASE-MANDATORY-1 — the law)
- Match king's budget: MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25
- Apply language-specific completeness rules from king
- Implement UPDATE-specific functional connectivity requirement
- Keep: COMPLETENESS BEATS MINIMALISM + asymmetry (under-edit costs more)
- ❌ NEVER add: "never delete or remove existing functions/components" pattern
- ❌ NEVER remove: the COMPLETENESS asymmetry statement
- ❌ NEVER remove: UPDATE TASK WIRING RULE

**Output:** `agent_cl_gpt_vNEXT.py`

**Audit (second Opus):** Check for:
- Forbidden patterns (L-SN66-NEVER-DELETE-RULE-1, L-SN66-MINIMALISM-FRAMING-1)
- Budget settings: MAX_STEPS=50, MAX_COMMANDS=25
- COMPLETENESS asymmetry present
- UPDATE WIRING RULE present
- No hardcoded API keys, endpoints, or wallet references
- solve() function signature unchanged

**Output:** `research/AUDIT_SN66_vNEXT.md`

**Debate (second Opus):** Challenge every audit finding with data.
**Output:** `research/DEBATE_AUDIT_SN66_vNEXT.md`

---

### Step 5: Checklist Alignment

Before gate test, verify all items:
```
[ ] MAX_STEPS=50 (matches king)
[ ] MAX_COMMANDS_PER_RESPONSE=25 (matches king)
[ ] COMPLETENESS BEATS MINIMALISM present
[ ] Under-editing asymmetry present
[ ] Language-specific completeness rules present
[ ] "Never delete" pattern NOT present
[ ] UPDATE functional connectivity rule (WIRING) present
[ ] No hardcoded API keys, endpoints, or wallet references
[ ] solve() function signature unchanged
[ ] File is syntactically valid Python
```

```bash
python3 -c "import agent_cl_gpt_vNEXT; print('syntax OK')"
```

See also: `MINER_SUBMISSION_CHECKLIST.md` Pre-Submission Fix Checklist (4 CI items).

---

### Step 6: Gate Test → Approval → Submit

**ALWAYS in tmux:**
```bash
tmux new-session -d -s sn66_vNEXT_gate
tmux send-keys -t sn66_vNEXT_gate \
  "cd /root/sn66-ninja && python3 -u validator_harness_v6.py \
  --challenger agent_cl_gpt_vNEXT.py --king king_agent.py \
  --tasks 50 --seed 42 --parallel 3 --timeout 600 > /tmp/vNEXT_gate_50.log 2>&1" Enter

# Monitor
tail -f /tmp/vNEXT_gate_50.log
```

**Threshold: ≥60% decisive WR on 50 tasks**

**If PASS (≥60%):**
→ Report full results to James (breakdown by task type)
→ Ask for explicit submission approval
→ Submit only after James says yes

**If FAIL (<60%):**
→ Send James the gate results with breakdown by task type
→ Document failure analysis in `research/GATE_FAIL_SN66_vNEXT.md`
→ Ask James to restart pipeline from Step 3 with new insights

**After PR #40 merges:** Recalibrate threshold. Unbiased gate may warrant re-evaluating the 60% bar. Monitor PR #40 merge status at https://github.com/unarbos/tau/pull/40.

---

## 🚀 STAGE 2: DEDICATED M2.7 PIPELINE (SOON — after T68-S2 NVLink)

### Trigger Conditions
- T68-S2 DGX Spark arrives and NVLink bridge configured (NVIDIA playbook: connect-two-sparks)
- All gold + DPO data collection complete (target: 9,122 tasks × all models)
- Stage 1 has produced ≥3 submitted versions with live duel results
- QLoRA fine-tune of MiniMax M2.7 on SN66 gold (364K+) + DPO (65K+) complete
- **Fallback:** If M2.7 judge simulation unreliable → return to Stage 1 immediately, notify James

---

### The Three Roles of Dedicated Fine-Tuned M2.7

| Role | What It Does | Replaces |
|------|-------------|---------|
| 🛠️ **Patch Generator** | Generates winning patches natively for any SN66 task. Trained on 364K+ gold examples from 20+ models. Knows exactly what Sonnet 4.6 + GPT-5.4 rewards. | External API calls (~$0.30/task) |
| ⚖️ **Judge Simulator** | Predicts judge decision for any patch pair (ours vs king). Trained on 86K+ DPO pairs with full judge rationale. Returns predicted winner + confidence. | Real judge calls (~$0.10/duel) |
| 🔬 **Offline Dev Tool** | Powers rapid iteration: Opus 4.7 writes improved SYSTEM_PROMPT → M2.7 generates patches → M2.7 simulates judge → score instantly. Full build-test cycle at near-$0. | 50-task gate test (~$15-30/run) |

**Net result:** 50-100 build-test cycles per day vs 1-2 today. Self-improving flywheel.

---

### Fine-Tuning Data Pipeline

#### FT-1: Patch Generator SFT

**Data:** `training_unified_gold.jsonl` — 366,125 records
**Format:** `{instruction → output(reference_patch)}` — supervised
**Filter:** All records (100% non-empty)
**Dedup:** By unique `(task_id, source)` pair — ~200-250K unique after dedup
**Training objective:** Teach M2.7 to generate reference-quality patches

```python
seen = set()
training = []
with open('training_data/training_unified_gold.jsonl') as f:
    for line in f:
        r = json.loads(line)
        key = (r['task_id'], r.get('source',''))
        if key not in seen and r.get('output') and r.get('instruction'):
            seen.add(key)
            training.append({
                'instruction': r['instruction'],
                'output': r['output'],
                'task_type': r.get('archetype','')
            })
```

#### FT-2: DPO Alignment (Judge-Preference)

**Data:** `full_matrix_dpo_pairs.jsonl` + `reference_dpo_pairs.jsonl` + `update_task_dpo_pairs.jsonl`
**Filter:** `consensus=True AND abs(score_diff) > 0.2`
**Size:** ~65,051 high-quality pairs (full_matrix alone)
**Format:** `{instruction, chosen_patch, rejected_patch}` — DPO
**Training objective:** Align M2.7 patches with Sonnet 4.6 judge preferences
**Phase 2 upgrade:** Use `consensus=True` (both judges agree) for dual-judge alignment

```python
dpo_training = []
with open('training_data/full_matrix_dpo_pairs.jsonl') as f:
    for line in f:
        r = json.loads(line)
        if r.get('consensus') and abs(r.get('score_diff',0)) > 0.2:
            dpo_training.append({
                'instruction': r['instruction'],
                'chosen': r['chosen_patch'],
                'rejected': r['rejected_patch'],
                'task_type': r['task_type'],
                'rationale': r.get('sonnet_rationale', r.get('judge_rationale','')),
            })
# Expected: ~65K from full_matrix + ~5K from reference + ~20K from update_task
```

#### FT-3: Judge Simulator SFT

**Data:** `judge_training_sft.jsonl` — **>176K consensus pairs** (204,292 total, 86.4% consensus)
**Filter:** `consensus=True` — 176,587 pairs
**Format:** `(task, patch_A, patch_B) → (score_A, score_B, winner, rationale)` — SFT
**Training objective:** Teach M2.7 to score patches like BOTH judges simultaneously — **one training run covers Phase 1 and Phase 2**.

> **✅ SINGLE TRAINING RUN STRATEGY (James directive 2026-05-19)**
> Train ONLY on `consensus=True` pairs (176K) — where Sonnet 4.6 AND GPT-5.4 already agree.
> - Phase 1 (Sonnet single judge): consensus pairs = valid Sonnet 4.6 signal ✅
> - Phase 2 (dual judges): consensus pairs = exactly what wins ✅
> - No retraining needed when validator upgrades to Phase 2
> - The ~14% disagreement cases are excluded — they are noisy/contradictory signal, excluding them is a benefit
>
> **Filter:** `consensus=True AND sonnet_winner==gpt54_winner` (strongest signal — both judges explicitly agree on winner)

```python
judge_training = []
with open('training_data/judge_training_sft.jsonl') as f:
    for line in f:
        r = json.loads(line)
        if r.get('consensus'):
            judge_training.append({
                'input': r['input'],
                'output': r['output'],
                'task_type': r.get('task_type',''),
                'winner': r.get('winner',''),
            })
# Size: 176,587 pairs
```

---

### Fine-Tune Hardware Config

- **Base model:** MiniMax-M2.7-base (NVFP4, ~115GB — at `/home/t68/models/minimax-m2.7-base/` on T68-S1)
- **Method:** QLoRA (LoRA rank 64, alpha 128, targets: q/k/v/o projections)
- **Hardware:** T68-S1 + T68-S2 NVLinked = 242GB unified RAM, SGLang TP=2
- **Phase 1 — SFT:** (issue + repo_context) → winning_patch using 200-250K deduplicated gold records
- **Phase 2 — DPO:** (instruction, chosen, rejected, rationale) → preference alignment
- **Deployment:** LiteLLM proxy port 4000, model alias `t68-sn66-m27`

---

### Stage 2 Pipeline Steps

**Step 0 (same as Stage 1):** King sync → `cp king_agent.py agent_vNext.py` (MANDATORY)

**Step 1 — Task Sampling** (automated, 5min)
Select 50 diverse tasks matching live distribution (check `dashboard.json` for current ratios).
*Note: Task pool rotates 10 tasks/hour — use varied seeds, match live ratios.*

**Step 2 — Patch Generation** (M2.7 Role 1, ~30min, $0)
Run fine-tuned M2.7 offline against all 50 tasks.
Generate 3 candidate patches per task at temperatures 0.7 / 1.0 / 1.3.
```bash
python3 run_m27_candidates.py --tasks gate_tasks.txt --candidates 3 --model t68-sn66-m27
```

**Step 3 — Judge Simulation + Best Pick** (M2.7 Role 2, ~10min, $0)
Fine-tuned M2.7 scores each candidate vs king — simulates Sonnet 4.6 decision.
Selects highest-scoring candidate per task.
```bash
python3 simulate_judge.py --candidates candidates.jsonl --king king_agent.py --judge t68-sn66-m27-judge
```

**Step 4 — Rapid Iteration** (M2.7 Roles 1+2 + Opus 4.7, multiple cycles)
If predicted WR < 60%: Opus 4.7 reads failure analysis → improves SYSTEM_PROMPT → back to Step 2.
Each cycle: ~40min, near $0. Max 10 cycles. If unmet after 10 → escalate to James.

**Step 5 — Audit + Debate** (when predicted WR ≥ 60%)
Same as Stage 1 Step 4 audit/debate.
Output: `research/AUDIT_STAGE2_vNEXT.md` + `research/DEBATE_STAGE2_vNEXT.md`

**Step 6 — Real Gate Test** (50 tasks, tmux, final confirmation)
```bash
tmux new-session -d -s sn66_stage2_gate
python3 validator_harness_v6.py --challenger agent_vNEXT.py --king king_agent.py \
  --tasks 50 --seed 42 --model t68-sn66-m27 --parallel 5 --timeout 600
```
Threshold: ≥60% decisive WR. Always in tmux.

**Step 7 — Report to James + Submit** (same approval rule as Stage 1)

---

### Data Flywheel (why Stage 2 wins long-term)

```
Live duel → Sonnet 4.6 (+ GPT-5.4 in Phase 2) judges → new DPO pair →
nightly fine-tune update → better M2.7 → better patch → win duel → repeat
```

Every win generates training data that makes the next version stronger.
**Final Unified Collector** (PM2: `sn66-final-unified-collector`, Hetzner1) feeds this flywheel 24/7.

---

## 📊 DATA ASSETS — ARCHITECTURE (James directive 2026-05-19)

### 🏛️ Single Source of Truth: HETZNER1
> **Hetzner1 = primary training data server. ALL fine-tuning runs from Hetzner1 only.**
> AnonServer = backup + active data generation only. Never train from AnonServer directly.

**Sync architecture (automatic, every 2 hours):**
- `sync_gold_from_anonserver.sh` — gold_patches/ + training_unified_gold.jsonl → Hetzner1
- `sync_dpo_from_anonserver.sh` — all DPO pair files → Hetzner1 + runs migrate_dpo_to_unified.py
- Both crons: `0 */2 * * *` on Hetzner1
- AnonServer files: NEVER deleted. Permanent backup.

**When T68-S2 arrives:** Run fine-tuning directly from Hetzner1's `/root/sn66-ninja/training_data/`.

---

## 📊 DATA ASSETS (Current Counts — verified 2026-05-19)

| Dataset | Location (Hetzner1) | Records | Use |
|---------|---------------------|---------|-----|
| Unified gold patches | `training_data/training_unified_gold.jsonl` | **366,125** | FT-1 SFT + M2.7 pattern analysis |
| DPO pairs (full matrix) | `training_data/full_matrix_dpo_pairs.jsonl` | **95,657** | FT-2 DPO + Intel A/D/E |
| DPO pairs (UPDATE tasks) | `training_data/update_task_dpo_pairs.jsonl` | **62,589** | FT-2 UPDATE specialization + Intel C |
| DPO pairs (reference) | `training_data/reference_dpo_pairs.jsonl` | **9,189** | Intel B — M2.7 vs reference |
| Judge simulator SFT | `training_data/judge_training_sft.jsonl` | **204,292** | FT-3 judge simulator |
| Self-play DPO | `training_data/self_play_dpo_pairs.jsonl` | **6,547** | M2.7 temp variation pairs |
| Synthetic DPO | `training_data/synthetic_dpo_pairs.jsonl` | **38,103** | Synthetic comparisons |
| High-quality DPO subset | filter: consensus=True + score_diff>0.2 | **65,051** | FT-2 gold subset |
| Judge SFT consensus | filter: consensus=True | **176,587** | FT-3 gold subset |
| Live duel DPO | `training_data/dpo/` (daily, growing) | growing | Real competition signal |
| King history | `training_data/king_history/` | 21 kings | "what wins" patterns |
| Harness v6 | `validator_harness_v6.py` | 1,842L | Local gate testing |

### DPO Task Type Distribution (full_matrix)
- UPDATE: 49.8% (47,572 pairs) — our weakest task type (14% WR crisis in v68/v65)
- FEATURE: 30.0% (28,646 pairs)
- API: 10.6% (10,101 pairs)
- BUGFIX: 9.8% (9,338 pairs)

### Data Quality Summary
- Consensus rate: **78.5–79.3%** across all task types (very strong signal)
- Score diff: median **0.320–0.350** (clear, decisive margins)
- UPDATE wiring pattern in rationale: **5,385 / 62,589** (8.6%) — ground-truth examples

### What's ABUNDANT (no need to collect more)
- ✅ General gold patches: 366K across 40+ models — sufficient
- ✅ DPO pairs (general): 65K high-quality consensus pairs — sufficient
- ✅ Judge SFT: 176K consensus records — excellent
- ✅ UPDATE task pairs: 62K — sufficient for fine-tuning

### What's SCARCE (still collecting)
- ⚠️ **BUGFIX DPO pairs**: Only 9,338 (10% of full_matrix) — under-represented vs live duels (~40% BUGFIX). Need 2× more.
- ⚠️ **Task pool rotation data**: New HuggingFace corpus (10 tasks/hour) — download weekly
- ⚠️ **Live duel DPO**: Growing daily — highest value (actual competition tasks)

---

## ⚖️ SCORING MECHANISM (Phase 1 Current + Phase 2 Coming)

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

### Phase 2 — COMING NEXT WEEK

| Field | Value |
|-------|-------|
| **Judges** | `anthropic/claude-sonnet-4.6` + `openai/gpt-5.4` (dual) |
| **Scoring** | Consensus of both judges |
| **Win condition** | Must win or tie against BOTH judges |

**Our data advantage:** All DPO pairs already contain BOTH judge fields:
- `sonnet_winner` / `sonnet_rationale` — Phase 1 ground truth
- `gpt54_winner` / `gpt54_score_chosen` / `gpt54_score_rejected` — Phase 2 ground truth
- `consensus` — True when both judges agree = highest quality training signal

**Training target for Phase 2:** `consensus=True` DPO pairs (both judges agree)

**When Phase 2 launches:**
1. Filter DPO training data to `consensus=True` pairs only
2. Rebuild agent version targeting dual-judge consensus wins
3. Gate test with both judges active in harness

---

### Harness v6 Judge Config (keep in sync with live validator)
```
JUDGE_MODEL: anthropic/claude-sonnet-4.6   # matches live validator
JUDGE_MODEL_FALLBACK: moonshotai/kimi-k2.6
Scoring: c_combined = llm_score_challenger  # cursor_sim telemetry only
Blind judge: FIX 8 (commit 81289db) — labels "PATCH A" / "PATCH B" only
```
**Rule:** After any PR merge to unarbos/ninja affecting scoring → verify harness matches, update if needed.

---

### PR #40 — Official Blind Judge Fix

**PR:** https://github.com/unarbos/tau/pull/40
**Status:** Open (2026-05-19) — SN66 team actively merging
**Lesson:** `L-SN66-BLIND-JUDGE-1` (in AGENTS.md)

**What it does:**
- Blinds the validator LLM judge: model sees **`candidate_a`** and **`candidate_b`** instead of **`king`** and **`challenger`**
- Adds deterministic per-round candidate mapping before prompt construction
- Maps neutral judge output back to `king_score` / `challenger_score` for backward compatibility
- Extends injection detection to catch neutral-label attacks
- Updates all tests for blinded label shape, parser role mapping, fallback behavior
- Relaunch safe: no validator state schema changes

**Impact on us:**
- Our v6 local harness already implements this fix (FIX 8, commit 81289db, 2026-05-19)
- Our gate results are ALREADY unbiased
- Once PR #40 merges: live duels also unbiased → true agent strength reflected on-chain
- Expected: agents underscored due to king-label bias will score higher after merge

**Action:** Monitor PR #40 merge. After merge, recalibrate gate threshold.

---

## 🚫 FORBIDDEN PATTERNS (Never Add to SYSTEM_PROMPT)

These patterns LOOK safe but cause catastrophic regressions. Verified from v59 and v65 data.

### ❌ PATTERN 1: "Never Delete" Rule
Any rule resembling:
- "Never delete or remove existing functions/components unless the task explicitly requests it"
- "Preserve existing code structure"
- "Do not remove existing implementations"
- "Only add, never remove"

**Why:** REFACTOR tasks REQUIRE deletion. UPDATE tasks frequently require removing outdated implementations.
v59 regression: this single rule → REFACTOR 60% → 0%, UPDATE 40% → 27%.
**Lesson: L-SN66-NEVER-DELETE-RULE-1**

### ❌ PATTERN 2: Pure Minimalism Without Asymmetry
Any framing with ONLY:
- "smallest correct change, no more"
- "patch a careful senior maintainer would submit: complete, precise, no more"

Without the COMPLETENESS ASYMMETRY counterbalance, this kills REFACTOR.

---

## 📋 STANDING RULES (ALL PIPELINE RUNS)

### Build Rules (hardened from experience)
- **L-SN66-KING-BASE-MANDATORY-1**: ALWAYS start from current `king_agent.py` as base — no exceptions, not just for CI, but for gate testing and research too
- **L-SN66-NO-PIPELINE-SHORTCUT-1**: Never shortcut any pipeline step. If build fails → retry the step, never substitute with a copy.
- **L-SN66-CI-VBASE-MATTERS-1**: King-base → CI 78 on first attempt. Any other base → CI 62 ❌ after 9 attempts.
- **L-SN66-CI-INCREMENTAL-FIXES-FAIL-1**: Stop after 3 failed CI attempts on same base. Switch to king-base approach.
- **L-SN66-GATE-REGRESSION-1**: Gate WR peaks early, regresses as harder tasks come in. Report WR only after ≥40/50 tasks complete.

### Required in Every Agent Version
✅ COMPLETENESS BEATS MINIMALISM (explicit header)
✅ "Under-editing costs MORE than over-editing" (explicit statement)
✅ UPDATE TASK WIRING RULE (functional connectivity — the #1 rule)
✅ MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25 (match king)
✅ Language-specific completeness rules (from king)
✅ CASCADE tracking (callers, importers, tests)

### Submission Rules
- Gate threshold: ≥60% decisive WR (50 tasks, seed 42, --timeout 600)
- Gate ALWAYS in tmux session
- NEVER submit without James's explicit approval (L-NO-AUTO-SUBMIT-1)
- Always verify acceptance via API after submission (not console)
- New hotkey for each submission (τ0.41-1.64 burn)
- Private repo: ProjectNobi/sn66-miners only
- Use `--agent-username ProjectNobi-vXX` for on-chain naming

### Hotkey Rules
- **CI failed (≤62):** Hotkey reusable — fix agent and resubmit to same hotkey
- **CI passed (≥72):** Hotkey spent — agent live in duel queue, need new hotkey next time
- Budget τ1.5+ before starting CI campaign

### Task Pool Rotation Rules (James directive 2026-05-19)
- Before every gate test: check live duel task type distribution from `dashboard.json`
- Ensure 50-task sample matches current live ratios (don't over-optimize to fixed R2 seed)
- Download HuggingFace corpus weekly (10 tasks/hour being uploaded with solutions)
- Vary `--seed` each pipeline run

---

## 🗒️ VERSION LOG (v62 → current)

### v62 — HISTORICAL BASELINE (2026-05-18)
| File | CI Score | Gate WR | Status |
|------|----------|---------|--------|
| `agent_v62_submit.py` | 62 ❌ (fails CI now) | ~56-68% vs king UID 64 | Historical only |
| `agent_cl_gpt_v62_fix.py` | 74 ✅ | same | Historical only |
| `agent_cl_gpt_v62ci.py` | 78 ✅ | — | King-base+UPDATE WIRING |

> ⚠️ **v62 as base is SUPERSEDED by L-SN66-KING-BASE-MANDATORY-1 (2026-05-19)**.
> All versions v68+ must use current `king_agent.py` as base. Not v62.

**v62 Key Strengths (preserved in all future versions):**
- MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25
- COMPLETENESS BEATS MINIMALISM + under-editing asymmetry
- UPDATE TASK WIRING RULE (functional connectivity)
- Language-specific completeness rules
- CASCADE tracking (callers, importers, tests)

**v62 Submissions (LIVE):**
- sn66-pnobi-v62 (UID 200): king-base + UPDATE WIRING, CI 78 ✅
- sn66-pnobi-v62b (UID 136): v62 + 4 min CI fixes, CI 74 ✅

### v63 — 2026-05-18
- Base: king d24c9d3 (4596L) + UPDATE TASK WIRING (functionally identical to v62ci)
- Files: agent_cl_gpt_v63.py (4608L)
- Gate: 50 tasks, seed 42, threshold ≥60%

### v65 — Gate FAIL 2026-05-19
- Gate: **37.5% WR** (15W/25L/1T) — FAIL ❌
- BUGFIX: 12% (2W/14L) — catastrophic root cause
- FEATURE: 45% | UPDATE: 60% ✅ | REFACTOR: 100% ✅
- Root cause: v62 base underperforms vs king on BUGFIX under LLM-only scoring
- 5 micro-changes (hail-mary, anti-churn, correctness, security, error handling) did NOT fix BUGFIX
- James directive: restart pipeline with v62b baseline, BUGFIX is primary target

### v62b Hotkey (ProjectNobi-v62b) — 2026-05-19
- Hotkey: sn66-rsvd-2 | UID 255
- CI Score: 78 ✅ | File: agent_cl_gpt_v62ci.py (king d24c9d3 + UPDATE WIRING only)
- Previous v62b duel (UID 136): 26W/23L — net +3, **1 round short** of dethroning (win_margin requires strictly >+3)

### v66 — Built 2026-05-19 (James approved)
- Base: agent_cl_gpt_v62_fix.py (v62b, 4,644L) — per James directive (superseded by king-base rule for v68+)
- Purpose: BUGFIX focus (v65 catastrophe: BUGFIX 12%)
- 5 surgical additions targeting BUGFIX root-cause tracing
- Gate: running | Log: /tmp/v66_gate_50.log | tmux: sn66_v66_gate50
- Threshold: ≥60%

### v71 — CURRENT BEST CHALLENGER (2026-05-19)
- Base: king d24c9d3 (4595L) + 33 lines
- Changes: UPDATE WIRING RULE restored + Sonnet 4.6 rubric (40/30/20/10) + task-type strategy
- Root cause fixed: UPDATE WIRING RULE was stripped in v68 → UPDATE WR 57% → 14% → restored
- Gate: `v71gate` tmux | 100 tasks seed 42 --timeout 600 | threshold ≥70%
- Key lesson: ALWAYS use --timeout 600 (king is multishot — never use 300s)
- Key lesson: UPDATE WIRING RULE = the #1 rule — never strip it again

---

*Consolidated from DATA_INTEL_PIPELINE_SN66.md + SN66_PIPELINE_FORMAL.md*
*By: T68Bot Opus 4.7 subagent | 2026-05-19*
*Previous files preserved for historical reference.*
