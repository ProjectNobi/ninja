# Data Run Audit — 2026-05-19
**Audited at:** 2026-05-19 ~16:55 UTC  
**Auditor:** Opus 4.7 subagent  
**Scope:** Hetzner1 + AnonServer (144.91.65.30)

---

## Summary (✅/❌/⚠️ per component)

| Component | Status | Notes |
|-----------|--------|-------|
| T68-S1 proxy | ✅ WORKING | socat service active 1d 8h, 401 = auth required (expected) |
| t68s1-gold run | ⚠️ SLOW | 1039/9122 tasks, ETA 124h, intermittent timeouts |
| gold-sweep5 | ✅ NEAR-COMPLETE | 9109/9122 lines, crash was near-end double-path bug |
| gold-sweep6 | ✅ NEAR-COMPLETE | 9063/9122 lines, same double-path bug |
| glm47-sweep7 | ✅ RUNNING | 2012/8242, ongoing |
| task1_kimi26 | ✅ DONE | "Nothing to do" |
| task1_opus47 | ✅ DONE | "Nothing to do" |
| task1_gpt54 | ✅ DONE | ~7154 pairs |
| task1_haiku45 | ✅ RUNNING | 7020/9031, ETA 166min |
| task1_sonnet46 | ✅ RUNNING | 7036/8052, ETA 84min |
| task_update_dpo | ✅ DONE | 62,589 UPDATE-task DPO pairs |
| task2_ref_dpo | ✅ DONE | 1070 pairs, 90% consensus |
| task3_selfplay | ✅ RUNNING | 745/2920 (25%), ETA 612min |
| task4_matrix | ✅ RUNNING | 11,961/141,158 (8.5%), ETA 2128min, cost $418 |
| gold-gpt5 | ✅ NEAR-DONE | 8912/9122 (98%) |
| gold-kimi-k25 | ✅ DONE | Complete |
| gold-gem31p | ✅ DONE | 4 errors |
| gold-gem3flash | ✅ DONE | 1 error |
| gold-qwen235-2507 | ✅ RUNNING | 2767/9122, ETA 60h |
| gold-llama70b | ✅ DONE | 66 errors |
| gold-o4mini | ✅ DONE | 32 errors |
| gold-o4mini-rerun | ✅ DONE | 103 errors |
| gold-dsr1-0528 | ✅ RUNNING | 4995/9122, ETA 22h |
| gold-dsr1-base | ❌ EFFECTIVELY FAILED | 7925/9122 errors (87%!) |
| gold-deepseek-v3-2 | ✅ DONE | 0 errors |
| gold-glm-4-7 | ✅ DONE | 464 errors |
| gold-glm-5-1 | ✅ DONE | 745 errors |
| gold-qwen3-max | ✅ DONE | 2 errors |
| gold-qwen3-6-max-preview | ✅ RUNNING | 6244/9122, ETA 12h |
| gold-v4pro | ✅ RUNNING | 8464/9122, ETA 2h |
| gold-gpt54-boost | ✅ DONE | 0 errors |
| gold-m27-v3 | ✅ DONE | 85 errors, 9122 tasks |
| gold-m25-rerun | ⚠️ ERRORS | IncompleteRead errors, still running |
| gold-kimi-k2think | ⚠️ TIMEOUTS | 4404/9122, ETA 28h, 1515s per fail |
| Migration (H1→Anon or Anon→H1) | ✅ COMPLETE | 366,125 unified gold records on H1 |
| Gold patches sync (H1 vs Anon) | ⚠️ SLIGHT DRIFT | In-progress files are growing on Anon, H1 needs delta rsync |
| judge_training_sft.jsonl | ✅ GOOD | 204,292 rows, correct schema |
| sn66-final-unified-collector | ✅ RUNNING | duels=930, sft=87,777, dpo=34,562, kings=25 |
| Hetzner1 disk | ✅ OK | 61% used (87GB free) |

---

## Issues Found + Fixed

### Issue 1: T68-S1 proxy — NOT actually broken
**Status:** ✅ No fix needed  
**Root cause of misdiagnosis:** `curl http://localhost:8082/v1/models` without auth key returns `{"error":"Unauthorized"}` (HTTP 401). This is EXPECTED behavior — the proxy IS working and routing to T68-S1, which requires Bearer auth.  
**Evidence:**  
- systemd service `t68s1-proxy.service` active since May 18 08:00 UTC (1d 8h)
- `curl -v http://localhost:8082` connects successfully, gets HTTP 401 from uvicorn
- t68s1-gold run IS making successful API calls (tasks 1031-1038 all completed ✅)
- "Broken pipe" errors in systemd logs = normal socat behavior for closed connections

**Conclusion:** Proxy is healthy. t68s1-gold IS running and making progress.

---

