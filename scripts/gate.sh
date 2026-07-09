#!/usr/bin/env bash
# gate.sh — HARD king-sync gate wrapper for validator_harness_v7.py (H4 fix, 2026-06-16)
#
# Problem solved (L-SN66-KING-SYNC-PIPELINE-1 / L-SN66-KING-SYNC-SILENT-FAIL-1):
#   sync_king.sh is advisory. Gates were repeatedly run against a STALE king
#   (king changed mid-queue) → WR data meaningless, hours wasted Jun 14-15.
#
# This wrapper performs a MANDATORY king-freshness check BEFORE any gate runs:
#   - Fetches the live king commit SHA from ninja66.ai/dashboard.json
#   - Compares it to the locally-synced SHA recorded in .king_sha
#     (king_agent.py is fetched from a GIT COMMIT, so the synced commit SHA is
#      the correct identity to compare — a content hash of king_agent.py would
#      NEVER equal a git commit SHA and is the wrong thing to compare.)
#   - MISMATCH  → HARD BLOCK (exit 1), no gate runs.
#   - --auto-sync → on mismatch, runs sync_king.sh then re-verifies before proceeding.
#   - MATCH     → forwards all remaining args to validator_harness_v7.py.
#
# Works from ANY directory. Does NOT modify validator_harness_v7.py.
#
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️  TIMEOUT RULES — L-SN66-LIVE-DUEL-TIMEOUT-1 + L-SN66-HARNESS-TIMEOUT-2
#     (confirmed from duel 7241 JSON forensics 2026-06-24 — MANDATORY)
#
# LIVE DUEL REALITY (confirmed from duel 7241 — all 37 rounds):
#   king_agent_timeout_seconds = 300 (EVERY round, no variation)
#   challenger_agent_timeout_seconds = 300 (EVERY round, no variation)
#   TAU_AGENT_TIMEOUT_SECONDS is NOT passed to solve() by the validator.
#   The live harness SIGKILLs at exactly 300s.
#
# AGENT BUDGET RULE (L-SN66-LIVE-DUEL-TIMEOUT-1):
#   _wall_clock_limit_seconds() fallback MUST be 270.0 (300s - 30s reserve).
#   NOT 570.0 (which is 2x the real live wall — agent gets SIGKILL'd at 300s).
#   NOT 280.0 / 300.0 (too tight or hits exact wall).
#   When TAU_AGENT_TIMEOUT_SECONDS=300 is set, dynamic calc applies:
#     max(60.0, float(300) - 30.0) = 270.0 — correct.
#   When NOT set (live reality), fallback = 270.0 — also correct for live.
#   WALL_CLOCK_RESERVE_SECONDS MUST be >= 30.0.
#
# GATE POLICY (L-SN66-HARNESS-TIMEOUT-2):
#   --timeout 300 = live-accurate for duel rounds (matches 300s per-round wall)
#   --timeout 600 = useful for testing agent behaviour with more budget
#   Canonical pre-submission gate: --timeout 300 --parallel 4 --tasks 30
#   (was --timeout 600; corrected after duel 7241 forensics confirmed 300s)
#
# CHECKPOINT-TO-DISK RULE (L-SN66-EMPTY-PATCH-CHECKPOINT-1):
#   King scores 0.15-0.50 even when timing out. We score 0.000.
#   Agent MUST write best-so-far patch to disk after every candidate.
#   On SIGKILL, last checkpoint is recovered from disk — never 0.000.
# ─────────────────────────────────────────────────────────────────────────────
#
# Usage (CANONICAL — live-accurate 300s, parallel 4):
#   bash scripts/gate.sh --auto-sync --challenger agent_cl_gpt_NextXX.py --tasks 30 --seed 42 --parallel 4 --timeout 300
#
# Usage (extended budget test — tests agent at longer window, NOT live-accurate for round timing):
#   bash scripts/gate.sh --auto-sync --challenger agent_cl_gpt_NextXX.py --tasks 30 --seed 42 --parallel 4 --timeout 600
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
HARNESS="$REPO_ROOT/validator_harness_v7.py"
KING_FILE="$REPO_ROOT/king_agent.py"
SHA_FILE="$REPO_ROOT/.king_sha"
SYNC_SCRIPT="$SCRIPT_DIR/sync_king.sh"
DASHBOARD_URL="https://ninja66.ai/dashboard.json"

# ── Parse --auto-sync (consumed here, NOT forwarded to harness) + --help ──────
AUTO_SYNC=0
ARGS=()
for a in "$@"; do
    case "$a" in
        --auto-sync) AUTO_SYNC=1 ;;
        -h|--help)
            sed -n '2,30p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            echo
            echo "Forwarded harness args (after the king check):"
            python3 -u "$HARNESS" --help 2>/dev/null || true
            exit 0
            ;;
        *) ARGS+=("$a") ;;
    esac
done

# ── Sanity: required files exist ──────────────────────────────────────────────
[[ -f "$HARNESS" ]]   || { echo "❌ Harness not found: $HARNESS"; exit 1; }
[[ -f "$KING_FILE" ]] || { echo "❌ King file not found: $KING_FILE (run sync_king.sh first)"; exit 1; }

