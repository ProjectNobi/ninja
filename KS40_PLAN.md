# KingSlayer40 (KS40) — Comprehensive Build Plan
**Date:** 2026-07-09  
**Author:** T68Bot + A Hung  
**Context:** KS39 duel 946782 — lost by delta +0.044 vs threshold +0.050. Missed by 0.006 (0.30 pts across 50 rounds). KS39 holds the record as the highest-scoring challenger ever (mean 0.729) across 40 duels. King UID 130 has never been dethroned.

---

## 🔬 Failure Analysis — KS39 Duel 946782

### Score Summary
| Metric | KS39 | King |
|--------|------|------|
| Mean score | **0.7290** | 0.6850 |
| Delta | **+0.0440** | — |
| Threshold needed | **+0.0500** | — |
| Gap to throne | **-0.0060** | — |
| W/L/T | 25/17/8 | — |
| Rounds ≥ 0.80 | 18/50 (36%) | 16/50 (32%) |
| Rounds < 0.30 | **5/50 (10%)** | 6/50 (12%) |

### Score Distribution
| Band | KS39 | King | Delta |
|------|------|------|-------|
| 0.00 (zero) | 1 | 1 | tied |
| 0.01–0.29 (near-zero) | **4** | 5 | we lose less |
| 0.30–0.49 | 4 | 6 | we win |
| 0.50–0.69 | 6 | 6 | tied |
| 0.70–0.89 | 17 | 16 | we win slightly |
| 0.90–1.00 | **18** | 16 | **we win** |

---

## 🔴 Failure Categories — 3 Root Causes

### ROOT CAUSE 1 — Near-Zero Rounds (PRIMARY, highest ROI fix)
**5 rounds scored 0.00–0.22: R1(0.15), R3(0.15), R13(0.22), R16(0.00), R47(0.20)**

Pattern: Both agents score low (king 0.25–0.35 on same rounds). These are **genuinely hard tasks** — but king ekes out 0.25–0.35 while we score 0.00–0.22.

Root cause hypothesis:
- Agent bails too early on unfamiliar task/language patterns → produces empty or trivially wrong patch
- Timeout on hard repo setup tasks → patch never lands
- Scope confusion → edits wrong file → judge scores near zero despite syntactically correct patch

**Impact: fixing these 5 rounds from avg 0.14 → avg 0.50 = +1.80 points = dethrone comfortably**

---

### ROOT CAUSE 2 — Hard Task Ceiling (KING'S MOAT)
**6 hard-loss rounds: R8(us=0.72 king=0.90), R24(us=0.45 king=0.92), R33(us=0.55 king=0.82), R40(us=0.72 king=0.95), R41(us=0.60 king=0.85), R42(us=0.60 king=0.88)**

Pattern: 3 consecutive losses R40-41-42 suggest a specific task-type cluster (possibly same repo/language batch). King dominates by 0.18–0.47 margin on these.

Root cause hypothesis:
- King's `reroll.py` (344L, added to bundle) — likely a re-attempt/retry strategy on hard tasks that we don't have
- King's `agent_loop.py` is 295L with more sophisticated loop logic
- King may do multi-attempt solve with partial diff merging

**Impact: improving these 6 rounds by avg +0.15 each = +0.90 pts = dethrone**

---

### ROOT CAUSE 3 — Narrow Win Margins (LOWER PRIORITY)
**7 wins by ≤0.05 margin: R9(+0.05), R17(+0.04), R20(+0.05), R21(+0.03), R23(+0.03), R36(+0.04), R39(+0.05)**

These are fragile wins. If any 2 flip to losses, we drop below threshold. Converting to 0.10+ margins adds safety buffer.

**Impact: widening 7 narrow wins by avg +0.07 each = +0.49 pts buffer**

---

## 🏆 Competitor Intelligence

### All Top-5 Challengers Compared
| Challenger | Delta | Mean | Zeros | Low | High |
|-----------|-------|------|-------|-----|------|
| UID 94 | +0.048 | 0.678 | 4 | 10 | 53/100 |
| UID 154 | +0.047 | 0.714 | 1 | 4 | 27/50 |
| **KS39 (UID 68)** | **+0.044** | **0.729** | **1** | **4** | **18/50** |
| UID 49 | +0.037 | 0.725 | 1 | 4 | 27/50 |
| UID 164 | +0.025 | 0.716 | 1 | 4 | 26/50 |

