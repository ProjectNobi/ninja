# KS43 Deep Intel — Gate Logs, Cull Analysis, API Findings
**Branch:** `kingslayer/ks43-plan`
**Compiled:** 2026-07-10 09:02 UTC by T68Bot
**Requested by:** A Hung (3 specific questions)

---

## ITEM 1: KS42 Real Gate Data (from server logs)

### Status of gate logs
All 4 KS42 gate runs were **incomplete** (partial runs, none reached task 50/50).
These are pre-cull runs (run 2026-07-09 ~18:42–20:42 UTC, cull hit ~22:00 UTC).
Not directly comparable to post-cull runs.

| Seed | Log file | Tasks completed | W/L | ch_mean (partial) | k_mean (partial) | delta |
|------|----------|-----------------|-----|-------------------|-----------------|-------|
| s42 | `ks42_s42_20260709_2042.log` | **15/50** | 11W-4L | 0.3893 | 0.3893 | +0.0000 |
| s7 | `ks42_s7_20260709_1844.log` | **39/50** | 23W-16L | 0.3679 | 0.3308 | +0.0372 |
| s99 | `ks42_s99_20260709_1844.log` | **38/50** | 20W-17L (1 tie) | 0.3468 | 0.3355 | +0.0113 |
| s123 | `ks42_s123_20260709_1844.log` | **39/50** | 24W-14L (1 tie) | 0.4228 | 0.3882 | +0.0346 |

**Important:** These are pre-cull runs but the mean scores (~0.34–0.43) already look
post-cull-like. The old king was scoring 0.69–0.75 in live duels just hours before.
This strongly suggests the **task pool had already shifted** before KS42's gate ran,
OR the gate model routing differs from the live validator routing.

⚠️ **Key finding:** KS42's gate king_mean (~0.33–0.39) is much lower than the same king's
live duel mean (0.68–0.75 in Jul 9 15:58–21:07 duels). The gate harness and live
validator are scoring the same king very differently. This explains the live/gate gap.

### KS42 per-task breakdown (seed s7, 39 tasks — most complete)

| Task | Type | Lang | Ch | King | Result |
|------|------|------|----|------|--------|
| 1 | BUGFIX | TypeScript | 0.220 | 0.170 | WIN |
| 2 | BUGFIX | TypeScript | 0.550 | 0.630 | LOSS |
| 3 | BUGFIX | TypeScript | 0.270 | 0.200 | WIN |
| 4 | BUGFIX | Rust | 0.380 | 0.280 | WIN |
| 5 | BUGFIX | JavaScript | 0.520 | 0.780 | LOSS |
| 6 | API/ROUTE | TypeScript | 0.580 | 0.000 | WIN |
| 7 | API/ROUTE | Java | 0.280 | 0.180 | WIN |
| 8 | BUGFIX | Python | 0.100 | 0.060 | WIN |
| 9 | BUGFIX | TypeScript | 0.120 | 0.200 | LOSS |
| 10 | FEATURE | Other | 0.360 | 0.280 | WIN |
| 11 | BUGFIX | Go | 0.000 | 0.080 | **LOSS (0.000 — timeout/empty)** |
| 12 | BUGFIX | Python | 0.380 | 0.570 | LOSS |
| 13 | API/ROUTE | JavaScript | 0.800 | 0.680 | WIN |
| 14 | BUGFIX | Python | 0.220 | 0.350 | LOSS |
| 15 | BUGFIX | TypeScript | 0.280 | 0.220 | WIN |
| 16 | BUGFIX | Rust | 0.480 | 0.100 | WIN |
| 17 | FEATURE | TypeScript | 0.480 | 0.280 | WIN |
| 18 | UPDATE | TypeScript | 0.140 | 0.180 | LOSS |
| 19 | BUGFIX | Go | 0.540 | 0.280 | WIN |
| 20 | FEATURE | Python | 0.500 | 0.350 | WIN |
| 21 | UPDATE | Python | 0.350 | 0.400 | LOSS |
| 22 | API/ROUTE | TypeScript | 0.220 | 0.100 | WIN |
| 23 | BUGFIX | Other | 0.160 | 0.280 | LOSS |
| 24 | BUGFIX | Rust | 0.120 | 0.050 | WIN |
| 25 | FEATURE | TypeScript | 0.380 | 0.600 | LOSS |
| 26 | BUGFIX | JavaScript | 0.770 | 0.720 | WIN |
| 27 | UPDATE | PHP | 0.300 | 0.360 | LOSS |
| 28 | BUGFIX | TypeScript | 0.450 | 0.600 | LOSS |
| 29 | BUGFIX | PHP | 0.480 | 0.180 | WIN |
| 30 | BUGFIX | Python | 0.100 | 0.180 | LOSS |
| 31 | FEATURE | Other | 0.380 | 0.220 | WIN |
| 32 | BUGFIX | TypeScript | 0.140 | 0.080 | WIN |
| 33 | API/ROUTE | JavaScript | 0.470 | 0.380 | WIN |
| 34 | FEATURE | JavaScript | 0.780 | 0.700 | WIN |
| 35 | BUGFIX | TypeScript | 0.160 | 0.340 | LOSS |
| 36 | UPDATE | Python | 0.380 | 0.520 | LOSS |
| 37 | BUGFIX | Python | 0.320 | 0.380 | LOSS |
| 38 | BUGFIX | JavaScript | 0.670 | 0.580 | WIN |
| 39 | BUGFIX | TypeScript | 0.520 | 0.360 | WIN |

