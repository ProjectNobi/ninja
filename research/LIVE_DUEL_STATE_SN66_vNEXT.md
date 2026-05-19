# LIVE DUEL STATE — SN66 vNEXT
Generated: 2026-05-19 05:55 UTC

---

## 🔑 CURRENT KING

| Field | Value |
|-------|-------|
| Commit | `d24c9d30fa9191150fe09371` (full: d24c9d30fa9191150fe093717b0660350d7a3538) |
| Runtime | `unarbos/ninja` |
| Source | private-submission |
| King UID | 64 |
| King hotkey | 5CUomfxh84uz... |
| King since | **2026-05-18 19:37 UTC** (yesterday ~10h ago) |
| Duels defended | 21 |
| Local king_agent.py | 4595 lines, updated May 18 20:01 UTC ✅ IN SYNC |

**King is UNCHANGED from d24c9d30. Local king_agent.py is synced.**

Note: This is a NEW king (promoted yesterday at 19:37 UTC). Previous long-reigning king was `fd2af7a6050e` (59 defended duels). New king replaced another short-lived king (6abf172, 0 defended).

---

## ⚡ ACTIVE DUEL RIGHT NOW — KING UNDER THREAT!

| Field | Value |
|-------|-------|
| Duel ID | 5141 |
| Challenger | 5CPnWW8JJ1eVtKmyHCFr7KEc5DqxeKim9Rd3GmY257APmsJk (UID 198) |
| Progress | 32/50 rounds scored |
| Score | **20W / 12L / 2T = +8 margin** |
| Threshold | 16 (net needed = 3+) |

**⚠️ KING IS LIKELY BEING DETHRONED RIGHT NOW.** Challenger leads +8 with 18 rounds remaining. Threshold is +3. King almost certainly falls. A NEW king will be installed shortly.

**Action required: Sync king after duel 5141 completes!**

---

## 🤖 OUR AGENTS DUEL RESULTS

### Duel Scoring Rule
- Method: `race` | 50 rounds | `win_margin: 3`
- **To dethrone: challenger_wins - king_wins > 3** (ties ignored, need NET ≥ +4)
- Scoring: 100% LLM diff judge (claude-sonnet-4.6), Cursor similarity = telemetry only

### Our 4 Agents

| Agent | Duel | Date | W/L/T | Net | WR | Score vs King | Result |
|-------|------|------|-------|-----|----|---------------|--------|
| 5Dqabiz8 (v56) | 5001 | May 17 | 13/25/0 | -12 | 34.2% | 0.483 vs 0.609 | ❌ LOST badly |
| 5FecE3QZ (v54) | 5013 | May 17 | 12/24/0 | -12 | 33.3% | 0.522 vs 0.620 | ❌ LOST badly |
| **5CciPvx7 (v62)** | 5123 | May 18-19 | 24/23/1 | **+1** | **51.1%** | **0.494 vs 0.474** | ❌ Lost by MARGIN (need +4) |
| **5G6JxJQv (v62b)** | 5124 | May 19 | 26/23/0 | **+3** | **53.1%** | **0.497 vs 0.466** | ❌ Lost by MARGIN (need >3) |

### Key Insight: v62/v62b OUTSCORED the king but lost on margin!
- v62b beat the king 26-23 (53.1% WR) AND had higher mean score (0.497 > 0.466)
- But win_margin=3 requires strictly MORE than +3 → need +4 minimum
- **v62b was ONLY 1 round short of dethroning the king**
- This king (d24c9d3) is WEAKER than the previous king (fd2af7a6050e)

### Duel 5001/5013 vs Old King (May 17): Different king!
- These duels ran BEFORE current king was promoted (May 18 19:37)
- Against stronger previous-era king(s), lost badly at ~33-34%
- Not representative of v62 potential against current king

---

## 📊 CRITICAL ANALYSIS

### Why v62 didn't dethrone despite winning more rounds:
The `win_margin=3` rule requires net wins > 3 (i.e., ≥ 4). 
v62b got +3 (26W-23L) — one round short.

### King is already being beaten (duel 5141):
Another challenger (5CPnWW8) currently leads +8 in 32/50 rounds. When this duel ends (~minutes), there will be a NEW king. This means:
1. Our king_agent.py will be stale again immediately
2. The new king may be harder or easier to beat
3. We need to monitor and resync after duel 5141

### Task type distribution: ALL tasks show `task_type: null`
The API does not expose task type fields in the duel data. Cannot break down by UPDATE/REFACTOR/BUGFIX from API alone.

### Key failure patterns in v62 losses:
From duel rationales:
- Round losses often involve CI/validation failures (`solver_error` on many rounds) — challenger completes but solver reports error
- Some rounds: king wins by producing more thorough output on complex multi-file tasks
- Example loss pattern: challenger_score=0.30 vs king_score=0.52 on complex 2600-line patch tasks

---

## 🎯 IMMEDIATE ACTIONS FOR vNEXT

1. **URGENT: Sync king after duel 5141 ends** — new king incoming in minutes
   ```bash
   cd /root/sn66-ninja && bash scripts/sync_king.sh && wc -l king_agent.py
   ```

2. **We need +4 net margin** not +3 — that's our exact gap. v62b was 1 round short.

3. **v62b performance is promising** — 53.1% WR against this king. With just minor improvements to convert 2-3 marginal losses to wins, we can hit the +4 threshold.

4. **New king context**: The current king (d24c9d3) is being beaten by a +8 challenger RIGHT NOW. The next king may be harder. Must resync before building vNEXT.

5. **Solver errors**: Multiple challenger rounds show `challenger_exit_reason: solver_error` even when scoring well. Investigate if this is a runtime issue that costs us wins.

---

## 📈 KING WINDOW (Recent 5 Kings)

| Commit | UID | Defended | Notes |
|--------|-----|----------|-------|
| d24c9d3 | 64 | 21 | **CURRENT — being beaten now** |
| 6abf172 | 86 | 0 | Very short reign |
| fd2af7a6 | 192 | 59 | Long-reigning, was hardest to beat |
| f557239c | 212 | 16 | — |
| f2cc7131 | 12 | 95 | Longest reigning in window |

All recent kings: private-submission via unarbos/ninja runtime. King pool is rotating fast.

---

## 🔢 CHAIN DATA (as of ~05:49 UTC)

- TAO price: $257.75 (-4.8% 24h)
- Alpha price: 0.01050 TAO / $2.71
- Burn cost: 0.2196 TAO ($56.60)
- Subnet TAO pool: 12,314 TAO
- Total rounds to date: 100,764
- Active miners seen: 332

---

## SUMMARY

**King d24c9d3: UNCHANGED locally ✅ but being dethroned in ~minutes by duel 5141.**

Our agents:
- v54/v56: Poor performance against older kings (34% WR) 
- **v62/v62b: NEAR-MISS against current king! v62b got +3 margin, need +4.**
- One more decisive round win on v62b would have dethroned the king.

Next step: Wait for duel 5141 to finish → sync new king → analyze gap → build vNEXT targeting +5+ net margin.
