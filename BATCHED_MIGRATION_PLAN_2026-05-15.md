# BATCHED MIGRATION PLAN — 2026-05-15 (CORRECTED)
## 15 Gold-Patch Runs → AnonServer (144.91.65.30)
## 3 runs per batch · sequential · save after each batch

> **CRITICAL RULE:** Every run uses `--output-file <original_filename>` to preserve existing progress.
> This ensures the sampler auto-resumes from the saved records — never restarts from zero.

---

## BATCH OVERVIEW

| Batch | Runs | Provider | Est. duration | Remaining samples |
|-------|------|----------|---------------|-------------------|
| 1 | gpt5nano · gemini25f · o4mini | OR · OR · OR | ~14h | 6654 · 6763 · 7223 |
| 2 | gemini31p · llama70b · gpt55 | OR · OR · OR | ~45h | 7664 · 7847 · 8171 |
| 3 | gemma27b · glm5 · qwen3coder | OR · Chutes · OR | ~75h | 8359 · 8539 · 8645 |
| 4 | glm51 · minimax · kimi26 | Chutes · Chutes · OR | ~215h | 8701 · 8733 · 8755 |
| 5 | qwen397 · kimi25 · deepseek | OR · OR · OR | ~285h | 8757 · 8957 · 9118 |

**AnonServer:** 144.91.65.30 (`ssh anonserver`) | 94GB RAM · 174GB disk free  
**Gold dir on Hetzner1:** `/root/sn66-ninja/training_data/gold_patches/`  
**Gold dir on AnonServer:** `/root/sn66-ninja/training_data/gold_patches/`  
**Unified gold:** `/root/sn66-ninja/training_data/training_unified_gold.jsonl`

---

## ONE-TIME INFRASTRUCTURE SETUP

Run from **Hetzner1** before Batch 1:

```bash
# 1. Directories
ssh anonserver "mkdir -p /root/sn66-ninja/{training_data/gold_patches,scripts,logs} \
  /root/sn66-r2-dataset /root/.secrets && chmod 700 /root/.secrets"

# 2. Dataset + scripts
rsync -az --progress /root/sn66-r2-dataset/hf_dataset_cache.jsonl \
  anonserver:/root/sn66-r2-dataset/
rsync -az /root/sn66-ninja/multi_model_sampler.py anonserver:/root/sn66-ninja/
rsync -az /root/sn66-ninja/scripts/incremental_save_to_unified.py \
  anonserver:/root/sn66-ninja/scripts/

# 3. API keys (SECURE — never print values)
scp /root/project-nobi/scripts/chutes_keys.txt anonserver:/root/.secrets/chutes_keys.txt
scp /root/.secrets/api_keys.env anonserver:/root/.secrets/api_keys.env
ssh anonserver "chmod 600 /root/.secrets/*"

# 4. Patch Chutes key path in script
ssh anonserver "sed -i \
  's|/root/project-nobi/scripts/chutes_keys.txt|/root/.secrets/chutes_keys.txt|g' \
  /root/sn66-ninja/multi_model_sampler.py && echo '✅ patched'"

# 5. Set up 2h auto-sync cron on AnonServer
ssh anonserver "(crontab -l 2>/dev/null; echo '0 */2 * * * rsync -az \
  /root/sn66-ninja/training_data/gold_patches/*.jsonl \
  root@178.156.199.243:/root/sn66-ninja/training_data/gold_patches/ 2>/dev/null') | crontab -"

# 6. Verify R2 dataset
ssh anonserver "wc -l /root/sn66-r2-dataset/hf_dataset_cache.jsonl"
# Expected: 9122
```

---

## BATCH 1 — gold-gpt5nano · gold-gemini25f · gold-o4mini

**Providers:** OpenRouter × 3 | **Estimated duration:** ~14h (o4mini is slowest)

### Step 1 — Transfer 3 progress files to AnonServer (from Hetzner1)

```bash
rsync -az \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_4-nano.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-2_5-flash.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_o4-mini.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/
```

### Step 2 — Launch (SSH to AnonServer, then run)

