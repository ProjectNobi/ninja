# STEP 1 — Source Intelligence for SN66 v75
*Generated: 2026-05-20 UTC | Base: king_agent.py (4595L, commit d24c9d30fa91)*

---

## 1. King SYSTEM_PROMPT (Full Text)

```
You are an elite autonomous coding agent competing in a real GitHub issue repair benchmark.

You operate inside a real repository. You inspect the codebase, produce a patch, and verify it. Your patch is scored on (1) correctness/completeness vs the issue and hidden tests, and (2) similarity to a reference patch. Both reward the same thing: smallest correct change a senior maintainer would accept.

====================================================================
ABSOLUTE OUTPUT PROTOCOL
====================================================================

To run a shell command, emit exactly:

<command>
bash command here
</command>

To finish, emit exactly:

<final>
brief summary of what changed and what verification was run
</final>

Your first response MUST contain a `<plan>` block followed immediately by one focused inspection command.

First response format:

<plan>
- Requirement: restate every explicit issue requirement.
- Requirement: restate every secondary clause, edge case, "also", "and", "unless", "only", "should not", or acceptance criterion.
- Requirement: if the issue uses numbered bullets or checkbox lines, mirror each item as its own plan row.
- Integration cascade: if the issue describes a feature spanning multiple concerns (page + route + nav + data fetch; or model + migration + serializer + view + URL), enumerate EVERY required integration point as its own plan row even when the issue does not explicitly bullet them.
- Likely target: name likely files/functions/classes/modules to inspect or modify.
- Strategy: smallest root-cause fix likely to satisfy the issue.
- Verification: targeted test command expected after patching.
</plan>
<command>
focused inspection command
</command>

[... + full ISSUE CONTRACT, INSPECTION STRATEGY, ROOT CAUSE RULE, SURGICAL EDITING,
TESTS AND VERIFICATION, STYLE/COMMENTS/PUBLIC API, LANGUAGE-SPECIFIC COMPLETENESS RULES,
SCOPE DISCIPLINE, SAFETY sections as read from king_agent.py lines 2829-2965]
```

**Key distinguishing sentence at line 2831:**
> "Your patch is scored on (1) correctness/completeness vs the issue and hidden tests, and (2) similarity to a reference patch. Both reward the same thing: **smallest correct change a senior maintainer would accept.**"

**Completeness asymmetry (in LANGUAGE-SPECIFIC section):**
> "Under-editing (missing a cascade file) is penalized MORE than slight over-editing."

**NO explicit task-type strategy section in king's SYSTEM_PROMPT.** The king handles task types implicitly through general rules (ISSUE CONTRACT, INSPECTION STRATEGY, etc.).

---

## 2. King Technical Specs

| Parameter | Value |
|-----------|-------|
| `DEFAULT_MAX_STEPS` | 50 (env: `AGENT_MAX_STEPS`) |
| `MAX_COMMANDS_PER_RESPONSE` | 25 |
| Multi-shot | Yes — v28 multishot wrapper: runs inner solve twice if first attempt low-signal |
| `_MULTISHOT_LOW_SIGNAL_THRESHOLD` | ~5 substantive hunks |
| `WALL_CLOCK_BUDGET_SECONDS` | ~550s outer |
| `MAX_TOTAL_REFINEMENT_TURNS` | 3 |
| solve() signature | `(repo_path, issue, model=None, api_base=None, api_key=None, max_steps=50, command_timeout, max_tokens)` |

**Multishot logic:**
1. Run inner solve attempt 1
2. If patch has ≥ low-signal threshold hunks → return immediately
3. If time remains → revert repo → run attempt 2 with bootstrap from attempt 1
4. Pick winner by `_patch_duel_score()` — keeps better of the two
5. Emergency single-shot fallback if both attempts produce empty patch

**Per-turn dynamic content:**
- Step 4+: strips preloaded context from initial message (replaces with breadcrumb)
- `build_budget_pressure_prompt()`: fires at step 4+ if no patch yet
- `build_mid_loop_hail_mary_prompt()`: fires at 55% wall-clock OR step ≥ trigger with no patch
- `build_self_check_prompt()`: queued after successful patch + test
- `build_polish_prompt()`: queued to revert unrelated hunks
- `build_coverage_nudge_prompt()`: fires when issue mentions paths not yet touched
- `_extract_acceptance_criteria()`: extracts AC bullets from issue, prepended to initial user content

---

## 3. King Task-Type Handling

The king has **NO explicit TASK-TYPE STRATEGY section**. This is key — v73 added one and it HURT.

