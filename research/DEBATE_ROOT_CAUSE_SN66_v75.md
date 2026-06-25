# DEBATE — ROOT CAUSE SN66 v75
*Step 3B: Adversarial Debate | 2026-05-20 UTC*
*Challenger: T68Bot Subagent | Target: ROOT_CAUSE_SN66_v75.md (Step 3A Synthesis)*
*Inputs: ROOT_CAUSE_SN66_v75.md + DPO_INTEL_SN66_v75.md + STEP1_SOURCE_INTEL_SN66_v75.md*

---

## Preamble

The synthesis has a clean narrative. That's a red flag. Complex failures rarely have clean narratives. The job here is to stress-test every claim before we build on it. A misdiagnosed root cause means every proposed change is aimed at the wrong target.

Five debates below. Each follows: Challenge → Evidence → Verdict → Modified Recommendation.

---

## Debate 1: Root Cause Diagnosis — "Dual Failure: M2.7 Gap + AC Coverage"

### The Synthesis Claim
"Root cause is (1) M2.7 model quality gap vs opus-4.7 (24% vs 74% raw WR) and (2) AC coverage failure across all task types."

### Challenge 1A: The DPO Labels Measure a Different Contest Than the Gate

The DPO `chosen_label`/`rejected_label` fields compare raw model outputs in isolated, curated duel pairs. These pairs pit M2.7 patches against patches from OTHER models (opus-4.7, gemini, gpt-5.5, etc.) — across ANY context, ANY judge. The Intel D table reflects: "when M2.7's raw output is placed next to opus-4.7's raw output, sonnet-4.6 picks opus-4.7 74% of the time."

**That is NOT what happens in the gate.** In the gate, the validator calls our agent (which calls M2.7) and the king agent (which calls... what?). STEP1 does not identify what model the king's deployed agent uses. If the king also calls M2.7 or a similar model, the DPO win rate comparison is IRRELEVANT to gate WR. The 24% vs 74% gap is a raw-output quality ranking against opus-4.7 — it does not predict what happens when two M2.7-based agents compete against each other.

**The v74 evidence breaks the hypothesis.** v74 is a pure king clone — same SYSTEM_PROMPT, same logic, same M2.7 execution model. It achieved 47.5% WR. If M2.7 had a "structural 50-point quality deficit" against the gate king, a king clone would still score much lower than 47.5% — because the king would be producing opus-4.7-quality patches while our clone produces M2.7-quality patches. Instead, 47.5% is consistent with BOTH SIDES using a similar-quality model (approaching 50% baseline). A genuine 50-point model gap would show up as ~30% WR for the king clone, not 47.5%.

**Causal chain flaw:** "M2.7 24% DPO WR → our agent loses UPDATE" requires two unproven links:
- Link 1: The gate king uses a meaningfully better model than M2.7 (unconfirmed)
- Link 2: The model quality gap explains UPDATE failure specifically (not SYSTEM_PROMPT differences)

Neither link is confirmed by available data.

### Challenge 1B: AC Coverage Failure — Confounding With DPO Pair Composition

The synthesis presents "addresses acceptance criteria" as the #1 lose signal. Intel A shows 2,227 LOSE-count vs 624 WIN-count for UPDATE tasks. But this phrase counts measure how often the JUDGE USES THE PHRASE — not necessarily whether our agent failed to address AC.

**The confound:** In DPO pairs where claude-opus-4.7 wins (74% of cases), the judge will naturally say "provides complete implementation" and "addresses all acceptance criteria" to describe the WINNER. These phrase counts are dominated by opus-4.7 wins vs everyone else. The 2,227 LOSE count for "addresses acceptance criteria" largely reflects cases where M2.7 lost to opus-4.7 in raw output comparison — NOT cases where our AGENT SYSTEM lost to the gate king.

The synthesis conflates "M2.7 loses to opus-4.7 in raw DPO pairs" with "our agent fails to address AC in gate duels." These are not the same population.

### Evidence Assessment

| Claim | Data Available | Data Supports Claim? |
|-------|---------------|---------------------|
| M2.7 raw WR is 24% | DPO Intel D | YES — in raw pairs |
| Gate king uses better model than M2.7 | None | UNKNOWN — missing data |
| AC failure is cause of UPDATE 38% WR | DPO phrase counts | INDIRECT at best |
| v74 47.5% WR explained by model gap | Contradicted by v74 result | NO — gap too small |