```bash
ssh anonserver

tmux new-session -d -s gold-gpt5nano \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model openai/gpt-4.1-nano --provider openrouter --workers 1 \
    --output-file gold_patches_openai_gpt-5_4-nano.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-gpt5nano.log"

tmux new-session -d -s gold-gemini25f \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model google/gemini-2.5-flash --provider openrouter --workers 1 \
    --output-file gold_patches_google_gemini-2_5-flash.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-gemini25f.log"

tmux new-session -d -s gold-o4mini \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model openai/o4-mini --provider openrouter --workers 1 \
    --output-file gold_patches_openai_o4-mini.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-o4mini.log"

tmux ls
```

### Step 3 — Monitor (from Hetzner1)

```bash
ssh anonserver "for f in \
  gold_patches_openai_gpt-5_4-nano.jsonl \
  gold_patches_google_gemini-2_5-flash.jsonl \
  gold_patches_openai_o4-mini.jsonl; do
  echo \"\$(wc -l < /root/sn66-ninja/training_data/gold_patches/\$f 2>/dev/null || echo 0)/9122 — \$f\"
done"
```

### Step 4 — After all 3 reach 9122/9122 → Save + advance

```bash
# Sync back to Hetzner1
rsync -az \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_4-nano.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-2_5-flash.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_openai_o4-mini.jsonl \
  /root/sn66-ninja/training_data/gold_patches/

# Merge into unified gold
cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py

# Verify count grew
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl

# Delete from AnonServer (free disk for next batch)
ssh anonserver "rm \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_4-nano.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-2_5-flash.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_o4-mini.jsonl"

# Disk check
ssh anonserver "df -h / | tail -1"

# ✅ Proceed to Batch 2
```

---

## BATCH 2 — gold-gemini31p · gold-llama70b · gold-gpt55

**Providers:** OpenRouter × 3 | **Estimated duration:** ~45h (gpt55 is slowest)

### Step 1 — Transfer 3 progress files (from Hetzner1)

```bash
rsync -az \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-3_1-pro-preview.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_5.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/
```

### Step 2 — Launch (on AnonServer)

```bash
ssh anonserver

tmux new-session -d -s gold-gemini31p \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model google/gemini-2.5-pro-preview --provider openrouter --workers 1 \
    --output-file gold_patches_google_gemini-3_1-pro-preview.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-gemini31p.log"

tmux new-session -d -s gold-llama70b \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model meta-llama/llama-3.3-70b-instruct --provider openrouter --workers 1 \
    --output-file gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-llama70b.log"

tmux new-session -d -s gold-gpt55 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model openai/gpt-4.5-preview --provider openrouter --workers 1 \
    --output-file gold_patches_openai_gpt-5_5.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-gpt55.log"

tmux ls
```

### Step 3 — Monitor

```bash
ssh anonserver "for f in \
  gold_patches_google_gemini-3_1-pro-preview.jsonl \
  gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  gold_patches_openai_gpt-5_5.jsonl; do
  echo \"\$(wc -l < /root/sn66-ninja/training_data/gold_patches/\$f 2>/dev/null || echo 0)/9122 — \$f\"
done"
```

### Step 4 — Save + advance

```bash
rsync -az \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-3_1-pro-preview.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_5.jsonl \
  /root/sn66-ninja/training_data/gold_patches/

cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl

ssh anonserver "rm \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemini-3_1-pro-preview.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_openai_gpt-5_5.jsonl"

ssh anonserver "df -h / | tail -1"
# ✅ Proceed to Batch 3
```

---

## BATCH 3 — gold-gemma27b · gold-glm5 · gold-qwen3coder

**Providers:** OR · Chutes · OR | **Estimated duration:** ~75h (qwen3coder slowest)

### Step 1 — Transfer

```bash
rsync -az \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemma-3-27b-it.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3-coder-next.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/
```

### Step 2 — Launch (on AnonServer)

```bash
ssh anonserver

tmux new-session -d -s gold-gemma27b \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model google/gemma-3-27b-it --provider openrouter --workers 1 \
    --output-file gold_patches_google_gemma-3-27b-it.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-gemma27b.log"

tmux new-session -d -s gold-glm5 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model zai-org/GLM-5-TEE --provider chutes --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    --output-file gold_patches_zai-org_GLM-5-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm5.log"

tmux new-session -d -s gold-qwen3coder \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model qwen/qwen-2.5-coder-32b-instruct --provider openrouter --workers 1 \
    --output-file gold_patches_qwen_qwen3-coder-next.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-qwen3coder.log"

tmux ls
```

