# AUDIT — SN66_PIPELINE_FORMAL.md
*Auditor: T68Bot subagent | Date: 2026-05-19*

---

## CRITICAL CONTRADICTIONS

### ❌ CONTRADICTION 1 — Step 4 "Start from v54 as base"
**Location:** Stage 1 STEP 4 Build, "Mandatory rules for the build"
**Text:** "Start from v54 as base (best at 52.1%)"
**Conflict:** L-SN66-KING-BASE-MANDATORY-1 CORRECTION explicitly states king source = starting point for EVERYTHING. v54 is an old, inferior base.
**Fix:** Replace "Start from v54 as base (best at 52.1%)" → "Start from king_agent.py as base (L-SN66-KING-BASE-MANDATORY-1 CORRECTION)"
Also remove `agent_cl_gpt_v54.py` from Step 4 Input list — king_agent.py is the only base.

---

### ❌ CONTRADICTION 2 — Step 1c Scoring Formula (stale)
**Location:** Stage 1 detailed pipeline, "STEP 1c — Scoring Mechanism Validation"
**Text:** "Confirm judge model = gpt-5.4, win_margin=3, scoring = 0.5×cursor_sim + 0.5×llm_judge."
**Conflict:** Scoring Mechanism section (Phase 1) clearly states:
- Judge = `anthropic/claude-sonnet-4.6` (NOT gpt-5.4)
- Scoring = 100% LLM judge — cursor_sim is telemetry ONLY (no weight)
This is a direct factual error that will cause any Opus task following Step 1c to validate the wrong formula.
**Fix:** Update Step 1c to: "Confirm judge model = anthropic/claude-sonnet-4.6, win_margin=3, scoring = 100% LLM judge (cursor_sim telemetry only, no scoring weight)"

---

### ❌ CONTRADICTION 3 — "OFFICIAL BASELINE — v62" section conflicts with king-base rule
**Location:** "🏆 OFFICIAL BASELINE — v62" section
**Text:** "All future agent versions build from v62 (CI-passing) as base."
**Conflict:** L-SN66-KING-BASE-MANDATORY-1 CORRECTION says "There is NO two-track system" and explicitly revokes the v62b-for-research track.
**Fix:** Add a prominent notice at the top of the "OFFICIAL BASELINE — v62" section:
> ⚠️ SUPERSEDED by L-SN66-KING-BASE-MANDATORY-1 CORRECTION (2026-05-19). v62 is historical reference only. All new versions start from current king_agent.py. Do not use v62 as base.

---

### ❌ CONTRADICTION 4 — v65 Gate Failure "James directive" contradicts king-base rule
**Location:** "v65 Gate Failure Analysis" section, final line
**Text:** "James directive (2026-05-19): Restart pipeline with **v62b (agent_cl_gpt_v62_fix.py) as baseline**."
**Conflict:** L-SN66-KING-BASE-MANDATORY-1 CORRECTION was issued on the same date and revokes v62b as base.
The v66 section confirms it was built from v62b ("per James directive") — but the king-base correction was issued AFTER this directive and supersedes it.
**Fix:** Add a note: "⚠️ This directive was superseded same day by L-SN66-KING-BASE-MANDATORY-1 CORRECTION. All versions after v66 use king as base."

---

## GAPS / ISSUES

### ⚠️ ISSUE 1 — Step 2a DPO Analysis asks about gpt-5.4 rewards, not Sonnet 4.6
**Location:** Stage 1, "STEP 2a — DPO Pair Deep Dive"
**Text:** "What does gpt-5.4 reward vs penalize?" and "For UPDATE: does judge care more about completeness..."
**Problem:** Phase 1 judge is Sonnet 4.6. The DPO analysis guide should direct Opus to study `sonnet_winner` + `sonnet_rationale` fields (Phase 1 ground truth), not gpt-5.4 fields.
**Fix:** Update Step 2a to: "Study `sonnet_winner` + `sonnet_rationale` (Phase 1 ground truth). For Phase 2 readiness also note `consensus=True` pairs."

---

### ⚠️ ISSUE 2 — PRE-STEP King Sync uses manual git command instead of sync_king.sh
**Location:** Stage 1 detailed pipeline, "PRE-STEP: King Sync"
**Text:** `git show <latest-commit>:agent.py > king_agent.py`
**Problem:** This is ambiguous — requires knowing `<latest-commit>` manually. The rest of the document consistently references `bash scripts/sync_king.sh`. This step will cause confusion for any automated or subagent execution.
**Fix:** Replace with: `cd /root/sn66-ninja && bash scripts/sync_king.sh && wc -l king_agent.py`

---

