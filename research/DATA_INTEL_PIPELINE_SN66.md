# SN66 Data Intelligence Pipeline
*T68Bot direct analysis | 2026-05-19 | Formal pipeline step 2a-2b*

---

## Section 1: Data Quality Audit (Verified)

| Dataset | Records | Non-empty % | Key signal |
|---------|---------|------------|------------|
| training_unified_gold.jsonl | 366,125 | 100% | 40+ model patch patterns |
| full_matrix_dpo_pairs.jsonl | 95,657 | 100% | Judge preferences, 80.2% consensus |
| reference_dpo_pairs.jsonl | 9,189 | 100% | M2.7 vs reference (M2.7 wins 12.5%) |
| update_task_dpo_pairs.jsonl | 62,589 | 100% | UPDATE patterns (75.6% non-M2.7 wins) |
| judge_training_sft.jsonl | 204,292 | 100% | Judge SFT (86.4% consensus) |
| self_play_dpo_pairs.jsonl | 6,547 | 100% | M2.7 temp variation pairs |
| synthetic_dpo_pairs.jsonl | 38,103 | 100% | Synthetic comparisons |

### Task type distribution (full_matrix DPO):
- UPDATE: 49.8% (47,572 pairs) — our weakest task type (14% WR)
- FEATURE: 30.0% (28,646 pairs)
- API: 10.6% (10,101 pairs)
- BUGFIX: 9.8% (9,338 pairs)

### Data quality signal:
- Consensus rate: **78.5–79.3%** across all task types (very strong signal)
- Score diff: median **0.320–0.350** (clear, decisive margins — not borderline)
- High-quality pairs (consensus=True AND score_diff>0.2): **65,051 pairs** (FT-2 training set)
- Judge SFT consensus pairs: **176,587** of 204,292 (86.4%) — excellent for judge simulator

### UPDATE wiring pattern in rationale: 5,385/62,589 (8.6%)
These are the ground-truth wiring examples most valuable for v71–v73 SYSTEM_PROMPT work.

---

## Section 2: Intelligence Extraction Steps (Stage 1 — SYSTEM_PROMPT)

### Intel A: Task-type winning vs losing phrases

**Method:**
```python
from collections import Counter
import json, re

def extract_phrases(text, n=3):
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())
    return [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]

win_phrases = Counter()
lose_phrases = Counter()
with open('full_matrix_dpo_pairs.jsonl') as f:
    for line in f:
        r = json.loads(line)
        if not r.get('consensus'): continue
        rat = r.get('judge_rationale','')
        winner = r.get('sonnet_winner') or r.get('gpt54_winner')
        phrases = extract_phrases(rat[:300], n=3)
        if winner == 'A':  # A = chosen/winner
            win_phrases.update(phrases)
        else:
            lose_phrases.update(phrases)
```

**Findings (verified):**

| Task | Top WIN signal | Top LOSE signal |
|------|---------------|-----------------|
| UPDATE | "patch more directly", "aligned with issue", "more directly addresses" | "appears incomplete truncated", "patch appears incomplete" |
| BUGFIX | "patch directly addresses", "aligned with issue", "patch closer issue" | "appears incomplete truncated", "patch better matches but" |
| FEATURE | "patch much closer", "acceptance criteria patch", "which aligns with" | "appears incomplete truncated", "only partially addresses" |

**→ SYSTEM_PROMPT rule**: "Your patch must directly address every stated acceptance criterion. Incomplete patches that trail off or partially implement features lose decisively. The judge explicitly checks for 'incompleteness' and 'truncation'."

---

### Intel B: M2.7 natural success patterns

**Findings (from 9,189 reference DPO pairs):**

| Type | M2.7 wins | M2.7 loses | Win rate |
|------|-----------|-----------|----------|
| UPDATE | 759 | 3,816 | 16.6% |
| FEATURE | 483 | 2,284 | 17.4% |
| BUGFIX | 163 | 721 | 18.4% |
| API | 153 | 810 | 15.9% |

- M2.7 wins MOST on **FEATURE tasks where it writes substantial multi-file implementations** (rationale: "at least touches the video panel and begins implementing issue-relevant changes... wiring Kling-specific payload fields")
- M2.7 **line count when winning: median 368** vs when losing: 362 — LINE COUNT BARELY MATTERS
- **Root cause**: M2.7 wins when it attempts the right architectural approach; loses when it attempts the right area but stops short of full integration

**→ SYSTEM_PROMPT rule**: "M2.7 strength = recognizing the RIGHT code to change. Weakness = stopping before full wiring. Never stop at 'beginning to implement' — always complete the integration."

---

### Intel C: UPDATE task wiring patterns

**Method:**
```python
# Extract wiring examples from winning UPDATE patches
with open('update_task_dpo_pairs.jsonl') as f:
    for line in f:
        r = json.loads(line)
        rat = r.get('judge_rationale','').lower()
        if r.get('gpt54_winner') == r.get('chosen_label') and \
           any(w in rat for w in ['wire','lifecycle','hook','state management']):
            # r['chosen_patch'] = example of winning wired implementation
```

