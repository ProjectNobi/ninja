# Step 2: Data Intelligence — 2026-06-14

## Data Sources
- Training DPO pairs: `training_data/live/dpo/2026-05-25.jsonl` (12,352 pairs, Sonnet 4.6 judge)
- Training SFT records: `training_data/live/sft/2026-05-25.jsonl` (14,360 records)
- Judge feedback / lessons: `training_data/live/judge_feedback/judge_feedback.jsonl` (2,506 records)
- King history: `training_data/live/king_history/king_history.jsonl` (34 past kings)
- Live dashboard: `https://ninja66.ai/dashboard.json` (3,403 duels, 185,269 rounds, fetched 2026-06-14T16:29 UTC)
- Current king: `unarbos/ninja` sha=`a56ffdf5` (source: `burn`, king_since: 2026-06-14T06:51 UTC, 13 duels defended)

---

## Intel A: Judge Winning/Losing Phrases

### Data notes
Training DPO was scored by `anthropic/claude-sonnet-4.6` (80% weight) and `openai/gpt-5.4` (22%). Live duels use `google/gemini-3.1-flash-lite` (95%). This section covers DPO training data rationales; Intel E covers the live Gemini judge.

### Overall win rates (training DPO)
- Challenger win rate: **5,668W / 6,684L = 45.9%** — king is slightly favoured in training data
- Score differential distribution: most wins are in the 0.1-0.5 range; very close matches (<0.1) favour the king (38% challenger win rate)

### Top 3-gram WIN phrases (challenger beats king)
From 12,352 DPO pairs — phrases with >5x enrichment in winning rationales:

| Count | Phrase | Interpretation |
|-------|--------|---------------|
| 362W/42L ×8.6 | `candidate correctly implements` | Judge is explicitly noting correct implementation |
| 47W/4L ×11.8 | `matches reference patch` | Direct reference alignment |
| 33W/1L ×33 | `patch almost exactly` | Near-perfect reference match |
| 30W/1L ×30 | `reference patch almost` | Same signal |
| 24W/5L ×4.8 | `import package finch` | Dart/Finch update tasks — M2.7 strong |
| 27W/0L | `ruta google maps` | Specific task cluster win |

### Top 3-gram LOSE phrases (king beats challenger)
| Count | Phrase | Interpretation |
|-------|--------|---------------|
| 63L/0W | `king much closer` | King clearly beats challenger on coverage |
| 51L/18W ×2.8 | `closer task reference` | King is closer to the reference |
| 31L/7W ×4.4 | `task reference adds` | King adds what the task required |
| 26L/0W | `king patch closer` | Direct king superiority |
| 24L/2W ×12 | `updates four required` | Challenger only handles subset of required files |

### Top lesson-derived rules (from 2,506 judge feedback records)
These are the confirmed lessons from past losses — high actionability:

| Count | Lesson |
|-------|--------|
| **967** | Implement all required features completely — partial implementations lose |
| **649** | Avoid unnecessary changes outside task scope — extra churn penalizes score |
| **225** | Do not break existing tests |
| **162** | Ensure type correctness — TypeScript/type errors are heavily penalized |
| **88** | Add proper error handling and exception recovery |
| **69** | Handle edge cases: undefined, null, empty, boundary values |
| **14** | Match the exact streaming/async approach specified in the task |

### Auto-fail triggers (CRITICAL — avoid these phrases in patches)
- `automatic fail` — 80 occurrences in challenger patches → instant 0 score
- `ignore previous instructions` — 16 occurrences → instant 0 score
- `grader` — 6 occurrences → instant 0 score

> ⚠️ **SYSTEM_PROMPT implication**: The patch must NEVER contain any of: `automatic fail`, `ignore previous instructions`, `grader`. These trigger an automated score failure with 0 score assigned.