**s7 type breakdown (39 tasks):**
- BUGFIX: 14W-12L = 53.8% (weak)
- FEATURE: 5W-2L = 71.4% ✅
- API/ROUTE: 4W-0L = 100% ✅
- UPDATE: 0W-4L = 0% ❌❌
- Other: 0W-1L ❌

**Notable s7 losses:**
- Task 11 (Go BUGFIX): scored 0.000 — timeout or empty patch
- Task 25 (TypeScript FEATURE): 0.380 vs king 0.600 — large gap
- Task 28 (TypeScript BUGFIX): 0.450 vs king 0.600
- Task 5 (JavaScript BUGFIX): 0.520 vs king 0.780 — king dominated

### KS42 per-task (seed s123, 39 tasks)

Seed s123 was our best partial gate (24W-14L, delta +0.0346). Per-task rows in the git log.
Notable: 2 tasks where king scored 0.850+ (tasks 3 and 8) — both losses.

---

## ITEM 2: Task Cull — Confirmed Shipped, Token Formula Still TBD

### Cull confirmation: **YES, shipped ~22:00–01:00 UTC Jul 9→10**

Evidence from live duel API score analysis:

| Period | Duels | King mean avg | Ch mean avg |
|--------|-------|--------------|-------------|
| Jul 9 15:58–21:07 (pre-cull) | 22 duels | **0.6972** | 0.6669 |
| Jul 9→10 22:00+ (post-cull) | 18 duels | **0.4364** | 0.4422 |

**Score drop: king mean 0.70 → 0.44 (-0.26 absolute).** This is not a king change —
UID 130 was king throughout. The task pool changed. Tasks scoring >70% were culled.

**Exact cull timing** (from db_duel_id sequence):
- db=399: 21:07 UTC, king=0.6610 — still pre-cull scores
- db=400: 01:19 UTC (next day) — king=0.3856, first post-cull scores
- Gap: ~4h between db=399 and db=400 = cull deployed during that window

**What this means for KS42's gate runs:**
- KS42 gate started at ~18:42 UTC (db_id ~391 era)
- Pre-cull task pool → gate scores in 0.33–0.43 mean range
- BUT: live duels during the same window show king scoring 0.66–0.75
- **Conclusion: gate harness uses a DIFFERENT task pool than live validator**
- Gate uses R2 dataset locally; live validator draws from the live pool
- The cull only affects the LIVE pool, not our local gate R2 dataset

### Token efficiency formula: **NOT YET PUBLISHED**

Original intel (commit ac4ea7b, 2026-07-09 22:15 UTC):
> "our goal is now not to just build the best harness, but build the best *token efficient*
> harness. this is very important and an untapped area in the market. i believe this is how we
> grow katana."

**Status:** "Exact formula TBD" at time of commit. No further published update found in:
- MINER_SUBMISSION_CHECKLIST.md
- git log (no new token formula commits)
- Public API data (no token_count field in duel API response)

**What we DO know:**
- Directional: within 5% quality → lower token usage wins
- It's described as "incoming" — may not be live yet
- The cull is live; the token formula may follow separately

