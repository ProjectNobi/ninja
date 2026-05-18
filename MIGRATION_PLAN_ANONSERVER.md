# Migration Plan: Multi-Model Gold Patch Runs → AnonServer

**Date:** 2026-05-15  
**Updated:** 2026-05-15 (OR strategy — James directive)  
**Author:** Opus (subagent) | **Updated by:** T68Bot subagent  
**From:** Hetzner1 (178.156.199.243) → **To:** AnonServer (144.91.65.30)  
**Scope:** 15 Multi-Model Gold Patch runs using `multi_model_sampler.py`  
**Provider strategy:** 14/15 runs on OpenRouter (avoids Chutes 429/timeout hell), 1/15 Chutes-only  
**Total data to transfer:** ~515 MB (R2 dataset) + ~1.1 GB (22 progress files) + script + keys

---

## ⚡ Provider Decision Matrix (Updated 2026-05-15 — OpenRouter priority)

**Context:** 7 of the 8 formerly "Chutes" runs now have confirmed OpenRouter equivalents with existing progress files. Since Chutes is experiencing 429s/timeouts, **OpenRouter is the PRIMARY provider** for those 7 runs. Chutes commands are retained as fallback only.

| Session | Chutes TEE Model | OR Model (PRIMARY) | Chutes Progress | OR Progress | Decision |
|---------|-----------------|-------------------|-----------------|-------------|----------|
| gold-deepseek | `deepseek-ai/DeepSeek-V3.2-TEE` | `deepseek/deepseek-v3.2` | 4/9122 (0%) | 298/9122 (3.3%) | ✅ **OR PRIMARY** |
| gold-glm5 | `zai-org/GLM-5-TEE` | `z-ai/glm-5` | 583/9122 (6.4%) | 189/9122 (2.1%) | ✅ **OR PRIMARY** |
| gold-glm51 | `zai-org/GLM-5.1-TEE` | `z-ai/glm-5.1` | 421/9122 (4.6%) | 146/9122 (1.6%) | ✅ **OR PRIMARY** |
| gold-kimi25 | `moonshotai/Kimi-K2.5-TEE` | `moonshotai/kimi-k2.5` | 165/9122 (1.8%) | 166/9122 (1.8%) | ✅ **OR PRIMARY** |
| gold-kimi26 | `moonshotai/Kimi-K2.6-TEE` | `moonshotai/kimi-k2.6` | 367/9122 (4.0%) | 21/9122 (0.2%) | ✅ **OR PRIMARY** |
| gold-minimax | `MiniMaxAI/MiniMax-M2.5-TEE` | `minimax/minimax-m2.5` | 389/9122 (4.3%) | 73/9122 (0.8%) | ✅ **OR PRIMARY** |
| gold-qwen397 | `Qwen/Qwen3.5-397B-A17B-TEE` | `qwen/qwen3.5-397b-a17b` | 365/9122 (4.0%) | 116/9122 (1.3%) | ✅ **OR PRIMARY** |
| gold-qwen3coder | `Qwen/Qwen3-Next-80B-A3B-Instruct-TEE` | **(no confirmed OR equiv)** | 477/9122 (5.2%) | — | ⚠️ **CHUTES ONLY** |

**Notes:**
- OR runs write to **different output files** than Chutes TEE runs → they are parallel, independent datasets (more total training data)
- GLM-5 and GLM-5.1 TEE runs have **more Chutes progress** (583/421) than OR (189/146) — but OR will run faster with no rate limits, so OR wins on completion speed
- If Chutes stabilizes later, Chutes TEE sessions can be resumed independently from their own progress files
- gold-qwen3coder: no OR equivalent found — Chutes only, watch for 429s
- OpenRouter key var: `OPENROUTER_API_KEY` or `SN62_OPENROUTER_API_KEY` (both in `/root/.secrets/api_keys.env`)

---

## 0. Overview

All 15 runs will continue on AnonServer from their **current progress** (auto-resume via task_id dedup). Hetzner1 remains free of these long-running API jobs. Periodic rsync every 2 hours pushes results back to Hetzner1 so `incremental_save_to_unified.py` can merge them.

**Migration takes ~20 minutes** (dominated by file transfer). Runs start immediately after.

---

## 1. Pre-Migration Checklist

