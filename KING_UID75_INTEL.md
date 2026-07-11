# King UID75 Intel — Captured 2026-07-11 11:55 UTC

## Identity
- **UID:** 75
- **Hotkey:** `5Dt3utA2SbttmEUbtCCiWd5Aa3WXcGvkPb2xR6YnQH7QzRQw`
- **Repo:** `private-submission/5Dt3utA2SbttmEUb` (private, code inaccessible)
- **Crowned:** 2026-07-10 22:39:40 UTC
- **Dethrone duel:** db=463, public_duel_id=845955

## Throne Duel Analysis (vs UID237, the previous king)
- **Rounds:** 100 (Pool1: 50 + Pool2: 50)
- **Result:** Challenger (UID75) wins 63 / Losses 29 / Ties 8 → **king_replaced = True**
- **UID75 score:** Pool1 mean = 0.6102 | Pool2 mean = 0.5582 | **Overall = 0.5842**
- **UID237 score:** Pool1 = 0.4428 | Pool2 = 0.4436 | Overall = 0.4432
- **Delta:** +0.1146 — dominant win

## Performance Profile (Throne Duel — UID75)
Bimodal distribution:
- 0.0–0.1: 7 tasks (7%) — hard fails, zeros recorded
- 0.1–0.3: 12 tasks (12%)
- 0.3–0.5: 17 tasks (17%) — mid-range struggles
- 0.5–0.7: 21 tasks (21%)
- 0.7–0.9: 39 tasks (39%) — strong zone
- 0.9–1.0: 4 tasks (4%)

**Key insight:** UID75 is strong on easy/medium tasks (scores 0.7+) but has genuine zeros on hard tasks. This is a vulnerability — tasks where UID75 scores 0.0–0.2 are where we can win rounds.

## Defense Record (17 duels, as of 2026-07-11 11:55 UTC)
All 17 defenses held. Mean king score: 0.4624 (range: 0.4382–0.4966)

| db | Challenger UID | King | Challenger | Delta | Outcome |
|----|---------------|------|-----------|-------|---------|
| 464 | 65 | 0.4966 | 0.4620 | -0.0346 | ✅ HELD |
| 465 | 45 | 0.4864 | 0.4412 | -0.0452 | ✅ HELD |
| 466 | 80 | 0.4924 | 0.4030 | -0.0894 | ✅ HELD |
| 467 | 197 | 0.4636 | 0.3892 | -0.0744 | ✅ HELD |
| 468 | 240 | 0.4682 | 0.3778 | -0.0904 | ✅ HELD |
| 469 | 72 | 0.4642 | 0.4174 | -0.0468 | ✅ HELD |
| 470 | 194 | 0.4650 | 0.4350 | -0.0300 | ✅ HELD |
| 471 | 214 | 0.4476 | 0.4262 | -0.0214 | ✅ HELD |
| **472** | **83** | 0.4426 | **0.5044** | **+0.0618** | ✅ HELD |
| 473 | 142 | 0.4468 | 0.3866 | -0.0602 | ✅ HELD |
| 474 | 158 | 0.4786 | 0.4634 | -0.0152 | ✅ HELD |
| 475 | 167 | 0.4654 | 0.3750 | -0.0904 | ✅ HELD |
| 476 | 146 | 0.4454 | 0.4252 | -0.0202 | ✅ HELD |
| 477 | 106 | 0.4382 | 0.3784 | -0.0598 | ✅ HELD |
| 478 | 144 | 0.4606 | 0.3748 | -0.0858 | ✅ HELD |
| 479 | 145 | 0.4556 | 0.3624 | -0.0932 | ✅ HELD |
| 480 | 42 | 0.4432 | 0.4628 | +0.0196 | ✅ HELD |

**Closest threats:** UID83 (+0.0618), UID42 (+0.0196) — both insufficient

## Dethrone Requirements
- King defense mean: **0.4624**
- 10% margin rule → need **≥ 0.5086 mean** consistently
- Safe target: **0.53+ mean** (accounts for UID75 variance)
- Our current KS42 gate scores: ~0.37–0.42 → gap of ~+0.09–0.11
- UID75's own throne score was 0.5842 — the field is getting stronger

## Our Status vs UID75
- None of our UIDs (177, 68, 225, 62) have dueled UID75 yet
- Must score 0.53+ mean to dethrone
- KS43 (token-efficient) is next submission candidate

## Strategy to Beat UID75
1. **Hard task exploitation:** UID75 has genuine zeros on hard tasks. Our harness must not zero those same tasks.
2. **Consistency over peaks:** UID75 is inconsistent (0.44–0.50 in defense). We need a stable 0.53 floor.
3. **Token efficiency:** Under SN66 team's new rule, within 5% quality → lower tokens wins. KS43 directly addresses this.
4. **Phase 3 gate first:** Confirm KS43 token delta vs KS39/KS42 before submitting.
