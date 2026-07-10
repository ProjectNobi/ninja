# KS43 Plan v2 — A Hung's Final Plan (Reviewed + Verified)
**Branch:** `kingslayer/ks43-plan`
**Plan author:** A Hung
**Verified by:** T68Bot 2026-07-10 09:13 UTC
**Source:** Hung's message 2026-07-10 09:13 UTC

---

## The Calibration Number

**Gate vs live gap — explained.**

| Measure | Gate (s7, 39 tasks) | Live (duel 768292) |
|---------|---------------------|--------------------|
| Our score | 0.3679 | 0.3754 |
| Opponent score | 0.3308 | 0.4198 |
| Delta | +0.0372 | **−0.0444** |

Our score barely moved (+0.0075). The opponent's score moved by **+0.0890**.
The burn baseline (`king_agent.py`, SHA `53bca97cbfe6`) is ~0.089 weaker than the
real king (UID 130) as it performs in the live duel environment.

**Working constant:** gate delta against burn ≈ live delta − 0.089

- Gate delta +0.0372 → live delta −0.044 (confirmed by actual result ✅)
- To dethrone (+0.05 live) → need gate delta ≈ **+0.14 against burn**
- Every gate result in the existing docs was read against a threshold ~3× too lenient

**Caveats (Hung's own):** derived from one duel + one partial gate run.
Treat as working constant to refine, not a law. Right shape, first actionable bar.

---

## Phase 0 — Fix Gate Truncation (BLOCKING)

All four KS42 gate runs were incomplete:
- s42: 15/50 tasks (killed at 22:02 when cull hit, was a 20:42 retry run)
- s7: 39/50 (killed ~22:01, process still running when cull hit)
- s99: 38/50 (killed ~21:59)
- s123: 39/50 (killed ~22:02)

**Root cause:** All four runs were still executing (parallel=2, 600s timeout, 50 tasks
= ~3.25h) when the session was killed around 22:00 UTC Jul 9 (cull deployment window).
The 1842/1843 abort logs show a separate issue: `KS41_TRACE: unbound variable` in
`gate.sh` with `set -euo pipefail` — crashed before harness launched.

**Consequence:** All per-task rows and deltas above are order-biased prefix samples.
The task sequence is deterministic by seed, not random, so early tasks ≠ representative subset.
No gate number is reliable until a run reaches 50/50.

**Fix required:** Run a complete 50/50 gate before any submission decision.

---

## Phase 1 — Instrument Tokens (Every Version, Non-Optional)

The model already accumulates `prompt_tokens` / `completion_tokens` per `Model` instance.
Problem: each `_run_loop` creates a **fresh `Model`**, so counters never sum across:
- The main loop
- The repair sub-loop (`_run_loop` call in repair)
- The polish sub-loop (`_run_loop` call in polish)
- The empty rescue sub-loop

`validator_harness_v7.py` records none of it. Token usage per round is currently invisible.

**Required change:**
- Aggregate token counters across all `Model` instances within a single `solve()` call
- Emit per-task total (prompt + completion tokens) in harness output
- This is needed under every version of this plan — do it before Phase 2, not after

**Why urgent:** token efficiency scoring is described as "incoming." You will be scored
on a quantity nobody currently measures.

---

## Phase 2 — KS43 = KS42 Minus Polish Fallback

**Delete these 4 lines** at `agent_cl_gpt_KingSlayer42.py:1953`:

```python
if reason is None:
    reason = ("polish", "the fix is correct and passes all tests, "
                        "but must be polished: no unrelated churn, "
                        "minimal edits, complete.")
```

**What this does:**
`_repair_reason()` returns `None` when the patch is already clean (correct, tests pass).
KS42 responds to `None` by setting reason = "polish" and launching a second `_run_loop`.
Polish fires on the GOOD case — it's an unconditional extra LLM loop when we're already done.

**Why remove it now:**
The cull deleted tasks scoring >70% from the live pool. Those are exactly the tasks where
both agents were already correct and the king's polish made it "fuller." The tasks that
remain are the harder ones where first-attempt quality is lower — polish on a mediocre
patch is not the same as polish on a near-perfect one.

**What to KEEP:**
- Test-gated repair adoption (free guard, zero extra calls)
- `no_test` branch in `_repair_reason` (costs a sub-loop, but 50–66% of losses trace to
  shipping fixes without a demonstrating test)

**What is NOT KS43:**
KS41's `_run_best_of_two_ks41` calls `_run_loop` twice unconditionally at full `max_steps`
(attempt_b uses wall-constrained budget but inherits the full `config.max_steps` — no
step reduction). It is the most token-expensive of the three options, not the leanest.
The agent history doc has this backwards — corrected here.

---

## Phase 3 — Three-Way Gate: KS39, KS42, KS43

**Gate all three on identical seeds, complete 50/50 runs, two axes: delta and tokens.**

This single run answers:
1. Which base is better post-cull?
2. What does polish actually buy in the new task distribution?
3. What is the token cost of each design choice?

**Submission bar:**
- Gate delta ≥ **+0.14 vs burn baseline** (working constant for +0.05 live)
- On ≥ 2 complete 50/50 seeds
- Gate log filename must contain the agent's own name
- No submission unless the run reached 50/50

---

## Phase 4 — UPDATE Tasks

KS42 s7 (39 tasks verified): UPDATE is **0W-4L** — the only clean categorical weakness.

**Actual type breakdown (verified from log, correcting docs):**

| Type | W | L | T | Win% |
|------|---|---|---|------|
| API/ROUTE | 5 | 0 | 0 | **100%** ✅ |
| FEATURE | 5 | 1 | 0 | **83%** ✅ |
| BUGFIX | 13 | 11 | 0 | 54% |
| UPDATE | 0 | 4 | 0 | **0%** ❌ |

*(Note: doc previously reported FEATURE 5W-2L and UPDATE 5W-2L — both wrong.
Recount from raw log: FEATURE=5W-1L, API/ROUTE=5W-0L, UPDATE=0W-4L. Total=39 outcomes.)*

**Action:** Confirm the 0-for-4 UPDATE pattern survives a complete 50/50 run before
building a targeted fix for it. Could be noise from 4 tasks.

---

## Process Rule (Most Important)

> **Nothing submits unless the gate log filename contains its own agent name and the run reached 50/50.**

KS42 went on-chain carrying KS41's gate numbers. This rule prevents a repeat.

---

## On King Sync

UID 130, UID 215, UID 180 are all `private-submission/…` with `repo_url: null`.
`sync_king.sh` reads `dashboard.json` frozen since **2026-06-23** (17+ days stale).
"Wait for dashboard to update" has not happened and will not happen.

**Resolution (Hung's recommendation):**
- Keep gating against the burn baseline (`king_agent.py` SHA `53bca97cbfe6`)
- Apply the **+0.089 offset** in every gate report — say it out loud
- The burn baseline is fixed, known, reproducible — what a regression gate needs
- Live delta remains the only ground truth
- Ground truth is bought with **submissions, not gate runs**

---

## Summary of Changes vs KS42

| Change | KS43 |
|--------|------|
| Polish fallback (`reason = None → "polish"`) | ❌ REMOVED |
| Test-gated repair adoption | ✅ KEPT |
| `no_test` repair branch | ✅ KEPT |
| Token instrumentation | ✅ ADDED |
| Reroll (`_run_best_of_two`) | ❌ NOT included (most expensive option) |
| UPDATE task fix | ⏳ AFTER Phase 3 confirms pattern |

---

## Corrected Numbers vs Previous Docs

| Claim in previous docs | Corrected value |
|------------------------|-----------------|
| KS42 gate "delta +0.05 against burn = competitive" | ❌ Need +0.14 (burn is 0.089 weaker than live king) |
| KS42 FEATURE: 5W-2L | ❌ Actual: 5W-1L (83%) |
| KS41 "leaner than KS42" | ❌ KS41 reroll calls _run_loop twice at full max_steps — most expensive |
| KS42 UPDATE: 5W-2L | ❌ Actual: 0W-4L (0%) |
| Gate logs reach 50/50 | ❌ All 4 partial (killed by cull deployment ~22:00 UTC Jul 9) |

---

## ⚠️ KING UPDATE — 2026-07-10 07:25:50 UTC

**UID 215 dethroned. New King = UID 180.**

| Field | Value |
|-------|-------|
| New King UID | **180** |
| Hotkey | `5CJ3J7Dr39E36SDampXD3few3vdLXsgkumBV6EYUQLpwrdtd` |
| Repo | `private-submission/5CJ3J7Dr39E36SDa` (no public URL) |
| Throne duel | 838438, db_duel_id=416 |
| Took throne | 2026-07-10T07:25:50 UTC |
| Winning delta | +0.0618 (100 rounds, W=52 L=37 T=11) |
| UID 215 mean | 0.4074 | UID 180 mean | 0.4692 |

**UID 180 defense record so far (2 duels):**
- db=417: vs UID 231 → k=0.4786 ch=0.4788 delta=+0.0002 ✅ (survived by 0.0002)
- db=418: vs UID 9   → k=0.4880 ch=0.4776 delta=−0.0104 ✅

New King scoring ~0.47–0.49 mean — slightly higher than UID 215 (~0.44).
Dethrone target: need **~0.53+ mean** (0.488 avg + 0.05 = 0.538).

**All three plan docs (KS43_PLAN, KS43_AGENT_HISTORY, KS43_PLAN_V2) referenced UID 215 as current king. UID 180 is the correct target as of 07:25 UTC.**

**Burn baseline calibration still holds:** burn opponent is still `king_agent.py` SHA `53bca97cbfe6`. The +0.089 offset was derived from UID 130 live vs burn gate. UID 180 is a new opponent — the offset may differ. First live duel against UID 180 will recalibrate.