Run these checks from **Hetzner1** before doing anything else:

```bash
# 1a. Verify SSH connectivity to AnonServer
ssh anonserver "echo '✅ SSH OK'"

# 1b. Check Python version (need 3.12+)
ssh anonserver "python3 --version"

# 1c. Check disk space — need ~2.5 GB free (dataset + progress files + headroom)
ssh anonserver "df -h /root"

# 1d. Verify tmux is available
ssh anonserver "tmux -V"

# 1e. Check AnonServer load (should be near-idle)
ssh anonserver "uptime && free -h"

# 1f. Confirm /root/.secrets/ directory doesn't already have conflicting keys
ssh anonserver "ls -la /root/.secrets/ 2>/dev/null || echo 'Directory does not exist — will create'"
```

**Expected results:**
- SSH: `✅ SSH OK`
- Python: `Python 3.12.x`
- Disk: at least 3 GB free on `/root`
- tmux: `tmux 3.x`
- Load: very low (< 1.0)

**Stop if any check fails.** Resolve before proceeding.

---

## 2. Directory Setup on AnonServer

Run from **Hetzner1** (all via SSH):

```bash
ssh anonserver "
mkdir -p /root/sn66-ninja/training_data/gold_patches
mkdir -p /root/sn66-ninja/scripts
mkdir -p /root/sn66-ninja/logs
mkdir -p /root/sn66-r2-dataset
mkdir -p /root/.secrets
chmod 700 /root/.secrets
echo '✅ Directories created'
"
```

---

## 3. File Transfer

### 3a. Transfer the R2 Dataset (515 MB)

```bash
# ~1-2 minutes via SCP (same datacenter)
rsync -avz --progress \
  /root/sn66-r2-dataset/hf_dataset_cache.jsonl \
  anonserver:/root/sn66-r2-dataset/hf_dataset_cache.jsonl
```

Verify:
```bash
ssh anonserver "wc -l /root/sn66-r2-dataset/hf_dataset_cache.jsonl"
# Expected: 9122 lines
```

### 3b. Transfer multi_model_sampler.py

```bash
scp /root/sn66-ninja/multi_model_sampler.py \
    anonserver:/root/sn66-ninja/multi_model_sampler.py

# Verify
ssh anonserver "head -3 /root/sn66-ninja/multi_model_sampler.py"
```

### 3c. Transfer incremental_save_to_unified.py (for reference, stays on Hetzner1 but copy for emergencies)

```bash
scp /root/sn66-ninja/scripts/incremental_save_to_unified.py \
    anonserver:/root/sn66-ninja/scripts/incremental_save_to_unified.py
```

### 3d. Transfer All Progress Files (~1.1 GB total)

**Updated:** Now transfers 22 files (15 original + 7 new OpenRouter-equivalent progress files).
Both Chutes TEE files and OR-equiv files are transferred so either can be resumed independently.

```bash
# This preserves all current progress so runs RESUME, not RESTART
# Group 1: Chutes TEE progress files (kept for fallback / parallel use)
rsync -avz --progress \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3-coder-next.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/

# Group 2: OpenRouter-equivalent progress files (PRIMARY for 7 runs — avoids Chutes 429s)
rsync -avz --progress \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek_deepseek-v3_2.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_z-ai_glm-5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_z-ai_glm-5_1.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_kimi-k2_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_kimi-k2_6.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_minimax_minimax-m2_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3_5-397b-a17b.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/

# Group 3: Original OpenRouter runs (gemma, gpt-5.5, llama, gemini, o4-mini, etc.)
rsync -avz --progress \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemma-3-27b-it.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-3_1-pro-preview.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_o4-mini.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-2_5-flash.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_4-nano.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/
```

Verify all 22 landed:
```bash
ssh anonserver "ls /root/sn66-ninja/training_data/gold_patches/gold_patches_*.jsonl | wc -l"
# Expected: 22
```

### 3e. Transfer API Key Files (SECURE — never print values)