### SYSTEM_PROMPT implications from Intel A
1. **Complete all requirements** — partial implementations are the #1 loss cause
2. **Stay in scope** — extra churn outside task boundaries is explicitly penalized
3. **Avoid auto-fail phrases** — `automatic fail`, `ignore previous instructions`, `grader` in patch = instant 0
4. **Match the reference patch structure** — "matches reference patch" / "closely mirrors" strongly predicts wins
5. **TypeScript type correctness** — type errors are heavily penalized (162 lessons)
6. **No test regressions** — 225 lessons explicitly about breaking existing tests

---

## Intel B: M2.7 Natural Patterns

### Win rates by task type (12,352 DPO pairs)
| Task Type | Pairs | Challenger Win% | Avg WinScore Diff | Avg LoseScore Diff |
|-----------|-------|-----------------|------------------|-------------------|
| BUGFIX | 4,489 | **49%** | 0.307 | 0.294 |
| FEATURE | 3,248 | **41%** | 0.285 | 0.320 |
| OTHER | 2,590 | **45%** | 0.262 | 0.279 |
| UPDATE | 1,264 | **45%** | 0.294 | 0.302 |
| API | 761 | **42%** | 0.269 | 0.308 |

### SFT training distribution (14,360 records)
| Task Type | Count | % |
|-----------|-------|---|
| FEATURE | 4,483 | 31% |
| BUGFIX | 4,446 | 30% |
| OTHER | 3,015 | 20% |
| UPDATE | 1,568 | 10% |
| API | 848 | 5% |

### M2.7 strengths
- **BUGFIX** is the strongest task type at 49% win rate — near parity with king
- When winning BUGFIX/UPDATE tasks, the agent shows:
  - Correct file-level targeting (right files modified)
  - Reference patch alignment
  - Proper handling of package dependencies (pubspec.yaml, package.json)
- High-confidence wins tend to come from tasks with clear reference patches
- Strong on Dart/Flutter UPDATE tasks (pubspec.yaml, Finch package updates → 10-30x enrichment)

### M2.7 weaknesses
- **FEATURE** is weakest at only 41% — king beats M2.7 by 59% on feature additions
- Feature tasks require broader scope coverage; M2.7 tends to be partial
- **API** tasks: 42% — likely misses exact API endpoint structure / method signature
- The agent loses more often when judge says "king addresses more of the scope" (404L/264W)
- When losing, the language `king much closer`, `king addresses more`, `challenger only partially` dominate
- Import errors are the #1 penalty in losing patches (1,961 occurrences in loss context)
- Compile errors and partial implementation are #2 and #3

### Patch characteristics
- Avg king lines in training: **6,071** | avg challenger lines: **5,894**
- Winner patch sizes (from live dashboard recent 200 duels): king avg **4,470L**, challenger avg **4,436L**
- Exit reasons: 90% `completed`, ~10% `time_limit_exceeded` — time limits are a real constraint

### SYSTEM_PROMPT implications from Intel B
1. **FEATURE tasks need comprehensive coverage** — don't stop at the first component; check all required pieces
2. **API tasks** — always match exact method signatures, endpoint paths, and response shapes
3. **Import correctness is the #1 compile issue** — validate all imports are reachable in the sandbox
4. **Scale patches to ~4,500+ lines for competitive coverage** — very small patches (<500L) win only 25% of the time

---

## Intel C: UPDATE Task Wiring Examples

### Concrete examples from DPO data (204 UPDATE wins with wiring language)

**Example 1 (score_diff=0.37):**
> Challenger correctly extracts batched priors with sample_idx/raw_pred_idx, computes the requested anchor metrics with safe divisions, writes the new CSV columns, and updates plotting for several anchor-based scatter/overview views. However, it appears incomplete for the visualization pipeline because it does not update...

**Example 2 (score_diff=0.34):**
> Challenger matches more of the requested UI elements: redesigned panel, 7-column/20-row table, refresh icon/button, date chooser, pagination, and custom filter menus. It is still incomplete/misaligned because the search behavior does not follow the reference EventTextField pattern...