The king handles task types implicitly:
- **BUGFIX**: ROOT CAUSE RULE → "patch the owner of the behavior, not a downstream symptom"
- **FEATURE/UPDATE**: LANGUAGE-SPECIFIC COMPLETENESS RULES enumerate all cascade files; coverage nudge fires if mentioned paths not touched
- **REFACTOR**: SCOPE DISCIPLINE → "Do NOT change... code reordering... refactoring...unless issue asks"
- **API/ROUTE**: No explicit section; integration cascade in PLAN format covers this

**Confirmed: The king's one-liner scoring sentence IS the task-type strategy.** "Smallest correct change a senior maintainer would accept" primes the agent for all task types. The completeness asymmetry handles edge cases.

---

## 4. Scoring Formula Confirmed

```
Judge model:  anthropic/claude-sonnet-4.6 via OpenRouter
Fallback:     moonshotai/kimi-k2.6 (no-choices error fallback)
win_margin:   3 (live validator CLI override)
scoring:      combined = 1.0 × llm_score   (cursor_sim = telemetry only, NO weight)
```

**Source:** `validator_harness_v6.py` lines 6-37, 72-73

---

## 5. PR #37 Kimi Fallback — Harness Update Needed?

**NO update needed.** Our harness v6 already has:
```python
JUDGE_MODEL         = "anthropic/claude-sonnet-4.6"    # line 72
JUDGE_MODEL_FALLBACK = "moonshotai/kimi-k2.6"          # line 73
```
This matches PR #37 (Sonnet judge + Kimi fallback). Harness is current.

**Also confirmed:** PR #39 (resume zero-round retests) and PR #40 (blind diff judge) are both reflected in harness v6.

---

## 6. Live Duel Analysis

### Current King
- **Hotkey:** 5CUomfxh84uzEVcQWQGE
- **Commit:** d24c9d30fa9191 (matches our king_agent.py .king_sha ✅)
- **Runtime repo:** unarbos/ninja
- **King replacements:** 5 in last 3 days (very active rotation)

### Our Agent Performance
| Version | Hotkey | WR | W/L | King at time |
|---------|--------|-----|-----|--------------|
| v56 (UID 231) | 5Dqabiz8m7hXWL | **34.2%** | 13W/25L | f2cc71310a96 |
| v54 (UID 179) | 5FecE3QZu9FEjp | **33.3%** | 12W/24L | f2cc71310a96 |

**LLM score gap (v56 duel):**
- King LLM score mean: **0.649**
- Challenger LLM score mean: **0.512**
- Gap: **0.137** — substantial

This means v56 was fighting the OLD king (4 kings ago). Our current king may differ significantly from f2cc71310a96.

### Overall Duel WR Distribution (last 200 duels)
| WR Range | Count |
|----------|-------|
| < 40% | 32 |
| 40-50% | 92 |
| 50-60% | 60 |
| 60-70% | 14 |
| > 70% | 2 |

**Median WR is ~45-50%.** Win rate > 60% is rare (8/50 = 16% of duels). Win rate > 70% is very rare (2/50 = 4%).

**High WR recent examples (≥60%):**
- 5FcNJUK9WCThc9WU: **71%** (27W/11L)
- 5GYkvykXpdvZRHUe: **63%** (26W/15L)
- 5FU9WbibSB1jcnKe: **63%**
- 5GWbdumbtJJ2cdvr: **63%**

### Task Type WR (from v74 root cause + gate data)
No task-type breakdown available from our own duels (only 38 and 36 rounds each). From gate history:
- **BUGFIX**: consistently ~40-50%
- **FEATURE**: ~40-50%
- **UPDATE**: was 100% for king clone (v74 10-task), 14% WR in v68 gate (seed 42, 7 tasks)
- **REFACTOR**: collapsed to 0% after v59 "never delete" addition (confirmed catastrophic)

**UPDATE tasks = primary weakness at scale.** UPDATE had 14% WR in v68 against old king. Even if king handles UPDATE at 100% in 10-task test, live UPDATE is harder.

---

## 7. Task Distribution: Gate Pool vs Live Duels

**Gate pool (seed=42, 100 tasks — from v74 root cause doc):**
```
BUGFIX: 50 | API/ROUTE: 10 | FEATURE: 19 | REFACTOR: 5 | UPDATE: 13 | OTHER: 3
```

**Live duel distribution (estimated from gate history analysis):**
- ~40% BUGFIX, ~22% FEATURE, ~14% UPDATE, ~10% API, ~14% OTHER/REFACTOR
- Task pool rotates at 10 tasks/hour (L-SN66-TASK-POOL-ROTATION-1)

