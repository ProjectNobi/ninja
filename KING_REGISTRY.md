# SN66 King Registry — Harness Configuration
*Updated: 2026-05-15 05:55 UTC*

## CURRENT KING (live as of 2026-05-15)
| Field | Value |
|-------|-------|
| **GitHub User** | adamninja |
| **PR** | #1551 (unarbos/ninja) |
| **Commit SHA** | `9272402e068ae35d1de2397a830f594eb1d79ed2` |
| **Lines** | 4,106 |
| **Harness file** | `king_agent.py` ✅ UPDATED |
| **Archive** | `agents_archive/king_agent_pre_adamninja_pr1551_backup.py` |
| **Confirmed by** | SN66 team (kingcharlezz gist + validator launch announcement, 2026-05-15) |
| **Architecture** | Multishot | WALL_CLOCK=248s inner / ~300s outer | 30 max steps |

### Confirmed by Team
- Gist `find_original.py` scanned PRs #1300–1595 for SHA `9272402e068ae35d1de2397a830f594eb1d79ed2` → found at **PR #1551**
- Team announced: "adamninja promoted to king, launching validator" (2026-05-15)

### Architecture Features
- WALL_CLOCK_BUDGET_SECONDS = 248.0 (inner), WALL_CLOCK_RESERVE_SECONDS = 20.0
- DEFAULT_MAX_STEPS = 30, DEFAULT_MAX_TOKENS = 8192
- Multishot architecture (multiple attempts per task)
- SYSTEM_PROMPT: elite autonomous coding agent framing
- Evidence priority chain: issue text → failing tests → similar tests → function owner → patterns → API compat

---

## PREVIOUS KING (PR #805, leec72991-a11y, 2026-05-10)
| Field | Value |
|-------|-------|
| **Hotkey** | `5HjcKEmAQXLLfgEWgmoYBpSD98Y2ZAddjX33NBE35gHRsJGB` |
| **UID** | 107 |
| **Commit** | `06416562287dc3d49c80cb8db05deae51bb3131d` |
| **Harness file** | `king_agent.py` (2993 lines) |
| **Architecture** | anon-magician v28 multi-shot + v21 edge + criteria-nudge |
| **Key change vs prev king** | +1 line: "Integration cascade" plan enumeration |
| **Archive** | `agents_archive/king_pr770_ninjaking66.py` |

### The King's Defining Innovation
```
- Integration cascade: if the issue describes a feature spanning multiple concerns
  (page + route + nav + data fetch; or model + migration + serializer + view + URL),
  enumerate EVERY required integration point as its own plan row even when the issue
  does not explicitly bullet them.
```
Source claim: targets dominant 26% king-loss pattern from 850 sampled LLM-judge rationales.

### Architecture Features (from code analysis)
- **Multi-shot wrapper** (v28): runs multiple attempts, each with WALL_CLOCK_BUDGET_SECONDS=270s
- **v21 edge**: recent-commit style anchors + criteria-nudge support
- **WALL_CLOCK_RESERVE_SECONDS = 20.0**: keeps budget for retries
- **DEFAULT_MAX_STEPS = 30**: same as our agents
- Significantly stronger than PR#640 (Challenge-winner) — multi-shot vs single-shot

### King Weakness Map (from duels 4381/4382 vs old king PR#640)
| Task | New King LLM | Notes |
|------|-------------|-------|
| 064697 (Supabase) | 0.56 | Hardcodes placeholder URL — still losing |
| 064950 (auth modal) | 0.32 | Large unrelated churn → penalized |
| 064829 (UI refresh) | 0.14 | Broken implementation |
| 064679 (regex util) | 0.18 | Misdefines DINPUT_PLACEHOLDER_REGEX |
| 064694 (categories) | 0.43 | Narrow patch misses full scope |

---

## KING HISTORY
| Date | Hotkey | PR | Architecture |
|------|--------|-----|-------------|
| May 9 | 5CfBJuxB1ak1KbxME8pVZw3UGF6yBqtBaCoT34qTdfWeLsv9 | #640 (Challenge-winner) | Single-shot |
| **May 10** | **5CPQ86cHikm8nR2YJQhW3Mc1vVspfEq8oc1BgRaKZt4v9VZS** | **#770 (ninjaking66)** | **Multi-shot v28** |

---

## HARNESS SETUP
```bash
# Run gate test against CURRENT king
python3 validator_harness_v5.py --challenger <agent.py> --king king_agent.py --tasks 25 --seed 42

# Gate threshold: ≥55% decisive win rate → ask James for approval
```

## WHEN KING CHANGES
1. Fetch new king's agent.py from their repo
2. Save as `king_agent.py` (overwrite)
3. Archive old king: `cp king_agent.py agents_archive/king_pr{N}_{name}.py`
4. Update this file (KING_REGISTRY.md)
5. Update SN66_FINAL_STRATEGY.md king section
6. Update SN66_STATE shard
7. Re-run gate test against new king

---

## 2026-05-10 10:15 UTC — NEW KING: PR #784 (victormorales9493-lab)

### Chain of Kings
| PR | King | Dethroned by |
|----|------|-------------|
| #770 (ninjaking66) | UID 249 | PR #783 (VladaWebDev) |
| #783 (VladaWebDev) | UID 79 | PR #784 (victormorales9493-lab) |
| **#784 (victormorales9493-lab)** | **UID 108** | **CURRENT KING** |