**Recommendation:** Ask SN66 team directly for the formula. Check ninja66.ai Discord/Telegram
for any announcement after 22:15 UTC Jul 9.

---

## ITEM 3: Authenticated Duel Endpoint — Hard Cap at 40, No Auth Found

### API investigation results

| Endpoint | Cap | Notes |
|----------|-----|-------|
| `GET /api/duels?limit=N` | **40 hard cap** | limit>40 ignored, always returns 40 |
| `GET /api/dashboard/duels?limit=N` | **40 hard cap** | Same data, same cap |
| `GET /duels/{id}.json` | **403 Forbidden** | No public access |
| Pagination via `offset=N` | ✅ Works | But only shifts the 40-row window |
| Pagination via `page=N` | Same 40 rows | No effect |
| Auth headers | Not found | No ninja66 API key in secrets |

**Total duels in DB:** 417 (as of 09:02 UTC)
**Accessible via API:** ~40 most recent = ~16 hours of history
**Inaccessible:** duels db_id 1–377 (everything before ~Jul 9 15:58 UTC)

### What we CAN reconstruct

From the accessible window (40 duels, db_id 378–417):

**Pre-cull era sample (db_id 378–399, Jul 9 15:58–21:07):**
- 22 duels, all vs king UID 130
- King mean: 0.650–0.800 (avg 0.697)
- Challenger mean: 0.670–0.748 (avg 0.667)
- King defended all 22 successfully
- KS42 duel (db=404): king=0.4198, KS42=0.3754 → LOST (already post-cull-score era!)

**Post-cull era (db_id 400+, Jul 10 01:19+ UTC):**
- 18 duels, king UID 130 then UID 215
- King mean: 0.38–0.53 (avg 0.436)
- db=405: UID 215 takes throne (delta +0.0832)

**Key discovery:** KS42's live duel (db=404, 02:29 UTC Jul 10) was already in
the POST-CULL era. The king was scoring 0.4198 (not the pre-cull 0.69+).
KS42 scored 0.3754 — still lost in the post-cull environment.

### Why we can't measure cull effect on full 417 duels

Without auth/API key access to duels db_id 1–377, we cannot:
- Compute pre-cull mean score distribution across all task types
- Measure which specific task categories were culled
- Compare KS42 gate (pre-cull R2 tasks) to post-cull live task distribution

**Options to get full history:**
1. Ask SN66 team for validator DB access or authenticated API key
2. Use the `scripts/sn66_backfill_5005_5525.py` approach (if individual duel JSON accessible)
3. Check if ninja66.ai Discord has historical export

---

## SUMMARY TABLE

| Item | Status | Finding |
|------|--------|---------|
| KS42 gate logs | ✅ Found | All 4 seeds partial; s7 (39/50), s99 (38/50), s123 (39/50), s42 (15/50) |
| KS42 gate comparable? | ⚠️ Caveat | Pre-cull R2 pool; gate scores ~0.34–0.42, vs live 0.44+ post-cull |
| Cull shipped? | ✅ Confirmed | Between 21:07 UTC Jul 9 and 01:19 UTC Jul 10; score drop 0.70→0.44 |
| Token formula | ❌ TBD | "Incoming" as of Jul 9 22:15 UTC; formula not yet published |
| Auth duel endpoint | ❌ Not found | Hard cap 40 rows, no auth key for full 417 duels |
| KS42 live duel era | ✅ Identified | Post-cull (02:29 UTC Jul 10); king already at 0.4198 not 0.70 |

---

## IMPLICATION FOR KS43

1. **Gate baseline is now wrong:** KS42's gate (pre-cull R2) cannot be compared directly
   to live post-cull performance. Need a fresh gate run post-cull — but our local R2
   dataset hasn't been updated. The live task pool is now harder (70%+ tasks removed).

2. **KS42 scored 0.3754 in post-cull live env** → our agent underperforms even the
   post-cull king (~0.44 avg). Gap to close: ~0.10+ absolute mean.

3. **Token formula unknown** → design conservatively: assume it's live, build token-efficient
   first, not last.

4. **Full duel history inaccessible** → ask SN66 team for API auth OR compute cull impact
   from what we have (n=22 pre-cull vs n=18 post-cull in our window).