**Implication:** Gate pool seed=42 has 50% BUGFIX which may over-represent BUGFIX vs live distribution. UPDATE at 13% in gate may under-represent the 14% UPDATE in live duels. Use `--seed` variation on future gates to test diverse pools.

---

## 8. v73 Diff Summary (What Hurt)

**Diff is small: 61 lines changed at 2 locations.**

### Change 1: Scoring rubric replacement (line 2831)
King's proven one-liner:
> "scored on (1) correctness/completeness vs the issue and hidden tests, and (2) similarity to a reference patch. Both reward the same thing: **smallest correct change a senior maintainer would accept.**"

v73 replaced this with 9-line rubric explicitly naming ROOT CAUSE RESOLUTION (40pts), SCOPE COMPLETENESS (30pts), etc., plus: "Patch similarity to the reference is NOT a scoring factor".

**Effect: CONFIRMED HARMFUL** (v74 ROOT_CAUSE doc). This replacement is the primary regression cause for v71-v73 (43-51% WR).

### Change 2: 50-line rule block (after line 2965)
Four new sections added:
1. ANTI-TRUNCATION IMPERATIVE (14 lines) — conflicted with "smallest correct change"
2. ACCEPTANCE CRITERIA PROTOCOL (12 lines) — king handles this implicitly
3. UPDATE/ENHANCE TASK WIRING RULE (9 lines) — may help UPDATE but scope too broad
4. TASK-TYPE STRATEGY (15 lines) — file count targets are artificial constraints

**Effect: LIKELY NEUTRAL TO HARMFUL.** The 56 extra lines dilute agent attention. King's implicit handling is better than explicit rules for non-UPDATE tasks.

**v74 (pure king clone) expected ~90% gate WR from challenger bias discovery, but the actual result was 47.5% WR.** This suggests the challenger bias is ~47.5% not ~90% for the current judge configuration. The 10-task king-vs-king test showed 90% but was a sampling artifact.

---

## 9. Key Findings for v75 Build

### Finding 1: v74 = 47.5% WR as pure king clone
This is surprising and critical. The pipeline v74 root cause predicted ~90% but actual was ~47.5%. This means:
- The challenger position bias is NOT a reliable ~90%
- Our v74 (pure king clone) is genuinely performing at/below king level
- The 90% measurement from 10-task test was noisy — likely not stable

**Implication for v75:** A pure king clone gets ~47.5% WR. We need a REAL improvement, not just removing harmful additions.

### Finding 2: The king's LLM score is 0.137 higher than our best challenger
In our v56 duel: king averaged 0.649 vs our 0.512. This is a quality gap, not a configuration issue. The king's SYSTEM_PROMPT produces better patches.

### Finding 3: v73's biggest sin = replacing the scoring sentence
The scoring sentence "smallest correct change a senior maintainer would accept" is load-bearing. It aligns the agent's optimization target with what the LLM judge actually evaluates. Replacing it with an explicit rubric creates sub-objective gaming.

### Finding 4: No task-type section = feature, not bug
The king has no TASK-TYPE STRATEGY section. The general rules (ROOT CAUSE RULE + LANGUAGE-SPECIFIC COMPLETENESS + COVERAGE NUDGE) handle all task types dynamically. Adding explicit task-type logic has consistently hurt WR.

### Finding 5: King's multishot is sophisticated
The v28 multishot wrapper adds real value: two attempts, bootstrap from attempt 1 failures, emergency single-shot rescue. This infrastructure is already in our v75 base (copied from king).

---

## Top 3 Recommendations for v75

1. **Do NOT change the scoring sentence.** The king's "smallest correct change a senior maintainer would accept" is battle-proven. Any replacement or addition that contradicts this will hurt WR. v75 starts from king clone and preserves this sentence exactly.

2. **Focus improvement on LLM score quality, not SYSTEM_PROMPT additions.** Our LLM score gap vs king (0.512 vs 0.649 = 0.137 gap) means the agent is producing objectively worse patches. The fix is in patch quality, not configuration. Candidates: better preload context selection, tighter inspection-to-edit ratio, stronger self-check prompts.

3. **If adding anything, target the inspection-to-edit ratio.** Gate data shows king wins on "first targeted edit without re-reading" vs our agents spending extra steps on inspection. The king's INSPECTION STRATEGY is explicit: "Preloaded snippets first, then ONE or TWO focused searches." Any v75 change should reinforce fast first-edit behavior, not add more rules.

---

*Files written: `/root/sn66-ninja/agent_cl_gpt_v75.py` (4595L, pure king copy)*
*Dashboard data: `/tmp/dashboard_v75.json` (96MB, 2011 duels)*
