# DPO Intelligence Report — SN66 v67
## Claude Sonnet 4.6 BUGFIX Analysis
**Date:** 2026-05-19  
**Data:** 500 BUGFIX pairs from `full_matrix_dpo_pairs.jsonl` + 18 live divergence cases  
**Focus:** What Claude Sonnet 4.6 rewards for BUGFIX — ground truth for v67  

---

## 🚨 Judge Context
- **Active judge:** Claude Sonnet 4.6 (LLM-only, since 2026-05-19)
- **Previous judge:** GPT-5.4
- **Fields:** Use `sonnet_winner` + `sonnet_rationale` as ground truth
- **Today's live duels:** 548 records (404 BUGFIX), `sonnet_winner` NOT yet populated in today's DPO
- **Disagreement rate:** 96/500 BUGFIX pairs (19.2%) where Sonnet ≠ GPT-5.4

---

## 📊 BUGFIX Statistics (500 pairs)

| Metric | Count |
|--------|-------|
| Total BUGFIX pairs analyzed | 500 |
| Consensus=True (agree) | 404/500 (80.8%) |
| Consensus=False (disagree) | 96/500 (19.2%) |
| Sonnet winner=B bias | ~75/100 (B usually = better patch) |

---

## 🏆 TOP 3: What Sonnet 4.6 Rewards for BUGFIX (that v62b/v66 don't address)

### #1 — EXPLICIT ACCEPTANCE CRITERIA MAPPING (344/500 = 68.8%)
**Pattern:** Sonnet explicitly checks the winning patch against EVERY stated requirement in the issue. It names specific criteria from the issue and confirms the patch covers each one.

**Sonnet phrases:**
- "directly addresses the core acceptance criteria"
- "covers all four repeat_every types mentioned in the acceptance criteria"
- "implements the domain error hierarchy (X, Y, Z)... which are explicitly called out in the issue"

**What v62b/v66 likely miss:** Generic BUGFIX approach without tracing output back to spec items. Sonnet wants to see: issue says X → patch does X, issue says Y → patch does Y.

**Fix for v67:** After every fix, enumerate: "Issue requires [A, B, C]. This patch addresses: A (line X), B (line Y), C (line Z)." Then produce a patch that visibly covers all items.

---

### #2 — COMPLETENESS / NON-TRUNCATION (275/500 = 55% penalize incomplete; 209/500 = 42% penalize truncated)
**Pattern:** Sonnet **severely penalizes** patches that are incomplete or truncated. This is the #1 loser pattern — 55% of all losing patches are flagged as incomplete.

**Sonnet phrases for losers:**
- "Patch A is truncated mid-implementation"
- "Patch A has incomplete diff output (truncated button HTML)"
- "Patch B only partially addresses the issue"
- "appears to be cut off and doesn't show the unauthenticated UI fallback"

**Critical insight:** Winner patches average **199.7 lines**. Loser patches average **261.5 lines** — longer patches LOSE more often because they're partially complete (started but not finished). Sonnet prefers a **shorter complete fix** over a **longer incomplete fix**.

**What v62b/v66 likely miss:** Under resource pressure, agents cut off mid-patch. Sonnet treats any truncated patch as an automatic loss.

**Fix for v67:** Rule: "NEVER truncate a patch mid-implementation. A complete 50-line patch beats an incomplete 300-line patch. If you cannot complete all changes, finish the most critical ones fully rather than starting all of them."

---

### #3 — ROOT CAUSE FIX vs SYMPTOM FIX (119/500 = 23.8%)
**Pattern:** Sonnet rewards patches that fix the actual underlying bug, not surface symptoms. It frequently penalizes patches that modify the wrong file, add workarounds, or introduce unnecessary abstractions.

**Sonnet phrases for winners:**
- "directly addresses the root cause by fixing the specific line where..."
- "correctly modifies the actual ResourceLoader.openStream method" (vs Patch B which modified wrong layer)
- "fixes the specific line where `task.last_done = task.due_date`" (pin to exact bug)