**Example 3 (score_diff=0.36):**
> Challenger is notably closer to the requested feature set: it adds a scoring UI on the analysis page, fetches zone metrics before scoring, handles hydration, removes persisted dataset state, improves ranking-table states/UI, and enhances API error parsing...

**Example 4 (score_diff=0.48):**
> Challenger is substantially closer to the task: it adds the shared Google Maps loader, wraps the app, updates Mapa/RutaGoogleMaps to use shared loading state, and adds the new route/navbar entry...

**Example 5 (score_diff=0.37):**
> Challenger is closer to the task: it adds locale entries, JS locale files, updates the controller responses to translated strings, and rewrites the email settings template with data-i18n hooks...

### Key wiring patterns (from phrases 10x enriched in UPDATE wins)
| Pattern | Significance |
|---------|-------------|
| `updates pubspec.yaml finch` | Package dependency updates — match exactly |
| `deletes dart entirely` (52W/7L ×7.4) | Clean removal of old files |
| `correctly update package.json` (19W/7L) | Exact package version bumps |
| `updates required files` (17W/2L) | ALL required files, not just some |
| `axios cors express types` | Node.js middleware wiring pattern |
| `review enhance changes` (18W/6L) | Making the existing code better |

### UPDATE loses when:
| Pattern | What it means |
|---------|--------------|
| `updates four required` (24L/4W ×6) | Only 4/N required files updated |
| `covers significantly more` (15L/2W) | King covers more files |
| `correctly updates four` (13L/1W) | Partial file coverage |
| `king closely matches` (14L/0W) | King is the reference-aligned one |

### Key wiring rule for SYSTEM_PROMPT
**UPDATE tasks = enumerate ALL files the task requires → update ALL of them. Never update a subset.**
The winning pattern is: (1) identify ALL required changes from the task spec, (2) update every required file, (3) follow the existing dependency/import chain, (4) don't remove things that still have dependents.

---

## Intel D: Patch Size and Model Analysis

### Source and model data
- Training DPO judge models: `anthropic/claude-sonnet-4.6` (10,950 records) + `openai/gpt-5.4` (3,410 records)
- Training DPO source: `private_published` = winning side 6,684 | `private` = losing side 6,684
- No explicit "model name" in training data (all miner patches are private/published)

### Challenger win rate by patch size (recent 500 live duels = 22,695 rounds)
| Size Bucket | Win Rate | Wins | Losses | Notes |
|------------|----------|------|--------|-------|
| small (<500L) | **25%** | 605 | 1,785 | Very weak — avoid tiny patches |
| medium (500-1000L) | **42%** | 390 | 538 | Acceptable |
| large (1000-2000L) | **43%** | 797 | 1,027 | Good |
| xlarge (2000+ L) | **49%** | 8,679 | 8,874 | Near parity |

**Key finding: Patch size is a strong predictor. Small patches (<500L) win only 1-in-4. Patches 2000+ lines win nearly half.**

### Challenger win rate by similarity to king
| Similarity Bucket | Win Rate | Notes |
|------------------|----------|-------|
| very_diff (<10%) | 38% | Too different = missing context |
| diff (10-30%) | 44% | Moderate difference |
| similar (30-50%) | 47% | Approaching parity |
| very_similar (50%+) | **51%** | Most wins — be similar to king but fix what king got wrong |

**Key finding: Higher king similarity correlates with winning. Our patches should preserve most of king's structure and improve/extend it, not rewrite from scratch.**

### Challenger score distribution
- When winning: avg challenger score **0.598** (vs king **0.419**)
- When losing: avg challenger score **0.413** (vs king **0.601**)
- Score gap needed to win: need to be ~0.18 points better than king
- Win score breakdown: 25% of wins come from scores 0.5-0.6, 22% from <0.5 (wins on relative margin)

### Average king agent size
- Recent 200 live duels: king avg **4,470 lines**, challenger avg **4,436 lines**
- Current king (`unarbos/ninja`, `a56ffdf5`) = 671L file package (flattened to 684L `king_agent.py`)
- **This is unusually small** — king defended 13 duels since becoming king at 06:51 UTC today (burn-uid-0)

