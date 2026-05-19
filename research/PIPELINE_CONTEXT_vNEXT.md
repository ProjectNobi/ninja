# SN66 Pipeline Context — vNEXT (2026-05-18)

## Mission
Build the next SN66 agent version that achieves ≥60% decisive win rate vs current king (5DoCiGfbjssN) in a 50-task gate test.

## Current State

### Best version: v54 — 52.1% WR (100-task, vs OLD king fd2af7a6050e)
- File: /root/sn66-ninja/agent_cl_gpt_v54.py (182KB, ~4400L)
- MAX_STEPS=30, MAX_COMMANDS_PER_RESPONSE=15
- Core philosophy: COMPLETENESS BEATS MINIMALISM

### Current King: 5DoCiGfbjssN (private submission, May 18, UID 86)
- Runtime from unarbos/ninja commit 6abf1725459ef8b1
- Public reference: /root/sn66-ninja/king_agent.py (4873L)
- MAX_STEPS=50, MAX_COMMANDS_PER_RESPONSE=25 ← 67% more budget than us
- Core philosophy: SURGICAL EDITING + LANGUAGE-SPECIFIC COMPLETENESS

## King vs Our Best: Key Structural Differences

### Budget Gap (CRITICAL)
| Metric | King | Our v54 | Gap |
|--------|------|---------|-----|
| MAX_STEPS | 50 | 30 | -40% |
| MAX_COMMANDS/turn | 25 | 15 | -40% |
| Multi-shot refinement | YES (3 rounds) | NO | missing |
| Candidate selection | YES (pick best) | NO | missing |
| Dynamic completeness injection | YES (per-turn) | NO | missing |

### King's SYSTEM_PROMPT Key Features
1. **SURGICAL EDITING section** (explicit): "Change the fewest lines necessary"
2. **LANGUAGE-SPECIFIC COMPLETENESS RULES**: Java, C/C++, TypeScript, Python, etc.
3. **Integration cascade planning**: "enumerate EVERY required integration point"
4. **ISSUE CONTRACT**: "Extract every requirement before editing"
5. **Forbidden list**: whole-file rewrites, formatting churn, whitespace edits, code reordering
6. **Completeness asymmetry** (implicit via language rules): under-editing = missing cascade files

### Our v54 Key Features
1. **COMPLETENESS BEATS MINIMALISM** (explicit header)
2. **Under-editing penalized MORE** (explicit)
3. **Cascade tracking** (search callers, importers, tests)
4. No multi-shot refinement
5. No language-specific rules
6. Lower budget (30/15)

## DPO Data Intelligence (86,937 pairs on Hetzner1)

### Task Distribution
- UPDATE: 59,252 (68%) ← DOMINANT — our UPDATE score is 50% (weak)
- FEATURE: 16,422 (19%)
- API: 5,828 (7%)
- BUGFIX: 5,435 (6%)

### What gpt-5.4 Rewards (from judge_rationale analysis)
**UPDATE tasks**: "complete wiring — not just adding code but integrating it into lifecycle"
- Example: "Patch B not only adds localStorage helpers but also wires them into the chat store lifecycle: saving on message updates, falling back to local backup when fetch fails..."
- Loser: "Patch A mainly adds platform forwarding... but doesn't implement the actual event-handling logic"
- Key: Judge wants FUNCTIONAL CONNECTIVITY — the feature must be connected end-to-end

**BUGFIX tasks**: "direct addressing of core acceptance criteria"
- Example: "adds the Number platform, introduces per-action duration config constants, and wires in a dedicated stop button, directly addressing the core acceptance criteria"
- Loser: "mainly adds platform forwarding and some option-menu descriptions"
- Key: Judge wants TARGETED ROOT CAUSE FIX + all explicit requirements met

**FEATURE tasks**: "complete end-to-end implementation"
- Example: "adds a reusable Google button component, initiates Google sign-in, and implements the callback route... matching the issue requirements"
- Loser: "incomplete/truncated"
- Key: Judge wants ALL integration points connected (UI + backend + route + auth)

### Forbidden Rules (from MEMORY.md + past gate failures)
❌ NEVER add: "Never delete or remove existing functions/components unless the task explicitly requests it"
→ Destroyed REFACTOR (60%→0%) and UPDATE (50%→27%) in v59

❌ NEVER frame without completeness asymmetry:
→ Removed in v61 → REFACTOR stayed at 0%, UPDATE dropped

✅ REQUIRED: "COMPLETENESS BEATS MINIMALISM. Under-editing costs MORE than over-editing."

## Gate History (vs OLD king fd2af7a6050e)
| Version | WR | Key change | Result |
|---------|-----|-----------|--------|
| v54 | 52.1% | Completeness-first | BEST |
| v56 | incomplete | Feature-builder framing | incomplete |
| v59 | 35.4% | Added "never delete" rule | REGRESSION |
| v61 | 39.4% | Removed asymmetry | PARTIAL RECOVERY |

**Best achieved: 52.1% — need ≥60% to submit (James's threshold)**

## Key Intelligence from DPO + Gold Data

### M2.7 Patch Generation Patterns (297,215 unified gold records locally)
- 44.9% of M2.7 gold records are under_edit (systematically under-generates)
- M2.7 generates good patches but needs explicit completeness push
- Training signal: weight completeness examples higher in fine-tuning

### Live Duel Status
- Our v54 (UID 179, 5FecE3QZ): duel result=N/A (pending)
- Our v56 (UID 231, 5Dqabiz8): duel result=N/A (pending)
- King has been replaced 3x in last 2 days (active competition)

## What Needs to Happen for vNEXT to Win

### High-Impact Changes (based on all data)
1. **Match king's step budget**: 30→50 MAX_STEPS, 15→25 MAX_COMMANDS_PER_RESPONSE
2. **Add multi-shot refinement**: generate 2-3 candidate patches, pick best
3. **Add language-specific completeness rules**: TS, Python, Java, etc. (from king)
4. **Fix UPDATE tasks (68% of all tasks)**: explicitly inject functional connectivity requirement
   - Current UPDATE score: 50% → target 65%+
   - Key: "Wire the feature into the existing system lifecycle, not just add isolated code"
5. **Keep COMPLETENESS BEATS MINIMALISM + asymmetry** (proven to work in v54)
6. **Add dynamic completeness injection per turn** (king has this)

### Low-Risk Changes (proven by v54)
- Cascade file tracking (callers, importers, tests)
- Explicit requirement extraction before editing
- Verification after each major change

## Scoring Formula (from harness v6)
combined_score = 0.5 × cursor_sim + 0.5 × llm_judge_score
decisive_win = combined_score > king_combined_score by win_margin=3
Win rate = decisive_wins / (decisive_wins + decisive_losses) [ties excluded]

## Files
- King: /root/sn66-ninja/king_agent.py (4873L)
- Our best: /root/sn66-ninja/agent_cl_gpt_v54.py
- Harness: /root/sn66-ninja/validator_harness_v6.py (1842L)
- DPO data: /root/sn66-ninja/training_data/ (86,937 pairs)
- Gold: /root/sn66-ninja/training_data/training_unified_gold.jsonl (297,215 records)
