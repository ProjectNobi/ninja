# DPO Intelligence Report — SN66 vNEXT
**Generated:** 2026-05-19  
**Analyst:** T68Bot Subagent  
**Data:** 62,589 UPDATE + 61,327 full_matrix (UPDATE/FEATURE/BUGFIX/API) + 4,677 self-play DPO pairs  
**Judge model (live duels from 2026-05-19):** `anthropic/claude-sonnet-4.6` via OpenRouter (PR#1598)  
**Previous judge:** `openai/gpt-5.4`

---

## ⚡ TOP 3 FINDINGS (Executive Summary)

### 1. COMPLETENESS IS KING — 94% Signal Strength
In every task type, the judge rewards completeness and penalizes incompleteness above all other criteria:
- UPDATE: 94% of chosen patches praised for completeness; 92% of rejected patches penalized for incompleteness
- FEATURE: 100% of chosen patches praised for completeness
- BUGFIX: 70% chosen praised for completeness; 85% rejected penalized for incompleteness
- **Surgical minimalism is praised only 3-6% of the time**. The agent that covers more acceptance criteria wins.

### 2. TRUNCATED / INCOMPLETE PATCHES = #1 KILL SIGNAL
The single most common rejection reason across all task types is truncation or partial implementation:
- UPDATE: 70% incomplete, 50% explicitly truncated
- FEATURE: 60% incomplete, 40% truncated
- BUGFIX: 80% incomplete, 35% truncated
- **Implication for our agent: never cut off mid-diff. A complete 3-file patch beats an incomplete 6-file patch.**

### 3. CLAUDE SONNET 4.6 REWARDS ARCHITECTURAL QUALITY MORE THAN GPT-5.4
Sonnet and GPT-5.4 agree 79.7% of the time. In the 20.3% disagreement cases:
- Sonnet uniquely rewards: `cleaner` (35/200), `architectural` (23/200), `error handling` (10/200), `production-ready` (5/200), `idiomatic` (5/200)
- GPT-5.4 focused more on raw acceptance criteria alignment (121/200)
- **Implication: New judge cares MORE about code quality and architecture, not just feature-matching**

---

## DETAILED ANALYSIS BY TASK TYPE

### UPDATE Tasks (n=50 sampled from 62,589 + 30,365 records)

#### What the judge rewards (chosen patch patterns):
1. **Multi-criteria coverage**: "Patch B better addresses the core acceptance criteria by covering all three required modules (equipos, mantenimientos, and reportes)" — completeness across ALL specified files/modules wins
2. **Correct architecture/file paths**: "implementing changes in the correct file paths (apps/mobile structure)" — touching the actual codebase files vs wrong/legacy paths
3. **Proper API design**: "it includes a more complete VoiceAnalyticsDashboard with proper KPI icons, richer chart data" — richness wins over minimalism
4. **Migration + wiring**: "it adds proper S3Error integration... includes tests" — includes migration files, routing, registration
5. **Conservative completeness under truncation**: "Neither patch is complete (both are truncated), but Patch A covers more acceptance criteria including the critical memory exhaustion fix"

#### What the judge penalizes (rejected patch patterns):
1. **Truncated mid-diff**: "Patch A is incomplete (truncated mid-diff) and only partially addresses" — death sentence even if approach is correct
2. **Wrong approach on wrong files**: "it modifies the wrong class/package, requires API 30+" — modifying old/legacy files instead of current codebase
3. **Missing critical components**: "it does not demonstrate the actual retry/fallback logic" — partial stubs that miss the core requirement
4. **Over-engineering**: "introduces unnecessary complexity with additional endpoints, record types, wrapper response objects that aren't mentioned in requirements" — adding unrequested complexity
5. **Inconsistent naming/typos**: "mixing 'CHÈQUE' with accented characters vs 'CHEQUE', a typo in the error message ('traties')" — small errors signal low confidence

#### Key question — completeness vs surgical precision for UPDATE:
**COMPLETENESS WINS DECISIVELY.** 33% of wins are primarily completeness-driven vs only 6% for surgical/focused precision. The margin between patches when "both are truncated" is decided by which covers more criteria.

---

### FEATURE Tasks (n=30 sampled from 18,433 records)

#### What the judge rewards (chosen patch patterns):
1. **End-to-end wiring**: "includes a migration file... and also registers the module in main.ts for proper application integration" — routing + DB + module registration all present
2. **Concrete implementation over docs/scaffolding**: "Patch A only adds documentation to a markdown file without touching any actual code files" — code beats docs
3. **Test coverage**: "includes a comprehensive test suite covering edge cases (null/undefined, no weapons, burst-only...)" — tests signal production-readiness
4. **Grounded in real codebase**: "makes concrete, targeted changes to real files (package.json, package.nls.json, discovery.ts)" — no fabricated paths
5. **Complete over clever**: "Patch B includes a migration file (partially shown) which is critical for actually creating the database table" — infrastructure completeness wins

#### What the judge penalizes (rejected patch patterns):
1. **Fabricated/template patches**: "largely a fabricated/template patch with placeholder paths and incomplete implementation" — death penalty
2. **Wrong file structure**: "Patch A modifies incorrect file paths, introduces a completely different and incorrect algorithm" — critical fail
3. **Truncated implementation**: "Patch A's implementation is incomplete (the columns.ts diff is truncated mid-line with `const value = g`)" — even minor truncation penalized
4. **Architecture-only without implementation**: "Patch A focuses only on database migrations with constraints and indexes... doesn't implement the primary feature"
5. **Missing registration/wiring**: No module.ts registration, no route wiring = incomplete feature

#### Key question — end-to-end wiring vs targeted implementation?
**END-TO-END WIRING.** A feature that creates a service but doesn't register it in the module or wire up routing is penalized as "non-functional." Include: model → service → controller → route → migration → module registration.

---

### BUGFIX Tasks (n=20 sampled from 6,004 records)

#### What the judge rewards (chosen patch patterns):
1. **Root cause over symptom**: "Patch B directly addresses the root cause by creating the vercel.json file with the proxy rewrite rule, which is the core requirement" — fix the actual problem
2. **Complete fix including all related files**: "adds proper S3Error integration for store errors with correct HTTP status code mapping, fixes key escaping... includes tests" — comprehensive fix
3. **Minimal, targeted, correct**: "changes are minimal, targeted, and correctly resolve each acceptance criterion stated in the issue" — correct scope for BUGFIX
4. **Retry/fallback logic**: "implementing retry logic with alternative API request formats when a 403 is encountered" — defensive programming wins
5. **No security regressions**: ".env.example includes a hardcoded `SETUP_SECRET=change-me` which is a security concern" → security mistakes kill patches

#### What the judge penalizes (rejected patch patterns):
1. **Incomplete/missing the actual fix**: "Patch A updates the service and CSP but is... critically missing the vercel.json configuration that actually implements the proxy" — implement the actual fix
2. **Wrong codebase entirely**: "Patch B modifies tariff models and updaters in a different codebase (pyenphase vs enphase_cloud)" — catastrophic
3. **Symptom patch without root cause**: "Patch A focuses on file permission security and minor refactoring that are not mentioned in the issue"
4. **Non-existent variants/enums**: "introduces a non-existent `S3Error::InternalError` variant" — hallucinated APIs
5. **Security regressions**: hardcoded secrets, broken .gitignore overwrites

#### Key question — root cause vs symptom fix for BUGFIX?
**ROOT CAUSE.** But root cause + all affected files + completeness beats root cause alone. BUGFIX is the most "surgical" of the three types but still requires covering all stated acceptance criteria.

---

## CLAUDE SONNET 4.6 vs GPT-5.4: BEHAVIORAL DIFFERENCES

### Agreement rate: 79.7% (48,867/61,327 pairs)
### Disagreement rate: 20.3% (12,460 pairs) — these matter for live duels

### When Sonnet disagrees with GPT-5.4, what does Sonnet uniquely reward?

| Signal | Sonnet frequency (200 disagree samples) |
|--------|----------------------------------------|
| `cleaner` code | 35/200 (17.5%) |
| `architectural` fitness | 23/200 (11.5%) |
| `error handling` | 10/200 (5%) |
| `more robust` | 6/200 (3%) |
| `production-ready` | 5/200 (2.5%) |
| `idiomatic` code | 5/200 (2.5%) |

### GPT-5.4 uniquely rewards (in same disagreement cases):
| Signal | GPT-5.4 frequency |
|--------|------------------|
| `acceptance criteria` alignment | 121/200 (60.5%) |
| `root cause` focus | 22/200 (11%) |
| `aligns with` requirements | 21/200 (10.5%) |

### Practical implication for vNEXT:
Sonnet is a **more holistic judge** — it rewards code that would survive code review, not just code that mechanically implements requirements. To beat the new judge:

1. **Write idiomatic code for the language** — Python should be Pythonic, TypeScript should use proper types
2. **Proper error handling** — don't leave bare exceptions, add fallbacks
3. **Clean architecture** — correct file paths, logical structure, no mixing of concerns
4. **Production-ready** — include tests where natural, migration files, proper imports
5. **Still prioritize completeness** — Sonnet still penalizes incompleteness at 92%+ rate

---

## REJECTION REASONS — RANKED BY FREQUENCY

| Reason | UPDATE | FEATURE | BUGFIX |
|--------|--------|---------|--------|
| Incomplete/partial implementation | 70% | 60% | 80% |
| Truncated patch | 50% | 40% | 35% |
| Fabricated/placeholder code | 18% | 17% | 10% |
| Wrong approach | — | 3% | — |
| Missing migration/wiring | 6% | 3% | — |
| Missing tests | 4% | 7% | — |
| Breaking API changes | 4% | — | — |
| Security issues | — | — | 10% |

---

## WINNING PHRASES IN SONNET RATIONALE

Phrases that appear when the judge picks a patch (from 50+30+20 sample):

**Positive signals (chosen patch):**
- "acceptance criteria" (34/50 UPDATE, 24/30 FEATURE, 12/20 BUGFIX)
- "proper" (17, 12, 10)
- "more complete" (14, 11, 2)
- "directly addresses" (13, 3, 8)
- "better addresses" (9, 2, 7)
- "correct file" (5, 3, 2)
- "root cause" (4, 2, 5)
- "cleaner" (rare in agreement cases, 35/200 in Sonnet disagreements)

**Negative signals (rejected patch):**
- "incomplete" (27/50 UPDATE, 16/30 FEATURE, 13/20 BUGFIX)
- "truncated" (24, 12, 7)
- "partial" (12, 6, 6)
- "missing" (11, 1, 2)
- "placeholder" (7, 3, 2)
- "non-functional" (4, 2, 3)
- "fabricated" (-, 2, -)
- "incorrect algorithm" (1, 1, -)

---

## STRATEGIC RECOMMENDATIONS FOR SN66 vNEXT AGENT

### Priority 1: Eliminate truncation (50-70% of rejection)
- Agent must produce complete diffs — never cut off mid-hunk
- If approaching token limit, complete current file fully then stop rather than truncating
- "A truncated patch that could be correct beats an error, but loses to any complete patch"

### Priority 2: Cover all acceptance criteria explicitly  
- Parse ALL bullet points in the issue
- Track which criteria each file change satisfies
- If criteria can't be met, make the partial work complete rather than attempting everything partially

### Priority 3: Sonnet-specific code quality signals
- **Idiomatic code**: use language conventions (Python list comprehensions, TypeScript generics)
- **Proper error handling**: add try/except, fallbacks, error types
- **Architecture fitness**: modify the CORRECT current files, not legacy/old paths
- **No security regressions**: never hardcode secrets, never overwrite .gitignore

### Priority 4: End-to-end wiring for FEATURE tasks
- Model → Service → Controller → Route → Module registration → Migration
- Missing ANY link in this chain = "non-functional" rating

### Priority 5: Root cause for BUGFIX (but still complete)
- Fix the root cause file first
- Then check: are there 2-3 related files that also need updating?
- Add error handling/fallback around the fix

---

## DATA SOURCES

- `update_task_dpo_pairs.jsonl`: 62,589 UPDATE pairs (GPT-5.4 scored, 1-10 integer scale)
- `full_matrix_dpo_pairs.jsonl`: 61,327 mixed pairs with BOTH `judge_rationale` (GPT-5.4) AND `sonnet_rationale` (Claude Sonnet 4.6) — **primary source for new judge analysis**
- `reference_dpo_pairs.jsonl`: 9,189 pairs (not sampled — used for training reference)
- `self_play_dpo_pairs.jsonl`: 4,677 pairs including temperature/model metadata

**Note on judge transition**: The `sonnet_rationale` field in `full_matrix_dpo_pairs.jsonl` gives direct evidence of how Claude Sonnet 4.6 evaluates patches. This is the most accurate predictor of current live duel outcomes since PR#1598 switched the judge.
