# Futures Automation Script and App Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the download script to produce a standard CSV with real newlines and no internal whitespace in metric names, then revert the workarounds in the Streamlit app.

**Architecture:** 
1. Update the JavaScript injection in the bash script to join records with actual newlines and remove all internal whitespace from extracted text.
2. Simplify the data loading logic in `app.py` to use standard pandas CSV reading without manual string replacement hacks.

**Tech Stack:** Bash, JavaScript (Chrome Console), Python (Pandas, Streamlit)

---

### Task 1: Fix `download_futures_account_status.sh`

**Files:**
- Modify: `download_futures_account_status.sh`

- [ ] **Step 1: Update the JS extraction logic**

Modify the `wait_for_month_data` function's JS code:
1. Change `clean` function to remove all whitespace: `const clean=s=>(s||'').replace(/\s+/g,'').trim();`
2. Change the final join from `\\\\n` to `\n`.

```bash
# In download_futures_account_status.sh
<<<<
    extracted="$(chrome_js "(()=>{const target='${month}'; const clean=s=>(s||'').replace(/\\\\s+/g,' ').trim(); const qq=v=>'\\\"'+String(v).replace(/\\\"/g,'\\\"\\\"')+'\\\"'; const basic=[...document.querySelectorAll('table')].find(t=>clean(t.rows?.[0]?.cells?.[0]?.innerText)==='基本资料'); const funds=[...document.querySelectorAll('table')].find(t=>clean(t.rows?.[0]?.cells?.[0]?.innerText)==='期货期权账户资金状况'); if(!basic||!funds) return 'WAIT'; let tradeMonth=''; for(const row of [...basic.rows]){ const cells=[...row.cells].map(c=>clean(c.innerText)); for(let i=0;i<cells.length-1;i++){ if(cells[i]==='交易月份') tradeMonth=cells[i+1]; } } if(tradeMonth!==target) return 'WAIT:'+tradeMonth; const lines=[]; for(const row of [...funds.rows].slice(1)){ const cells=[...row.cells].map(c=>clean(c.innerText)); if(cells[0]&&cells[1]) lines.push([tradeMonth,cells[0],cells[1]].map(qq).join(',')); if(cells[2]&&cells[3]) lines.push([tradeMonth,cells[2],cells[3]].map(qq).join(',')); } return lines.join('\\\\n');})()")" || true
====
    extracted="$(chrome_js "(()=>{const target='${month}'; const clean=s=>(s||'').replace(/\s+/g,'').trim(); const qq=v=>'\\\"'+String(v).replace(/\\\"/g,'\\\"\\\"')+'\\\"'; const basic=[...document.querySelectorAll('table')].find(t=>clean(t.rows?.[0]?.cells?.[0]?.innerText)==='基本资料'); const funds=[...document.querySelectorAll('table')].find(t=>clean(t.rows?.[0]?.cells?.[0]?.innerText)==='期货期权账户资金状况'); if(!basic||!funds) return 'WAIT'; let tradeMonth=''; for(const row of [...basic.rows]){ const cells=[...row.cells].map(c=>clean(c.innerText)); for(let i=0;i<cells.length-1;i++){ if(cells[i]==='交易月份') tradeMonth=cells[i+1]; } } if(tradeMonth!==target) return 'WAIT:'+tradeMonth; const lines=[]; for(const row of [...funds.rows].slice(1)){ const cells=[...row.cells].map(c=>clean(c.innerText)); if(cells[0]&&cells[1]) lines.push([tradeMonth,cells[0],cells[1]].map(qq).join(',')); if(cells[2]&&cells[3]) lines.push([tradeMonth,cells[2],cells[3]].map(qq).join(',')); } return lines.join('\n');})()")" || true
>>>>
```

- [ ] **Step 2: Commit changes**

```bash
git add download_futures_account_status.sh
git commit -m "fix: generate standard CSV format with real newlines and clean metric names"
```

### Task 2: Revert Workarounds in `app.py`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Simplify `load_report`**

Remove the `replace("\\n", "\n")` hack and the manual `io.StringIO` wrapping.

```python
@st.cache_data
def load_report(csv_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(csv_path)

    # Clean up column names and string data
    raw.columns = [c.strip() for c in raw.columns]
    # Keep the whitespace cleanup for safety, but it should be redundant now
    raw["指标"] = raw["指标"].astype(str).str.replace(r"\s+", "", regex=True)

    raw["数值"] = raw["值"].map(parse_numeric)
    # ... rest of function ...
```

- [ ] **Step 2: Remove unused `import io`**

- [ ] **Step 3: Commit changes**

```bash
git add app.py
git commit -m "refactor: simplify CSV loading after script fix"
```