```bash
# Chutes key pool
scp /root/project-nobi/scripts/chutes_keys.txt \
    anonserver:/root/.secrets/chutes_keys.txt
ssh anonserver "chmod 600 /root/.secrets/chutes_keys.txt"

# OpenRouter + INT2 keys (api_keys.env has them all)
scp /root/.secrets/api_keys.env \
    anonserver:/root/.secrets/api_keys.env
ssh anonserver "chmod 600 /root/.secrets/api_keys.env"

# Verify files arrived (check size, never contents)
ssh anonserver "wc -l /root/.secrets/chutes_keys.txt && stat -c '%a %n' /root/.secrets/chutes_keys.txt"
ssh anonserver "stat -c '%a %s %n' /root/.secrets/api_keys.env"
```

---

## 4. Script Adaptation

The script has 3 hardcoded paths that need updating for AnonServer. Apply these `sed` patches:

```bash
ssh anonserver "
cd /root/sn66-ninja

# 1. Update R2 dataset path (already correct — same path on AnonServer)
# R2_DATASET_PATH = '/root/sn66-r2-dataset/hf_dataset_cache.jsonl'
# ✅ No change needed — same absolute path

# 2. Update OUTPUT_DIR (already correct — same path on AnonServer)
# OUTPUT_DIR = Path('/root/sn66-ninja/training_data/gold_patches')
# ✅ No change needed — same absolute path

# 3. Update Chutes key file default fallback path
sed -i 's|/root/project-nobi/scripts/chutes_keys.txt|/root/.secrets/chutes_keys.txt|g' \
    /root/sn66-ninja/multi_model_sampler.py

echo '✅ Patch applied'

# Verify the patch
grep 'chutes_keys' /root/sn66-ninja/multi_model_sampler.py
"
```

**Why:** The script has `/root/project-nobi/scripts/chutes_keys.txt` hardcoded in 2 places (lines 80, 426). On AnonServer, we put the key file at `/root/.secrets/chutes_keys.txt`. The sed replaces both occurrences.

**Verify patch is correct:**
```bash
ssh anonserver "grep -n 'chutes_keys\|api_keys' /root/sn66-ninja/multi_model_sampler.py"
```
Expected: all references now point to `/root/.secrets/chutes_keys.txt` or `/root/.secrets/api_keys.env`.

---

## 5. Launch Commands (All 15 Runs in tmux)

SSH into AnonServer first:
```bash
ssh anonserver
```

Then run all 15 commands below. Each creates its own tmux session and logs output.

---

### 5a. OpenRouter-Primary Runs (7) + 1 Chutes-Only Run

> **Updated strategy:** 7 of 8 runs now use `--provider openrouter` as PRIMARY to avoid Chutes 429s/timeouts.
> Each OR run resumes from its own OR-specific progress file (separate from the Chutes TEE files).
> Chutes fallback commands are provided below each run — use only if OR experiences problems.
> 1 run (gold-qwen3coder) stays on Chutes: no confirmed OR equivalent model exists.

---

#### gold-deepseek — OR PRIMARY ✅
*Chutes TEE progress: 4/9122 (0%) | OR progress: 298/9122 (3.3%)*

```bash
# PRIMARY (OpenRouter — deepseek/deepseek-v3.2)
tmux new-session -d -s gold-deepseek \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model deepseek/deepseek-v3.2 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-deepseek.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — deepseek-ai/DeepSeek-V3.2-TEE)
tmux new-session -d -s gold-deepseek-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model deepseek-ai/DeepSeek-V3.2-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-deepseek-chutes.log"
```
</details>

---

#### gold-glm5 — OR PRIMARY ✅
*Chutes TEE progress: 583/9122 (6.4%) | OR progress: 189/9122 (2.1%) — OR starts behind but runs without 429 hell*

```bash
# PRIMARY (OpenRouter — z-ai/glm-5)
tmux new-session -d -s gold-glm5 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model z-ai/glm-5 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm5.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — zai-org/GLM-5-TEE) — NOTE: has 583 Chutes TEE tasks done, worth running in parallel if Chutes stabilizes
tmux new-session -d -s gold-glm5-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model zai-org/GLM-5-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm5-chutes.log"
```
</details>

---

#### gold-glm51 — OR PRIMARY ✅
*Chutes TEE progress: 421/9122 (4.6%) | OR progress: 146/9122 (1.6%) — OR starts behind but runs without 429 hell*