### Verdict: CHALLENGED

The synthesis correctly identifies that AC coverage phrases appear heavily in LOSE rationales. But the causal story — "M2.7 quality gap explains our UPDATE 38% WR" — is not proven. The DPO data measures a different contest. The v74 king clone result (47.5%) is inconsistent with a 50-point structural model gap.

**The simpler explanation being missed:** The 38% UPDATE WR is consistent with M2.7 executing against the same king but on a harder subset of tasks. UPDATE tasks require full integration chain coverage. M2.7 with the king's SYSTEM_PROMPT covers BUGFIX well (root cause focus aligns with M2.7 strengths) but struggles with multi-layer integration tasks regardless of whether the gap is model-level or instruction-level.

### Modified Recommendation

Before attributing UPDATE failure to model quality, identify what model the king's deployed agent calls. This is a one-line check against the king's submitted code:
```bash
grep -n "model\|api_base\|claude\|gpt\|opus" /root/sn66-ninja/king_agent.py | head -40
```
If the king calls opus-4.7 → model gap is the binding constraint; SYSTEM_PROMPT changes are marginal.
If the king calls M2.7 or similar → model gap is not the issue; SYSTEM_PROMPT differences explain everything.

This 30-second check changes the entire diagnosis. The synthesis skipped it.

---

## Debate 2: Proposed Change 1 — AC Checklist in Plan Block

### The Synthesis Claim
Add after `Verification:` in plan block format:
> "AC checklist: after listing all requirements above, explicitly state: 'All AC points covered: [yes/no for each]'. If any AC point is not yet covered, add a specific step to address it before finishing."

### Challenge 2A: The King Already Has AC Extraction — v74 Proves It Doesn't Work

STEP1 source intel, Section 2 (King Technical Specs) confirms the king has `_extract_acceptance_criteria()`:
> "extracts AC bullets from issue, prepended to initial user content"

This is RUNTIME AC injection that fires before every solve. The king clone (v74) used this exact mechanism. v74 still got 38% UPDATE WR. Adding a SYSTEM_PROMPT-level checklist to the plan block is a weaker version of what the king already does dynamically.

The king extracts AC from the issue text and puts it IN FRONT OF THE AGENT before step 1. Our v75 (king clone) inherits this. The synthesis is proposing to add a static reminder ("state 'All AC points covered: [yes/no]'") when a dynamic AC extraction is already in place. If the dynamic extraction doesn't solve the problem, the static reminder won't either.

### Challenge 2B: The Checklist Adds Plan Block Overhead for All Task Types

The plan block format already has 7 explicit bullets (`Requirement:`, `Requirement:`, `Integration cascade:`, `Likely target:`, `Strategy:`, `Verification:`). Adding an 8th — a meta-checklist — extends the plan block for EVERY task, including BUGFIX (50% of the gate), where AC is already handled by "root cause fix."

For BUGFIX tasks, asking the agent to enumerate "All AC points covered: [yes/no for each]" creates:
- Extra tokens in the plan that consume step budget
- A mechanical checklist exercise before BUGFIX tasks that have simple AC (fix the bug)
- Risk of M2.7 spending plan tokens on checklist theater instead of actual diagnosis

The synthesis estimates "+1-2%" BUGFIX impact (near zero). But zero impact is optimistic — the actual risk is slight negative from overhead.

### Challenge 2C: Self-Verification Under M2.7 Quality Constraints

The synthesis argues: "M2.7 may plan correctly but not execute fully through all plan rows." The proposed fix: add a checklist so M2.7 self-verifies coverage.

This is circular. If M2.7 lacks the capability to execute all plan rows, adding a checklist step that ALSO requires M2.7's execution doesn't help — M2.7 will mark "yes" for AC points it didn't actually implement, because it doesn't know what it missed. The coverage nudge (`build_coverage_nudge_prompt()`) already fires when mentioned paths haven't been touched. It's a runtime enforcement mechanism, not a static checklist.

The synthesis doesn't address why a static self-check would succeed where a dynamic runtime nudge already in place hasn't solved the problem.

