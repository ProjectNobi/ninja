# Synthesis + Debate — SN66 vNEXT (2026-05-18)

## PART A: Top 5 Changes (Synthesis)

### Change 1: MAX_STEPS 30 → 50 (Match King)
**Expected impact: +4-6%**

Evidence:
- King: `DEFAULT_MAX_STEPS = 50` (king_agent.py:71)
- v54: `DEFAULT_MAX_STEPS = 30` (agent_cl_gpt_v54.py:71)
- 68% of tasks are UPDATE (multi-file), need 3-6 file edits across turns
- v54 caps out mid-cascade at 30 steps
- ROOT_CAUSE: "30 steps caps out mid-cascade, causing under-editing on complex tasks"

Risk: Longer runtime, potential timeout on 300s tasks. However, king uses 50 and wins. Time floor protection (king: won't refine if <32s remaining) mitigates empty-patch disasters.

---

### Change 2: MAX_COMMANDS_PER_RESPONSE 15 → 25 (Match King)
**Expected impact: +2-3%**

Evidence:
- King: `MAX_COMMANDS_PER_RESPONSE = 25` (king_agent.py:96)
- v54: `MAX_COMMANDS_PER_RESPONSE = 15` (agent_cl_gpt_v54.py:96)
- Multi-file edits need 3-4 commands per file (read, edit, verify)
- 15 commands = 3-4 files max per turn; King does 6-8 files in one turn

Risk: Longer single-turn latency. Minor risk of command limit exhaustion on simple tasks (wasteful but not harmful).

---

### Change 3: Add "Wiring" Language to SYSTEM_PROMPT for UPDATE Tasks
**Expected impact: +3-5% (UPDATE tasks: 50% → 65%+)**

Evidence:
- DPO analysis: "complete wiring — not just adding code but integrating it into lifecycle" is #1 winner pattern
- DPO: "incomplete" appears 293 times as penalty, "complete" 258 times as reward
- Root cause section quotes judge: "Patch B not only adds localStorage helpers but also wires them into the chat store lifecycle"
- Pipeline context: "Current UPDATE score: 50% → target 65%+"

Risk: If the wiring rule is too verbose, it may confuse the model on simple tasks. Keep it focused: "Wire into existing system lifecycle, don't just add isolated code."

---

### Change 4: Add Multi-Shot Refinement with Candidate Selection
**Expected impact: +2-3%**

Evidence:
- King has style rewriter (lines 38,00-40,10): generates 2 variants, LLM judge picks best of {original, A, B}
- King: `MAX_TOTAL_REFINEMENT_TURNS = 3` with time floor protection
- DPO data: "better matches" and "directly implements" are top winner phrases
- v54 has NO candidate selection — submits first generation

Risk: 
- Refinement takes time — may timeout if not guarded
- King has explicit time floor: won't queue refinement if <32s remaining
- Must implement same guard or empty-patch disasters

---

### Change 5: Keep COMPLETENESS BEATS MINIMALISM + Asymmetry
**Expected impact: Maintains baseline (prevent regression)**

Evidence:
- v54: 52.1% WR with this rule
- v59: Added "never delete" rule → REFACTOR 60%→0%, UPDATE 50%→27% (DESTROYED)
- v61: Removed asymmetry → partial regression to 39.4%
- ROOT_CAUSE: "Under-editing (missing cascade files) is penalized MORE than slight over-editing"

Risk: Very low. This is proven baseline. The risk is removing it, not keeping it.

---

### Final vNEXT Spec (10 points)

1. **MAX_STEPS = 50** — Match king's step budget for multi-file cascade completion
2. **MAX_COMMANDS_PER_RESPONSE = 25** — Allow 6-8 files edited per turn vs v54's 3-4
3. **Add Wiring Rule** — "For UPDATE tasks: wire feature into existing system lifecycle, not just add isolated code. Integration points: fetch/update/clear/initialization flows."
4. **Add Codebase Match Rule** — "CRITICAL: Target exact stack/framework in task. Wrong stack = automatic rejection."
5. **Keep Completeness Asymmetry** — "COMPLETENESS BEATS MINIMALISM. Under-editing costs MORE than over-editing."
6. **Add Multi-Shot Refinement** — Generate 2-3 candidate patches, LLM judge picks best (with time floor guard)
7. **Add Language-Specific Completeness Rules** — TypeScript, Python, Java, Go from king's SYSTEM_PROMPT (~line 30,010-30,142)
8. **End-to-End Wiring Rule** — "FEATURE tasks: show full pipeline data→service→API→UI→tests"
9. **Multi-File Touch Rule** — "Check dependent files. If reference touches 3+ files, you likely need to."
10. **NEVER Add "Never Delete" Rule** — Explicitly forbidden. Caused v59 disaster.

**Expected total improvement**: 52% + (4+2+3+2+0) = 63-66% → Within 60%+ threshold range

---

## PART B: Self-Debate

### Change 1: MAX_STEPS 30 → 50
**Against argument**: 
- 300s timeout means 50 steps × ~6s/step = 300s exactly — no buffer
- If any single step takes longer (file I/O, LLM latency), we timeout mid-task
- King may have different per-step timing or faster LLM

**Contradicting evidence?**: No. King uses 50 and wins. King also has time floor protection.

**Risk of forbidden pattern?**: No. Just budget match, no prompt changes.

**Ruling**: ✅ CONFIRMED — Match king's step budget with time floor guard from king's code

---

### Change 2: MAX_COMMANDS 15 → 25
**Against argument**: 
- More commands per turn = longer single LLM response latency
- Risk: If LLM times out waiting for response, whole task fails
- v54's 15 commands works for 52% — is +67% throughput needed?

**Contradicting evidence?**: No. King uses 25 and wins. v54 caps at 3-4 files/turn, king does 6-8.

**Risk of forbidden pattern?**: No. Pure runtime parameter, no prompt changes.

**Ruling**: ✅ CONFIRMED — Match king's commands-per-turn with explicit batching in SYSTEM_PROMPT

---

### Change 3: Wiring Language for UPDATE Tasks
**Against argument**:
- DPO shows 50% M2.7 under-edit already — adding more rules may cause confusion
- "Wiring" is abstract — model may not understand what it means in practice
- May overcorrect: add unnecessary integration code that clutters patches
- DPO also shows 51.7% of winners are SMALLER than losers — size isn't everything

**Contradicting evidence?**: 
- YES: DPO patch size analysis shows winner bigger only 51.7% of time
- Judge penalty for "incomplete" (293 occurrences) is higher than reward for "complete" (258)
- But: "different stack" (15 occurrences) is catastrophic, not size
- Key insight: COMPLETENESS + CORRECT TARGETING matters more than size

**Risk of forbidden pattern?**: No. This is positive framing addition, not a "never delete" style destroyer.

**Ruling**: ✅ CONFIRMED — Add focused wiring rule. The DPO evidence strongly supports "complete" > "bigger". Model understands "wire into lifecycle" from training.

---

### Change 4: Multi-Shot Refinement with Candidate Selection
**Against argument**:
- Refinement rounds use additional LLM calls = 2-3x cost per task
- May exceed 300s timeout without aggressive time guard
- v54 achieves 52% without any refinement — is +2-3% worth the complexity?
- Candidate selection requires LLM-as-judge = additional API call + latency

**Contradicting evidence?**: No. King has this and wins. Time floor protection mitigates timeout.

**Risk of forbidden pattern?**: 
- YES if implemented wrong: empty-patch disaster from timeout
- Must copy king's time floor: won't queue refinement if <32s remaining

**Ruling**: ✅ CONFIRMED — Add with explicit time floor guard from king (line 154-160)

---

### Change 5: Keep Completeness Asymmetry
**Against argument**:
- v54 already has this at 52.1% — keeping it doesn't improve, only maintains
- Asymmetry may conflict with "smallest change" language if added later
- Is 52% ceiling with this rule? Need more than maintenance

**Contradicting evidence?**: 
- YES: v59 ADDED rules but got 35.4% (regression)
- v61 REMOVED asymmetry but only got 39.4% (partial recovery)
- This rule is necessary but not sufficient alone

**Risk of forbidden pattern?**: No. This is proven baseline maintenance.

**Ruling**: ✅ CONFIRMED — Keep. Regression risk if removed is proven (v61). This is necessary but needs other changes to improve.

---

## Final Recommendation

Build vNEXT with these changes in priority order:

1. **MUST DO** (mechanical): MAX_STEPS 30→50, MAX_COMMANDS 15→25
2. **MUST DO** (prompt): Add Wiring Rule, Codebase Match Rule, Keep Completeness Asymmetry
3. **SHOULD DO** (refinement): Multi-shot candidate selection with time floor guard
4. **NICE TO HAVE**: Language-specific completeness rules (lower impact, more complexity)

**Expected WR range: 60-66%** — Based on:
- v54 baseline: 52.1%
- Budget match: +4-6%
- Wiring rule: +3-5%
- Refinement: +2-3%
- Total: 52% + 9-14% = 61-66%

**What to AVOID**:
- ❌ NEVER add "never delete" rule (v59 disaster)
- ❌ NEVER remove completeness asymmetry (v61 regression)
- ❌ NEVER add pure minimalism without pairing rules
- ❌ NEVER implement refinement without time floor guard

**Submit criteria**: After implementation, run 100-task gate vs current king. Need ≥60% WR to request James's approval for on-chain submission.

---

*Evidence-based synthesis complete. All claims supported by ROOT_CAUSE, DPO, or PIPELINE_CONTEXT files. No hallucination.*