### PR #784 Identity
- **Hotkey:** 5FCXNcRsuArK7MmzDeYd5emVXzaGovXWe8RYz2WZ9ENsLNfu
- **Commit:** 127a8c91b34aa7bf8ae621216ef6022bc4f3f8b7
- **Lines:** 4,080 (vs PR#770's 2,993 = +1,087 more lines!)
- **Harness file:** `king_agent.py` UPDATED ✅
- **Archive:** `agents_archive/king_pr784_victormorales9493.py`
- **Backup prev king:** `king_agent_pr770_backup.py`

### Key Innovations vs Previous Kings
- Focused-region reading around identifier definitions
- Multishot memo (directed retry, not blind retry)
- Emergency single-shot fallback
- 9 new refinement gates (lint, contract, integration, artifact, dependency nudges)
- Safety net wrapper
- WALL_CLOCK: 240s (tighter)

### Weakness Map
- 064628 (multi-upload): undefined TypeScript var bug (king LLM 0.22)
- 064703 (flashcard): CSS 3D tilt (both agents fail)
- Analysis: `research/SN66_NEW_KING_PR784_ANALYSIS_2026-05-10.md`

---

## 2026-05-10 15:04 UTC — NEW KING: PR #897 (Challenge-winner)
- **Hotkey:** 5DFBRm1dBbJN7BapdDnzsLkzFhDtSuJ1jr6D274zEwpTtctx
- **Lines:** 2,855 | **SYSTEM_PROMPT:** 5,492 chars
- **Architecture:** Multishot | WALL_CLOCK=270s | NO focused reading | NO lint gate
- **Key innovation:** Verifies issue-named tests FIRST before <final>
- **Context:** Won after validator was fixed + reset to PR#770

### Context: Validator Break + King History Today
1. PR#770 → PR#783 → PR#784 (broken validator period)
2. Validator fixed → king reset to PR#770
3. PR#897 (Challenge-winner, simpler) dethroned PR#770

### VALIDATOR INTEL (from owner)
Priority: Codebase refactor (too complex, causing bugs)
Coming: Verifiably fair deterministic tasks via drand/block hash

---

## 2026-05-10 18:30 UTC — KING CONFIRMED: PR#784 (victormorales9493) via retest
- Duel #4393: Challenger PR#784 vs King PR#770 — full 50 rounds
- Final score: **28-21-1** (challenger wins)
- Threshold 5: 28 > 21+5=26 ✅ Confirmed dethroned
- king_agent.py updated back to PR#784 ✅
- Our v8/v9 (built on PR#784 base) are most competitive submissions

---

## 2026-05-10 20:30 UTC — NEW KING: PR #805 (leec72991-a11y)
- **Hotkey:** 5HjcKEmAQXLLfgEWgmoYBpSD98Y2ZAddjX33NBE35gHRsJGB
- **UID:** 107 | **Lines:** 3,192 | **SYSTEM_PROMPT:** 12,337 chars (SAME as PR#770)
- **Base:** PR#770 + 199 lines of issue-aware preloading code
- **Key win:** Issue-aware partial file loading (reads around relevant lines vs head/tail)
- **Duels:** 4408 (35-14, no DQ), 4409 (31-19, no DQ) — mean similarity ~0.57
- **Critical:** REAL CODE CHANGES → diverse patches → no copy detection trigger


---

## 2026-05-15 05:55 UTC — NEW KING: PR #1551 (adamninja) — CONFIRMED BY SN66 TEAM

### Team Announcement
- Message from SN66 team: "PR #1551 is the real king — promoting adamninja to king and launching validator"
- Verified via `find_original.py` gist: scanned PRs 1300-1595, SHA `9272402e068ae35d1de2397a830f594eb1d79ed2` → **PR #1551**

### King Identity
- **GitHub User:** adamninja
- **Repo:** unarbos/ninja PR #1551
- **Commit SHA:** `9272402e068ae35d1de2397a830f594eb1d79ed2`
- **Lines:** 4,106
- **Architecture:** Multishot | WALL_CLOCK=248s | MAX_STEPS=30

### Harness Updated
- `king_agent.py` → adamninja PR#1551 ✅
- Old king archived: `agents_archive/king_agent_pre_adamninja_pr1551_backup.py`
- SHA verified in harness ✅

### Action Required
- Re-run gate tests for all active challenger agents against new king
- Rebuild v41+ based on adamninja's architecture as baseline
- Study adamninja's SYSTEM_PROMPT for new patterns to beat

---
## King Update — 2026-05-15 14:51 UTC

**New King:** 5FGuXw2aEJCunPo2rqwLkMJHiajM (private submission, no PR)
**GitHub SHA:** 627b16d9ffdbe805
**Lines:** 4,247 (was 4,106 with adamninja PR#1551)

### Key Addition: `_find_test_partner_by_grep()` (+149 lines, -7)
- `_TEST_DIR_MARKERS`: tuple of test directory patterns
- `_TEST_LANG_SUFFIX_MAP`: language → test file extension mapping
- `_find_test_partner_by_grep()`: fallback test discovery for non-standard layouts
  - Catches: `tests/unit/foo_test.py`, `features/foo/__tests__/bar.spec.ts`, `spec/legacy/foo_spec.rb`
  - Pure set/string operations — no I/O
  - Scores by stem match, test dir presence, language family match

### Impact
- Non-standard test layout discovery now much more robust
- Wires companion tests for more task types → better TEST_FIX refinement turns
- v49 MUST include this function to match king's baseline

### Harness
- king_agent.py updated ✅
- Archive: agents_archive/king_agent_adamninja_pr1551_backup.py