# ── Fetch live king SHA from dashboard ────────────────────────────────────────
fetch_live_sha() {
    local json
    json=$(curl -sf --max-time 15 "$DASHBOARD_URL") || return 1
    echo "$json" | python3 -c "
import json,sys
d=json.load(sys.stdin)
k=d.get('current_king',{})
sha=(k.get('runtime_commit_sha') or k.get('commit_sha') or '').strip()
if not sha:
    sys.exit(2)
print(sha)
"
}

local_synced_sha() {
    [[ -f "$SHA_FILE" ]] && tr -d '[:space:]' < "$SHA_FILE" || echo ""
}

# ── Step 1: mandatory king-freshness check ────────────────────────────────────
echo "🔐 Gate king-sync check (HARD BLOCK on mismatch)…"
LIVE_SHA=$(fetch_live_sha) || {
    echo "❌ Could not fetch live king SHA from $DASHBOARD_URL — REFUSING to run gate."
    echo "   (Network/dashboard error. A gate against an unverified king is meaningless.)"
    exit 1
}
LOCAL_SHA=$(local_synced_sha)

echo "   Live  king SHA (dashboard): ${LIVE_SHA:0:12}"
echo "   Local synced SHA (.king_sha): ${LOCAL_SHA:0:12}${LOCAL_SHA:+}"

# Compare first 12 chars (dashboard uses full SHA; 12-char prefix is unambiguous)
if [[ "${LIVE_SHA:0:12}" != "${LOCAL_SHA:0:12}" ]] || [[ -z "$LOCAL_SHA" ]]; then
    echo "⚠️  KING MISMATCH — local king is STALE."
    if [[ "$AUTO_SYNC" -eq 1 ]]; then
        echo "🔄 --auto-sync set → running sync_king.sh…"
        bash "$SYNC_SCRIPT"
        LOCAL_SHA=$(local_synced_sha)
        LIVE_SHA=$(fetch_live_sha) || { echo "❌ Re-fetch of live SHA failed after sync."; exit 1; }
        echo "   Re-check → live ${LIVE_SHA:0:12} vs local ${LOCAL_SHA:0:12}"
        if [[ "${LIVE_SHA:0:12}" != "${LOCAL_SHA:0:12}" ]]; then
            echo "❌ HARD BLOCK — king still mismatched after sync_king.sh. Aborting gate."
            exit 1
        fi
        echo "✅ King synced + verified current."
    else
        echo "❌ HARD BLOCK — gate will NOT run against a stale king."
        echo "   Fix: run  'bash scripts/sync_king.sh'  then retry,"
        echo "        or re-run this command with  --auto-sync."
        exit 1
    fi
else
    echo "✅ King is current (${LIVE_SHA:0:12}) — proceeding to gate."
fi

# ── Step 2: challenger budget sanity check (L-SN66-LIVE-BUDGET-MISMATCH-1 + L-SN66-GATE-TIMEOUT-HARDCODE-1) ────
# Block if challenger agent has the hardcoded 280s/300s budget fallback that
# causes catastrophic live-duel losses (agent self-terminates, king grinds to 570s).
CHALLENGER_FILE=""
for arg in "${ARGS[@]}"; do
    if [[ "$arg" == *.py ]]; then
        CHALLENGER_FILE="$arg"
        break
    fi
done
if [[ -n "$CHALLENGER_FILE" ]]; then
    ABS_CHALLENGER="$REPO_ROOT/$CHALLENGER_FILE"
    [[ -f "$CHALLENGER_FILE" ]] && ABS_CHALLENGER="$CHALLENGER_FILE"
    # Import the module and call the resolver -- grep cannot see through named
    # constants or arithmetic (KS38: float(28*10), KS41: _FALLBACK_WALL_CLOCK=280).
    # scripts/check_budget.py strips TAU_AGENT_* env so the fallback path runs.
    # Settled 2026-07-09 (A Hung audit): MAX=270.0s, MIN_RESERVE=30.0s.
    if ! python3 "$REPO_ROOT/scripts/check_budget.py" "$ABS_CHALLENGER"; then
        echo "❌ BUDGET CHECK FAILED (L-SN66-LIVE-DUEL-TIMEOUT-1)"
        echo "   Live duel = 300s per round (confirmed duel 7241 forensics 2026-06-24)."
        echo "   Fix: _FALLBACK_WALL_CLOCK = 270.0, _WALL_CLOCK_RESERVE_SECONDS = 30.0"
        echo "   File: $ABS_CHALLENGER"
        exit 1
    fi
fi

# ── Step 3: forward to harness with verified king + king-sha ──────────────────
# ── KS41_TRACE check ─────────────────────────────────────────────────────────
# _KS41_TRACE_PATH is read at import time. KS41_TRACE must be exported BEFORE
# Python starts — setting it inside a wrapper after import is too late.
if [[ -n "$KS41_TRACE" ]]; then
    echo "📝 KS41_TRACE enabled → $KS41_TRACE"
    export KS41_TRACE
else
    echo "ℹ️  KS41_TRACE not set — reroll decisions will not be logged."
    echo "   To instrument: export KS41_TRACE=/tmp/ks41_trace.jsonl before running gate.sh"
fi

echo "🚀 Launching gate: validator_harness_v7.py --king king_agent.py --king-sha ${LIVE_SHA:0:12}"
exec python3 -u "$HARNESS" --king "$KING_FILE" --king-sha "${LIVE_SHA:0:12}" "${ARGS[@]}"
