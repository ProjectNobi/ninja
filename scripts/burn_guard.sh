#!/usr/bin/env bash
# burn_guard.sh — Pre-registration safety check for SN66 (H5 fix, 2026-06-16)
#
# WHY: Jun 14-16 the pipeline burned ~τ1.5 over 11+ registrations with ZERO
#      kings won — the agent kept registering/submitting after consecutive
#      duel losses with the same root cause. This guard forces a pause.
#
# Run BEFORE every `btcli s burned_register` / hotkey registration / submission.
#   Exit 0 = SAFE to proceed
#   Exit 1 = BLOCKED (analyse root cause first; low balance; or fetch error)
#
# Usage:
#   bash scripts/burn_guard.sh                      # reads .sn66_hotkeys
#   bash scripts/burn_guard.sh 5Hk... 5Gk... ...    # explicit hotkeys
#
set -euo pipefail

# ── Tunables ─────────────────────────────────────────────────────────────────
MAX_CONSECUTIVE_LOSSES=3
MIN_BALANCE_TAO="0.25"
DASHBOARD_URL="https://ninja66.ai/dashboard.json"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
HOTKEYS_FILE="$REPO_DIR/.sn66_hotkeys"
BALANCE_CACHE="$REPO_DIR/.coldkey_balance"
COLDKEY_SS58="5HiWGQSRZ64WQhaaiCKPav3NXpdUB5UPKn41GVmL9qYtaizh"  # T68Coldkey
BTCLI_PY="/root/bt_venv/bin/python"