**5,385 wiring pairs available** with explicit wiring language in rationale.

**Concrete wiring patterns from rationale analysis:**
1. **"wires them into the chat store lifecycle: saving on message updates"** — data persistence hooks
2. **"wires a teacher-mode toggle through the app state and passes that mode into both TheorySection and TestCard"** — state prop-drilling
3. **"adding server-side developer token generation with origin aggregation"** — backend+frontend bridge
4. **"not only adds X but also wires them into the lifecycle"** — the meta-pattern

**→ SYSTEM_PROMPT rule** (already in v71): "A feature that exists but is never called = 0 points. Wire new code into: event handlers, state management, data flows, call sites."

---

### Intel D: Models that beat M2.7 most (what to learn from)

| Model | Times beats M2.7 | Avg score gap |
|-------|-----------------|---------------|
| o3 | 2,808 | 0.392 |
| gpt-5.5 | 1,947 | 0.389 |
| claude-opus-4.7 | 1,501 | 0.383 |
| gemini-3.1-pro | 910 | 0.351 |
| qwen3.5-397b-tee | 643 | 0.301 |

**→ Action**: Extract the *structural differences* in o3/gpt-5.5/opus-4.7 winning patches vs M2.7 losing patches. These represent the aspirational target for M2.7 fine-tuning.

**→ SYSTEM_PROMPT insight**: The models with highest gap (o3, gpt-5.5, opus-4.7) are known for deep reasoning before coding. They READ MORE CAREFULLY first, then implement completely. This maps to: "Read ALL affected files before writing ANY code."

---

### Intel E: Data quality map (which intel to trust most)

| Task | Consensus % | Median gap | Trust level | Priority |
|------|------------|-----------|-------------|----------|
| BUGFIX | 79.3% | 0.350 | ⭐⭐⭐ HIGHEST | 3rd (already OK at ~52%) |
| FEATURE | 78.9% | 0.340 | ⭐⭐⭐ HIGHEST | 2nd |
| UPDATE | 78.8% | 0.330 | ⭐⭐⭐ HIGH | **1st** (14% WR crisis) |
| API | 78.5% | 0.320 | ⭐⭐ HIGH | 4th |

All task types have excellent signal quality (consensus >78%, gap >0.3). Trust ALL of them equally.

---

## Section 3: Fine-Tuning Data Pipeline (Stage 2)

### FT-1: Patch Generator SFT

**Data**: `training_unified_gold.jsonl` — 366,125 records  
**Format**: `{instruction → output(reference_patch)}` — supervised  
**Filter**: All records (100% non-empty after current cleaning)  
**Dedup**: By unique `(task_id, source)` pair  
**Size after dedup**: ~200-250K unique (task_id, reference_patch) pairs  
**Training objective**: SFT — teach M2.7 to generate reference-quality patches

```python
# Build FT-1 training set
seen = set()
training = []
with open('training_unified_gold.jsonl') as f:
    for line in f:
        r = json.loads(line)
        key = (r['task_id'], r.get('source',''))
        if key not in seen and r.get('output') and r.get('instruction'):
            seen.add(key)
            training.append({
                'instruction': r['instruction'],
                'output': r['output'],      # reference patch
                'task_type': r.get('archetype','')
            })
```

---

### FT-2: DPO Alignment (Judge-Preference)

**Data**: `full_matrix_dpo_pairs.jsonl` + `reference_dpo_pairs.jsonl` + `update_task_dpo_pairs.jsonl`  
**Filter**: `consensus=True AND abs(score_diff) > 0.2`  
**Size**: **65,051 high-quality pairs** (full_matrix alone)  
**Format**: `{instruction, chosen_patch, rejected_patch}` — DPO  
**Training objective**: Align M2.7 patches with Sonnet 4.6 judge preferences

```python
# Build FT-2 DPO set
dpo_training = []
with open('full_matrix_dpo_pairs.jsonl') as f:
    for line in f:
        r = json.loads(line)
        if r.get('consensus') and abs(r.get('score_diff',0)) > 0.2:
            dpo_training.append({
                'instruction': r['instruction'],
                'chosen': r['chosen_patch'],
                'rejected': r['rejected_patch'],
                'task_type': r['task_type'],
                'rationale': r.get('judge_rationale',''),
            })
# Expected: ~65K from full_matrix + ~5K from reference + ~20K from update_task
```

---

### FT-3: Judge Simulator SFT

**Data**: `judge_training_sft.jsonl` — 204,292 records  
**Filter**: `consensus=True` (176,587 pairs — 86.4%)  
**Format**: `(task, patch_A, patch_B) → (score_A, score_B, winner, rationale)` — SFT  
**Training objective**: Teach M2.7 to score patches like Sonnet 4.6

```python
# Build FT-3 judge simulator set
judge_training = []
with open('judge_training_sft.jsonl') as f:
    for line in f:
        r = json.loads(line)
        if r.get('consensus'):
            judge_training.append({
                'input': r['input'],    # (task + patch_A + patch_B)
                'output': r['output'],  # (score_A, score_B, winner, reasoning)
                'task_type': r.get('task_type',''),
                'winner': r.get('winner',''),
            })
# Size: 176,587 pairs
```

