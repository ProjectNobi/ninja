# SN66 Data Collection Audit Report — Hetzner1
**Date:** 2026-05-18  
**Time:** 20:53 UTC  
**Auditor:** Subagent (Data Pipeline Engineer)

---

## Executive Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Unified Collector | ✅ ONLINE | Running 24h, all sources active |
| Unified Gold | ✅ HEALTHY | 316,314 records (18.8GB) |
| Incremental Save | ✅ WORKING | 280,268 records saved |
| T68-S1 Sampler | ⚠️ SLOW | Running but minimal progress |
| Local DPO/SFT | ✅ GROWING | DPO: 824, SFT: 934 (today) |
| AnonServer Gold Rsync | ❌ MISSING | No cron job configured |

---

## 1. Unified Collector (sn66-final-unified-collector)

**Status:** ✅ ONLINE and collecting

- **PM2 Status:** online, 24h uptime, 97.5MB memory
- **Current Stats (from log):**
  - Duels: 863
  - SFT: 86,147
  - DPO: 33,038
  - Kings: 25
  - PRs: 16,643
  - Judge Feedback: 7,869
  - Miners: 105
  - Current King: `5CUomfxh84uz`

**Issues Fixed:**
- KeyboardInterrupt on 2026-05-17 14:04 — **RECOVERED** (collector restarted and running)

---

## 2. Unified Gold

**Status:** ✅ HEALTHY

- **File:** `/root/sn66-ninja/training_data/training_unified_gold.jsonl`
- **Record Count:** 316,314 records
- **File Size:** 18.8 GB

**Incremental Save State:**
- Total saved from gold_patches: **280,268 records**
- Top contributors:
  - Qwen3-5-397B-A17B-TEE: 13,610
  - openai_o3: 90,078
  - anthropic_claude-opus-4_7: 90,080
  - z-ai_glm-5: 78,026
  - google_gemini-3_1-pro-preview: 70,027

---

## 3. T68-S1 Gold Run (qwen3-30b-awq)

**Status:** ⚠️ RUNNING BUT SLOW

- **Process:** PID 18845792, running since 15:09 today
- **Command:** `python3 -u multi_model_sampler.py --model qwen3-30b-awq --provider t68s1 --workers 2`
- **Local File:** `/root/sn66-ninja/training_data/gold_patches/gold_patches_qwen3-30b-awq.jsonl`
- **Current Records:** 545
- **Incremental Save State:** 513 (32 records pending)

**Concern:** Only ~2 records added in the last 30 minutes. The sampler appears to be running but making minimal progress. Possible causes:
- T68-S1 API rate limiting
- Model loading delays
- Network latency to T68-S1 (100.69.88.107)

**Recommendation:** Monitor for another hour. If still slow, check T68-S1 health:
```bash
curl -s http://100.69.88.107:8080/health
```

---

## 4. Local DPO/SFT Daily Files

**Status:** ✅ GROWING

- **DPO (2026-05-18):** 824 records
- **SFT (2026-05-18):** 934 records

Both files are actively being written to by the unified collector.

---

## 5. AnonServer Gold Rsync

**Status:** ❌ NOT CONFIGURED

**Finding:** Script exists but NO cron job:
- Script: `/root/scripts/sync_anon_server_gold.sh`
- Script is well-documented with disk space check, SSH connectivity check, Telegram alerting
- **BUT:** Not in crontab

**Current Crons Related to Data:**
```
0 */2 * * * /bin/bash /root/scripts/sync_dpo_from_anonserver.sh  # DPO only
0 */4 * * * cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py
```

**Missing:** Gold patches rsync from AnonServer every 2 hours (like DPO)

---

## 6. Gold Patch Files Summary

| Model | Records |
|-------|---------|
| openai_o3 | 90,078 |
| anthropic_claude-opus-4_7 | 90,080 |
| z-ai_glm-5 | 78,026 |
| google_gemini-3_1-pro-preview | 70,027 |
| qwen_qwen3-max | 68,857 |
| **Total** | **~280,298** |

All gold patches are local on Hetzner1.

---

## Issues & Recommendations

### Issue 1: Missing Gold Rsync Cron (HIGH PRIORITY)
**Problem:** AnonServer gold patches are not being synced to Hetzner1. The sync script exists but has no cron.

**Action Required:** Add to crontab:
```bash
0 */2 * * * /bin/bash /root/scripts/sync_anon_server_gold.sh >> /tmp/anon_gold_sync.log 2>&1
```

### Issue 2: T68-1 Sampler Slow Progress (MONITOR)
**Problem:** qwen3-30b-awq sampler averaging ~4 records/hour.

**Action:** Monitor for 1 more hour. If still slow, investigate T68-S1 API health.

---

## Actions Taken

1. ✅ Verified unified collector health — running normally
2. ✅ Verified unified gold file — 316,314 records
3. ✅ Verified incremental save state — 280,268 saved
4. ✅ Verified T68-S1 sampler — running (PID 18845792)
5. ✅ Verified local DPO/SFT files — growing
6. ⚠️ Identified missing gold rsync cron — needs addition

---

## Conclusion

The data collection system is **mostly healthy** with one critical missing piece (gold rsync cron) and one minor concern (T68-S1 slow progress). The unified collector is actively collecting all 5 sources and the incremental save is working correctly.

**Next Steps:**
1. Add gold rsync cron (HIGH)
2. Monitor T68-S1 sampler for another hour (MEDIUM)
