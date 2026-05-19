# Source Intelligence — SN66 vNext (2026-05-19)
**Author:** Opus 4.7 Subagent (Step 1 — Source Intelligence)
**Date:** 2026-05-19 UTC
**King:** d24c9d30fa9191150fe093717b0660350d7a3538 (4595 lines, private submission)
**v71 gate:** 47% WR (34/100) — BELOW threshold (≥70%)

---

## 1a. Recent PRs / Source Changes

**Most recent commits on origin/main:**
1. `9413fc4` — Promote miner 5EJLdeY77nia as ninja king (current king d24c9d30)
2. `81289db` — **FIX 8 (2026-05-19): Blind judge** — remove king/challenger labels, randomize A/B assignment (eliminates king-label bias) — **TODAY, our harness already has this fix**
3. `0b427c8` — Strengthen PR judge against prompt-only edits (PR#952)

**Harness validator_harness_v6.py changes (CRITICAL):**
- **FIX 8 (today):** Blind A/B judging — challenger/king no longer labeled. Our local harness already includes this fix (commit 81289db).
- **PR#1598 (2026-05-19 earlier):** Judge model changed: `openai/gpt-5.4` → `anthropic/claude-sonnet-4.6` via OpenRouter. Scoring formula: `0.5×cursor_sim + 0.5×llm_score` → **`1.0×llm_score` (LLM-only)**. cursor_sim now **telemetry only**.

**Impact on vNext:** All previous gate results (v68–v71) were run against the **old gpt-5.4 judge + cursor_sim formula**. The new Sonnet-4.6 judge uses a different rubric. vNext gate must be run fresh with the new judge.

---

## 1b. King Analysis (d24c9d30, 4595L)

### MAX_STEPS + MAX_COMMANDS
- `DEFAULT_MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "50"))` — king_agent.py:71
- `MAX_COMMANDS_PER_RESPONSE = 25` — king_agent.py:96
- `MAX_TOTAL_REFINEMENT_TURNS = 3` — king_agent.py:134

### SYSTEM_PROMPT Key Rules (verbatim excerpts)

**Opening framing** (king_agent.py:2831):
> "Your patch is scored on (1) correctness/completeness vs the issue and hidden tests, and (2) similarity to a reference patch. Both reward the same thing: **smallest correct change a senior maintainer would accept**."

⚠️ **CRITICAL:** The king's SYSTEM_PROMPT still says "similarity to reference patch" — but PR#1598 has made cursor_sim irrelevant. King's SYSTEM_PROMPT is **STALE** relative to actual scoring. This is an exploitable gap.

**ISSUE CONTRACT** (king_agent.py:~2870):
> "Treat the issue as a contract. Extract every requirement before editing — main task, bullet points, acceptance criteria, error messages, edge cases…"

**ROOT CAUSE RULE** (king_agent.py:~2900):
> "Patch the owner of the behavior, not a downstream symptom. Parser rejects valid input → fix parser."

**SURGICAL EDITING** (king_agent.py:~2915):
> "Change the fewest lines necessary. Forbidden unless explicitly required: whole-file or whole-function rewrites when 1-5 lines suffice, formatting churn…"

**HIDDEN-TEST EDGE CASES** (king_agent.py:2949):
> "Before finalizing, mentally check: empty/null input, missing/extra fields, duplicates, case sensitivity, unicode, path separators, async ordering, idempotency, boundary values…"

### UPDATE task handling
King has **NO explicit UPDATE-specific strategy** in SYSTEM_PROMPT. The WIRING RULE that v71 added is NOT in king. King treats all tasks with the same "smallest correct change" framing.

### BUGFIX task handling
King has the ROOT CAUSE RULE section — trace symptom to owner, fix owner. But no explicit BUGFIX-specific checklist.

### FEATURE task handling
King has INTEGRATION CASCADE in the plan block format — enumerate every integration point as its own plan row.

### Multi-shot / Refinement logic
- Multi-shot wrapper around `_solve_inner` — king_agent.py:3647 (v28 multi-shot)
- `MAX_TOTAL_REFINEMENT_TURNS = 3` cap across all gates (hail-mary excepted) — king_agent.py:134
- **Refinement gates** (in order): hail-mary (empty patch) → syntax fix → test fix → deletion nudge → coverage nudge → criteria nudge → polish → self-check
- **`_solve_emergency_single_shot`**: king has this at ~line 3556 — fires when `MULTISHOT_TOTAL_BUDGET - elapsed < 60s` AND normal multishot not triggered. Picks 1 target file, reads 2000-char snippet, direct patch. Our v62–v71 are ALL MISSING this.

### Completeness Asymmetry rule
King does NOT have an explicit "under-editing costs more" statement in SYSTEM_PROMPT. King relies on LANGUAGE-SPECIFIC COMPLETENESS RULES (Flutter screens, TypeScript cascades, C/C++ header+impl, Go struct fields) for coverage.

**Key completeness mechanism in king's runtime** (king_agent.py:~2586):
```
_uncovered_required_paths() → lists files the issue implies but patch doesn't touch
→ triggers coverage_nudge refinement turn if any missing
```

### Language-specific rules (king_agent.py:2951)
- **Java:** Complete method bodies, cascade all call-site changes, include all imports
- **C/C++:** Edit both .h AND .cpp for each changed function
- **TypeScript/C#:** Cascade interface+type changes to ALL implementing classes
- **Go/Rust:** Update every struct field usage
- **Dart/Flutter:** Enumerate EVERY `*_screen.dart`, `*_page.dart`, `*_view.dart` implied by the task

---

## 1c. King Base Confirmed

```
cp king_agent.py agent_cl_gpt_vNext.py ✅
Base: 4595 lines
```

`agent_cl_gpt_vNext.py` = exact copy of king_agent.py (d24c9d30) confirmed.

---

## 1d. Scoring Mechanism

### Judge model(s)
- **Primary:** `anthropic/claude-sonnet-4.6` via OpenRouter (changed 2026-05-19 per PR#1598)
- **Fallback:** `moonshotai/kimi-k2.6`
- Previously was `openai/gpt-5.4` — ALL v66–v71 gates were run against the old judge

### win_margin
- `win_margin = 3` (live CLI override; harness code default = 0)
- Challenger must win by +3 rounds (out of 50) to dethrone

### cursor_sim weight
- **ZERO.** cursor_sim = LCS(agent_patch, R2_reference_patch) / max_lines
- Since PR#1598: telemetry only, does NOT affect win/loss
- Previous formula was `0.5×cursor_sim + 0.5×llm_score` — that is GONE

### Formula (current, post-PR#1598)
```
combined = 1.0 × llm_score

llm_score = claude-sonnet-4.6 judge score (0.0–1.0)

Inferred rubric (from validator_harness_v6.py opus rubric + validator_harness_v6.py:737):
  Root Cause Resolution:    0–40 pts
  Scope Completeness:       0–30 pts  
  Acceptance Criteria:      0–20 pts
  Code Quality:             0–10 pts
  
Winner = challenger if (challenger_llm_score - king_llm_score > win_margin/100) × rounds
```

**Key implication:** Since cursor_sim is gone, "similarity to reference" no longer helps. Pure code quality and completeness wins.

---

## 1e. Live Duel State

### Overall WR vs current king (d24c9d30)
- **71 total duels vs current king** in database
- Typical challenger WR vs this king: **40–55%**
- Best challenger we've seen: de812619 — 65% WR (one duel)
- Our overall WR across all 102 duels: **42.4%** (1820W / 4291R)

### v71 gate performance
- **Gate result: 47% WR (34/100 tasks won) — BELOW 70% threshold**
- v71 added: explicit rubric in SYSTEM_PROMPT + UPDATE WIRING RULE + TASK-TYPE STRATEGY
- v71 was NOT yet blind-judged (FIX 8 applied today, after v71 gate)

### Where we lose most (top 3 loss patterns from ROOT_CAUSE_SN66_vNEXT.md)
1. **Missing `_solve_emergency_single_shot`** — king forces a patch when budget < 60s; we produce empty patches on tight tasks. Empty patch = loss.
2. **UPDATE tasks: wiring not grounded** — adding UPDATE WIRING RULE in SYSTEM_PROMPT is correct direction but insufficient without runtime enforcement (coverage nudge for wiring paths).
3. **Stale SYSTEM_PROMPT framing** — king says "similarity to reference" (irrelevant since PR#1598). v71 added correct rubric. But 47% suggests the rubric injection alone doesn't fix the structural gaps (emergency single-shot, coverage nudge for UPDATE wiring).

---

## 1f. Gate Task Distribution (seed 42, 100 tasks)

### Distribution by type (classifier: fix/bug/error → BUGFIX, implement/add/create → FEATURE, update/enhance → UPDATE)
```
FEATURE: 41%  (keywords: implement, add, create, build, new, introduce)
UPDATE:  38%  (keywords: update, enhance, improve, refactor, modify)
BUGFIX:   8%  (keywords: fix, bug, error, broken, wrong, fail, crash)
OTHER:   13%  (no strong signal)
```

**⚠️ Discrepancy vs live distribution:** AGENTS.md states live: ~40% BUGFIX, ~22% FEATURE, ~14% UPDATE. Seed-42 sample shows inverse (41% FEATURE, 8% BUGFIX). The R2 dataset phrasing may not match live task wording — FEATURE tasks in R2 may use words like "implement" that look like BUGFIX in live. Treat this distribution as approximate.

### Recommendation: task-type aligned sampling
Use seed 42 for reproducibility, but verify task type distribution manually on 5–10 tasks before committing to strategy. The gate sample should have enough UPDATE tasks to validate the WIRING RULE is working.

---

## Summary: Top 3 Actionable Insights for vNext

### Insight 1: Add `_solve_emergency_single_shot` (HIGHEST IMPACT)
**Evidence:** king_agent.py:~3556 — explicit emergency fallback for budget-exhausted rounds. v62–v71 all lack this. Empty patch = immediate loss. This is a **pure mechanical gap** that should improve WR on time-constrained tasks.
**Action:** Port `_solve_emergency_single_shot` from king exactly. Wire into the main solve loop at the same conditional point (< 60s remaining).

### Insight 2: Update SYSTEM_PROMPT to reflect PR#1598 reality (cursor_sim = 0, rubric = sonnet-4.6)
**Evidence:** King's SYSTEM_PROMPT still says "similarity to reference patch" (stale). v71 added the rubric — CORRECT. But the framing should explicitly say cursor_sim is irrelevant. Sonnet-4.6 judges on Root Cause (40) + Scope (30) + AC (20) + Quality (10). The agent should optimize for THOSE criteria, not R2 proximity.
**Action:** Keep v71's rubric addition. Add one line: "Do NOT optimize for patch similarity to any reference — only correct, complete code matters."

### Insight 3: Sonnet-4.6 judge = new behavior, re-run gate fresh
**Evidence:** All v66–v71 gates used old gpt-5.4 + cursor_sim formula. Sonnet-4.6 may reward different patterns (verbosity, completeness style, AC bullet coverage). v71's 47% gate result is partially based on old judge — we don't know true WR under new judge yet.
**Action:** Run vNext gate using `--judge-model anthropic/claude-sonnet-4.6` (already default in harness). Do NOT compare vNext gate to v71 gate directly — different judge.