### ⚠️ ISSUE 3 — Step 1d uses hardcoded /tmp/dashboard_sn66.json without fetch command
**Location:** Stage 1, "STEP 1d — Live Duel API Pull"
**Problem:** The Python snippet reads from `/tmp/dashboard_sn66.json` but no command in the pipeline fetches this file. An agent following step-by-step would fail here.
**Fix:** Add fetch command before the Python snippet:
```bash
curl -s https://ninja66.ai/dashboard.json > /tmp/dashboard_sn66.json
```

---

### ⚠️ ISSUE 4 — Duplicate Stage 2 sections with conflicting record counts
**Location:** Two "STAGE 2 — DEDICATED FINE-TUNED M2.7 PIPELINE" sections exist
- Middle of document (embedded after Step 7): shows 297K+ gold, 30K+ DPO
- Bottom of document (🚀 heading): shows 364K+ gold, 61K+ DPO
**Problem:** This creates confusion — which section is authoritative? The bottom section is newer (higher counts) but both sections describe the same pipeline.
**Fix:** Remove the middle Stage 2 section (after Step 7) entirely. Keep only the bottom "🚀 STAGE 2" section with the updated counts. Or add a prominent "⚠️ SEE UPDATED SECTION BELOW" notice to the middle one.

---

### ⚠️ ISSUE 5 — v66 entry is now archived contradiction
**Location:** "v66 — Built 2026-05-19" section
**Problem:** v66 was built from v62b base (pre-king-base correction). The entry is accurate as historical record but could mislead future pipeline runs into thinking v62b base is acceptable.
**Fix:** Add a note: "⚠️ v66 used v62b base (pre-king-base rule). All versions v67+ must use current king as base (L-SN66-KING-BASE-MANDATORY-1 CORRECTION)."

---

### ⚠️ ISSUE 6 — BUGFIX task distribution discrepancy (73% vs 6%)
**Location:** v65 Gate Failure Analysis ("BUGFIX = 73% of today's live competition tasks") vs pipeline task selection ("68% UPDATE, 19% FEATURE, 7% API, 6% BUGFIX")
**Problem:** 73% vs 6% is a huge discrepancy. If BUGFIX is truly 73% of live duels right now, the 50-task gate test should reflect this, not the standard 68/19/7/6 distribution. This could invalidate gate test results.
**Fix:** Add a note in Step 1f (Harness + Task Selection): "Verify live task type distribution via dashboard.json before fixing gate test proportions. Distribution may shift significantly (e.g. BUGFIX was 73% on 2026-05-19)."

---

## CORRECT ITEMS

### ✅ L-SN66-CI-HOTKEY-SPENT-1 CORRECTION
Fully documented in "🔑 HOTKEY REUSE RULE" section with table showing failed=reusable, passed=spent. ✅

### ✅ L-SN66-KING-BASE-MANDATORY-1 CORRECTION
Both the original rule AND the final correction are present. The correction explicitly revokes the two-track system. ✅

### ✅ Harness v6 judge update
"Harness v6 Judge Config" section correctly documents JUDGE_MODEL = anthropic/claude-sonnet-4.6 and states "Always keep harness judge in sync with live validator." ✅

### ✅ Dual-judge Phase 2 next week
Phase 2 section fully documented with judge identities, consensus field, DPO field names, and action plan. ✅

### ✅ Stage 2 NVLink setup
References NVIDIA playbook (connect-two-sparks) and T68-S1+S2 242GB unified RAM correctly. ✅

### ✅ Stage 2 trigger conditions
Clearly stated: T68-S2 arrival + data complete + ≥3 Stage 1 versions submitted. ✅

### ✅ Gate threshold consistent
≥60% decisive WR on 50 tasks, seed 42, always in tmux — consistent throughout. ✅

### ✅ Submission checklist present
Step 5 has 10-item checklist with syntax check command. ✅

### ✅ Data flywheel description
Stage 2 data flywheel loop is clear and actionable. ✅

---

## PRIORITY FIX ORDER

| Priority | Issue | Impact |
|----------|-------|--------|
| 🔴 P1 | Step 1c wrong judge + wrong formula | Causes Opus to validate stale scoring |
| 🔴 P1 | Step 4 "v54 as base" | Causes next build to start from wrong base |
| 🟡 P2 | Step 2a asks about gpt-5.4 rewards | Sends DPO analysis in wrong direction |
| 🟡 P2 | OFFICIAL BASELINE v62 section | Misleads future pipeline reads |
| 🟡 P2 | PRE-STEP sync command ambiguous | Breaks subagent execution |
| 🟢 P3 | Step 1d missing fetch command | Easy fix, prevents silent failure |
| 🟢 P3 | Duplicate Stage 2 sections | Cosmetic confusion |
| 🟢 P3 | v66 entry note needed | Historical clarity only |

---

*Total issues: 4 contradictions, 6 gaps. 9 items correct. P1 fixes needed before next pipeline run.*