# ── Collect hotkeys ──────────────────────────────────────────────────────────
HOTKEYS=()
if [[ $# -gt 0 ]]; then
  HOTKEYS=("$@")
elif [[ -f "$HOTKEYS_FILE" ]]; then
  while IFS= read -r line; do
    # strip inline comments + whitespace; skip blank/comment lines
    hk="$(printf '%s' "$line" | sed -e 's/#.*//' -e 's/[[:space:]]//g')"
    [[ -z "$hk" ]] && continue
    HOTKEYS+=("$hk")
  done < "$HOTKEYS_FILE"
fi

if [[ ${#HOTKEYS[@]} -eq 0 ]]; then
  echo "🛡️  BURN GUARD CHECK"
  echo "└─ ❌ BLOCKED — no hotkeys supplied and $HOTKEYS_FILE is empty/missing"
  exit 1
fi

# ── Fetch dashboard & compute consecutive losses ────────────────────────────
# Build a jq --arg list of our hotkeys, filter duels to ours, sort by
# finished_at ascending, then count trailing king_replaced==false.
TMP_DASH="$(mktemp /tmp/sn66_dash.XXXXXX.json)"
trap 'rm -f "$TMP_DASH"' EXIT

HTTP_OK=1
if ! curl -sf --max-time 60 "$DASHBOARD_URL" -o "$TMP_DASH" 2>/dev/null; then
  HTTP_OK=0
fi

CONSEC_LOSSES="?"
TOTAL_OURS=0
RECENT_W=0
RECENT_L=0
LAST_DUEL_TS="(none)"
DUEL_LINE=""

if [[ "$HTTP_OK" -eq 1 ]] && [[ -s "$TMP_DASH" ]]; then
  # Emit one line per our-duel: "<finished_at>\t<king_replaced>" sorted asc.
  HK_JSON="$(printf '%s\n' "${HOTKEYS[@]}" | jq -R . | jq -s .)"
  RESULTS="$(jq -r --argjson hks "$HK_JSON" '
      [ .duels[]
        | select(.challenger_hotkey as $c | $hks | index($c))
        | {ts: (.finished_at // .started_at // ""), repl: (.king_replaced // false)} ]
      | sort_by(.ts)
      | .[] | "\(.ts)\t\(.repl)"
    ' "$TMP_DASH" 2>/dev/null || true)"

  if [[ -n "$RESULTS" ]]; then
    TOTAL_OURS="$(printf '%s\n' "$RESULTS" | grep -c . || true)"
    RECENT_W="$(printf '%s\n' "$RESULTS" | grep -c $'\ttrue$' || true)"
    RECENT_L="$(printf '%s\n' "$RESULTS" | grep -c $'\tfalse$' || true)"
    LAST_DUEL_TS="$(printf '%s\n' "$RESULTS" | tail -1 | cut -f1)"
    # Count trailing consecutive losses (king_replaced=false at the end)
    c=0
    while IFS= read -r row; do
      [[ -z "$row" ]] && continue
      repl="${row##*$'\t'}"
      if [[ "$repl" == "false" ]]; then
        c=$((c+1))
      else
        c=0
      fi
    done < <(printf '%s\n' "$RESULTS")
    CONSEC_LOSSES="$c"
  else
    CONSEC_LOSSES=0
    TOTAL_OURS=0
  fi
fi

# ── Resolve coldkey balance (live SDK → cache fallback) ──────────────────────
BAL=""
BAL_SRC=""
if [[ -x "$BTCLI_PY" ]]; then
  BAL="$(timeout 70 "$BTCLI_PY" - "$COLDKEY_SS58" <<'PYEOF' 2>/dev/null || true
import sys
cold = sys.argv[1]
try:
    import bittensor as bt
    sub = None
    for ctor in ("Subtensor", "subtensor", "AsyncSubtensor"):
        if hasattr(bt, ctor):
            try:
                sub = getattr(bt, ctor)(network="finney"); break
            except Exception:
                continue
    if sub is None:
        from bittensor.core.subtensor import Subtensor
        sub = Subtensor(network="finney")
    bal = sub.get_balance(cold)
    try: v = float(bal.tao)
    except Exception: v = float(bal)
    print(f"{v:.6f}")
except Exception:
    sys.exit(3)
PYEOF
)"
  if [[ -n "$BAL" ]]; then
    BAL_SRC="live"
    printf '%s\n' "$BAL" > "$BALANCE_CACHE" 2>/dev/null || true
  fi
fi

if [[ -z "$BAL" ]] && [[ -f "$BALANCE_CACHE" ]]; then
  BAL="$(sed -e 's/[^0-9.]//g' "$BALANCE_CACHE" | head -1)"
  [[ -n "$BAL" ]] && BAL_SRC="cache"
fi

# ── Evaluate gates ───────────────────────────────────────────────────────────
BLOCK=0
REASONS=()

# Gate A: consecutive losses
LOSS_FLAG=""
if [[ "$CONSEC_LOSSES" == "?" ]]; then
  LOSS_FLAG="← UNKNOWN (dashboard fetch failed)"
  BLOCK=1
  REASONS+=("could not fetch duel history — fail-closed (analyse manually before registering)")
elif [[ "$CONSEC_LOSSES" -ge "$MAX_CONSECUTIVE_LOSSES" ]]; then
  LOSS_FLAG="← AT/OVER LIMIT ($MAX_CONSECUTIVE_LOSSES)"
  BLOCK=1
  REASONS+=("$CONSEC_LOSSES consecutive duel losses — same root cause likely; analyse before burning more τ")
fi

# Gate B: balance
BAL_FLAG=""
if [[ -z "$BAL" ]]; then
  BAL_FLAG="← UNKNOWN (no live value, no cache)"
  BLOCK=1
  REASONS+=("could not resolve T68Coldkey balance — fail-closed")
else
  if awk -v b="$BAL" -v m="$MIN_BALANCE_TAO" 'BEGIN{exit !(b < m)}'; then
    BAL_FLAG="← BELOW MIN (τ$MIN_BALANCE_TAO)"
    BLOCK=1
    REASONS+=("balance τ$BAL below minimum τ$MIN_BALANCE_TAO — low-balance alert")
  fi
fi

# ── Report ───────────────────────────────────────────────────────────────────
echo "🛡️  BURN GUARD CHECK  ($(date -u '+%Y-%m-%d %H:%M:%S UTC'))"
echo "├─ Tracked hotkeys: ${#HOTKEYS[@]}"
if [[ "$CONSEC_LOSSES" == "?" ]]; then
  echo "├─ Recent duels: (fetch failed)"
else
  echo "├─ Recent duels: $RECENT_L losses / $RECENT_W wins (total ${TOTAL_OURS}, last $LAST_DUEL_TS)"
fi
echo "├─ Consecutive losses: $CONSEC_LOSSES $LOSS_FLAG"
if [[ -n "$BAL" ]]; then
  echo "├─ T68Coldkey balance: τ$BAL ($BAL_SRC) $BAL_FLAG"
else
  echo "├─ T68Coldkey balance: unknown $BAL_FLAG"
fi

if [[ "$BLOCK" -eq 1 ]]; then
  echo "└─ ❌ BLOCKED — analyse root cause before next registration"
  echo ""
  echo "   Reasons:"
  for r in "${REASONS[@]}"; do echo "     • $r"; done
  echo ""
  echo "   Required before retry: identify WHY duels are lost (read validator"
  echo "   source, compare king_agent.py, run local gate ≥ thresholds), and"
  echo "   confirm sufficient T68Coldkey balance. Override only with James's"
  echo "   explicit approval (NO-AUTO-SUBMIT rule, L-NO-AUTO-SUBMIT-1)."
  exit 1
fi

echo "└─ ✅ SAFE — no consecutive-loss block, balance OK. Proceed with care."
exit 0
