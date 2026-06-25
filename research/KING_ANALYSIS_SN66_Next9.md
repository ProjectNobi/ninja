# King Analysis — af1291d31cfb (unarbos/ninja)
*Pipeline Step 1b — 2026-06-15*

## King Stats
- SHA: af1291d31cfb169da7dd4b049c9b91357f9d37f1
- Repo: unarbos/ninja (public runtime)
- King since: 2026-06-15T06:38 UTC
- Defenses: 3 | Record: 67W/71L/2T (LOSING overall)
- King score mean: 0.742 (WEAK — vs c7add572's 0.841)

## What Changed vs Previous King (c7add572)
1. **agent.py +76L**: JS syntax check via `node --check` (with JSX hard guard)
2. **model.py +20L**: `_TransientContentError` retry for 200-OK empty responses
3. prompts.py, agent_loop.py, repo_diff.py: IDENTICAL

## Scoring (LIVE — confirmed from dashboard.json)
- Judge: **google/gemini-3.1-flash-lite** (0.95 weight) — NOT sonnet-4.6!
- solve_time_weight: 0.05
- win_margin: **6** (challenger needs wins > losses + 6)
- round_score_win_margin: 0.02 (decisive = 2% gap)
- duel_rounds: 50

## King Weakness Profile (from 140 live rounds)
- King avg score: 0.742 (stdev 0.257)
- King rounds <0.70: 44/140 = 31.4% — VERY vulnerable
- When king scores <0.70: challengers win 44/44 = 100%!
- King rounds ≥0.85: 73/140 = 52.1%

## Gemini Flash-Lite Judge Rewards (from rationales)
WINNER patterns: "comprehensive implementation", "follows project architecture",
"updates all relevant files", "includes necessary documentation",
"properly integrates", "correct layer/framework conventions"

LOSER patterns: "fails to implement", "incomplete", "does not update",
"only partially addresses", "skeleton implementation", "missing integration"

## Next9 Strategy
Built from Next8 + king's 2 new features:
1. JS syntax check (reduces empty/broken JS patches)
2. TransientContentError retry (stops losing rounds to API glitches)
3. READ BEFORE WRITE rule (reduces partial-context mistakes)