```bash
# PRIMARY (OpenRouter — z-ai/glm-5.1)
tmux new-session -d -s gold-glm51 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model z-ai/glm-5.1 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm51.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — zai-org/GLM-5.1-TEE) — NOTE: has 421 Chutes TEE tasks done, worth running in parallel
tmux new-session -d -s gold-glm51-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model zai-org/GLM-5.1-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm51-chutes.log"
```
</details>

---

#### gold-kimi25 — OR PRIMARY ✅
*Chutes TEE progress: 165/9122 (1.8%) | OR progress: 166/9122 (1.8%) — nearly identical, OR is safer*

```bash
# PRIMARY (OpenRouter — moonshotai/kimi-k2.5)
tmux new-session -d -s gold-kimi25 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model moonshotai/kimi-k2.5 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-kimi25.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — moonshotai/Kimi-K2.5-TEE)
tmux new-session -d -s gold-kimi25-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model moonshotai/Kimi-K2.5-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-kimi25-chutes.log"
```
</details>

---

#### gold-kimi26 — OR PRIMARY ✅
*Chutes TEE progress: 367/9122 (4.0%) | OR progress: 21/9122 (0.2%) — OR starts fresh but won't 429*

```bash
# PRIMARY (OpenRouter — moonshotai/kimi-k2.6)
tmux new-session -d -s gold-kimi26 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model moonshotai/kimi-k2.6 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-kimi26.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — moonshotai/Kimi-K2.6-TEE) — NOTE: has 367 Chutes TEE tasks done
tmux new-session -d -s gold-kimi26-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model moonshotai/Kimi-K2.6-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-kimi26-chutes.log"
```
</details>

---

#### gold-minimax — OR PRIMARY ✅
*Chutes TEE progress: 389/9122 (4.3%) | OR progress: 73/9122 (0.8%)*

```bash
# PRIMARY (OpenRouter — minimax/minimax-m2.5)
tmux new-session -d -s gold-minimax \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model minimax/minimax-m2.5 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-minimax.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — MiniMaxAI/MiniMax-M2.5-TEE)
tmux new-session -d -s gold-minimax-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model MiniMaxAI/MiniMax-M2.5-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-minimax-chutes.log"
```
</details>

---

#### gold-qwen397 — OR PRIMARY ✅
*Chutes TEE progress: 365/9122 (4.0%) | OR progress: 116/9122 (1.3%)*

```bash
# PRIMARY (OpenRouter — qwen/qwen3.5-397b-a17b)
tmux new-session -d -s gold-qwen397 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model qwen/qwen3.5-397b-a17b \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-qwen397.log"
```

<details><summary>Chutes fallback (use only if OpenRouter has issues)</summary>

```bash
# FALLBACK (Chutes TEE — Qwen/Qwen3.5-397B-A17B-TEE)
tmux new-session -d -s gold-qwen397-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model Qwen/Qwen3.5-397B-A17B-TEE \
    --provider chutes \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-qwen397-chutes.log"
```
</details>

---

#### gold-qwen3coder — ⚠️ CHUTES ONLY (no confirmed OR equivalent)
*Chutes TEE progress: 477/9122 (5.2%) | No OpenRouter equivalent model found.*

```bash
# CHUTES ONLY (Qwen/Qwen3-Next-80B-A3B-Instruct-TEE — no OR equiv confirmed)
tmux new-session -d -s gold-qwen3coder \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model Qwen/Qwen3-Next-80B-A3B-Instruct-TEE \
    --provider chutes \
    --output-file gold_patches_qwen_qwen3-coder-next.jsonl \
    --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    2>&1 | tee /root/sn66-ninja/logs/gold-qwen3coder.log"
```

> **Note on qwen3coder:** The model name `Qwen/Qwen3-Next-80B-A3B-Instruct-TEE` maps to output file `gold_patches_Qwen_Qwen3-Next-80B-A3B-Instruct-TEE.jsonl` by default, but the existing progress file is `gold_patches_qwen_qwen3-coder-next.jsonl`. Use `--output-file` to ensure the script resumes from the correct file.
> **⚠️ Watch this session closely** — if it starts 429-looping, check if `qwen/qwen3-coder-next` or `qwen/qwen3-next-80b-a3b` is now listed on OpenRouter. If found, switch to OR and use `--output-file gold_patches_qwen_qwen3-coder-next.jsonl` to resume from same progress.

---

