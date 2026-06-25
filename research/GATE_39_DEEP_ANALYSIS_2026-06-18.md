# Gate-39 Deep Analysis — Root Cause for Next40
Date: 2026-06-18 ~11:50 UTC
Gate-39 killed at 6 tasks: 1W-4L-1T (17% WR)

## Evidence

| # | Type | Lang | Us | King | Gap | Result |
|---|------|------|----|------|-----|--------|
| T1 | BUGFIX | C/C++ 3f | 0.380 | 0.180 | +0.200 | ✅ WIN |
| T2 | BUGFIX | Python 2f | 0.320 | 0.630 | -0.310 | ❌ BIG LOSS |
| T3 | BUGFIX | TypeScript 9f | 0.000 | 0.330 | -0.330 | ❌ ZERO OUTPUT |
| T4 | API/ROUTE | Python 10f | 0.430 | 0.550 | -0.120 | ❌ LOSS |
| T5 | API/ROUTE | PHP 5f | 0.140 | 0.550 | -0.410 | ❌ BIG LOSS |
| T6 | BUGFIX | Go 11f | 0.000 | 0.000 | 0.000 | 🤝 TIE (both timeout) |

## The Real Root Cause — Found After Deep King Analysis

After reading the king's full source, the critical difference is NOT the
TASK_TEMPLATE (ours is now equivalent). The real differences are:

### DIFFERENCE 1: King's _integration_hints() is MUCH SIMPLER and BETTER targeted

King has 6 hints based on simple, broad regexes that fire on TASK CONTENT:
- _DATA_UPDATE_RE → "edit data/config files directly, don't refactor source"
- _INTEGRATION_RE → "wire into entrypoints, routes, providers, config, docs"
- _COMPONENT_RE → "read nearest sibling, mirror prop/callback naming"
- _NEW_SYMBOL_RE → "grep for analogous existing symbol, copy naming convention"
- _REFACTOR_RE → "refactor in place, preserve working logic"
- _UI_DETAIL_RE → "implement every named visual/detail requirement"

These are CONTENT-BASED (fire on task description), not LANGUAGE-BASED.
They give general guidance that helps ANY language.

Our hints were LANGUAGE-BASED (C++, Go, Python) — too narrow, causing overfitting.

### DIFFERENCE 2: King's extract_criteria() builds an ACCEPTANCE CHECKLIST

King explicitly extracts bullet points and numbered items from the issue,
then appends _integration_hints(), and formats them as a visible
"## Acceptance checklist" that the agent must verify before submitting.

This is a MAJOR quality driver — it forces the agent to check every requirement
before finishing. We don't have this. Our agent can submit without verifying
all requirements.

### DIFFERENCE 3: King has multiple guard functions we're missing or weaker on

King has: destructive_patch_reason(), munge_artifact_reason(),
refactor_delete_reason(), task_coverage_reason(), extended_repair_reason(),
patch_acceptable() — a full suite of guards that check the patch quality.

Our Next39 may have these but are they working correctly?

### DIFFERENCE 4: T3 TypeScript ZERO OUTPUT (0.000) — Likely a collapse/timeout

T3 was 9 files TypeScript, our score = 0.000. This means the agent either:
a) Timed out without submitting
b) Produced an empty/invalid patch

This is a step budget / large-repo problem. 9-file TypeScript tasks need
more focused file reading. The king scores 0.330 on the same task — it
finds the right files faster.

## Next40 Plan: Adopt King's _integration_hints() + Acceptance Checklist

### CHANGE 1 — Replace our _integration_hints() with king's approach
Remove ALL language-based hints. Replace with the king's 6 content-based hints:
- _DATA_UPDATE_RE: fires when issue mentions data/config/snapshot updates
- _INTEGRATION_RE: fires when issue mentions wiring/entrypoints/routes/providers
- _COMPONENT_RE: fires when issue mentions UI components
- _NEW_SYMBOL_RE: fires when issue mentions new props/callbacks/keys/handlers
- _REFACTOR_RE: fires when issue mentions refactor/rename
- _UI_DETAIL_RE: fires when issue mentions UI polish/visual/animation

Copy king's exact regex patterns (they're not protected, they're functional).
Copy king's exact hint TEXT (the hints are not the IP, the agent strategy is).

### CHANGE 2 — Add king's extract_criteria() + format_checklist() pattern
King's extract_criteria() reads the issue, extracts bullet/numbered items as
acceptance criteria, appends _integration_hints(), and returns up to 15 items.
format_checklist() formats them as "## Acceptance checklist".
This checklist gets appended to the task prompt — agent must verify each item.

Add this to our build_task_prompt() by appending the formatted checklist.
This forces our agent to check every requirement before finishing.

### CHANGE 3 — Keep only proven additions from our stack
Keep: _build_polish_task (king-byte-identical), _polish_worth_adopting,
SYSTEM_PROMPT rider, render_observation, _CPP_LANG_RE (our only stable hint —
T1 C++ wins with it), _FEATURE_VERB_RE (T9 reliable). Everything else
already removed in Next39.

The result should be structurally very close to king + our 2 proven hints +
the acceptance checklist injection.

## Expected Impact
- T2 Python (0.320 vs 0.630): acceptance checklist forces checking all reqs → better score
- T3 TypeScript zero: content hints (_COMPONENT_RE, _INTEGRATION_RE) give better direction
- T4 Python API (0.430 vs 0.550): checklist + integration hint closes gap
- T5 PHP (0.140 vs 0.550): integration + checklist = major improvement
- T6 Go (0.000): both timeout — step budget issue, not fixable by hints

Conservative: 40-50% → Optimistic: 60%+ if acceptance checklist is the key