### Key Intel: UID 154 (Previous Best)
- Same zero/low count as KS39 but scored delta +0.047 vs our +0.044
- **Lower overall mean (0.714 vs 0.729) but fewer hard-task collapses**
- Their agent appears better at "graceful degradation" — when hard task hits, scores 0.40-0.55 instead of 0.22
- Study pattern: they lost R30(0.05 vs 0.60) and R35(0.20 vs 0.50) — partial credit even in failures

### King's Actual Weaknesses (EXPLOITABLE)
- King scores <0.35 on 6 rounds in our duel: R1(0.25), R3(0.30), R13(0.30), R16(0.25), R47(0.35), R50(0.00)
- These overlap exactly with OUR low rounds — both struggle on same tasks
- **KS40 opportunity:** on tasks where both score low, be the one who scores 0.45 instead of 0.22
- King's R50 zero (0.00) while we got 0.45 = partial credit extraction works — need more of this

### Universal Pattern Across ALL Challengers
Every top challenger (94, 154, 49, 164, KS39) has:
- 1–4 near-zero rounds on the SAME categories of hard tasks
- King consistently outperforms by 0.05–0.15 on those exact rounds
- **Conclusion: there is a specific hard-task class where king has a structural edge — possibly `reroll.py` retry logic**

---

## 📋 KS40 Build Plan — Phased Tasks

### PHASE 1: Diagnose Zero/Near-Zero Rounds (Day 1)
> **Goal:** Understand exactly why R1, R3, R13, R16, R47 scored 0.00–0.22

**Task 1.1 — Replay failure rounds locally**
- Use v7 harness with seed matching to reproduce the 5 low-score rounds
- Log full agent transcript: what commands ran, what patch was produced, why judge scored low
- Deliverable: per-round failure report (agent timeout? wrong file? empty patch? syntax error?)

**Task 1.2 — Study king's `reroll.py` (344L)**
- Full read and understand of `/root/sn66-ninja/agent/reroll.py`
- What does it do? Re-attempt logic? Diff repair? Score estimation?
- Document: does this explain king's better floor on hard tasks?

**Task 1.3 — Classify hard task types**
- From round patterns (R40-41-42 consecutive losses), identify the task characteristics
- Hypothesis: infra/config tasks, multi-file refactors, or specific language (Rust/Go)
- Check gate log language breakdown: where did KS39 score lowest by language?

---

### PHASE 2: Architectural Changes (Day 1–2)
> **Goal:** Fix near-zero rounds without regressing current high-score performance

**Task 2.1 — "Graceful Degradation" Mode (HIGHEST PRIORITY)**
- When agent produces patch with score risk indicators (empty diff, wrong file, syntax error):
  - Fall back to minimal correct patch (fix one clear thing, leave rest)
  - Partial credit at 0.45 beats zero at 0.00 every time
  - Rule: "something correct > nothing complete"
- Target: floor lift from avg 0.14 → avg 0.50 on the 5 bad rounds