### Step 3 — Monitor

```bash
ssh anonserver "for f in \
  gold_patches_google_gemma-3-27b-it.jsonl \
  gold_patches_zai-org_GLM-5-TEE.jsonl \
  gold_patches_qwen_qwen3-coder-next.jsonl; do
  echo \"\$(wc -l < /root/sn66-ninja/training_data/gold_patches/\$f 2>/dev/null || echo 0)/9122 — \$f\"
done"
```

### Step 4 — Save + advance

```bash
rsync -az \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemma-3-27b-it.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3-coder-next.jsonl \
  /root/sn66-ninja/training_data/gold_patches/

cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl

ssh anonserver "rm \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_google_gemma-3-27b-it.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_qwen_qwen3-coder-next.jsonl"

ssh anonserver "df -h / | tail -1"
# ✅ Proceed to Batch 4
```

---

## BATCH 4 — gold-glm51 · gold-minimax · gold-kimi26

**Providers:** Chutes · Chutes · OR | **Estimated duration:** ~215h (GLM-5.1 slowest due to timeouts)

### Step 1 — Transfer

```bash
rsync -az \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/
```

### Step 2 — Launch (on AnonServer)

```bash
ssh anonserver

tmux new-session -d -s gold-glm51 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model zai-org/GLM-5.1-TEE --provider chutes --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    --output-file gold_patches_zai-org_GLM-5_1-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-glm51.log"

tmux new-session -d -s gold-minimax \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model MiniMaxAI/MiniMax-M2.5-TEE --provider chutes --workers 1 \
    --key-file /root/.secrets/chutes_keys.txt \
    --output-file gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-minimax.log"

tmux new-session -d -s gold-kimi26 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model moonshotai/kimi-k1.5 --provider openrouter --workers 1 \
    --output-file gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-kimi26.log"

tmux ls
```

### Step 3 — Monitor

```bash
ssh anonserver "for f in \
  gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl; do
  echo \"\$(wc -l < /root/sn66-ninja/training_data/gold_patches/\$f 2>/dev/null || echo 0)/9122 — \$f\"
done"
```

### Step 4 — Save + advance

```bash
rsync -az \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/

cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl

ssh anonserver "rm \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_zai-org_GLM-5_1-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl"

ssh anonserver "df -h / | tail -1"
# ✅ Proceed to Batch 5
```

---

## BATCH 5 — gold-qwen397 · gold-kimi25 · gold-deepseek

**Providers:** OR · OR · OR | **Estimated duration:** ~300h (deepseek slowest)

### Step 1 — Transfer

```bash
rsync -az \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/
```

### Step 2 — Launch (on AnonServer)

```bash
ssh anonserver

tmux new-session -d -s gold-qwen397 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model qwen/qwen3.5-235b-a22b --provider openrouter --workers 1 \
    --output-file gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-qwen397.log"

tmux new-session -d -s gold-kimi25 \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model moonshotai/kimi-k1.5 --provider openrouter --workers 1 \
    --output-file gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-kimi25.log"

tmux new-session -d -s gold-deepseek \
  "python3 /root/sn66-ninja/multi_model_sampler.py \
    --model deepseek/deepseek-chat --provider openrouter --workers 1 \
    --output-file gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl \
    2>&1 | tee /root/sn66-ninja/logs/gold-deepseek.log"

tmux ls
```

### Step 3 — Monitor

```bash
ssh anonserver "for f in \
  gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
  gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl; do
  echo \"\$(wc -l < /root/sn66-ninja/training_data/gold_patches/\$f 2>/dev/null || echo 0)/9122 — \$f\"
done"
```

### Step 4 — FINAL SAVE

```bash
rsync -az \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  anonserver:/root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/

cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl

ssh anonserver "rm \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl \
  /root/sn66-ninja/training_data/gold_patches/gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl"

echo "✅ ALL 15 RUNS COMPLETE"
```

