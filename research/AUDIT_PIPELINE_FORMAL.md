# Audit — SN66_ PIPELINE_FORMAL.md (2026-05-18)

## Findings

**Q1: ✅ OK** — Steps logically ordered: PRE-STEP → 1a-1e → 2a/2b → 3 → 4 → 5 → 6. No gaps. Stage 1 ends at Step 6 (Gate Test) with inline handoff to "Report to James" — effectively Step 7 without formal numbering.

**Q2: ✅ OK** — Gate threshold stated consistently: ≥60% decisive WR, 50 tasks, seed 42. Appears in Stage 1 STEP 6 and Stage 2 STEP 6.

**Q3: ✅ OK** — Forbidden patterns complete. "Never delete" ban explicitly listed in Standing Rules + STEP 4 build instructions + STEP 5 checklist. COMPLETENESS asymmetry required and verified in STEP 5.

**Q4: ⚠️ WARNING** — Three roles defined in table (Patch Generator / Judge Simulator / Offline Dev Tool) but STEP 2, 3, 4 reference them inconsistently. Role 2 (Judge Simulator) and Role 3 (Offline Dev Tool) overlap in rapid iteration — both use M2.7 for evaluation. Could cause confusion but functionally works.

**Q5: ⚠️ WARNING** — STEP 4 (Rapid Iteration) loop-exits "when predicted WR ≥ 60%" but has no max-iteration cap or timeout. If threshold unreachable, loop runs forever. Risk: low in practice (human monitors), but no programmatic safeguard.

**Q6: ⚠️ WARNING** — STEP 3 (Judge Simulation) uses fine-tuned M2.7 as judge simulator without independent validation. No step to verify M2.7's judge predictions match gpt-5.4 before trusting it. Trust assumption: fine-tuned on 86K+ DPO pairs is sufficient.

**Q7: ⚠️ WARNING** — No fallback defined if Stage 2 fails. If fine-tuning crashes, M2.7 judge simulation unreliable, or predicted WR stuck below 60%, no explicit fallback path. Implicit fallback: return to Stage 1 but not documented.

**Q8: ✅ OK** — Version number: "Last updated: 2026-05-18" at footer. Clear handoff: Trigger Conditions section defines prerequisites (T68-S2 arrival, data collection, 3+ versions submitted). Stage 1 → Stage 2 transition is explicit.

## Summary

6 OK, 2 warnings, 0 issues — **APPROVED**

Pipeline is functionally sound. Warnings are minor operational risks, not blockers.

## Recommended Changes

1. **Add max-iteration cap to Rapid Iteration (Stage 2 STEP 4):** "Max 10 cycles per run, then escalate to James if threshold unmet." Prevents infinite loop.

2. **Add Judge Simulator validation step (Stage 2 STEP 3):** Before full judge simulation, run M2.7 on 20 holdout DPO pairs and report accuracy vs gpt-5.4. Skip if accuracy <80%.

3. **Document fallback to Stage 1 (Stage 2):** Add explicit line: "If fine-tuning fails or M2.7 judge unreliable → return to Stage 1 pipeline, notify James."

4. **Clarify role overlap in Rapid Iteration:** Stage 2 STEP 4 states "M2.7 Roles 1+2 + Opus" — clarify Role 2 (Judge) vs Role 3 (Dev Tool) distinction in this step.

5. **Formally number Step 7 in Stage 1:** "STEP 7 — Report to James + Submit" to match the document's own outline (Pre-step → 1a-1e → 2a/2b → 3 → 4 → 5 → 6 → 7).

6. **Add version number to header:** "*James directive 2026-05-18 | v1.0*" for tracking.

7. **Add safety threshold for judge simulation:** "If predicted WR confidence <70%, skip M2.7 judge and run gpt-5.4 instead."

8. **Document data quality checks:** Add pre-flight validation that gold/DPO files are not corrupted before pipeline runs.
