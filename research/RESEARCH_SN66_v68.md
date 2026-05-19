# RESEARCH_SN66_v68 — Pipeline Step 1 Intelligence
*Generated: 2026-05-19 ~10:45 UTC | Subagent: Research Analyst*

---

## 1a — PR/Source Check

**Latest commit on unarbos/main:** `5569306` — "Document LLM-only duel scoring (#1598)" — 2026-05-19  
**King commit:** `d24c9d3` — unchanged since ~05:40 UTC today ✅  
**No new PRs after #1598.** PR#1598 is the only change since king promotion.

**What PR#1598 changed (CRITICAL for v68):**
- Judge model: `openai/gpt-5.4` → `anthropic/claude-sonnet-4.6` (via OpenRouter)
- Scoring formula: `combined = 0.5×cursor_sim + 0.5×llm_score` → `combined = 1.0×llm_score` (LLM-only)
- cursor_sim is now **telemetry only** — does NOT affect win/loss
- Harness v6 already updated for PR#1598 ✅ (JUDGE_MODEL = "anthropic/claude-sonnet-4.6", fallback = Kimi-K2.6)

**Diff stat HEAD..unarbos/main:** 45 files changed (424 insertions, 83176 deletions) — mostly cleanup of old scripts.

---

## 1b — King Code Study

**King:** `d24c9d3` | 4595 lines

**King mechanisms and whether v67 has them:**

| Mechanism | King | v67 | Gap? |
|-----------|------|-----|------|
| `_strip_preloaded_section` | ✅ line 3038 | ✅ (3 refs) | No gap |
| `build_attempt2_bootstrap` (multishot) | ✅ line 3291 | ✅ (5 refs) | No gap |
| `build_mid_loop_hail_mary_prompt` | ✅ line 3372 | ✅ (6 refs) | No gap |
| `build_hail_mary_prompt` (empty-patch) | ✅ line 3406 | ✅ | No gap |
| **`_solve_emergency_single_shot`** | ✅ line 3556 | ❌ **MISSING** | **⚠️ GAP** |
| MULTISHOT params (278s, 52s, 132s, threshold=3) | ✅ | ✅ (same values) | No gap |
| `MAX_COMMANDS_PER_RESPONSE = 25` | ✅ line 96 | (check) | TBD |

**The critical missing mechanism — `_solve_emergency_single_shot`:**
- Triggered when `(MULTISHOT_TOTAL_BUDGET - elapsed) < 60s` AND multishot conditions not met
- Fires a focused emergency single-shot API call: picks 1 target file, reads 2000 chars snippet, direct patch
- Params: max_tokens=1024, timeout=45s, command_timeout=30s
- Purpose: **prevents empty patches when budget exhausted**
- This directly explains our empty-patch losses (ch_lines=0, ch_llm=0.000)

v67 has `_EMERGENCY_MIN_REMAINING_BUDGET = 60.0` constant but uses it only for hail-mary text injection — does NOT have the actual `_solve_emergency_single_shot` function or the conditional call at harness line 3706-3708.

---

## 1c — Baseline Setup

```
king_agent.py: 4595 lines (confirmed d24c9d3, synced)
```
✅ `king_agent.py` is current baseline for v68 gate tests.

---

## 1d — Scoring Mechanism (post-PR#1598)

```
JUDGE_MODEL = "anthropic/claude-sonnet-4.6" (via OpenRouter)
FALLBACK    = "moonshotai/kimi-k2.6"
SCORING     = LLM-only (combined = 1.0 × llm_score)
WIN_MARGIN  = 3 (live CLI override)
cursor_sim  = telemetry only (no longer affects win/loss)
```

**Harness update status:** ✅ validator_harness_v6.py already updated for PR#1598 (confirmed 2026-05-19).  
**No harness changes needed for v68.**

**Implication for v68 build:** Since cursor_sim no longer counts, optimizing for LLM judge quality is the ONLY lever. The judge (Sonnet 4.6) rewards:
- Completeness (hitting all required files)
- Correctness of each change
- Missing cascade files = direct point loss

---

## 1e — Live Duel Analysis

**Today's active duels (2026-05-19):**

| UID | Agent | W | L | WR | avg ch_llm | avg k_llm |
|-----|-------|---|---|----|-----------|----------|
| 255 | v62b  | 19| 24| 44.2% | 0.449 | 0.507 |
| 78  | v62b-re | 24 | 22 | 52.2% | 0.474 | 0.478 |

**Loss pattern analysis:**

**Pattern 1 — Empty patches (ch_lines=0, ch_llm=0.000):**
- Both UIDs 255 and 78 have loss rounds with `challenger_lines=0`
- Judge: "challenger patch is completely empty and implements nothing"
- **Root cause: budget exhaustion without emergency fallback**
- King scores 0.580–0.600 on same tasks → king's emergency mechanism prevents this
- **Fix: implement `_solve_emergency_single_shot` in v68**

**Pattern 2 — Cascade file misses:**
- task `064765`: v62b-re ch_llm=0.930 vs king=0.970 — "king patch additionally updates..." extra file
- task `064716`: ch_llm=0.480 vs king=0.600 — "king correctly implements addr/list.vue active style change, adds click handler to btn4, creates reasonable express/index.vue"
- Judge: both do core correctly, king adds 1–2 cascade files we miss
- **Fix: stronger cascade detection / broader file search in SYSTEM_PROMPT**

**Pattern 3 — Slight completeness margin:**
- task `064687`: both implement same core, both miss same reference additions → near-tie
- When tied on core, king wins by 0.03–0.05 margin on extra cascade coverage
- King avg lines: ~8000–9000 vs our ~7000–8000 on losses

**Win pattern:**
- task `064697`: ch_llm=0.680 vs king=0.580 — we win when king over-edits and we're more precise
- task `064801`: ch_llm=0.720 vs king=0.380 — decisive win when king misses core requirements

**UID 78 (v62b-re) outperforms UID 255 (v62b) by ~8pp WR** — confirming that the re-submit config is marginally better.

---

## 1f — Task Distribution

`task_type` field is not exposed in `dashboard.json` round data (empty from API).  
From v67 gate output (50-task run, seed 42):
- BUGFIX, UPDATE, REFACTOR, FEATURE all observed
- Refactor losses prominent (king higher cursor_sim on structural changes: 0.095 vs our 0.034)
- Update wins when we better understand the feature requirement

---

## Summary for v68 Build

**What changed since v67:**
- PR#1598: Judge switched to claude-sonnet-4.6, scoring is now LLM-only (100% LLM, 0% cursor_sim)
- Harness already updated. No code changes needed for harness.
- King unchanged (d24c9d3 since ~05:40 UTC). No new king since last pipeline.

**What live duels reveal about our loss pattern:**
- Empty patches are killing us (ch_llm=0.000 on budget-exhausted tasks) — king's `_solve_emergency_single_shot` prevents this; we don't have it
- Cascade file coverage: we miss 1–2 extra files that king gets, costing 0.03–0.07 LLM score per round
- v62b-re (UID 78) at 52.2% WR proves our core logic is competitive when budget managed correctly

**King mechanisms we still haven't added to v67:**
1. **`_solve_emergency_single_shot`** — the most critical missing piece, directly causing empty-patch zeros
2. King has this exact implementation: pick 1 target file via `_emergency_pick_target`, read 2000-char snippet, fire direct patch with max_tokens=1024, timeout=45s — all in <60s remaining budget window

**v67 gate status (running):** ~44-46/50 tasks complete as of this report. Score TBD.

---
*Step 1 complete. Ready for Sub-tasks A–E and Task 2 (Build).*