### 5b. OpenRouter Runs (7) — Can use `--workers 1` or `--workers 2`

**gold-gemma27b** (763/9122):
```bash
tmux new-session -d -s gold-gemma27b \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model google/gemma-3-27b-it \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-gemma27b.log"
```

**gold-gpt55** (951/9122):
```bash
tmux new-session -d -s gold-gpt55 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model openai/gpt-5.5 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-gpt55.log"
```

**gold-llama70b** (1275/9122):
```bash
tmux new-session -d -s gold-llama70b \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model meta-llama/llama-3.3-70b-instruct \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-llama70b.log"
```

**gold-gemini31p** (1458/9122):
```bash
tmux new-session -d -s gold-gemini31p \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model google/gemini-3.1-pro-preview \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-gemini31p.log"
```

**gold-o4mini** (1899/9122):
```bash
tmux new-session -d -s gold-o4mini \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model openai/o4-mini \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-o4mini.log"
```

**gold-gemini25f** (2359/9122):
```bash
tmux new-session -d -s gold-gemini25f \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model google/gemini-2.5-flash \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-gemini25f.log"
```

**gold-gpt5nano** (2468/9122):
```bash
tmux new-session -d -s gold-gpt5nano \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model openai/gpt-5.4-nano \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-gpt5nano.log"
```

---

### 5c. Verify All 15 Sessions Started

```bash
# From AnonServer (or via SSH)
tmux ls
```

Expected output shows all 15 sessions (7 OR-primary + 1 Chutes-only + 7 original OR):
```
gold-deepseek: 1 windows    ← OpenRouter (deepseek/deepseek-v3.2)
gold-glm5: 1 windows        ← OpenRouter (z-ai/glm-5)
gold-glm51: 1 windows       ← OpenRouter (z-ai/glm-5.1)
gold-kimi25: 1 windows      ← OpenRouter (moonshotai/kimi-k2.5)
gold-kimi26: 1 windows      ← OpenRouter (moonshotai/kimi-k2.6)
gold-minimax: 1 windows     ← OpenRouter (minimax/minimax-m2.5)
gold-qwen397: 1 windows     ← OpenRouter (qwen/qwen3.5-397b-a17b)
gold-qwen3coder: 1 windows  ← CHUTES (no OR equiv)
gold-gemma27b: 1 windows    ← OpenRouter (original)
gold-gpt55: 1 windows       ← OpenRouter (original)
gold-llama70b: 1 windows    ← OpenRouter (original)
gold-gemini31p: 1 windows   ← OpenRouter (original)
gold-o4mini: 1 windows      ← OpenRouter (original)
gold-gemini25f: 1 windows   ← OpenRouter (original)
gold-gpt5nano: 1 windows    ← OpenRouter (original)
```

### 5d. Quick Sanity Check (30 seconds after launch)

```bash
# Check logs for all 15 — look for first task starting, no crash
for sess in gold-deepseek gold-glm5 gold-glm51 gold-kimi25 gold-kimi26 gold-minimax gold-qwen397 gold-qwen3coder gold-gemma27b gold-gpt55 gold-llama70b gold-gemini31p gold-o4mini gold-gemini25f gold-gpt5nano; do
  echo "=== $sess ==="
  tail -5 /root/sn66-ninja/logs/$sess.log 2>/dev/null || echo "no log yet"
done
```

Look for:
- OR runs: `[N/9122] task_id=xxx` or `Skipping task_id=xxx (already done)` → confirms resume from OR progress file
- Chutes run (gold-qwen3coder): `[KEY POOL] Loaded N keys from /root/.secrets/chutes_keys.txt`
- No `FileNotFoundError`, `KeyError`, or `401 Unauthorized`
- **Red flag on OR runs:** `429` or `rate_limit` in logs → OR itself is throttling — rare but check

---

## 6. Results Sync Back to Hetzner1

### 6a. Create sync script on AnonServer