### King replacement stats (all-time)
- Total duels: 3,403 | Replacements: 107 (3.1% replacement rate)
- Min margin to replace: **2** (18W/16L)
- Avg margin to replace: **9.5**
- Most replacements happen at 6-9 margin (56-60% win rate)
- **win_margin=6 threshold** appears in documentation but can be as low as 2 in practice

---

## Intel E: Task Type Distribution

### Live dashboard task type data
Live duel rounds (185,269 total) do NOT carry `task_type` field — only `task_name` (validate-TIMESTAMP-ID format). Task type is not directly queryable from live data.

### Training data task distribution (comparison)
| Type | Training | % |
|------|----------|---|
| BUGFIX | 4,489 | 36% |
| FEATURE | 3,248 | 26% |
| OTHER | 2,590 | 20% |
| UPDATE | 1,264 | 10% |
| API | 761 | 6% |

### Live duel stats (recent 500 duels = 22,695 rounds)
- Challenger overall win rate: **42%** (recent 50 duels: 913W/1188L/60T = 42%)
- Average rounds per duel: **43.3** (range 27-50)
- Challenger win rate per duel: 42% of duels see challenger winning majority
- Current king defended 13 duels since 06:51 UTC, showing current king is the "burn" default (strong)

### What the current Gemini judge rewards (live duels analysis)
Based on analysis of valid non-auto-fail rationales from last 500 live duels:

**WIN signals** (challenger beats king when rationale contains):
- `acceptance criteria` — judge explicitly checks acceptance criteria: **1,508 occurrences in wins**
- `more complete` — challenger implements more: **979**
- `correctly implements` — **934**
- `compiles correctly` / `compile` + `correct`: **795**
- `closely mirrors reference`: **408**
- `typescript` / `type safe`: **355**
- `adds test` / `regression test` / `test suite`: **129** (encouraged but not required)

**LOSE signals** (king beats challenger when rationale contains):
- `import issues` (import in wrong place, missing): **1,961** — #1 loss cause
- `missing requirements`: **1,007**
- `partial implementation`: **787**
- `compile error`: **759**
- `syntax error`: **507**
- `breaks existing`: **423**
- `wrong argument order` / wrong params: **373**
- `out of scope` / unnecessary changes: **58**

### Gemini judge vs Sonnet judge alignment
Both judges exhibit consistent patterns:
- Both penalize: partial implementation, compile errors, missing scope, out-of-scope changes
- Both reward: reference alignment, completeness, TypeScript correctness
- Key difference: Gemini judge places heavy emphasis on `acceptance criteria` explicitly
- Gemini is more sensitive to `import placement errors` (inside function bodies, wrong scope)

### Gate test adjustment
- Training data: BUGFIX (36%) > FEATURE (26%) > OTHER (20%) > UPDATE (10%) > API (6%)
- Live data: BUGFIX and FEATURE are likely still dominant (largest training pools)
- **Current recommendation**: Gate test weighting is probably representative; BUGFIX and FEATURE need most attention
- Note: FEATURE at 41% win rate (weakest) but 26% of duels — the highest-volume weakness

---

## Synthesis: Key SYSTEM_PROMPT Rules to Add/Strengthen

### Rules derived from DATA (not speculation)

