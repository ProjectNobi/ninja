# SN66 Gold Patch Pipeline Investigation — 2026-05-16

## Executive Summary

- **Unified gold**: 87,493 records (87,493 after manual incremental save)
- **9 complete runs** (9122 each = 82,098 records): gpt-5_5, Kimi-K2.5-TEE, Qwen3-Coder-Next-TEE, qwen3b_tasks, glm47_sweep3, glm47_sweep4, Qwen_Qwen3_5-397B-A17B-TEE (via save_state), s10/s-series batches
- **16 active processes on AnonServer** — all tmux sessions alive, 12 gold runs + 1 duel validator + 3 SN11/SN62 sessions
- **T68-S1 gold run**: 2,548/9,122 — healthy, ETA ~5.3h
- **Pipeline (rsync + incremental save)**: ✅ Working correctly on 30min cycle
- **Comprehensive collector**: ✅ Running (PM2, 5 restarts, online 3h, collecting duels/SFT/DPO)

## Issues Found

### 🔴 CRITICAL: DeepSeek-V3.2-TEE (Chutes) — 100% Rate-Limited
- **260 records on AnonServer, ALL producing empty llm_patches since ~record 250**
- Solid 429 errors across all 21 Chutes key rotations — every single request fails
- ETA: 165h (unreachable — will never complete)
- **Recommendation**: KILL this process — it's wasting cycles and polluting the gold file
- Previous data (3,487 records from earlier run) already saved to unified gold

### 🟡 WARNING: MiniMax-M2.5-TEE (Chutes) — Extremely Slow
- 103 records on AnonServer, 40/103 (39%) empty llm_patches  
- Constant timeouts (265s per task), ETA: **430 hours**
- Previous run saved 5,528 records — this is a restart
- **Recommendation**: Consider killing — cost/benefit poor at this rate

### 🟡 WARNING: Kimi-K2.6-TEE (Chutes) — Moderate Issues
- 90 records, 20/90 (22%) empty — better than DeepSeek/MiniMax
- Slow but producing some usable data

### 🟡 WARNING: Qwen3.5-397B-A17B-TEE (Chutes) — Very Slow
- 84 records after 3h — extremely slow throughput
- Qwen3.5 was already completed via save_state (9122 records from prior run)
- This is a duplicate/restart run — consider whether it's needed

### ✅ HEALTHY: OpenRouter Runs (5 models)
| Model | Records | ETA | Empty% |
|-------|---------|-----|--------|
| gpt-5.4-nano (gpt-4.1-nano) | 4,596 | ~2.6h | <0.1% |
| gemini-2.5-flash | 4,373 | ~2.5h | <0.2% |
| o4-mini | 2,865 | ~3.5h | <1% |
| gemini-3.1-pro-preview | 2,074 | ~4h | <1% |
| llama-3.3-70b-instruct | 1,784 | ~5h | <1% |
| deepseek-v4-pro | 381 | ~12h | ~1% |

### ✅ HEALTHY: GLM-4.7 sweep5 (int2)
- 179 records, 6/179 (3.3%) empty — good quality
- Progressing steadily

### ✅ HEALTHY: T68-S1 (qwen3-30b-awq)
- 2,548/9,122 (27.9%), ETA ~5.3h
- Running in tmux `t68s1-gold`, no errors

## Pipeline Health

### Rsync: ✅ Working
- **Hetzner1 pulls** from AnonServer every 30min (`/root/scripts/sync_anonserver_gold.sh`)
- **AnonServer pushes** to Hetzner1 every 2h (redundant backup)
- Last sync: 2026-05-16 12:00 UTC — successful, files updated
- Disk: 117GB free on Hetzner1

### Incremental Save: ✅ Working
- Runs every 30min after rsync (same cron line)
- Correctly skips empty llm_patches (line 115 filter)
- Cursor-based dedup via `incremental_save_state.json` — no duplicate records
- Manual run at 12:13 UTC added 28 new records (qwen3-30b-awq only — AnonServer files not yet synced since 12:00)