```bash
ssh anonserver "cat > /root/sn66-ninja/scripts/sync_to_hetzner1.sh << 'EOF'
#!/bin/bash
# Sync gold patch progress files from AnonServer → Hetzner1
# Runs every 2 hours via cron

HETZNER1_IP="178.156.199.243"
DEST="/root/sn66-ninja/training_data/gold_patches/"
SRC="/root/sn66-ninja/training_data/gold_patches/"
LOG="/root/sn66-ninja/logs/sync.log"

echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] Starting rsync to Hetzner1...\" >> \$LOG
rsync -az --update \$SRC root@\${HETZNER1_IP}:\$DEST >> \$LOG 2>&1
RC=\$?
if [ \$RC -eq 0 ]; then
  echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] ✅ Sync complete\" >> \$LOG
else
  echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] ❌ Sync FAILED (rc=\$RC)\" >> \$LOG
fi
EOF
chmod +x /root/sn66-ninja/scripts/sync_to_hetzner1.sh
echo '✅ Sync script created'
"
```

### 6b. Ensure AnonServer can SSH back to Hetzner1

```bash
# From AnonServer — check if SSH key exists
ssh anonserver "ls ~/.ssh/id_rsa 2>/dev/null && echo 'KEY EXISTS' || echo 'NO KEY — need to set up SSH'"
```

If no key exists, set up passwordless SSH from AnonServer to Hetzner1:
```bash
# On AnonServer
ssh anonserver "ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa -q 2>/dev/null; cat ~/.ssh/id_rsa.pub"
# Copy the output, then on Hetzner1:
# echo "<public_key_output>" >> ~/.ssh/authorized_keys
```

OR (simpler — run from Hetzner1):
```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub anonserver  # already works
ssh anonserver "ssh-copy-id -i ~/.ssh/id_rsa.pub root@178.156.199.243"
```

### 6c. Add Cron Job on AnonServer (every 2 hours)

```bash
ssh anonserver "
(crontab -l 2>/dev/null; echo '0 */2 * * * /root/sn66-ninja/scripts/sync_to_hetzner1.sh') | crontab -
crontab -l | grep sync_to_hetzner1
"
```

### 6d. Test the sync immediately

```bash
ssh anonserver "/root/sn66-ninja/scripts/sync_to_hetzner1.sh && echo '✅ Manual sync OK'"
```

### 6e. On Hetzner1 — Run incremental save after sync

After the sync lands, merge on Hetzner1:
```bash
python3 /root/sn66-ninja/scripts/incremental_save_to_unified.py
```

To automate the merge (optional, add to Hetzner1 cron after sync):
```bash
# On Hetzner1 — add to crontab (runs 10 min after each sync)
(crontab -l 2>/dev/null; echo '10 */2 * * * python3 /root/sn66-ninja/scripts/incremental_save_to_unified.py >> /root/sn66-ninja/logs/unified_merge.log 2>&1') | crontab -
```

---

## 7. Monitoring — Check All 15 Runs from Hetzner1

### 7a. One-liner progress check (from Hetzner1)

```bash
ssh anonserver "
echo '=== OR-PRIMARY runs (7 active) ==='
for f in \
  gold_patches_deepseek_deepseek-v3_2.jsonl \
  gold_patches_z-ai_glm-5.jsonl \
  gold_patches_z-ai_glm-5_1.jsonl \
  gold_patches_moonshotai_kimi-k2_5.jsonl \
  gold_patches_moonshotai_kimi-k2_6.jsonl \
  gold_patches_minimax_minimax-m2_5.jsonl \
  gold_patches_qwen_qwen3_5-397b-a17b.jsonl; do
  path="/root/sn66-ninja/training_data/gold_patches/\$f"
  lines=\$(wc -l < "\$path" 2>/dev/null || echo 0)
  echo "\$lines/9122 — \$f"
done
echo '=== CHUTES ONLY (1) ==='
path="/root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3-coder-next.jsonl"
lines=\$(wc -l < "\$path" 2>/dev/null || echo 0)
echo "\$lines/9122 — gold_patches_qwen_qwen3-coder-next.jsonl"
echo '=== Original OpenRouter runs (7) ==='
for f in \
  gold_patches_google_gemma-3-27b-it.jsonl \
  gold_patches_openai_gpt-5_5.jsonl \
  gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  gold_patches_google_gemini-3_1-pro-preview.jsonl \
  gold_patches_openai_o4-mini.jsonl \
  gold_patches_google_gemini-2_5-flash.jsonl \
  gold_patches_openai_gpt-5_4-nano.jsonl; do
  path="/root/sn66-ninja/training_data/gold_patches/\$f"
  lines=\$(wc -l < "\$path" 2>/dev/null || echo 0)
  echo "\$lines/9122 — \$f"
done
echo '=== Chutes TEE files (fallback/parallel) ==='
for f in \
  gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl \
  gold_patches_zai-org_GLM-5-TEE.jsonl \
  gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl \
  gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl; do
  path="/root/sn66-ninja/training_data/gold_patches/\$f"
  lines=\$(wc -l < "\$path" 2>/dev/null || echo 0)
  echo "\$lines/9122 (TEE fallback) — \$f"
done
"
```
### 7b. Check tmux sessions still running

