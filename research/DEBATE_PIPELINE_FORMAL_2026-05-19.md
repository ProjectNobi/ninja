# DEBATE — SN66_PIPELINE_FORMAL.md Audit Findings
*Debate partner: T68Bot subagent | Date: 2026-05-19*

---

## VERDICT TABLE

| # | Audit Finding | Challenge | Evidence Used | Verdict |
|---|---------------|-----------|---------------|---------|
| F1 | Step 4 "Start from v54 as base" | Legacy content or real contradiction? | Harness confirms v54 stuck at CI 62 after 9 attempts; king-base = CI 78 first try. L-SN66-KING-BASE-MANDATORY-1 CORRECTION explicitly revokes any non-king base. | ✅ **FIX** |
| F2 | Step 1c wrong judge + formula | Are stale header comments authoritative? | Harness v6 line 71 = `claude-sonnet-4.6`. Lines 848–849 = `c_combined = llm_score_challenger` (LLM-only). Header lines 4/28/32 are un-updated docs. Code is truth. | ✅ **FIX** |
| F3 | OFFICIAL BASELINE v62 contradicts king-base | Just historical record? | Correction says "ALL future versions build from king. REVOKED two-track system." Section says "All future agent versions build from v62." Direct contradiction that will mislead future reads. | ✅ **FIX** |
| F4 | v65 James directive vs king-base rule | Historical record doesn't need update? | v66 already built from v62b — the history is correct. But correction was issued same day and explicitly supersedes it. Note required to prevent v67+ from repeating v62b base mistake. | ✅ **FIX** |
| F5 | Step 2a asks "what does gpt-5.4 reward" | Partially updated in OFFICIAL section? | OFFICIAL top-level Step 2a was updated. Detailed pipeline Step 2a still referenced gpt-5.4. DPO analysis directed at wrong judge = wrong insights. | ✅ **FIX** |
| F6 | PRE-STEP uses ambiguous git show command | Functional if user knows the commit? | `git show <latest-commit>` requires manual commit SHA lookup. sync_king.sh is the documented standard everywhere else. Subagent execution would fail. | ✅ **FIX** |

**All 6 findings: ACCEPTED → FIXED**

---

## FIXES APPLIED TO SN66_PIPELINE_FORMAL.md

1. **PRE-STEP sync** — replaced `git show <latest-commit>` with `bash scripts/sync_king.sh && wc -l king_agent.py`
2. **Step 1c** — updated to: "judge model = anthropic/claude-sonnet-4.6, scoring = 100% LLM judge (cursor_sim telemetry only, no scoring weight). [Updated 2026-05-19: PR#1598]"
3. **Step 2a** — updated to reference `sonnet_winner` + `sonnet_rationale` (Phase 1 ground truth); added Phase 2 prep guidance on `consensus=True` pairs
4. **Step 4** — removed `agent_cl_gpt_v54.py` from task and input; replaced "Start from v54 as base (best at 52.1%)" with "Start from king_agent.py as base (L-SN66-KING-BASE-MANDATORY-1 CORRECTION)"
5. **OFFICIAL BASELINE v62 section** — added ⚠️ SUPERSEDED notice at top: v62 = historical reference only, do NOT use as base
6. **v65 Failure Analysis** — added note: "This directive was superseded the same day by L-SN66-KING-BASE-MANDATORY-1 CORRECTION. v62b applies to v66 only; v67+ must use king as base."

---

## VERIFICATION

All 8 checks passed ✅ (confirmed by automated check on document content)

---

*Pipeline document is now internally consistent with L-SN66-KING-BASE-MANDATORY-1 CORRECTION and PR#1598 judge update.*