### Evidence Assessment

| Point | Evidence | Strength |
|-------|---------|---------|
| King has existing AC extraction | STEP1 Section 2: `_extract_acceptance_criteria()` | CONFIRMED |
| v74 (with king AC extraction) got 38% UPDATE WR | ROOT_CAUSE baseline | CONFIRMED |
| Checklist addresses a gap the AC extraction doesn't | None | UNCONFIRMED |
| Self-verification works for M2.7 at 24% raw WR | None | UNCONFIRMED |

### Verdict: CHALLENGED

The AC checklist is redundant with the king's existing dynamic AC extraction mechanism. The mechanism is already present in v74 (king clone). The mechanism doesn't solve UPDATE at 38%. Adding a static SYSTEM_PROMPT reminder of the same thing is unlikely to produce different results.

### Modified Recommendation

If the AC extraction is already present but not working, the problem is execution quality, not instruction clarity. The right investigation is: in failed UPDATE duels, did M2.7 PLAN correctly (listing all AC) but FAIL to IMPLEMENT? Or did M2.7 miss AC points in the plan itself? These require different fixes.
- If planning fails → fix the plan extraction (not SYSTEM_PROMPT)
- If implementation fails → no SYSTEM_PROMPT change will help; model upgrade or fine-tune required

Without this breakdown, the AC checklist is a guess. If the team wants to add it anyway as a low-cost experiment, cap it at 15 words and don't frame it as likely to close the UPDATE gap.

---

## Debate 3: Proposed Change 2 — UPDATE/FEATURE Wiring Rule

### The Synthesis Claim
Add after LANGUAGE-SPECIFIC COMPLETENESS RULES header:
> "UPDATE AND FEATURE TASKS — WIRING COMPLETENESS: A feature that exists but is never called scores zero. Trace the FULL execution chain: data model → service layer → API endpoint → frontend/consumer → lifecycle hooks → call sites. Every layer mentioned in the issue must be wired through. Check call sites last."

### Challenge 3A: Nearly Identical to v73's Rule That Was Identified as Harmful

v73 added "UPDATE/ENHANCE TASK WIRING RULE (9 lines)" — the STEP1 synthesis explicitly labeled this "LIKELY NEUTRAL TO HARMFUL" and it was removed in v74. The ROOT_CAUSE_SN66_v75 now recommends essentially the same rule, just condensed to 5 lines.

The response to this will be: "v73's rule was harmful because it was combined with the scoring sentence replacement. In isolation it might be beneficial." This is the classic confounding problem: when multiple changes are applied simultaneously, you can't isolate individual effects. v73 changed (1) scoring sentence + (2) 4 rule blocks including the wiring rule. v74 removed ALL of them and got 47.5%. We cannot conclude the wiring rule was neutral — we only know the full set of v73 changes was harmful.

**The safe prior:** When you can't isolate the effect of a removed rule, and the king succeeds without that rule, don't re-add the rule.

### Challenge 3B: The King Succeeds Without This Rule

The king has NO explicit wiring completeness rule. The king handles UPDATE through the general "integration cascade" bullet in the plan format and the "LANGUAGE-SPECIFIC COMPLETENESS RULES" section. The king presumably achieves better UPDATE WR than our 38% without an explicit wiring rule.

If the king handles UPDATE without a wiring rule, and our failure on UPDATE is either (a) model quality or (b) something in our SYSTEM_PROMPT that differs from the king, adding a wiring rule that the king doesn't have is unlikely to be the fix. We'd be adding something the winning agent doesn't use.

### Challenge 3C: "Every Layer Mentioned in the Issue Must Be Wired" — Scope Ambiguity

The rule says "trace the FULL execution chain: data model → service layer → API endpoint → frontend/consumer → lifecycle hooks → call sites." This is a 6-layer chain. For a simple UPDATE task that only mentions one layer (e.g., "add a config option"), this rule pushes the agent to implement all 6 layers even if the issue only requires 1.

This is the same failure mode as v73's TASK-TYPE STRATEGY section with file count targets: artificial constraints that push the agent to over-implement. "Implementation with proper [X]" is a WIN signal in Intel A (API/ROUTE tasks), but "a feature that exists but is never called = 0 points" sets up M2.7 to add unnecessary call sites on simpler tasks.