```bash
ssh anonserver "tmux ls 2>/dev/null | wc -l && echo 'sessions active'"
```

### 7c. Tail recent log from any specific run

```bash
ssh anonserver "tail -20 /root/sn66-ninja/logs/gold-glm5.log"
```

### 7d. Check if any run crashed

```bash
ssh anonserver "
for sess in gold-deepseek gold-glm5 gold-glm51 gold-kimi25 gold-kimi26 gold-minimax gold-qwen397 gold-qwen3coder gold-gemma27b gold-gpt55 gold-llama70b gold-gemini31p gold-o4mini gold-gemini25f gold-gpt5nano; do
  if tmux has-session -t \$sess 2>/dev/null; then
    echo '✅ RUNNING: '\$sess
  else
    echo '❌ DEAD: '\$sess
  fi
done
"
```

---

## 8. Rollback Plan

If AnonServer migration fails for any reason, restart on Hetzner1 is straightforward.

### 8a. Recover progress files from AnonServer (if partially done)

```bash
# Pull whatever AnonServer produced back to Hetzner1
rsync -avz anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_*.jsonl \
  /root/sn66-ninja/training_data/gold_patches/
```

### 8b. Kill AnonServer sessions

```bash
ssh anonserver "
for sess in gold-deepseek gold-glm5 gold-glm51 gold-kimi25 gold-kimi26 gold-minimax gold-qwen397 gold-qwen3coder gold-gemma27b gold-gpt55 gold-llama70b gold-gemini31p gold-o4mini gold-gemini25f gold-gpt5nano; do
  tmux kill-session -t \$sess 2>/dev/null && echo \"killed \$sess\" || echo \"\$sess already gone\"
done
"
```

### 8c. Restart failed runs on Hetzner1

For each run that needs to be restarted on Hetzner1, the commands are identical to Section 5 but without the `ssh anonserver` prefix, and without `--key-file` flag (Hetzner1 has the default key file path still).

**Example (Hetzner1 restart for gold-glm5 — OR primary):**
```bash
tmux new-session -d -s gold-glm5 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model z-ai/glm-5 \
    --provider openrouter \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm5.log"
```

**Example (Hetzner1 restart for gold-glm5 — Chutes TEE fallback):**
```bash
tmux new-session -d -s gold-glm5-chutes \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model zai-org/GLM-5-TEE \
    --provider chutes \
    --workers 1 \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm5-chutes.log"
```

The script auto-resumes from the last completed task_id in the `.jsonl` file — **no data is lost**.

### 8d. Verify resume works correctly

After restart (anywhere), check the first few log lines:
```bash
grep "Skipping task_id\|Starting task" /root/sn66-ninja/logs/gold-glm5.log | head -10
```
You should see: `Skipping task_id=xxx (already done)` for the first N tasks, then `Starting task_id=yyy` where yyy is the first unprocessed one.

---

## 9. Notes and Edge Cases

### qwen3-coder output file mismatch
The model `Qwen/Qwen3-Next-80B-A3B-Instruct-TEE` would normally produce output file `gold_patches_Qwen_Qwen3-Next-80B-A3B-Instruct-TEE.jsonl`, but the existing progress file is named `gold_patches_qwen_qwen3-coder-next.jsonl`. Always use `--output-file gold_patches_qwen_qwen3-coder-next.jsonl` for this run or the script won't find the existing progress and will restart from 0.

### GLM-5.1-TEE model name
The run is `gold-glm51` with model `zai-org/GLM-5.1-TEE`. Verify this model ID is still active on Chutes before launching. If Chutes returns 404 on this model, skip this run until the model is re-listed.