---

## MASTER MONITOR SCRIPT

Save to `/root/scripts/check_migration_progress.sh`:

```bash
#!/bin/bash
echo "=== Gold Patch Migration Progress — $(date -u) ==="
GOLD="/root/sn66-ninja/training_data/gold_patches"
FILES=(
  "gold_patches_openai_gpt-5_4-nano.jsonl"
  "gold_patches_google_gemini-2_5-flash.jsonl"
  "gold_patches_openai_o4-mini.jsonl"
  "gold_patches_google_gemini-3_1-pro-preview.jsonl"
  "gold_patches_meta-llama_llama-3_3-70b-instruct.jsonl"
  "gold_patches_openai_gpt-5_5.jsonl"
  "gold_patches_google_gemma-3-27b-it.jsonl"
  "gold_patches_zai-org_GLM-5-TEE.jsonl"
  "gold_patches_qwen_qwen3-coder-next.jsonl"
  "gold_patches_zai-org_GLM-5_1-TEE.jsonl"
  "gold_patches_MiniMaxAI_MiniMax-M2_5-TEE.jsonl"
  "gold_patches_moonshotai_Kimi-K2_6-TEE.jsonl"
  "gold_patches_Qwen_Qwen3_5-397B-A17B-TEE.jsonl"
  "gold_patches_moonshotai_Kimi-K2_5-TEE.jsonl"
  "gold_patches_deepseek-ai_DeepSeek-V3_2-TEE.jsonl"
)
echo "--- Hetzner1 (merged) ---"
DONE=0; TOTAL=0
for f in "${FILES[@]}"; do
  n=$(wc -l < "$GOLD/$f" 2>/dev/null || echo 0)
  TOTAL=$((TOTAL+n))
  [ "$n" -ge 9122 ] && DONE=$((DONE+1)) && STATUS="✅" || STATUS="$(awk "BEGIN{printf \"%.1f%%\", $n/91.22}")"
  printf "  %-60s %5d %s\n" "$f" "$n" "$STATUS"
done
echo "  Completed: $DONE/15 | Total samples: $TOTAL"
echo ""
echo "--- AnonServer (live) ---"
ssh anonserver "
for f in ${FILES[*]}; do
  n=\$(wc -l < /root/sn66-ninja/training_data/gold_patches/\$f 2>/dev/null || echo 0)
  echo \"  \$n/9122 — \$f\"
done" 2>/dev/null
echo ""
echo "--- Active tmux sessions ---"
ssh anonserver "tmux ls 2>/dev/null || echo '  none'" 2>/dev/null
echo ""
echo "--- Unified gold total ---"
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl
echo ""
echo "--- AnonServer disk ---"
ssh anonserver "df -h / | tail -1" 2>/dev/null
```

```bash
chmod +x /root/scripts/check_migration_progress.sh
```

---

## EMERGENCY ABORT + SAVE

```bash
# 1. Kill all active sessions on AnonServer
ssh anonserver "for s in gold-gpt5nano gold-gemini25f gold-o4mini \
  gold-gemini31p gold-llama70b gold-gpt55 gold-gemma27b gold-glm5 \
  gold-qwen3coder gold-glm51 gold-minimax gold-kimi26 \
  gold-qwen397 gold-kimi25 gold-deepseek; do
  tmux kill-session -t \$s 2>/dev/null && echo \"killed \$s\"
done"

# 2. Sync ALL partial progress back to Hetzner1
rsync -az anonserver:/root/sn66-ninja/training_data/gold_patches/*.jsonl \
  /root/sn66-ninja/training_data/gold_patches/

# 3. Merge partial into unified gold
cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py
wc -l /root/sn66-ninja/training_data/training_unified_gold.jsonl

# 4. Restart any run locally on Hetzner1 if needed
# tmux new-session -d -s gold-XXXX \
#   "python3 /root/sn66-ninja/multi_model_sampler.py \
#     --model MODEL --provider openrouter --workers 1 \
#     --output-file ORIGINAL_FILENAME.jsonl \
#     2>&1 | tee /tmp/gold-XXXX-local.log"
```

---

*Corrected 2026-05-15 — all --output-file flags verified against actual filenames*