### Challenge 3D: Task-Type Detection is Implicit and Unreliable

The rule says "UPDATE AND FEATURE TASKS —" but there's no explicit task-type detection in the SYSTEM_PROMPT. The king identified the current task type via ISSUE CONTRACT inference, not by tagging. If M2.7 misclassifies a BUGFIX as an UPDATE, it will apply the wiring rule to a bug that just needs a one-line fix — causing over-implementation on the most common task type (50% BUGFIX).

The synthesis says the king has "NO TASK-TYPE STRATEGY section — feature, not bug." Adding a task-type-conditional rule reintroduces the exact pattern the synthesis correctly identifies as harmful.

### Evidence Assessment

| Point | Evidence | Strength |
|-------|---------|---------|
| v73 had nearly identical wiring rule | STEP1 Section 8 | CONFIRMED |
| v73 wiring rule was removed as harmful (possibly) | ROOT_CAUSE v74 | CONDITIONAL — can't isolate |
| King succeeds on UPDATE without wiring rule | STEP1 Section 3 | CONFIRMED |
| Rule applies only to UPDATE/FEATURE correctly | No task-type detection mechanism | UNCONFIRMED |

### Verdict: CHALLENGED

The proposed wiring rule is a shorter restatement of a v73 addition that was removed. The king achieves better UPDATE WR without this rule. The rule risks over-implementation on BUGFIX tasks if M2.7 misidentifies the task type. The causal link is broken: if the king handles UPDATE without a wiring rule, and our failure is model quality or instruction-following, a wiring rule doesn't address either root cause.

### Modified Recommendation

Instead of a task-type-conditional wiring rule (which reintroduces explicit task-type logic), strengthen the integration cascade bullet that already exists in the plan block:

Current king plan format includes:
> "Integration cascade: if the issue describes a feature spanning multiple concerns... enumerate EVERY required integration point as its own plan row even when the issue does not explicitly bullet them."

If strengthening is needed, add ONE word: "**every**" emphasized, not a new section. This stays within the plan block where it already lives, adds no task-type classification, and doesn't introduce a new rule block. Risk: near zero. Expected improvement: marginal but cleaner than a separate section.

---

## Debate 4: Model Quality Gap — The 24% Win Rate Interpretation

### The Synthesis Claim
"M2.7 raw WR: 24% (DPO Intel D, 40K pairs). This is a structural quality gap — M2.7 with the best SYSTEM_PROMPT is still ceiling-limited."

### Challenge 4A: The DPO Win Rate is Not the Gate Win Rate

Intel D's 24% WR comes from `chosen_label`/`rejected_label` fields in DPO pairs. These pairs were constructed to compare raw model outputs for fine-tuning purposes. The contest is: "given this instruction, which model's raw output do judges prefer?"

**Critical distinction:** In the gate, the execution flow is:
1. Validator calls our agent (M2.7 + SYSTEM_PROMPT)
2. Our agent runs a multi-step agentic loop (inspection → planning → coding → verification)
3. Result is a PATCH, not a raw model output

The DPO pairs compare SINGLE-SHOT raw model outputs, not multi-step agentic outputs with the king's SYSTEM_PROMPT guidance. The king's SYSTEM_PROMPT adds: plan block structure, integration cascade, AC extraction, multishot retry, coverage nudge, budget pressure prompts. These are AGENTIC SCAFFOLDING that transforms M2.7 raw output into a structured patching process.

The synthesis itself acknowledges: "SYSTEM_PROMPT (king's) + M2.7 = 47.5% WR → worth +23.5 points above M2.7 raw." This means the SYSTEM_PROMPT is already compensating 24% → 47.5%. The remaining gap from 47.5% to king's WR may also be SYSTEM_PROMPT-driven — not additional model quality.

### Challenge 4B: The v74 King Clone Falsifies the "50-Point Structural Gap" Claim

If M2.7 is structurally 50 points worse than the gate king's model, then the gate king MUST be using a much better model. But v74 (king clone, M2.7) achieves 47.5% WR. If the king used opus-4.7 (74% DPO WR) and we used M2.7 (24% DPO WR), we'd expect the gate to reflect this quality difference — our WR would be significantly below 50%, perhaps 30-35%.