**Sonnet phrases for losers (consensus=False cases, Sonnet unique):**
- "modifies the wrong file (scheduler.py instead of the task file where the bug exists)"
- "introduces an unnecessary `last_done_override` parameter"
- "Patch B introduces non-existent dependencies (LRUCache, FileUtils) that would cause compilation failures"
- "Patch B has a logical bug where the while loop condition allows 4 attempts instead of 3"

**Sonnet uniquely penalizes:** Phantom imports (dependencies that don't exist), logic bugs in the fix itself, adding abstraction layers when a direct fix suffices.

**What v62b/v66 likely miss:** Agent adds workaround or abstraction rather than fixing the exact offending line.

**Fix for v67:** Rule: "Find the EXACT line(s) causing the bug. Fix them directly. Do not introduce new abstractions, new files, or new parameters unless the issue explicitly requires them. The minimal direct fix wins."

---

## ⚡ Sonnet 4.6 vs GPT-5.4 Key Differences (96 disagreement cases)

| Dimension | Sonnet 4.6 | GPT-5.4 |
|-----------|-----------|---------|
| Completeness threshold | Stricter — penalizes partial more | More lenient with partial implementations |
| Architectural elegance | Lower weight | Higher weight |
| Phantom imports/broken deps | Instant loss | Sometimes ignored |
| Direct file targeting | Strongly rewards | Moderate reward |
| Truncation detection | Explicit mention (42% of cases) | Rarely called out |
| Logic bugs in the patch itself | Flagged as disqualifying | Sometimes overlooked |

**When Sonnet picks A but GPT picks B (55/96):** Sonnet found B has a logic bug, wrong file, or phantom dependency that GPT overlooked.

**When Sonnet picks B but GPT picks A (41/96):** Sonnet found A is incomplete/truncated while B is more complete.

---

## 📋 Sonnet's BUGFIX Scoring Mental Model

```
Sonnet BUGFIX Score ≈
  + Issue criteria explicitly mapped (each AC item addressed)
  + Root cause targeted (not symptom)
  + Patch is complete (no truncation, no "TODO" stubs)
  + Correct files modified (where bug actually lives)
  - Incomplete/truncated patch  [HEAVY PENALTY -40%]
  - Phantom imports/broken deps [DISQUALIFYING]
  - Wrong file modified         [HEAVY PENALTY]
  - Logic bug in the patch itself [DISQUALIFYING]
  - Unnecessary abstraction layers [MILD PENALTY]
```

---

## 🎯 v67 SYSTEM_PROMPT Rules to Add

```
BUGFIX PROTOCOL — SONNET 4.6 JUDGE:

1. ACCEPTANCE CRITERIA MAPPING: Before writing any fix, list ALL requirements 
   from the issue. After writing, verify each is addressed. The judge checks 
   every AC item explicitly.

2. COMPLETENESS OVER COVERAGE: A complete 50-line fix beats an incomplete 
   300-line fix. NEVER truncate a patch mid-implementation. If you cannot 
   implement everything, implement the MOST CRITICAL items completely.

3. ROOT CAUSE TARGETING: Find the EXACT line(s) where the bug lives. Fix them 
   directly. Do NOT introduce new abstractions, new parameters, or new files 
   unless explicitly required. Do NOT modify files that don't contain the bug.

4. ZERO PHANTOM DEPS: Never import or reference classes, functions, or modules 
   that don't exist in the codebase. Sonnet flags this as an automatic loss.

5. VERIFY YOUR OWN LOGIC: Before finalizing, re-read your patch for logic bugs. 
   Off-by-one errors, wrong loop conditions, and incorrect exception handling 
   in the fix itself are instant disqualifiers.
```

---

## 📊 Live Duel Context (2026-05-19)
- Today's live duels: 548 records (404 BUGFIX = 73.7% of daily volume)
- Sonnet labels NOT yet populated in today's DPO file
- Heavy BUGFIX day → these rules are critical for today's scoring
- v66 current WR ~50% on BUGFIX (14/50) → these 3 gaps explain the deficit

---

**Bottom line for v67 BUGFIX:** Sonnet 4.6 is an explicit spec-checker + completeness enforcer. It reads the issue requirements like a QA engineer and marks against each one. Incomplete patches and phantom dependencies are instant disqualifiers. Fix the root cause directly — no abstraction layers.