### Chutes 429 handling
The script has built-in key rotation on 429. With `--workers 1` and multiple keys in the pool, it will automatically rotate through keys on rate limits. No manual intervention needed.

**Updated strategy (2026-05-15):** 7 of 8 formerly-Chutes runs now use OpenRouter as the primary provider to bypass Chutes 429 hell entirely. Only gold-qwen3coder remains on Chutes (no confirmed OR equivalent). If Chutes stabilizes, the Chutes TEE sessions can be run in parallel (different output files = more unique training data, not duplicates).

### OpenRouter key on AnonServer
The OR key is stored in `/root/.secrets/api_keys.env` as `OPENROUTER_API_KEY` (or `SN62_OPENROUTER_API_KEY`). The multi_model_sampler.py reads it automatically when `--provider openrouter` is used. No additional `--key-file` flag needed for OR runs.

### Memory on AnonServer
AnonServer has 94 GB RAM / 18 cores. Running all 15 runs simultaneously is safe — each run is I/O bound (API calls) not compute bound. Total RSS per run is ~100 MB. 15 × 100 MB = ~1.5 GB RAM, well within limits.

### Disk growth estimate
Each completed task adds ~6-7 KB to the output file. Remaining tasks across all 15 runs:
- ~(9122 - current_progress) × 6.5 KB per run
- Rough total: ~15 runs × ~8000 remaining tasks × 6.5 KB ≈ ~780 GB worst case at full completion
- AnonServer has 169 GB free — sufficient for ~3-4 months of progress before needing to clear merged data from Hetzner1 off AnonServer
- **Action item:** Monitor disk weekly with `ssh anonserver "df -h /root"`

---

## 10. Quick-Reference: Full Migration in One Go

Copy-paste this entire block to execute steps 1-5 in sequence from Hetzner1:

```bash
# STEP 1: Pre-checks
ssh anonserver "python3 --version && df -h / | tail -1 && tmux -V && echo '✅ PRE-CHECKS OK'"

# STEP 2: Directories
ssh anonserver "mkdir -p /root/sn66-ninja/{training_data/gold_patches,scripts,logs} /root/sn66-r2-dataset /root/.secrets && chmod 700 /root/.secrets && echo '✅ DIRS OK'"

# STEP 3: Transfer files (takes ~5-8 min — 22 progress files + dataset)
rsync -az --progress /root/sn66-r2-dataset/hf_dataset_cache.jsonl anonserver:/root/sn66-r2-dataset/ && \
rsync -az /root/sn66-ninja/multi_model_sampler.py /root/sn66-ninja/scripts/incremental_save_to_unified.py anonserver:/root/sn66-ninja/ && \
rsync -az /root/sn66-ninja/scripts/incremental_save_to_unified.py anonserver:/root/sn66-ninja/scripts/ && \
rsync -az --progress \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3-coder-next.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek_deepseek-v3_2.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_z-ai_glm-5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_z-ai_glm-5_1.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_kimi-k2_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_kimi-k2_6.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_minimax_minimax-m2_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3_5-397b-a17b.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemma-3-27b-it.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-3_1-pro-preview.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_o4-mini.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-2_5-flash.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_4-nano.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/ && echo "✅ FILES TRANSFERRED (22 files)"

# STEP 4: Copy keys
scp /root/project-nobi/scripts/chutes_keys.txt anonserver:/root/.secrets/chutes_keys.txt && \
scp /root/.secrets/api_keys.env anonserver:/root/.secrets/api_keys.env && \
ssh anonserver "chmod 600 /root/.secrets/chutes_keys.txt /root/.secrets/api_keys.env" && \
echo "✅ KEYS COPIED"

# STEP 5: Patch script
ssh anonserver "sed -i 's|/root/project-nobi/scripts/chutes_keys.txt|/root/.secrets/chutes_keys.txt|g' /root/sn66-ninja/multi_model_sampler.py && echo '✅ SCRIPT PATCHED'"

echo ""
echo "✅ ✅ ✅ SETUP COMPLETE — now SSH to AnonServer and run launch commands from Section 5"
```

---

*Plan written by Opus, 2026-05-15. Execute from Hetzner1 terminal. All commands are copy-pasteable. API keys referenced by path only — never printed.*