**Task 2.2 — Reroll/Retry Strategy (Study king's approach)**
- If `reroll.py` implements re-attempt with diff merging → implement equivalent
- KS40 should retry solve() on hard tasks when first attempt produces low-confidence patch
- Bounded: max 1 retry, only when patch quality signals are bad (empty, syntax error, wrong file)
- Do NOT blindly copy king's code — understand the mechanism, implement our own

**Task 2.3 — Hard-Task Detection & Routing**
- Detect task difficulty signals early (large repo, ambiguous scope, infra-heavy)
- Route hard tasks to a more conservative solve strategy:
  - Smaller scope (focus on one explicit requirement)
  - Shorter command sequences (less exploration, more direct edit)
  - Early sentinel if patch is valid but minor — partial credit > nothing

**Task 2.4 — Consecutive-Loss Pattern Fix (R40-41-42)**
- 3 consecutive hard losses suggest a specific task cluster (same repo or task set)
- Hypothesis: our agent gets into a state after timeout/failure that degrades subsequent rounds
- Check: does our agent's state carry over between rounds? It should NOT
- Fix: ensure full reset between rounds — no shared state contamination

---

### PHASE 3: Targeted Improvements (Day 2)
> **Goal:** Improve hard-task ceiling and widen narrow wins

**Task 3.1 — Completeness Gate Tuning**
- KS39's completeness gate fires when `_COMPLETENESS_MIN_STEPS_LEFT ≥ 2` and `≥ 45s` remain
- On hard tasks this may be too aggressive — triggering false gap reports → agent wastes steps on non-issues
- Tune thresholds: only fire if patch is actually incomplete (not just "looks incomplete")
- Deliverable: tighter `_uncovered_criteria()` — reduce false positives by 50%

**Task 3.2 — Narrow Win Hardening**
- 7 wins by ≤0.05 margin — these are fragile
- Root cause: agent produces correct but minimal patch where king produces correct + more complete
- Fix: on tasks where our patch is syntactically valid and covers all explicit criteria, add one more completeness pass
- Target: convert 3 of 7 narrow wins from +0.04 → +0.10 margin

**Task 3.3 — Language/Repo-Type Calibration**
- KS39 gate weakness: BUGFIX tasks at 50% on seed 99, FEATURE at 0% on seed 7
- Investigate: do low rounds correlate with specific language? (check gate logs for R1,R3,R13,R16,R47)
- If Rust/Go/PHP tasks cluster in failures → add language-specific context preloading

---

### PHASE 4: Audit, Debate, Gate (Day 2–3)
> **Full-Pipeline protocol — no shortcuts**

**Task 4.1 — Dragon Lord builds KS40**
- Implement all Phase 2+3 changes
- Must be minimum-change where possible (don't break what works)
- Focus: fix the floor, don't touch the ceiling

**Task 4.2 — A Hung review** ← replaces Opus audit + debate (James directive 2026-07-09)
- A Hung (dev, Microsoft Dublin) reviews KS40 code
- Feedback incorporated if any

**Task 4.3 — 4-seed gate (seeds 42, 99, 7, 123 vs current king)**
- Always sync king first (`L-SN66-HARNESS-SYNC-BEFORE-GATE-1`)
- Target: mean delta ≥ 0.055 on all 4 seeds (buffer above 0.05 threshold)
- If any seed <0.050: do not submit, iterate

**Task 4.5 — James approval → submit**
- No auto-submit (`L-NO-AUTO-SUBMIT-1`)
- Present full 4-seed gate results + Opus audit summary
- Wait for explicit James go-ahead

---

## 🎯 Success Criteria for KS40

| Metric | KS39 (actual) | KS40 (target) |
|--------|--------------|---------------|
| Live duel mean delta | +0.044 | **≥ +0.055** |
| Near-zero rounds (0.00–0.22) | 5 | **≤ 2** |
| Hard-task losses (king ≥0.85, us ≤0.72) | 6 | **≤ 3** |
| Gate mean delta (4-seed avg) | +0.065 | **≥ 0.070** |
| Gate win rate (4-seed avg) | 65.0% | **≥ 68%** |

---

## ⏱️ Timeline

| Day | Milestone |
|-----|-----------|
| Day 1 AM | Task 1.1–1.3: Diagnose zeros, study reroll.py, classify hard tasks |
| Day 1 PM | Task 2.1–2.4: Implement graceful degradation + reroll strategy |
| Day 2 AM | Task 3.1–3.3: Tune completeness gate, harden narrow wins |
| Day 2 PM | Task 4.1–4.3: Dragon Lord builds + Opus audit + debate |
| Day 3 AM | Task 4.4: 4-seed gate runs |
| Day 3 PM | Task 4.5: Present to James → submit if approved |

---

## 📝 Standing Rules (carry forward to KS40)

1. `L-NO-AUTO-SUBMIT-1` — Never submit without James approval
2. `L-SN66-HARNESS-SYNC-BEFORE-GATE-1` — Always verify king SHA + all files before any gate
3. `L-SN66-SUBMISSION-CI-MIN-CHANGE-1` — Only minimum CI fixes in submitted copy
4. `L-SN66-DUEL-AUTOPSY-KS39-1` — Near-zero rounds are the primary loss driver; fix the floor first
5. **NEW: `L-SN66-GRACEFUL-DEGRADATION-1`** — Partial credit (0.45) always beats zero (0.00). Build explicit fallback for hard-task failure modes.
6. **NEW: `L-SN66-REROLL-STUDY-1`** — Study king's `reroll.py` before building KS40 retry logic. Never copy blindly; understand the mechanism.

---

*Built from: KS39 duel 946782 full 50-round autopsy + top-5 competitor cross-analysis (UIDs 94, 154, 49, 164, 96) + 40-duel king survival history*
