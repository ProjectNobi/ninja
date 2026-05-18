# Debate — SN66_ PIPELINE_FORMAL.md Audit (2026-05-18)

## Per-Change Debate

### Change 1: Max-iteration cap for Rapid Iteration loop
**For:** Prevents infinite loop if threshold unreachable. Low implementation cost.
**Against:** Artificial cap may cut off good runs early. Human monitoring already exists.
**Risk of skipping:** MEDIUM — Low in practice (human monitors), but programmatic safeguard is cheap insurance.
**Ruling:** SHOULD ADD

### Change 2: Judge Simulator validation step
**For:** Validates M2.7 judge predictions match gpt-5.4 before trusting. Critical for confidence.
**Against:** 20 holdout pairs + accuracy check adds 10-15 min to pipeline. DPO training already done.
**Risk of skipping:** HIGH — If M2.7 judge is miscalibrated, entire Stage 2 rests on faulty signal.
**Ruling:** MUST ADD

### Change 3: Document fallback to Stage 1
**For:** Explicit fallback prevents confusion when Stage 2 fails. Low cost to document.
**Against:** Implicit fallback is obvious — return to what worked before.
**Risk of skipping:** LOW — Already implicit, humans can figure it out.
**Ruling:** SHOULD ADD

### Change 4: Clarify role overlap in Rapid Iteration
**For:** Reduces confusion between Role 2 (Judge) and Role 3 (Dev Tool) when both use M2.7.
**Against:** Minor naming clarification, doesn't affect functionality.
**Risk of skipping:** LOW — Works fine, just unclear naming.
**Ruling:** SKIP

### Change 5: Number Step 7 in Stage 1
**For:** Matches document's own outline structure. Cleaner.
**Against:** Trivial cosmetic change. Current inline "Report to James" works fine.
**Risk of skipping:** NONE — Cosmetic only.
**Ruling:** SKIP

### Change 6: Add version number to header
**For:** Enables tracking across updates. Low cost.
**Against:** Date already in footer serves same purpose.
**Risk of skipping:** NONE — Date sufficient for versioning.
**Ruling:** SKIP

### Change 7: Safety threshold for judge simulation
**For:** Extra safety net — if M2.7 judge uncertain, escalate to gpt-5.4.
**Against:** Adds complexity. M2.7 DPO-trained should be reliable; extra check may never trigger.
**Risk of skipping:** LOW — Double-check is nice but M2.7 should be solid after 86K+ DPO.
**Ruling:** SKIP

### Change 8: Document data quality checks
**For:** Prevents pipeline running on corrupted gold/DP0 files. Pre-flight validation is smart.
**Against:** Could be handled by external data prep, not pipeline itself.
**Risk of skipping:** MEDIUM — Corrupted data would waste hours. Pre-flight check is cheap insurance.
**Ruling:** SHOULD ADD

## Final Edit List

1. **Change 2 (MUST ADD)** — After Stage 2 STEP 3 paragraph, add:
   > **Judge Validation:** Before full simulation, run M2.7 on 20 holdout DPO pairs. Report accuracy vs gpt-5.4. Skip if accuracy <80%.

2. **Change 1 (SHOULD ADD)** — In Stage 2 STEP 4, add after "when predicted WR ≥ 60%":
   > Max 10 cycles per run. If threshold unmet after 10 cycles, escalate to James.

3. **Change 3 (SHOULD ADD)** — Add at end of Stage 2 intro/overview:
   > **Fallback:** If fine-tuning fails or M2.7 judge unreliable → return to Stage 1 pipeline, notify James.

4. **Change 8 (SHOULD ADD)** — Add as new Pre-flight section before Stage 1:
   > **Pre-flight Data Check:** Validate gold.jsonl and DPO files are readable and not corrupted before pipeline runs.

## Final Verdict

**APPROVED — apply 4 changes** → pipeline is finalized

The pipeline is functionally sound. The 4 retained changes (2 MUST ADD + 2 SHOULD ADD) address real operational risks without adding unnecessary complexity. Changes 4-8 are cosmetic or low-value — skipped to keep pipeline clean and focused.