### Issue 2: gold-sweep5 and gold-sweep6 crashed with double-path bug
**Status:** ✅ No restart needed — data is ~99% complete  
**Root cause:** `multi_model_sampler.py:361` constructed output path as `training_data/gold_patches/training_data/gold_patches/gold_patches_glm47_sweep5.jsonl` (double prefix bug). This directory doesn't exist → FileNotFoundError.  
**BUT:** The crash appears to have happened very late in execution. Actual output files are nearly complete:
- `gold_patches_glm47_sweep5.jsonl`: **9,109 lines** (9122 max = 99.9% done)
- `gold_patches_glm47_sweep6.jsonl`: **9,063 lines** (9122 max = 99.3% done)

Both files exist on AnonServer AND Hetzner1 (migration complete). Missing 13-59 tasks are negligible gaps.  
**Recommendation:** Accept as complete. The double-path bug should be fixed in `multi_model_sampler.py` before next sweep run.

---

### Issue 3: gold-dsr1-base — Effectively failed
**Status:** ❌ Requires James decision  
**Details:** 7,925 out of 9,122 tasks errored (87% error rate). The `deepseek-r1` base model (non-instruct) appears unable to follow the code patching task format. The output file will have mostly empty/failed entries.  
**Recommendation:** This gold patch file should be excluded from unified training data, or the ~1,197 successful entries verified before inclusion.  
**Action needed:** James to decide whether to retry with a different prompt/model or discard this run.

---

## Issues Requiring Attention (James Decision Needed)

### 1. t68s1-gold — VERY SLOW (ETA 124 hours remaining)
- **Current state:** 1,039/9,122 tasks done (~11%), running in `/root/backups/github-staging/sn66-ninja/`
- **Issue:** qwen3-30b-awq on T68-S1 is slow for complex coding tasks (19-466s/task)
- **Intermittent timeouts:** Some tasks fail all 5 attempts (466s wasted per fail)
- **ETA:** ~124h from now (completing ~May 25)
- **Options:**
  A. Let it run — it will finish, just slow. Free compute.
  B. Switch to a faster model (GPT-4o-mini, Claude Haiku, etc.) — costs money but 10x faster
  C. Kill and restart against Chutes model — free but may have rate limits
- **No auto-action taken** — this affects cost and strategy

### 2. gold-m25-rerun — IncompleteRead errors
- Still running but experiencing `IncompleteRead(4422 bytes read)` errors
- This indicates the m25 model API is returning incomplete responses (network issue or model instability)
- The run has retry logic (5 attempts) so it's continuing, but many tasks may be failing
- **Recommendation:** Monitor; if error rate exceeds 20% after another hour, restart with `--new-only`

### 3. gold-kimi-k2think — Timeout issues  
- 4,404/9,122 tasks (48%), ETA 28h, but 1,515s per failed task (extreme timeouts)
- kimi-k2-thinking model is very slow (it does chain-of-thought reasoning for each patch)
- May complete but at high latency cost
- **No action taken** — let it run to completion

### 4. task4_matrix — Ongoing, $418 spent, ETA 36h more
- 11,961/141,158 (8.5%) complete, cost $418.60
- This is a long-running job, currently healthy
- **Projected total cost:** ~$4,900 for 141,158 pairs
- **Recommendation:** James should confirm if this budget is acceptable

### 5. Gold patches delta rsync needed
- 4 files still growing on AnonServer (qwen235-2507, qwen3-6-max-preview, dsr1-0528, kimi-k2thinking)
- Current size differences:
  - dsr1-0528: Anon=281M vs H1=278M
  - kimi-k2thinking: Anon=305M vs H1=304M
  - qwen235-2507: Anon=183M vs H1=181M
  - qwen3-6-max-preview: Anon=399M vs H1=396M
- **After these runs complete, run delta rsync:**
  ```bash
  rsync -av --progress root@144.91.65.30:/root/sn66-ninja/training_data/gold_patches/ \
    /root/sn66-ninja/training_data/gold_patches/ \
    --include="*.jsonl" --exclude="*.bak*"
  ```

---

## All Session Status

### Hetzner1 Sessions
| Session | Status | Notes |
|---------|--------|-------|
| t68s1-gold | ⚠️ RUNNING SLOW | 1039/9122, ETA 124h, intermittent timeouts |
| gold_migration | ✅ COMPLETE | rsync done, 366,125 unified records |
| v71gate | ✅ RUNNING | Gate test (do not touch per instructions) |
| sn66_v62/65/66/67/68_gate50 | 🔵 OLD | Legacy gate sessions, can be cleaned up |