47.5% is NOT consistent with competing against an opus-4.7-based agent. It is consistent with:
- (a) Both agents use M2.7, and small SYSTEM_PROMPT differences explain the gap
- (b) The king uses a slightly better model (gpt-5.5 at 50%, not opus-4.7 at 74%)
- (c) The king has subtle SYSTEM_PROMPT advantages that even a clone doesn't perfectly replicate

The 0.137 LLM score gap from v56 duel (king 0.649 vs ours 0.512) IS evidence of a quality gap. But this was v56 (NOT the king clone v74) against a DIFFERENT king (4 kings ago). This data is stale and confounded.

### Challenge 4C: What Model Does the King Actually Use?

This is the central unknown. STEP1 analyzed the king's code (4595L, commit d24c9d30) but did not extract the model configuration. The king's `solve()` signature takes `model=None, api_base=None, api_key=None` — suggesting the model is passed at runtime by the validator, not hardcoded.

If the validator provides the same model to ALL competing agents (as is common in benchmark setups), then BOTH challenger and king use M2.7. The 24% DPO WR is irrelevant. The entire "model quality gap" diagnosis is built on a structural assumption that has not been verified.

From STEP1 Section 2: `solve()` signature shows `model=None`. This is STRONG EVIDENCE the validator injects the model — it's not the agent's choice. Both agents run on whatever model the validator specifies.

### Evidence Assessment

| Point | Evidence | Strength |
|-------|---------|---------|
| M2.7 24% DPO WR in raw pairs | Intel D | CONFIRMED |
| Gate king uses a better model than M2.7 | NOT in STEP1 | UNCONFIRMED |
| v74 47.5% WR inconsistent with 50pt model gap | Logic + v74 result | STRONG |
| Validator injects model (not agent choice) | STEP1: `model=None` parameter | PROBABLE |

### Verdict: REJECTED

The "structural 50-point model quality gap" diagnosis is unconfirmed and inconsistent with the v74 result. The DPO win rate measures raw model output quality in isolated pairs — not gate performance with agentic scaffolding. The `model=None` parameter in `solve()` suggests the validator injects the model for ALL agents, meaning both challenger and king use the same underlying model.

This doesn't mean model quality is irrelevant — it means the 24% DPO WR tells us nothing actionable about the gate. The actual quality gap, if any, is much smaller than 50 points and may be entirely explained by SYSTEM_PROMPT differences.

### Modified Recommendation

Before any SYSTEM_PROMPT changes, determine what model the validator injects:
```bash
grep -n "model=\|api_key=\|api_base=\|claude\|gpt\|opus\|m2\.7\|minimax" \
  /root/sn66-ninja/king_agent.py | grep -v "^#" | head -20
```
Also check how the validator calls the agents:
```bash
grep -n "model\|solve\|agent" /root/sn66-ninja/validator_harness_v6.py | head -30
```

If both use the same model → SYSTEM_PROMPT changes are the ONLY lever. Focus there.
If king specifies a better model → model upgrade is the fix; SYSTEM_PROMPT changes are marginal.

This is 5 minutes of investigation that determines whether the entire synthesis is correctly framed.

---

## Debate 5: Confidence Level — Gate Threshold Error

### The Synthesis Claim
"MEDIUM confidence of reaching ≥60% gate with SYSTEM_PROMPT alone (estimated 53–58%)."

### Challenge 5A: The Gate Threshold Is ≥70%, Not ≥60%

From AGENTS.md (James directive 2026-05-17):
> **Gate test policy (James directive 2026-05-17): 100-task gate ONLY. Skip 25-task. Threshold ≥70%.**

The ROOT_CAUSE_SN66_v75 synthesis states throughout: "≥60% gate threshold" and in the build spec: "Threshold: ≥60% decisive WR (gate policy per AGENTS.md directive 2026-05-17)."

**This is WRONG.** The threshold per the 2026-05-17 directive is ≥70%, not ≥60%. The synthesis misread or misremembered the threshold.

The estimated combined WR with all 3 changes is 55.5% (synthesis Table in Section 4). This is:
- 4.5 points BELOW the wrong threshold (60%)
- 14.5 points BELOW the correct threshold (70%)