### Comprehensive Collector: ✅ Running
- PM2 process `sn66-comprehensive-collector`, online 3h
- Collecting: duels (636), SFT (79,642), DPO (27,455), kings (15), PRs (1,446), judge feedback (6,324), miners (91)
- Polling every ~5min, catching new duels

### Data Quality Verified
- Sampled records from all active runs — JSON valid, proper schema
- Fields: task_id, archetype, source, model, instruction, llm_patch, reference_patch, n_added_llm, n_added_ref, elapsed_s
- Unified gold uses: instruction, output, llm_response, model, archetype, source

## AnonServer Resource Usage
- **RAM**: 75GB free / 94GB total — safe headroom
- **Active processes**: 16 multi_model_sampler + 1 validator_harness + Docker
- **Each worker**: ~1.2GB RSS
- **Can add**: 2-3 more workers safely

## Stopped Incomplete Runs (Hetzner1, NOT running anywhere)

These have partial data in save_state but no active process:
| Model | Saved | Source | Status |
|-------|-------|--------|--------|
| glm-4.7-sweep2 | 5,635 | int2 | Stopped — cannot restart (int2 key constraint) |
| glm47b_all_tasks | 4,784 | int2 | Stopped — cannot restart |
| glm47b_tasks | 4,656 | int2 | Stopped — cannot restart |
| glm47p1_all_tasks | 3,597 | int2 | Stopped — cannot restart |
| glm47p1_tasks | 2,705 | int2 | Stopped — cannot restart |
| google_gemma-3-27b-it | 910 | OR/Chutes | Could restart on AnonServer |
| zai-org_GLM-5-TEE | 819 | Chutes | Could restart but likely rate-limited |
| zai-org_GLM-5_1-TEE | 646 | Chutes | Could restart but likely rate-limited |
| openai_gpt-5_4 | 798 | OR | Could restart on AnonServer |
| anthropic_claude-opus-4-6 | 672 | Anthropic | Expensive — probably not worth restarting |

**Recommendation**: The int2 runs cannot be restarted. The Chutes GLM-5 runs would likely hit the same 429 issues. Best candidates for restart: `google_gemma-3-27b-it` (via OR) and `openai_gpt-5_4` (via OR) — both would be OR-based and reliable.

## Recommendations

### Immediate (James approval needed)
1. **Kill DeepSeek-V3.2-TEE** on AnonServer — 100% failures, zero usable output
2. **Consider killing MiniMax-M2.5-TEE** — ETA 430h, 39% failure rate, previous run data already saved

### Short-term Optimizations
3. **Rsync frequency is adequate** — 30min pull from Hetzner1 is fine. AnonServer push (2h) is redundant backup.
4. **No race conditions detected** — rsync reads are atomic enough for append-only JSONL files.
5. **Consider restarting gemma-3-27b-it via OR** on AnonServer — 910/9122 saved, reliable via OR.

### Data Projections
- **OR models completing**: gpt-5.4-nano and gemini-2.5-flash will hit 9122 within ~3-4h
- **T68-S1**: qwen3-30b-awq will complete in ~5.3h
- **Expected unified gold by end of day**: ~95,000-100,000 records (as OR runs complete and get saved)
- **Estimated records when all active healthy runs complete**: ~130,000+

## No Actions Taken (per constraints)
- Did NOT kill any running processes (requires James approval)
- Did NOT start any new int2/GLM-4.7 runs (key constraint)
- Ran manual incremental save (+28 records)
- Verified all systems healthy

## Final State
```
Unified Gold:        87,493 records
Active AnonServer:   16 processes (12 gold, 4 other)
Active T68-S1:       1 process (qwen3-30b-awq, 2548/9122)
Comprehensive:       Online, collecting data
Pipeline:            Healthy (30min sync cycle)
AnonServer RAM:      75GB free
```