### AnonServer DPO Task Sessions
| Session | Status | Notes |
|---------|--------|-------|
| task1_gpt54 | ✅ DONE | ~7154 pairs |
| task1_haiku45 | ✅ RUNNING | 7020/9031, ETA 166min |
| task1_sonnet46 | ✅ RUNNING | 7036/8052, ETA 84min |
| task1_kimi26 | ✅ DONE | 105,128 pairs already done |
| task1_opus47 | ✅ DONE | 105,128 pairs already done |
| task1_synthetic | ✅ DONE | — |
| task1_m27_kimi | ✅ DONE | — |
| task1_m27_m25 | ✅ DONE | 11 pairs |
| task2_ref_dpo | ✅ DONE | 1070 pairs |
| task3_selfplay | ✅ RUNNING | 745/2920, ETA 612min |
| task4_matrix | ✅ RUNNING | 11,961/141,158, ETA 36h, $418 |
| task_update_dpo | ✅ DONE | 62,589 UPDATE DPO pairs |

### AnonServer Gold Sessions
| Session | Status | Lines | Notes |
|---------|--------|-------|-------|
| gold-gpt5 | ✅ NEAR-DONE | 8912/9122 tasks | Last task timed out |
| gold-kimi-k25 | ✅ DONE | ~9122 | Complete |
| gold-gem31p | ✅ DONE | ~9118 | 4 errors |
| gold-gem3flash | ✅ DONE | ~9121 | 1 error |
| gold-qwen235-2507 | ✅ RUNNING | 2767/9122 | ETA 60h |
| gold-llama70b | ✅ DONE | ~9056 | 66 errors |
| gold-o4mini | ✅ DONE | ~9090 | 32 errors |
| gold-o4mini-rerun | ✅ DONE | ~9019 | 103 errors |
| gold-dsr1-0528 | ✅ RUNNING | 4995/9122 | ETA 22h |
| gold-dsr1-base | ❌ FAILED | ~1197 valid | 87% error rate |
| gold-deepseek-v3-2 | ✅ DONE | 9122 | 0 errors (perfect) |
| gold-glm-4-7 | ✅ DONE | ~8658 | 464 errors |
| gold-glm-5-1 | ✅ DONE | ~8377 | 745 errors |
| gold-qwen3-max | ✅ DONE | ~9120 | 2 errors |
| gold-qwen3-6-max-preview | ✅ RUNNING | 6244/9122 | ETA 12h |
| gold-v4pro | ✅ RUNNING | 8464/9122 | ETA 2h |
| gold-gpt54-boost | ✅ DONE | 9122 | 0 errors (perfect) |
| gold-m27-v3 | ✅ DONE | ~9037 | 85 errors |
| gold-m25-rerun | ⚠️ ERRORS | unknown | IncompleteRead errors |
| gold-kimi-k2think | ⚠️ SLOW | 4404/9122 | ETA 28h, timeout issues |
| gold-sweep5 | ✅ NEAR-DONE | 9109/9122 | Double-path crash at end |
| gold-sweep6 | ✅ NEAR-DONE | 9063/9122 | Same double-path crash |
| glm47-sweep7 | ✅ RUNNING | 2012/8242 | Ongoing |

---

## Data File Counts

### Hetzner1 `/root/sn66-ninja/training_data/`
| File | Size | Records |
|------|------|---------|
| training_unified_gold.jsonl | 27GB | 366,125 |
| full_matrix_dpo_pairs.jsonl | 2.2GB | — |
| judge_training_sft.jsonl | 1.7GB | 204,292 |
| update_task_dpo_pairs.jsonl | 1.3GB | 62,589 |
| synthetic_dpo_pairs.jsonl | 963MB | — |
| reference_dpo_pairs.jsonl | 640MB | — |
| self_play_dpo_pairs.jsonl | 139MB | — |

**Gold patch files:** 42 files present (same as AnonServer)  
**Disk usage:** 61% (87GB free)

### Judge Training SFT Format ✅
```python
['task_id', 'task_type', 'input', 'output', 'score_a', 'score_b', 'winner', 'consensus', 'source']
```
Schema is correct and complete.

---

## Recommendations

1. **t68s1-gold:** Decision needed — let run at 124h ETA or switch model. Recommend switching to Chutes fast model (kimi-k2-thinking or sonnet) if James wants it done sooner.

2. **gold-dsr1-base:** Exclude from training data or filter to only the ~1,197 successful entries. The deepseek-r1 base model cannot do instruction following for code patches.

3. **Fix double-path bug in multi_model_sampler.py:** Before next sweep run, fix line 361 to use correct relative path.

4. **Delta rsync after running gold sessions complete** (v4pro in 2h, qwen3-6-max in 12h, dsr1-0528 in 22h, qwen235-2507 in 60h).

5. **Monitor task4_matrix cost:** At $418 for 8.5% done, projected total ~$4,900. James should confirm budget.

6. **Clean up old gate sessions on Hetzner1:** sn66_v62/65/66/67/68_gate50 sessions can be killed to free tmux resources.

7. **glm47-sweep7 normalized file:** `gold_patches_glm47_sweep7_normalized.jsonl` is very small (1.1M). Verify it was processed correctly after sweep7 completes.

---

*Report generated by Opus 4.7 subagent | 2026-05-19 ~17:00 UTC*
