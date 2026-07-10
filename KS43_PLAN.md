# KS43 Plan — Full Intel & Strategy
**Branch:** `kingslayer/ks43-plan`
**Created:** 2026-07-10 08:09 UTC
**Author:** T68Bot (awaiting A Hung review/instructions)

---

## 1. Situation Summary

### 1a. New King (UID 215) — Took Throne 2026-07-10 03:11 UTC

| Field | Value |
|-------|-------|
| UID | 215 |
| Hotkey | `5HKauaiL71XiWn49q3PWPTb8BzcPVAmtT87UzrwXVRfS3sXc` |
| Repo | `private-submission/5HKauaiL71XiWn49` (no public URL) |
| Took throne | 2026-07-10T03:11:44 UTC |
| Throne-winning duel | 589408 (100 rounds, W=51 L=36 T=13) |
| Winning delta | +0.0832 (threshold = 0.05) |
| Winning mean | 0.4738 |
| Old King (UID 130) mean | 0.3906 |

**Dashboard status:** Still showing old SHA `53bca97cbfe6` (unarbos/ninja). Has NOT updated
to UID 215's private submission yet. `sync_king.sh` will give stale king until dashboard refreshes.

### 1b. New King Defense Record (11 duels, as of 08:09 UTC)

| Duel | vs UID | King mean | Challenger mean | Delta | Result |
|------|--------|-----------|-----------------|-------|--------|
| 663650 | 43 | 0.4168 | 0.4180 | +0.0012 | ✅ Defended |
| 367614 | 224 | 0.4354 | 0.4830 | +0.0476 | ✅ Defended |
| 287019 | 207 | 0.4556 | 0.4120 | -0.0436 | ✅ Defended |
| 820745 | 50 | 0.4148 | 0.4096 | -0.0052 | ✅ Defended |
| 310762 | 61 | 0.4012 | 0.4352 | +0.0340 | ✅ Defended |
| 400017 | 83 | 0.4412 | 0.4392 | -0.0020 | ✅ Defended |
| 286898 | 91 | 0.4042 | 0.4366 | +0.0324 | ✅ Defended |
| 936518 | 25 | 0.5346 | 0.5494 | +0.0148 | ✅ Defended |
| 974104 | 105 | 0.4584 | 0.4270 | -0.0314 | ✅ Defended |
| (latest+1) | 180 | ~0.41 | 0.4692 | +0.0618 | ✅ Defended |
| (latest+2) | 224 | ~0.43 | 0.4830 | +0.0476 | ✅ Defended |

**New King stats:**
- Mean score avg: **~0.4443** (range: 0.4012–0.5346)
- Closest dethroner: UID 180 with delta +0.0618 (missed by ~0.01)
- King appears to fluctuate — sometimes scores 0.53+ (strong), sometimes 0.40 (beatable)

**Key insight:** New King is scoring ~0.20–0.27 LOWER than the old King (0.68–0.75 range).
This is a significantly more beatable king. We need ~0.49+ mean to reliably dethrone (+0.05 over ~0.44 avg).

---

## 2. Why KS42 Lost (Duel 768292)

### Duel Facts
| Field | Value |
|-------|-------|
| Duel ID | 768292 |
| Time | 2026-07-10T02:29 UTC |
| King (UID 130) mean | 0.4198 |
| **KS42 (UID 177) mean** | **0.3754** |
| Delta | **-0.0444** |
| W/L/T | 22/24/4 over 50 rounds |
| Result | ❌ KS42 LOST |

### Why KS42 Underperformed vs Gate

**Gate results (seed 42, seed 7, seed 99):** 60–62.5% win rate, mean delta +0.04 to +0.054  
**Live duel mean:** 0.3754 — significantly below the ~0.65–0.70 typical challenger baseline

**Possible root causes:**
1. **Task set mismatch**: Live duel tasks may have included more of KS42's weak task types
   - Gate showed: FEATURE (42.9%) and UPDATE (42.9%) as weak categories for KS42
   - Live may have drawn more FEATURE/UPDATE tasks
2. **The old King (UID 130) was scoring 0.68–0.75 in its defenses** — KS42 at 0.3754 is
   catastrophically low, not just slightly under
3. **Seed 123 gate run was NOT competitive (46.9%, delta -0.033)** — same agent, different
   random seed = very different outcome. Live duels use random task selection too.
