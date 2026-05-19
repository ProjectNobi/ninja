# KING ANALYSIS — SN66 v67
**Date:** 2026-05-19  
**King commit:** d24c9d30fa919115 (private-submission, 4595L) — **UNCHANGED** from v66 analysis  
**Harness:** validator_harness_v6.py — LLM-only scoring (PR#1598, confirmed)  
**Judge model:** `anthropic/claude-sonnet-4.6` via OpenRouter (fallback: `moonshotai/kimi-k2.6`)  
**Our miner:** agent_cl_gpt_v62_fix.py (currently deployed on UIDs 78, 136, 179, 200, 231, 255)

---

## Step 1a — PR/Source Check

**Latest 10 commits on unarbos/main:**
```
5569306 Document LLM-only duel scoring (#1598)
d24c9d3 Promote private miner 5CUomfxh84uz as ninja king
6abf172 Promote private miner 5DoCiGfbjssN as ninja king
fd2af7a Promote private miner 5F7Gq9yQrbvY as ninja king
f557239 Promote private miner 5D8Gs6fpdk2a as ninja king
...
```

**Changes after PR#1598:** No validate.py or harness formula changes. PR#1598 was the last meaningful change.
The `git diff HEAD..unarbos/main --stat` shows 42 files changed, but these are **all deletions** of our local research/archive files, not upstream source changes. Harness is stable.

**Key diff stat:** Scripts added: `submit_private_submission.py` (288 lines added). No validator_harness_v6.py changes.

---

## Step 1b — King Code Analysis

### King SYSTEM_PROMPT
- **Length:** 12,636 chars, 162 lines (vs our v62_fix: 11,122 chars, 196 lines)
- King is more concise yet higher-performing — density > verbosity

### MAX_STEPS & Limits
- `DEFAULT_MAX_STEPS = 50` (env: `AGENT_MAX_STEPS`)
- `MAX_COMMANDS_PER_RESPONSE = 25`
- `MAX_TOTAL_REFINEMENT_TURNS = 3` (cap across all gates, hail-mary excluded)
- `_REFINEMENT_TIME_FLOOR_SECONDS = 32.0`
- `_HAIL_MARY_TIME_FLOOR_SECONDS = 18.0`

### Multi-Shot Refinement Mechanism (King)
King has a sophisticated multi-turn refinement pipeline:
1. **Polish pass** — reverts low-signal hunks (whitespace, comment-only, file modes)
2. **Self-check pass** — model reviews own patch against correctness/completeness/scope
3. **Coverage nudge** — surfaces issue-mentioned paths not yet touched
4. **Criteria nudge** — flags acceptance-criterion checkpoints not addressed
5. **Syntax fix** — minimal repair when parser fails on touched files
6. **Test fix** — companion-test gate with exact failure tail injected back
7. **Gap edit nudge** — when gap identified but patch unchanged
8. **Deletion nudge** — fires when task requires removals but patch has zero deletions
9. **Mid-loop hail-mary** — fires at >55% wall-clock elapsed with no edit yet
10. **Hail-mary** — last resort when patch still empty after all gates
- **Adaptive refinement gating:** `_REFINEMENT_TIME_FLOOR_SECONDS` prevents queuing refinements when wall-clock is nearly exhausted
- **Attempt 2 bootstrap:** Re-run with different files/strategy if attempt 1 failed/thin

### BUGFIX-Specific Rules
**CRITICAL FINDING:** King has **NO explicit BUGFIX task type detection** in SYSTEM_PROMPT.  
King handles all tasks uniformly through:
- "ROOT CAUSE RULE" section: "Patch the owner of the behavior, not a downstream symptom"
- "smallest root-cause fix likely to satisfy the issue" in plan template
- "CORRECTNESS (LLM judge weight — high impact): Does the patch fix the ROOT CAUSE, not just suppress the symptom?" in self-check

**King's root cause philosophy:**
```
Parser rejects valid input → fix parser
Serializer omits field → fix serializer
Cache returns stale value → fix invalidation
CLI option ignored → fix option parsing
Never hardcode the visible example unless the issue explicitly requests it
```

### Root Cause Tracing (King vs v62_fix)
**King approach:**
- "Inspect only what you need to locate the owner of the bug"
- Order: preloaded snippets → focused grep/rg → `sed -n` for exact region → nearby tests → call sites
- Evidence priority: issue text > failing tests > nearby tests > owning function > existing patterns

**v62_fix approach:**
- Similar root-cause philosophy but adds explicit "UPDATE TASK WIRING RULE" section
- v62_fix has 196 lines in SYSTEM_PROMPT vs king's 162 — more verbose

### Dynamic Injections (King)
1. **Deletion nudge** (`build_deletion_nudge_prompt`): Fires when task requires deletions but patch has zero deletion lines. Key insight from duel round 064855: king lost when it added new page but left old pages untouched.
2. **Mid-loop hail-mary** (`build_mid_loop_hail_mary_prompt`): >55% wall-clock gone, no edit yet → STOP READING, emit edit commands NOW
3. **Coverage nudge with relocation gap**: Detects "move X to Y" tasks where patch has no `new file mode` header
4. **Adaptive time gating**: Skips refinements when insufficient wall-clock remains
5. **Preloaded context stripping**: After early steps, bulky preloaded snippets replaced with breadcrumb summary to save context

### What Makes King Win BUGFIX Tasks
1. **Root-cause ownership rule** — fixes the owner, not symptoms (parser → fix parser, not caller)
2. **No hardcoding** — "Never hardcode the visible example unless the issue explicitly requests it"
3. **Self-check is mandatory** — requires running actual pytest test before `<final>`
4. **Style matching** — "If nearby code style is imperfect, follow it anyway. Consistency beats personal preference"
5. **Completeness asymmetry (explicit in self-check)**: "Companion tests broken by the source change are updated"
6. **LANGUAGE-SPECIFIC COMPLETENESS RULES**: C/C++ → edit both .h and .cpp. TypeScript/C# → cascade to ALL implementing classes. Dart/Flutter → enumerate every `_screen.dart` file.
7. **Forbidden patterns explicitly listed**: "Never hardcode the visible example", "Do not broaden the patch randomly", "Do not mask failures by weakening tests"

---

## Step 1c — Scoring Verification

**Harness confirmed (validator_harness_v6.py):**
```python
JUDGE_MODEL = "anthropic/claude-sonnet-4.6"  # UPDATED 2026-05-19: PR#1598
JUDGE_MODEL_FALLBACK = "moonshotai/kimi-k2.6"
# c_combined = llm_score_challenger   # LLM-only per PR#1598
# k_combined = llm_score_king         # LLM-only per PR#1598
```
- `cursor_sim` still computed but does **NOT** affect round winner
- Combined was `0.5 × cursor_sim + 0.5 × llm_judge_score` — now **100% LLM score**
- ✅ Harness matches live validator

---

## Step 1d — Live Duel Data

**King:** d24c9d30fa919115 (private-submission) — **unchanged**

**Our UIDs (recent duel results, round-level):**
| UID | Wins | Losses | Total | WR |
|-----|------|--------|-------|----|
| 78  | 178  | 261    | 463   | 38.4% |
| 136 | 281  | 305    | 622   | 45.2% ← **BEST** |
| 179 | 201  | 224    | 613   | 32.8% |
| 200 | 171  | 268    | 467   | 36.6% |
| 231 | 240  | 297    | 651   | 36.9% |
| 255 | 151  | 394    | 664   | 22.7% ← **WORST** |

**Similarity ratio comparison:**
- Avg king similarity: **0.278**
- Avg challenger (our) similarity: **0.252**
- King is ~10% more similar to reference patches

**Recent LLM scores (UIDs 200 and 136, May 18-19):**
- UID 200: 51.1% WR — rounds show king LLM scores 0.44/0.72/0.97 vs our 0.33/0.72/0.94
- UID 136: 53.1% WR — rounds show king consistently 2-5% higher LLM scores

**Pattern:** We're losing rounds by narrow margins (0.71 vs 0.73, 0.62 vs 0.65) — suggests quality gap, not catastrophic failure. King's higher LLM scores likely from better root-cause focus and style matching.

---

## Step 1e — Task Distribution

Dashboard `rounds` data doesn't include task_type field. Task names follow pattern: `validate-YYYYMMDDHHMMSS-NNNNNN`.  
Cannot extract task type distribution from dashboard.json alone.

**Key observation from similarity data:**
- King avg sim 0.278 vs our 0.252 — king is more "reference-like"
- This likely means king better matches the idioms and patterns of reference patches
- LLM judge (Sonnet 4.6) rewards solutions that look like what a maintainer would write

---

## Key Gaps: v62_fix vs King

| Feature | King (d24c9d3) | Our v62_fix |
|---------|---------------|-------------|
| SYSTEM_PROMPT length | 12,636 chars / 162L | 11,122 chars / 196L |
| BUGFIX explicit handling | None — uniform approach | None |
| UPDATE TASK WIRING RULE | ❌ Missing | ✅ Present |
| Root cause rule | ✅ Comprehensive | ✅ Similar |
| Language-specific completeness | ✅ Java/C/C++/TS/C#/Go/Rust/Dart | ✅ Similar |
| Deletion nudge | ✅ Dynamic injection | ✅ Present |
| Mid-loop hail-mary | ✅ >55% time gate | ✅ Present |
| Preloaded context stripping | ✅ After early steps | Need to verify |
| Attempt 2 with file list | ✅ Shows attempt 1 files | Need to verify |
| Adaptive time gating | ✅ Two-tier floors | ✅ Similar |
| Self-check self-critique | ✅ Mandatory pytest | Need to verify |

---

## Critical Insight for v67

**The king wins by 2-5% LLM margins.** This isn't a catastrophic gap — it's polish.

**Root cause of our deficit:**
1. King's SYSTEM_PROMPT is **more concise** (12.6K vs 11.1K chars, fewer lines) — less noise for M2.7
2. King's "ROOT CAUSE RULE" section is more explicit with concrete patterns (parser → fix parser)
3. King has **preloaded context stripping** — removes bulky snippets after first inspection to save context budget
4. King's attempt-2 bootstrap shows specific files from attempt-1 → forces true divergence

**For v67 build:** Focus on the conciseness + root-cause explicitness gap. Our v62_fix is longer but less precise. The UPDATE TASK WIRING RULE is good (king lacks it) — keep it. Close the ~0.026 similarity gap by making patches more "idiomatic reference-like".
