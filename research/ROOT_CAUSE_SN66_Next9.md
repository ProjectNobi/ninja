# Root Cause Analysis — SN66 Next9
*Pipeline Step 3 — 2026-06-15*

## Why Next8 Got 80% Gate (vs c7add572) But New King is af1291

### Timing Issue
- We submitted Next8 against c7add572 (scored 0.841 avg)
- c7add572 was replaced WHILE our hotkey was in queue
- New king af1291 is much weaker: 0.742 avg score
- Our Next8 at 80% gate should be ~85%+ vs af1291

### Root Causes of Our Losses (Next7 live: 22 losses out of 49)
1. **Wrong architectural layer** (R44/R45): Agent placed code in wrong module/layer → 0.10 score
2. **Deleted working implementations** (R10): Agent replaced full impl with skeleton → 0.10 score
3. **Partial implementations** (R24, R35): Stopped short of full integration
4. **Missing project conventions** (R5, R20): forwardRef, Redux, Next.js server components

### Fixes Applied in Next8/Next9
- ✅ ARCHITECTURE-FIRST RULE (layer awareness)
- ✅ NEVER DELETE, ALWAYS EXTEND
- ✅ Arch probe (project layout context before first step)
- ✅ Fast-path for simple tasks (better solve_time score)
- ✅ READ BEFORE WRITE (prevents partial-context edits) [NEW in Next9]
- ✅ JS syntax check via node --check [NEW in Next9, matches king]
- ✅ TransientContentError retry [NEW in Next9, matches king]

### Expected Impact
- Next8 vs c7add572: 80% gate WR
- Next9 vs af1291 (weaker king): projected 80-87%
- af1291 king score 0.742 vs our Next7 avg 0.793 → we already outscored it
- Need: wins > losses + 6 → need ~29W/21L minimum
- 85% gate projects to ~38W/12L in live duel → well above threshold