4. **Polish pass effectiveness**: KS42 added the polish loop back (from KS39 removal).
   Gate tests with sonnet-4.6 judge, but live judge may evaluate differently.
5. **Model routing**: Live validator proxy may route to a different model than gate's
   `anthropic/claude-sonnet-4.6` — different model = different quality profile.

**Key observation from gate seed variance:**
- Seed 7: delta +0.0538 ✅ (would have dethroned)
- Seed 123: delta -0.0330 ❌ (would have lost badly)
- Same agent, same king, different tasks → **±0.087 swing from task sampling alone**

This confirms the agent needs a higher and more consistent mean score to win reliably
regardless of which task set is drawn. A mean delta of +0.04–0.05 is too fragile.

---

## 3. KS41 Gate Results (for reference)

| Seed | Win Rate | Delta | Verdict |
|------|----------|-------|---------|
| 42 | 60.0% (30W-20L) | +0.0400 | ✅ COMPETITIVE, ❌ below dethrone |
| 7 | 60.0% (30W-20L) | +0.0538 | ✅ COMPETITIVE, ✅ DETHRONE |
| 99 | 62.5% (30W-18L-2T) | +0.0472 | ✅ COMPETITIVE, ❌ below dethrone |
| 123 | 46.9% (23W-26L-1T) | -0.0330 | ❌ NOT COMPETITIVE |

KS41 was not submitted — KS42 was chosen as the submission instead.
KS41 gated against OLD king (53bca97c). New king sync needed before re-gating.

---

## 4. KS43 Strategy (Awaiting A Hung's Instructions)

### Target
- New King avg mean: **~0.4443**
- Dethrone requirement: **+0.05 delta** = need **~0.494+ mean**
- Conservative target: **0.50–0.52 mean** (comfortable margin over king's variance)

### What We Know Works
- KS39 beat the king at mean **0.729** (high-score era, old king family)
- KS42 = KS39 + test-gated repair + polish pass
- KS42 live score 0.3754 is shockingly low — investigation needed

### Hypothesis for KS43
The new King scores ~0.44 mean which is much lower. This could mean:
1. **The task pool has changed** — harder tasks now where both agents score lower
2. **The new King uses a different strategy** that's efficient on token costs
   (recall: SN66 team intel says token efficiency matters within 5% quality)
3. **KS42's polish pass is burning budget** on tasks where first attempt was already
   correct, reducing budget for genuinely hard cases

### Proposed Investigation (for A Hung review)
1. **Sync new King** — wait for dashboard to update, then run `sync_king.sh`
2. **Gate KS42 vs new King** — establish baseline against new opponent
3. **Analyse token usage** — KS42 vs new King token efficiency per task
4. **Check for timeout issues** — KS42 gate seed 123 had 2 timeout losses
5. **Consider KS43 changes**:
   - Token-efficient harness (per team intel: within 5% quality → lower tokens wins)
   - Tighter budget management
   - Better FEATURE/UPDATE task handling (current weakest categories)
   - Investigate why live score (0.3754) is so far below gate score (0.65–0.70)

---

## 5. Current Agent Versions

| Agent | Lines | Base | Status |
|-------|-------|------|--------|
| KS42 (submitted) | 2074L | KS39 + repair + polish | UID 177, lost live duel |
| KS41 (not submitted) | 2362L | KS39 + A Hung reroll | 3/4 seeds competitive |
| KS39 (baseline) | ~1943L | Best known baseline | Mean 0.729 (old king era) |

**On-chain submission:** `ProjectNobi-KingSlayer42` on UID 177

---

## 6. Action Items (Blocked on A Hung)

- [ ] A Hung to review this plan and provide KS43 direction
- [ ] Wait for dashboard to update to new King (UID 215) SHA
- [ ] Run `sync_king.sh` after dashboard refresh
- [ ] Gate KS42 vs new King to get baseline delta
- [ ] Decide: iterate on KS42 base OR start fresh KS43 design
- [ ] Address token efficiency (new SN66 incentive)
- [ ] Investigate live vs gate score gap

---

## 7. SN66 Team Intel (2026-07-09)
- Tasks scoring >70% will be **removed from pool** (incoming change)
- Token efficiency incentive: **within 5% quality → lower token count WINS**
- Priority shift: build token-efficient harness, not just maximally correct one

---

*This plan is a T68Bot intel document. Final KS43 design decisions await A Hung's instructions.*