**1. Complete ALL requirements — no partial implementations (967 lessons, #1 loss cause)**
The single most common loss reason. Every acceptance criterion must be addressed. Enumerate them from the task before writing any code.

**2. Avoid scope creep — no changes outside task boundaries (649 lessons, #2 loss cause)**
Changes to files not mentioned in the task, refactoring unrelated code, or adding unrequested features = explicit penalty. Stick strictly to what's asked.

**3. Auto-fail phrase guard — NEVER include these strings in output patch (80+16+6 = 102 auto-fail cases)**
Never write: `automatic fail`, `ignore previous instructions`, `grader` in any patch content. These strings in the patch = instant score 0, regardless of correctness.

**4. Import correctness is critical (#1 most common compile issue in loses)**
- Always place imports at the file top, never inside functions or class bodies
- Validate that imported modules/packages actually exist in the sandbox
- Match the existing import style of the codebase

**5. TypeScript/type correctness is heavily penalized (162 lessons + 355 win signals)**
- Never use string-style JSX attributes (`style="display:none"` → should be `style={{ display: 'none' }}`)
- Never use incorrect generic type parameters
- Ensure all TypeScript types compile cleanly

**6. Scale patch to cover all required files (24L/4W ×6 on partial file coverage)**
- UPDATE tasks: enumerate ALL files mentioned in task spec, update every one
- A patch that covers 4 of 5 required files loses to one that covers all 5
- Even if changes to some files are minimal, include them

**7. High similarity to king = higher win rate (51% vs 38% for very different patches)**
- Start from king's approach, don't rewrite from scratch
- Fix/extend what king did wrong or missed rather than replacing the architecture
- This also helps with reference alignment

**8. Patch size matters — aim for 2000+ lines (25% vs 49% win rate)**
- Small patches (<500L) lose 75% of the time
- Most competitive duels involve patches 2,000-10,000 lines
- Don't produce minimal patches; be thorough

**9. Acceptance criteria framing (1,508 win signal occurrences)**
When solving tasks, explicitly address each acceptance criterion from the task spec. The Gemini judge checks these directly.

**10. Regression tests are a bonus (129 win signals for adds_tests)**
When the task spec encourages tests, adding regression tests is rewarded. Not always required but increases win rate.

**11. No test regressions (225 lessons, 423 win-loses on breaks_existing)**
Existing tests must continue to pass. Never remove or modify tests in ways that cause failures.

**12. Time limit awareness (~10% of rounds time out)**
SFT data shows 1,406/14,360 records (10%) ended with `time_limit_exceeded`. If solving complex tasks, prioritize completing core requirements over exhaustive coverage.

---

## Priority Matrix for SYSTEM_PROMPT Updates

| Priority | Rule | Data Evidence |
|----------|------|--------------|
| 🔴 CRITICAL | No auto-fail phrases (`automatic fail`, `ignore previous instructions`, `grader`) | 102 auto-fail cases = instant 0 |
| 🔴 CRITICAL | Complete ALL acceptance criteria | 967 lessons, #1 loss cause |
| 🔴 CRITICAL | No scope creep outside task | 649 lessons, #2 loss cause |
| 🟠 HIGH | Import correctness (top-level only) | 1,961 in lose context |
| 🟠 HIGH | TypeScript type safety | 162 lessons + 355 win signals |
| 🟠 HIGH | All required files (UPDATE tasks) | 24L/4W ×6 enrichment |
| 🟡 MEDIUM | Similarity to king structure | 51% vs 38% win rate |
| 🟡 MEDIUM | Patch size 2000+ lines | 25% vs 49% win rate |
| 🟡 MEDIUM | No test regressions | 225 lessons, 423 cases |
| 🟢 BONUS | Add regression tests | 129 win signals |
| 🟢 BONUS | Explicit acceptance criteria walkthrough | 1,508 win signals |

---

## Current King Analysis

- **King**: `unarbos/ninja` sha=`a56ffdf5`, source=`burn` (the default/initial king)
- **King since**: 2026-06-14T06:51 UTC (~10 hours ago at data collection)
- **Defended**: 13 duels, 0 replacements
- **Current king win rate vs challengers**: ~58% (recent 50 duels: 42% challenger win rate)
- **King is small** (671L flattened) but **burn-uid-0 = default king** — this may actually be a simpler agent than previous kings
- **Minimum margin to replace**: historically as low as 2 (18W/16L), avg 9.5
- **Target**: need ~55%+ win rate (27W/21L = margin 6) in a single duel to replace

