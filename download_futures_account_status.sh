#!/bin/bash

set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  -s, --start MONTH    Start month in YYYY-MM format (default: 2024-09)
  -e, --end MONTH      End month in YYYY-MM format (default: last month)
  -o, --output FILE    Output CSV file path
  -h, --help           Show this help message

Example:
  $(basename "$0") --start 2024-10 --end 2025-01
EOF
  exit 0
}

# Default values
START_MONTH="2024-09"
END_MONTH=$(python3 - <<'PY'
from datetime import date, timedelta
today = date.today()
first_of_this_month = today.replace(day=1)
last_month = first_of_this_month - timedelta(days=1)
print(last_month.strftime("%Y-%m"))
PY
)
OUTFILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--start)
      START_MONTH="$2"
      shift 2
      ;;
    -e|--end)
      END_MONTH="$2"
      shift 2
      ;;
    -o|--output)
      OUTFILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      ;;
  esac
done

if [[ -z "$OUTFILE" ]]; then
  OUTFILE="$(cd "$(dirname "$0")" && pwd)/futures_account_status_${START_MONTH}_to_${END_MONTH}.csv"
fi

chrome_js() {
  local js="$1"
  osascript - "$js" <<'APPLESCRIPT'
on run argv
  tell application "Google Chrome"
    execute front window's active tab javascript (item 1 of argv)
  end tell
end run
APPLESCRIPT
}

months_between() {
  python3 - "$1" "$2" <<'PY'
from datetime import date
import sys

start = date.fromisoformat(sys.argv[1] + "-01")
end = date.fromisoformat(sys.argv[2] + "-01")
cur = start

while cur <= end:
    print(cur.strftime("%Y-%m"))
    if cur.month == 12:
        cur = date(cur.year + 1, 1, 1)
    else:
        cur = date(cur.year, cur.month + 1, 1)
PY
}

wait_for_month_data() {
  local month="$1"
  local extracted=""
  local attempt

  for attempt in $(seq 1 15); do
    sleep 1
    extracted="$(chrome_js "(()=>{const target='${month}'; const clean=s=>(s||'').replace(/\s+/g,'').trim(); const qq=v=>'\\\"'+String(v).replace(/\\\"/g,'\\\"\\\"')+'\\\"'; const basic=[...document.querySelectorAll('table')].find(t=>clean(t.rows?.[0]?.cells?.[0]?.innerText)==='基本资料'); const funds=[...document.querySelectorAll('table')].find(t=>clean(t.rows?.[0]?.cells?.[0]?.innerText)==='期货期权账户资金状况'); if(!basic||!funds) return 'WAIT'; let tradeMonth=''; for(const row of [...basic.rows]){ const cells=[...row.cells].map(c=>clean(c.innerText)); for(let i=0;i<cells.length-1;i++){ if(cells[i]==='交易月份') tradeMonth=cells[i+1]; } } if(tradeMonth!==target) return 'WAIT:'+tradeMonth; const lines=[]; for(const row of [...funds.rows].slice(1)){ const cells=[...row.cells].map(c=>clean(c.innerText)); if(cells[0]&&cells[1]) lines.push([tradeMonth,cells[0],cells[1]].map(qq).join(',')); if(cells[2]&&cells[3]) lines.push([tradeMonth,cells[2],cells[3]].map(qq).join(',')); } return lines.join('\n');})()")" || true
    case "$extracted" in
      WAIT*|"")
        ;;
      ERR*)
        echo "$extracted" >&2
        return 1
        ;;
      *)
        printf '%s\n' "$extracted"
        return 0
        ;;
    esac
  done

  echo "failed to extract ${month}" >&2
  return 1
}

printf '交易月份,指标,值\n' > "$OUTFILE"

while IFS= read -r month; do
  chrome_js "(()=>{const target='${month}'; const s=document.querySelector('select[name=\\\"tradeDate\\\"]'); if(!s) return 'ERR:NO_SELECT'; if(![...s.options].some(o=>o.value===target)){ const opt=document.createElement('option'); opt.value=target; opt.text=target; s.appendChild(opt); } s.value=target; document.forms['customerForm'].submit(); return 'SUBMITTED:'+target;})()" >/dev/null
  wait_for_month_data "$month" >> "$OUTFILE"
  echo "${month} done"
done < <(months_between "$START_MONTH" "$END_MONTH")

echo "$OUTFILE"
