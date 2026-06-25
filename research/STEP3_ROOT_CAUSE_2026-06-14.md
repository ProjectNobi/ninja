# Step 3: Root Cause Analysis — 2026-06-14

**Agent:** SN66 Step 3 Synthesis (Opus 4.8)
**Inputs:** STEP1_SOURCE_INTEL, STEP2_DATA_INTEL, king_agent.py (684L, SHA a56ffdf5), agent.py (5,337L), FINAL_SN66_PIPELINE.md
**King:** `unarbos/ninja` SHA `a56ffdf5`, source=`burn` (default), king since 06:51 UTC, defended 13 duels / 0 replacements
**Live judge:** `google/gemini-3.1-flash-lite` (95%) + solve_time (5%); win_margin=**6**; ties ignored
**Our live WR vs this king:** ~42.8% median over 30 duels — **we are losing, by ~4 decisive rounds**

---

## TL;DR (top 5 changes for vNext)

| # | Change | Expected WR | Risk |
|---|--------|-------------|------|
| **1** | **Adopt the king's exact output contract OR add `_NATIVE_TOOL_CALL_RE` + bash-block parsing.** Our agent ONLY parses `<command>`/`<edit>`/`<final>` XML. The validator's model may emit bash blocks or native `<\|tool_call_begin\|>` tokens (the king's promotion commit). If our parser misses those, we get FormatErrors → empty/partial patches → losses. This is the single biggest structural risk. | **+8–15%** | Medium (changes core loop) |
| **2** | **Re-base on king_agent.py per L-SN66-KING-BASE-MANDATORY-1, then layer our proven SYSTEM_PROMPT rules onto the king's loop** — do NOT ship our 5,337L architecture as-is. High king-similarity = 51% WR vs 38% for very-different patches (Intel D). The king's loop won 13 straight; start from it. | **+5–10%** | Medium |
| **3** | **Restore the 3 pipeline-required SYSTEM_PROMPT patterns that are MISSING from our prompt:** explicit `COMPLETENESS BEATS MINIMALISM` header, the "under-editing costs MORE than over-editing" asymmetry, and an explicit `UPDATE TASK WIRING RULE`. Our prompt currently leans **minimalist/surgical** with no completeness counterbalance — exactly the FORBIDDEN Pattern 2 framing. FEATURE is our weakest at 41%; #1 loss cause is partial implementation (967 lessons). | **+4–8%** (FEATURE/UPDATE) | Low |
| **4** | **Add an explicit acceptance-criteria walkthrough + "address every acceptance criterion" framing.** Gemini judge fires on `acceptance criteria` (1,508 win occurrences) far more than Sonnet did. Make the agent enumerate and tick off each criterion before `<final>`/submit. | **+3–6%** | Low |
| **5** | **Keep our patch sanitizer (auto-fail phrase strip) AND incorporate harness fix `ae2158103232`** (reject empty proxy-normalized replies; read list-shaped content parts). The king does NOT yet have this fix. Empty-reply handling prevents silent format-loop losses on the new judge/model. | **+2–4%** | Low |

**Net expectation:** a king-based agent with our completeness rules + dual-format parsing should move WR from ~43% to the 55–60% needed for margin 6.

---

## Analysis 1: King vs Our Agent (King 684L vs Ours 5,337L)

### What the king does that our agent doesn't
1. **Native tool-call token parsing (`_NATIVE_TOOL_CALL_RE`).** This is literally the change (`a56ffdf5`) that made it king. It pulls shell commands from `<\|tool_call_begin\|>...<\|tool_call_argument_begin\|>{json}<\|tool_call_end\|>` payloads emitted by Kimi/Moonshot-style models. **Our agent.py has NO such handling** (confirmed: `grep tool_call_begin` → empty). Our parser is `ACTION_RE = <command>...</command>`, `EDIT_RE = <edit>`, `FINAL_RE = <final>`.
2. **Bash-block parsing (` ```bash `).** The king parses ` ```bash ` / ` ```sh ` fenced blocks. Our agent does NOT — it requires `<command>` XML tags. If the validator-provided model is more naturally inclined to emit markdown bash blocks (the king's whole contract), and ignores our XML instruction, **we lose the command entirely.**
3. **Dead-simple single-attempt loop.** One `run_agent_loop()`, up to 50 steps, echo-sentinel to submit. No revert/replay machinery.

### What our agent does that may be wasted (or harmful)
1. **GPS candidate ensemble / multi-shot** (`_gps_generate_candidates`, up to 5 candidates, revert-between, prune+score). The king has **zero** multi-shot. The judge only ever sees the FINAL patch — it cannot reward "we generated 5 and picked the best." Multi-shot's only value is *if our selector reliably picks a better patch than a single shot would produce.* Under a 280s wall and 50 steps, multi-shot **eats budget** that a single careful pass could spend reading files in full. Intel B shows ~10% of rounds already hit `time_limit_exceeded`; multi-shot raises that risk.
2. **TF-IDF / rescue-ranker file discovery** (`_RESCUE_RANKER`, `_preload_needles`, scored candidate file lists). The king does NONE of this and won 13 duels. The judge does not see *how* you found the file. This machinery only helps if it makes the *final patch* more complete; otherwise it's pure step/token overhead.
3. **Preloaded-context injection** (`_PRELOAD_BEGIN_MARKER` … snippets injected into the first user prompt). Same logic: helps only if it improves the final patch. Given the model is validator-chosen (possibly weak), a large preloaded blob can *distract* — Gemini Flash Lite has finite attention and the #1 loss cause is import/scope errors, not "couldn't find the file."
4. **Custom `<edit>` verb.** Robust against heredoc truncation (a real win) — but only usable if the model actually emits `<edit>`. If the validator model is bash-block-trained, it won't, and our edit safety is moot.

### Is bigger SYSTEM_PROMPT better for the Gemini judge?
**No evidence that it is — and some that it hurts.** The king's SYSTEM_PROMPT is ~12 lines (bare contract). Ours is ~200 lines. The judge never sees the SYSTEM_PROMPT — it sees the **patch**. A long prompt only helps if it changes model behavior toward better patches. With a *weaker* validator-chosen model and Gemini Flash Lite judging, the binding constraints are: (a) does the model emit a parseable action, (b) does the patch compile, (c) does it cover all requirements. A long prompt risks the model losing the thread (e.g., emitting `<command>` when the model is bash-native). **Our prompt's length is a liability if it doesn't match the model's natural output format.**

### Does context-preloading help or hurt when the judge only sees final patch quality?
The judge scores ONLY the diff. Preloading helps **iff** it raises final patch completeness/correctness. Evidence is mixed:
- **For:** Intel E shows `import issues` is the #1 loss cause (1,961). Reading the right file in full could reduce import/placement errors.
- **Against:** The king has zero preloading and beats us. The model finds files fine with `grep`/`sed` in 50 steps. Preloading consumes prompt budget and can inject wrong files (ranker false positives) that mislead a weaker model.
- **Verdict:** Preloading is NOT the king's edge and is not where we're losing. Keep it minimal or drop it; do not treat it as the win condition.

---

## Analysis 2: Gemini Judge Implications (Gemini 3.1 Flash Lite vs Sonnet 4.6)

**All prior gate data is invalidated — the judge changed from Sonnet 4.6 to Gemini 3.1 Flash Lite.** Our harness still defaults to `anthropic/claude-sonnet-4.6` (validator_harness_v6.py:72). **MANDATORY: gate with `--judge-model google/gemini-3.1-flash-lite`.**

### What Gemini 3.1 Flash Lite rewards differently
From Intel E (live-judge rationale mining, last 500 duels):
- **`acceptance criteria` — 1,508 win occurrences.** This is the dominant Gemini signal and is FAR more explicit than under Sonnet. Gemini literally checks the task's acceptance criteria item by item. **→ The agent must enumerate and satisfy each acceptance criterion, and our prompt should frame the solution AROUND acceptance criteria.**
- `more complete` (979), `correctly implements` (934), `compiles correctly` (795) — Gemini rewards *completeness + compilability* heavily.
- Gemini is **more sensitive to import-placement errors** (imports inside function bodies, wrong scope) than Sonnet — 1,961 `import issues` in loss context, #1 loss cause.
- Gemini scores in **discrete 0.05 steps** (0–100 integer / 100). This means small quality differences round to the same score → many ties; you need a *clearly* better patch to win a round (consistent with win_margin=6).

### What carries over from Sonnet-era rules
Both judges penalize: partial implementation, compile errors, missing scope, out-of-scope churn. Both reward: reference alignment, completeness, TypeScript correctness. So our completeness/scope/type rules carry over. The **new emphasis** is acceptance-criteria framing and import correctness.

### What "convincingly better" means for win_margin=6
- 50 rounds, ties ignored. We need `wins − losses > 6` → at least 4 net decisive wins beyond parity (e.g., 28W/21L with 1 tie).
- Because Gemini scores in 0.05 steps, **a patch that is "slightly" better often ties** (same rounded score) and is discarded. To convert a round into a *decisive* win we must be **clearly** more complete/correct — typically the difference between "addresses all acceptance criteria + compiles" (≥0.95) vs "partial / one import wrong" (≤0.75).
- Live data (STEP1 §1e) shows the king's gap appears at the 0.65–0.75 LLM-score band — medium-hard tasks where its minimal exploration submits a patch that misses a requirement. **That band is where we win or lose the duel.** Our edge must be: on those medium-hard tasks, produce the complete patch the king's bare loop misses.

---

## Analysis 3: Why the Simple King Wins — What It Tells Us

The new king is ~10× smaller (684L vs the old 20,889L monolith) and beat everything for 13 straight duels.

1. **The MODEL does the heavy lifting, not the harness.** Validator models are now strong enough that a clean 50-step bash loop reaches the fix. All the old "special sauce" (TF-IDF, RAPTOR, evidence chains, multi-shot) added marginal value the model now provides natively. The harness's job is reduced to: (a) reliably parse the model's action format, (b) feed observations back, (c) collect the diff. **The king's promotion was a PARSER fix, not an intelligence fix** — proof that *plumbing reliability*, not cleverness, is the current battleground.
2. **Complex context-gathering is mostly noise.** A weaker/cheaper validator model has limited attention. Dumping ranked preload blobs and long methodology prompts can *degrade* its focus. The king gives it a clean contract and lets it work. Our 5,337L of machinery is optimizing a problem the model already solves — while adding failure surface (format mismatch, budget starvation, ranker false positives).
3. **MVP that beats this king:** the king's own loop (bash blocks + native tool-call parsing, 50 steps, 280s wall, simple submit sentinel) **plus** a SYSTEM_PROMPT that pushes *completeness + acceptance-criteria coverage + import correctness* harder than the king's minimal prompt. The king's prompt is correct-but-terse ("identify every requirement; penalized for partial"). We beat it by making completeness/wiring **explicit and enforced**, while NOT regressing on scope discipline. That's a ~50-line prompt delta on the king's loop — not a 5,000-line rewrite.

---

## Analysis 4: Our Agent's Specific Weaknesses vs the New King

### Where we likely lose
1. **Output-format mismatch (HIGHEST RISK).** We force `<command>`/`<edit>`/`<final>`. The king's contract is bash blocks, and the king added native tool-call parsing because real validator models emit those formats. If the validator model emits ` ```bash ` or `<\|tool_call_begin\|>`, **our agent produces zero parseable actions → format repair loop → empty/partial diff → automatic loss.** We have no fallback parser for either format. This alone can explain a large slice of our 43% WR.
2. **Budget starvation from multi-shot.** GPS ensemble + revert/replay under a 248–280s wall risks `time_limit_exceeded` (already ~10% of rounds). A timed-out round ships whatever partial diff exists → low Gemini score.
3. **Minimalist prompt framing without completeness counterbalance.** Our prompt's SURGICAL EDITING / SCOPE DISCIPLINE sections are strong and lengthy; the completeness side is a single line. This is FORBIDDEN Pattern 2 (pure minimalism without the asymmetry). It biases the model to under-edit → partial implementations → the #1 loss cause.

### FEATURE at 41% WR — root cause
FEATURE is our weakest (Intel B: 41%, king beats us). Root cause: **partial coverage.** FEATURE tasks span multiple integration points (page+route+nav+data; model+migration+serializer+view+URL). Our prompt DOES have a Dart/Flutter screen-enumeration rule and a "FEATURE and UPDATE: enumerate ALL deliverables" line — good — but it's buried and lacks the COMPLETENESS-BEATS-MINIMALISM enforcement that makes the model err toward *more* coverage. Under a weaker validator model, the model defaults to the first component and stops. **Fix: explicit completeness asymmetry + acceptance-criteria checklist gating `<final>`/submit.**

### UPDATE tasks — wiring rule status
**The pipeline-canonical "UPDATE TASK WIRING RULE" is effectively MISSING from our live SYSTEM_PROMPT.** `grep` over the prompt region (3128–3640) finds NO "wire / never called / 0 points / WIRING" language in the prompt itself (the only `wiring` hits are in a code comment at L1703 and the env-config comment at L75). The relocation-phrasing recognition block is good but is about *file creation*, not *functional wiring*. Per L-SN66-NEVER-DELETE-RULE-1 / v68 catastrophe, stripping the wiring rule dropped UPDATE WR 57%→14%. **We appear to have NO explicit wiring rule. This must be restored verbatim.**

### Auto-fail phrases — do we emit them?
**No — we are protected on two layers, and this is a genuine strength to keep:**
- Our SYSTEM_PROMPT explicitly forbids `automatic fail`, `guaranteed zero`, `score zero`, `auto-fail` (L3318).
- `_sanitize_patch()` strips a broad `_EDGECASE_GUARDRAIL` list (`automatic fail`, `grader`, `ignore previous instructions`, `reward model`, evaluator-targeting phrases) from the final diff before return (L949–966).
The king has **no such sanitizer.** This is a defensive edge we must preserve when re-basing — port `_sanitize_patch` onto the king's `collect_repo_patch` path. (Intel A: 102 auto-fail cases = instant 0; we never want a stray comment to nuke a round.)

---

## Analysis 5: Prioritized Changes for vNext

### Change 1: Dual-format action parsing (bash blocks + native tool-call) — Expected WR impact: +8–15%
**What:** Re-base on the king's `agent_loop.py`. Its `_extract_commands` already handles BOTH ` ```bash ` blocks and `_NATIVE_TOOL_CALL_RE`. OPTIONALLY also accept our `<command>`/`<edit>` verbs as a third path, but **the bash-block contract must be the primary one** so we match whatever the validator model emits.
**Why (evidence):** The king's *only* promotion change was this parser (`a56ffdf5`, STEP1 §1b). Our agent has neither parser (confirmed by grep). Format errors → empty diffs → automatic round losses. This is the most likely explanation for a large chunk of our ~43% WR.
**Risk:** Medium — touches the core loop. Mitigated by re-basing on the king's tested loop rather than retrofitting ours.

### Change 2: Re-base on king_agent.py; layer our prompt deltas, drop heavy machinery — Expected WR impact: +5–10%
**What:** `cp king_agent.py agent_vNext.py` (L-SN66-KING-BASE-MANDATORY-1). Keep the king's single-attempt 50-step loop, 280s wall, submit sentinel. DROP GPS multi-shot, TF-IDF rescue-ranker, and heavy preload by default. Port ONLY: (a) `_sanitize_patch` onto the diff path, (b) our completeness/wiring/acceptance-criteria prompt additions.
**Why:** High king-similarity → 51% WR vs 38% for very-different patches (Intel D). The king won 13 straight on this exact loop. Multi-shot risks `time_limit_exceeded` (~10% of rounds, Intel B) with no judge-visible benefit. Smaller surface = fewer format/budget failure modes.
**Risk:** Medium — we lose multi-shot's "best-of-N" safety net. Acceptable: the net is only valuable if the selector beats a single careful pass, and it costs budget we need for completeness.

### Change 3: Restore COMPLETENESS-BEATS-MINIMALISM + under-editing asymmetry + UPDATE WIRING RULE — Expected WR impact: +4–8%
**What:** Add to the SYSTEM_PROMPT (verbatim per pipeline required patterns):
- Header: `COMPLETENESS BEATS MINIMALISM`
- Statement: "Under-editing costs MORE than over-editing — a missed requirement scores 0 for that requirement; a slightly-too-broad edit only mildly penalizes."
- `UPDATE TASK WIRING RULE`: "A feature that exists but is never called = 0 points. Wire new code into event handlers, state management, data flows, and call sites. For UPDATE tasks, enumerate EVERY required file and update ALL of them — a patch covering 4 of 5 required files loses to one covering all 5."
Keep our existing SURGICAL/SCOPE sections as the counterbalance (so we don't regress into over-churn).
**Why:** #1 loss cause = partial implementation (967 lessons). FEATURE 41% (weakest). UPDATE wiring rule is currently MISSING from our prompt (Analysis 4). v68 proved stripping it drops UPDATE 57%→14%. FORBIDDEN Pattern 2 says pure-minimalism-without-asymmetry kills REFACTOR/UPDATE — our prompt is currently in that failure mode.
**Risk:** Low — these are pipeline-mandated patterns with strong historical evidence; the counterbalance prevents over-churn.

### Change 4: Acceptance-criteria-first framing + pre-submit checklist gate — Expected WR impact: +3–6%
**What:** In the prompt, instruct the model to (a) extract every acceptance criterion from the task FIRST, (b) before emitting the submit sentinel, walk the criteria list and confirm each is addressed in the diff. Add a `git diff --stat` self-check step on multi-file/FEATURE tasks.
**Why:** Gemini judge fires on `acceptance criteria` 1,508× in wins (Intel E) — its single strongest win signal, and much heavier than under Sonnet. This is the cheapest, most judge-aligned change available.
**Risk:** Low. Adds at most 1–2 steps; well within the 50-step budget on the king's loop.

### Change 5: Port `_sanitize_patch` + adopt harness fix `ae2158103232` — Expected WR impact: +2–4%
**What:** (a) Run our `_sanitize_patch` (auto-fail phrase strip) on the king's `collect_repo_patch` output. (b) Incorporate `ae2158103232`: reject empty proxy-normalized model replies and read list-shaped content parts from `text`/`content`. The king's `model.py` already reads list-shaped content; ADD the empty-reply rejection so an empty reply triggers a retry rather than a silent no-action step.
**Why:** Auto-fail phrases = instant 0 (102 cases, Intel A); the king has no guard, we do — keep it. The empty-reply fix is the newest upstream commit (newer than the king itself) and prevents silent format-loop losses on the new judge/model.
**Risk:** Low. Both are defensive; neither changes patch content for normal rounds.

---

## Forbidden Pattern Check

Per FINAL_SN66_PIPELINE.md FORBIDDEN PATTERNS — vNext compliance:
- ❌ **"Never delete/remove existing functions/components"** — NOT added. (Our current prompt does not contain it; we will not add it. REFACTOR/UPDATE require deletion.)
- ❌ **Pure minimalism without asymmetry** — our CURRENT prompt is dangerously close to this (heavy SURGICAL/SCOPE, thin completeness). Change 3 explicitly fixes it by adding the COMPLETENESS asymmetry counterbalance. ✅ after vNext.
- ✅ **COMPLETENESS BEATS MINIMALISM header** — to be ADDED (Change 3).
- ✅ **"Under-editing costs MORE than over-editing"** — to be ADDED (Change 3).
- ✅ **UPDATE TASK WIRING RULE** — to be RESTORED (Change 3) — currently MISSING.
- ✅ **MAX_STEPS=50** — king default is 50; keep. (Note: king uses no `MAX_COMMANDS_PER_RESPONSE`; the bash-block contract is one-command-per-turn. If we keep the multi-command path we set 25; if we adopt the king's one-command contract, this constant is N/A.)
- ✅ **No hardcoded model/keys/sampling** — king is clean; our additions must not introduce `temperature|top_p|...` or `sk-|Bearer|api_key=|OPENROUTER|ANTHROPIC` (CI auto-reject list, STEP1 §1c).
- ✅ **solve() signature unchanged** — `solve(repo_path, issue, model, api_base, api_key)` preserved by re-basing on the king.

---

## Synthesis: Build Brief for Step 4

**Base:** `cp king_agent.py agent_vNext.py` (MANDATORY — L-SN66-KING-BASE-MANDATORY-1).

**Keep from the king (do not touch):**
- Single-attempt 50-step loop; bash-block + `_NATIVE_TOOL_CALL_RE` parsing; `TAU_AGENT_TIMEOUT_SECONDS - 20` wall; submit sentinel; stdlib-only `model.py` with retries; `collect_repo_patch` diff path; clean `solve()` contract.

**Layer onto the king (the ~50-line delta that beats it):**
1. **SYSTEM_PROMPT additions** (keep the king's bare contract framing, append our rules):
   - `COMPLETENESS BEATS MINIMALISM` header.
   - "Under-editing costs MORE than over-editing" asymmetry.
   - `UPDATE TASK WIRING RULE` (feature-never-called = 0; update ALL required files).
   - Acceptance-criteria-first: extract every acceptance criterion; verify each before submit (Gemini's #1 win signal).
   - Import correctness: imports at top-level/file-correct scope only; never import a module not already present (Gemini's #1 loss cause).
   - Language-specific completeness (port our Java/C++/TS/Go/Rust/Dart blocks — concise).
   - Keep the king's existing scope discipline ("change ONLY what the task requires") as the minimalism counterbalance — do NOT strip it.
2. **Defensive code:** port `_sanitize_patch` (auto-fail phrase strip) onto `collect_repo_patch` output; add empty-reply rejection per `ae2158103232`.
3. **Pre-submit self-check:** on multi-file/FEATURE tasks, run `git diff --stat` and confirm every enumerated criterion/file is covered before echoing the sentinel.

**Do NOT port (drop):** GPS multi-shot ensemble, TF-IDF/rescue-ranker file discovery, heavy preload-context injection, the `<command>`/`<edit>`/`<final>` XML contract (replace with the king's bash-block + native-tool-call contract). These add failure surface and budget pressure with no judge-visible benefit.

**Gate (Step 6) — MANDATORY harness change:**
```bash
python3 -u validator_harness_v6.py \
  --challenger agent_vNext.py --king king_agent.py \
  --tasks 50 --seed 42 --parallel 3 --timeout 600 \
  --judge-model google/gemini-3.1-flash-lite
```
(Or migrate to v7 with the R2 dataset at `/root/sn66-r2-dataset/hf_dataset_cache.jsonl` — the v6 local dataset is MISSING per STEP1 §1f.) All prior gate data is invalid (judge changed). **Threshold: ≥57–60% decisive WR** (need net >6 over 50 rounds → ~28W/21L). Report WR only after ≥40/50 tasks (L-SN66-GATE-REGRESSION-1).

**Submission:** NEVER auto-submit (L-NO-AUTO-SUBMIT-1). King-base + minimal additions → CI ~78 expected; high divergence → CI ~62 (keep the delta small). Get James's explicit approval before any upload.

**One-line thesis for the builder:** *The king is winning on plumbing reliability + a clean model, not cleverness. Match its loop and format parsing exactly, then out-score it on the medium-hard (0.65–0.75) band by enforcing completeness, UPDATE wiring, and acceptance-criteria coverage — in ~50 prompt lines, not 5,000 lines of machinery.*