At the correct threshold, the synthesis's own estimates show the proposed changes fall dramatically short. The synthesis recommends submitting if gate result is 55-59%, declaring "partial success." With a 70% threshold, 55-59% is not partial success — it's a clear gate failure that should trigger a full rebuild cycle.

### Challenge 5B: Live Duel WR vs Gate WR — Different Distributions

The win_margin=3 parameter applies to LIVE DUELS (STEP1 Section 4: "live validator CLI override"). This means: in live duels, net wins must exceed losses by >3. For gate tests (our local harness), win_margin is not in play — it's straight WR.

The synthesis mixes these contexts: "55 wins and 45 losses = net +10, which clears the margin." This math applies to live duels, not gate tests. Gate tests simply require ≥70% WR (per the directive). There's no win_margin grace in the gate.

STEP1 Section 6 shows: only 16% of live duels achieve >60% WR, and only 4% achieve >70%. Getting ≥70% in the gate with SYSTEM_PROMPT changes alone is a 4% success-rate territory achievement. The synthesis's "MEDIUM confidence" understates how hard this is.

### Challenge 5C: The Synthesis's Own Combined WR Estimate

The synthesis projects 55.5% combined WR (Section 4 table). This is:
- Based on +3.5% from AC checklist change
- Based on +4.5% from wiring rule
- Added to 47.5% baseline

But Debates 2 and 3 above argue both changes are unlikely to deliver their estimated gains. The AC checklist is redundant with existing dynamic AC extraction. The wiring rule risks regression on BUGFIX tasks. If both changes deliver zero net improvement, WR stays at 47.5% — 22.5 points below the correct 70% threshold.

Even if both changes work as estimated (55.5%), that's 14.5 points below 70%. The synthesis acknowledges this is below their own (wrong) threshold of 60%. Under the correct 70% threshold, reaching ≥70% with SYSTEM_PROMPT changes alone would require the changes to contribute +22.5 points — almost 5× what the synthesis estimates.

### Evidence Assessment

| Point | Evidence | Strength |
|-------|---------|---------|
| Gate threshold is ≥70% | AGENTS.md James directive 2026-05-17 | CONFIRMED |
| ROOT_CAUSE uses ≥60% threshold | ROOT_CAUSE Section 4 + build spec | CONFIRMED ERROR |
| Estimated 55.5% falls below 70% | Math | CONFIRMED |
| Changes can deliver +22.5% above baseline | None | REFUTED |

### Verdict: REJECTED

The synthesis has the wrong gate threshold. The correct threshold (≥70%) renders the synthesis's entire v75 plan insufficient on its own terms — the maximum estimated WR (55.5%) is 14.5 points below the pass line. The synthesis's recommendation to "submit if gate shows 55-59%" would mean submitting something that fails the gate threshold by a large margin.

### Modified Recommendation

Given ≥70% is the correct threshold:
1. Accept that SYSTEM_PROMPT changes alone are unlikely to reach ≥70% with M2.7 execution
2. The honest recommendation is: run the gate knowing it will likely fail at 47-56%, use the results to inform fine-tune training priorities, and escalate to model upgrade decision with James
3. Do NOT submit on a 55-59% gate result — that's below both the correct threshold AND the existing SN66 directives

---

## Cross-Cutting Findings Not Addressed by Synthesis

### Finding A: Challenger Bias Collapse Was Not Explained

The synthesis notes: "v74 expected ~90% WR based on challenger bias hypothesis, actual was 47.5%." It dismisses this as "sampling artifact from 10-task test." But the 90% WR hypothesis was the ENTIRE justification for v74 being a useful baseline measurement.

If the challenger bias doesn't exist (or is ~2-3%, not 45%), then:
- The "47.5% baseline" includes a small challenger bias contribution
- Our true performance may be BELOW 47.5% in live duels where the bias doesn't apply
- The live duel average for challengers is ~45-50% (STEP1 Section 6: median WR ~45-50%)

47.5% in the gate with a slight challenger bias could mean ~44-46% in live duels. This hasn't been addressed and changes how we should interpret the "starting point."

### Finding B: Task Distribution Mismatch Between Gate and Live Duels