---

## Section 4: Audit — What's Missing vs Abundant

### ABUNDANT (no need to collect more):
- ✅ General gold patches: 317K records across 42 models — more than enough
- ✅ DPO pairs (general): 65K high-quality consensus pairs — sufficient
- ✅ Judge SFT: 176K consensus records — very strong for judge simulator
- ✅ UPDATE task pairs: 62K — enough for fine-tuning UPDATE-specific behavior

### SCARCE (still collecting):
- ⚠️ **BUGFIX DPO pairs**: Only 9,338 (10% of full_matrix) — under-represented vs live duel distribution (~40% BUGFIX in duels). Need 2× more BUGFIX-specific pairs
- ⚠️ **M2.7 temperature variation**: 6,547 self-play pairs (Task 3) — still running. Need full 3,313 pairs
- ⚠️ **Task pool rotation data**: New HuggingFace corpus (10 tasks/hour starting this week) — will add rotating task coverage. Download weekly.
- ⚠️ **Live duel DPO**: 34,147 pairs from final collector — growing daily. These are the most valuable (actual competition tasks)

### Systematic biases:
1. **Task type imbalance**: UPDATE 49.8% vs BUGFIX 9.8% in DPO (but BUGFIX is 40%+ of live duels) → weight BUGFIX up in training
2. **Model imbalance**: 40+ models but o3/gpt-5.5/opus-4.7 are the top performers → their winning patches are the most valuable training signal
3. **Reference patch dominance**: M2.7 loses 87.5% vs reference → SFT on (instruction→reference) will pull M2.7 toward reference quality

### What would improve quality:
1. **Dual-judge labels on all pairs**: As GPT-5.4 comes online next week, re-label all existing pairs with dual consensus → `consensus_both=True` subset will be even stronger signal
2. **Task-type stratified sampling**: Ensure FT-2 DPO has equal representation of BUGFIX/UPDATE/FEATURE/API for balanced training
3. **Difficulty-weighted sampling**: Pairs with score_diff > 0.4 (very clear wins) are more valuable — oversample these

---

## Section 5: Priority Order (Stage 1 — Immediate SYSTEM_PROMPT Actions)

Ranked by **expected WR improvement × data evidence quality**:

### Priority 1 (DONE in v71): UPDATE WIRING RULE
- Evidence: 5,385 consensus pairs with explicit wiring language; UPDATE WR 14% → expected 50%+
- Action: DONE ✅ (v71 has UPDATE WIRING RULE restored)

### Priority 2 (DONE in v71): Sonnet 4.6 rubric update
- Evidence: Live validator uses 40/30/20/10 rubric; old SYSTEM_PROMPT had wrong 2-criteria
- Action: DONE ✅ (v71 has correct rubric)

### Priority 3 (NEXT — v72): "Never truncate" rule with evidence
- Evidence: "appears incomplete truncated" is TOP losing phrase across ALL task types (8,500+ mentions)
- Rule to add: "The judge explicitly penalizes incomplete/truncated patches. If you cannot finish all changes, complete the most critical ones fully rather than starting all partially."

### Priority 4 (v72): Explicit "read all affected files first" rule
- Evidence: o3/gpt-5.5 (avg gap 0.39+) win by deep pre-reading; M2.7 loses when it starts coding too early
- Rule: "Before writing ANY code, run: find . -type f | grep relevant_extension | head 50. Read all files the issue references. Only then start editing."

### Priority 5 (v72): Task-type aware completeness targets
- Evidence: FEATURE wins=153 lines vs loses=161 (shorter wins); BUGFIX wins=107 vs loses=112
- Rule: "Expected patch size: BUGFIX=2-5 files, UPDATE=3-8 files, FEATURE=complete feature (don't over-build), API=3 layers (backend+route+frontend)"

### Priority 6 (Stage 2): Fine-tune M2.7 on FT-1 + FT-2 + FT-3
- 366K SFT patches + 65K DPO pairs + 176K judge simulator pairs
- Expected: close the 87.5% gap between M2.7 and reference quality
- Timing: when T68-S2 arrives (NVLink 242GB for QLoRA)

---

## Pipeline Step Integration

This document becomes **Step 2a** (DPO analysis) and **Step 2b** (M2.7 pattern analysis) in `SN66_PIPELINE_FORMAL.md`.

For every new agent version:
1. Run Intel A (rationale phrases) to update task-type rules
2. Run Intel B (M2.7 wins) to find new strength zones
3. Run Intel C (wiring examples) to refresh UPDATE rule examples
4. Check Intel E (data quality map) to confirm which task types have best signal
5. Use FT-1/2/3 pipelines for Stage 2 fine-tuning when T68-S2 arrives

*File: /root/sn66-ninja/research/DATA_INTEL_PIPELINE_SN66.md*
*Next update: After HuggingFace corpus downloads start (task pool rotation week)*
