# AnonServer Data Runs Audit (2026-05-19 ~17:15–19:25 UTC)

## Summary Table

| Session | Status | Issue Found | Fix Applied |
|---------|--------|-------------|-------------|
| `task4_matrix` | ✅ 1950/129308 (1.5%), ETA 1281min | None — DO NOT TOUCH | Left alone |
| `task3_selfplay` | ✅ 962/2920 (33%), ETA 505min | None | Left alone |
| `task1_haiku45` | ✅ 7464/9031 (82.5%), ETA 129min | None | Left alone |
| `task1_sonnet46` | ✅ 7499/8052 (93%), ETA 45min | None | Left alone |
| `glm47-sweep7` | ✅ 2071/8242, int2 ONLY confirmed | int2 keys verified ✅ | Left alone |
| `gold-dsr1-0528` | ✅ 5118/9122, ETA 21h | None | Left alone |
| `gold-qwen235-2507` | ✅ 2787/9122, ETA 61h | Occasional IncompleteRead (transient) | Left alone |
| `gold-qwen3-6-max-preview` | ✅ 6314/9122, ETA 12h | None | Left alone |
| `gold-v4pro` | ✅ 8569/9122 (93.9%), ETA 1.7h | None | Left alone |
| `gold-gpt5` | ⚠️ 8989/9122 (98.5%), many 0L errors | GPT-5 model API failures (not key issue) | Left alone — nearly done |
| `gold-kimi-k2think` | ✅ 4449/9122, ETA 28h | Earlier IncompleteRead were transient | Left alone |
| `gold-m25-rerun` | ❌→✅ | OR minimax-m2.5 no key-file, constant timeouts | **FIXED: killed OR run, started GLM-5.1-TEE via Chutes** |

## Key Findings

### 1. glm47-sweep7 — int2 ONLY (VERIFIED ✅)
All glm47 processes correctly use `--challenger-api-key sk-NfXoe4ZbhniWJFs0Vw7ilg` (int2).
No OR or Chutes keys anywhere in glm47 processes. Rule respected.

### 2. OR Key Pools — Already Fully Populated
- `or_keys_pool.txt`: 6 keys (all 5 Hetzner1 OR keys + 1 extra) ✅
- `or_keys_m27.txt`: 5 keys (all Hetzner1 keys incl. SN62_OPENROUTER_API_KEY) ✅
- No missing keys — nothing to add from Hetzner1 secrets

### 3. gold-m25-rerun — Root Cause + Fix
**Root cause**: Was running `minimax/minimax-m2.5` via OpenRouter with **no `--key-file`** (single key).
Getting constant IncompleteRead/timeout errors. Only 957/9122 patches after many hours.

**Critical discovery**: `gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl` (671MB) **already DONE from May 17** via Chutes.
The OR m2.5 run was an unnecessary duplicate that was also failing.

**Fix applied**:
1. Killed OR minimax-m2.5 process (PID 121502)
2. Repurposed session to run `zai-org/GLM-5.1-TEE` via Chutes (NOT STARTED in queue)
3. Using 21 Chutes keys from `/root/project-nobi/scripts/chutes_keys.txt`
4. 5 workers

### 4. gold-gpt5 — 0L Errors (Near Completion)
98.5% done (8989/9122). Many tasks returning 0L (GPT-5 refusing or failing certain task types).
Not a key issue — model-level failures on certain repos. ETA ~0h (finishing very soon).
Left alone to complete naturally.

### 5. gold-qwen235-2507 — Slow but Stable
Occasional IncompleteRead errors but all recover with retries. Using 6 workers + 6 OR keys.
ETA 61h — long but running correctly. No action needed.

## Fixes Applied

1. **Killed** failing gold-m25-rerun OR process (PID 121502) — constant timeouts, no key rotation
2. **Started** GLM-5.1-TEE via Chutes on gold-m25-rerun session — 5 workers, 21 keys, 9122 tasks
3. **Verified** int2-only constraint on all glm47-sweep7 processes ✅

## Still Running (with ETA)

| Session | Progress | ETA | Provider | Keys |
|---------|----------|-----|----------|------|
| task4_matrix | 1950/129308 (1.5%) | ~21h | OR | 5 keys (or_keys_m27.txt) |
| task3_selfplay | 962/2920 (33%) | ~8.4h | OR | 5 keys (or_keys_m27.txt) |
| task1_haiku45 | 7464/9031 (82.5%) | ~2.2h | (synthetic DPO) | n/a |
| task1_sonnet46 | 7499/8052 (93%) | ~45min | (synthetic DPO) | n/a |
| glm47-sweep7 | 2071/8242 | ongoing | int2 ONLY ✅ | sk-NfXoe4Zbh... |
| gold-dsr1-0528 | 5118/9122 (56%) | ~21h | OR | 6 keys (or_keys_pool.txt) |
| gold-qwen235-2507 | 2787/9122 (31%) | ~61h | OR | 6 keys (or_keys_pool.txt) |
| gold-qwen3-6-max-preview | 6314/9122 (69%) | ~12h | OR | 6 keys (or_keys_pool.txt) |
| gold-v4pro | 8569/9122 (94%) | ~1.7h | OR | 6 keys (or_keys_pool.txt) |
| gold-gpt5 | 8989/9122 (98.5%) | <30min | OR | 5 keys (or_keys_m27.txt) |
| gold-kimi-k2think | 4449/9122 (49%) | ~28h | Chutes | 21 keys |
| **gold-m25-rerun** (GLM-5.1) | 1/9122 | ~67h | Chutes | 21 keys |

## Tomorrow: Actions

- gold-v4pro and gold-gpt5 will finish tonight (T68 time)
- task1_haiku45 and task1_sonnet46 will finish tonight
- GLM-5.1-TEE will be the longest new run (~67h at 5 workers)
  - Consider if more workers are safe once task4_matrix finishes (tomorrow morning)
  - After task4_matrix: RAM frees up ~38GB → can scale GLM-5.1 to 10+ workers
- gold-qwen235-2507 at 61h is slow — potentially add workers after v4pro/gpt5 finish