STEP1 Section 7 shows:
- Gate (seed=42): 50% BUGFIX, 19% FEATURE, 13% UPDATE, 10% API, 5% REFACTOR
- Live duels: ~40% BUGFIX, ~22% FEATURE, ~14% UPDATE, ~10% API, ~14% OTHER

The gate OVER-REPRESENTS BUGFIX (50% vs 40% live) and UNDER-REPRESENTS OTHER (5% vs 14%). If our BUGFIX performance is our strongest suit (50% WR), the gate will systematically report better WR than live duels. Any gate result will be ~2-3% optimistic vs live performance on this distribution mismatch alone.

This means: if gate shows 57%, live WR is likely ~54%. Even further from ≥70%.

---

## Final Recommendations (Post-Debate)

### Two Highest-Confidence Changes for v75 (Surviving Debate)

**Recommendation 1: Verify What Model the Validator Injects (5 minutes, highest ROI)**

Before writing a single line of SYSTEM_PROMPT changes:
```bash
grep -n "model\|solve\|api_key" /root/sn66-ninja/validator_harness_v6.py | head -20
grep -n "model=\|api_base=" /root/sn66-ninja/king_agent.py | head -10
```

If the validator injects the same model for both agents → SYSTEM_PROMPT changes are the only lever.
If king hard-codes a better model → model upgrade first, then SYSTEM_PROMPT.

This 5-minute check validates or invalidates the entire synthesis.

**Recommendation 2: Strengthen Inspection-to-Edit Ratio (STEP1 Recommendation #3 — Survives All Debates)**

STEP1 explicitly says: "King wins on quick targeted edits vs our agents spending extra steps on inspection. The king's INSPECTION STRATEGY is explicit: 'Preloaded snippets first, then ONE or TWO focused searches.'"

This recommendation:
- Comes directly from STEP1 source intel (not DPO phrase counts)
- Targets the 0.137 LLM score gap that comes from PATCH QUALITY, not task coverage
- Does NOT add task-type classification or new rule blocks
- Aligns with the king's "smallest correct change" philosophy
- Cannot cause regression — it reinforces existing king behavior

**What this looks like:** Strengthen the INSPECTION STRATEGY language:
> "Preloaded snippets first, then AT MOST TWO focused searches. If you have not started your first edit by step 3, you are over-inspecting — stop and write the patch."

This is ≤2 lines, targets a concrete failure mode identified by STEP1, and does not contradict any existing rule.

### What Additional Data Would Resolve Remaining Uncertainties

| Question | How to Get the Answer | Impact |
|----------|----------------------|--------|
| What model does validator inject? | `grep model validator_harness_v6.py` | Changes entire diagnosis |
| Does AC checklist change plan execution? | Run 20-task gate with/without checklist | Validates Change 1 |
| Does wiring rule cause BUGFIX regression? | Run 10-task BUGFIX-only gate with wiring rule | Validates Change 2 |
| What is actual WR by task type in v74 gate? | Analyze v74 gate log with task-type breakdown | Quantifies where to focus |
| Is 47.5% gate WR = 45% live WR (challenger bias)? | Compare gate WR vs live duel WR when we have both | Calibrates baseline |

### Honest Assessment of v75 Outcome

If the synthesis's proposed changes (AC checklist + wiring rule) are implemented and the gate achieves 53-58% WR:

- Against the CORRECT threshold (≥70%): **CLEAR GATE FAILURE** — do not submit
- Next step: use gate results to identify where gains are real, escalate to James with model upgrade decision
- Fine-tuned M2.7 on gold data (the synthesis's "long-term fix") is actually the SHORT-TERM priority given the gate threshold gap

If the model investigation (Recommendation 1 above) reveals the validator injects M2.7 for both agents:
- The SYSTEM_PROMPT difference is the ONLY explanation for any WR gap
- The AC checklist and wiring rule become higher-confidence candidates because they're the only available lever
- Even so, +22.5% from SYSTEM_PROMPT changes is beyond any documented precedent

**Bottom line:** The synthesis is coherent but built on an unverified model assumption and uses the wrong gate threshold. Fix both before building.

---

*Debate complete. Five debates: 2 CHALLENGED, 2 REJECTED, 1 CONFIRMED (scoring sentence preservation). Model investigation and inspection-to-edit ratio are the highest-confidence next steps.*
