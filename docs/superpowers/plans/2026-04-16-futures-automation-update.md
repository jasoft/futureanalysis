# Futures Automation Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `download_futures_account_status.sh` to support dynamic end dates (last month by default) and automatic navigation to the inquiry page.

**Architecture:** Use macOS `date` command for date calculation and inject enhanced JavaScript via `osascript` to handle navigation and page state verification.

**Tech Stack:** Bash, AppleScript, JavaScript (for Chrome automation).

---

### Task 1: Update Date Logic

**Files:**
- Modify: `download_futures_account_status.sh`

- [ ] **Step 1: Replace hardcoded dates with dynamic calculation**

```bash
# Old:
# START_MONTH="${1:-2024-09}"
# END_MONTH="${2:-2026-02}"

# New:
DEFAULT_END=$(date -v-1m +%Y-%m)
START_MONTH="${1:-2024-09}"
END_MONTH="${2:-$DEFAULT_END}"
```

- [ ] **Step 2: Verify date calculation**

Run: `date -v-1m +%Y-%m` (locally in terminal)
Expected: Output matches current year and previous month.

- [ ] **Step 3: Commit**

```bash
git add download_futures_account_status.sh
git commit -m "feat: use dynamic end date by default"
```

---

### Task 2: Implement Auto-Navigation and Wait Logic

**Files:**
- Modify: `download_futures_account_status.sh`

- [ ] **Step 1: Update `wait_for_month_data` to handle navigation**

Modify the JavaScript inside `chrome_js` call in `wait_for_month_data` to check URL.

```javascript
// Add to start of JS in wait_for_month_data:
const TARGET_URL = 'https://investorservice.cfmmc.com/customer/setupViewCustomerMonthDataFromCompanyAuto.do';
if (!window.location.href.includes('setupViewCustomerMonthDataFromCompanyAuto.do')) {
    window.location.href = TARGET_URL;
    return 'NAVIGATING';
}
// Check if select element exists
if (!document.querySelector('select[name="tradeDate"]')) return 'WAIT:LOADING';
```

- [ ] **Step 2: Update the main loop JS injection**

Ensure the submit action also handles navigation check.

```bash
# Update the JS in the while loop:
chrome_js "(()=>{
  const TARGET_URL = 'https://investorservice.cfmmc.com/customer/setupViewCustomerMonthDataFromCompanyAuto.do';
  if (!window.location.href.includes('setupViewCustomerMonthDataFromCompanyAuto.do')) {
    window.location.href = TARGET_URL;
    return 'NAVIGATING';
  }
  const target='${month}'; 
  const s=document.querySelector('select[name=\"tradeDate\"]'); 
  if(!s) return 'WAIT:LOADING'; 
  // ... rest of existing logic ...
})()"
```

- [ ] **Step 3: Verify navigation**

1. Open Chrome to a different page (e.g., google.com).
2. Run script (dry run or limited range).
3. Verify tab redirects to CFMMC.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat: add automatic navigation to target page"
```

---

### Task 3: Final Integration and CSV Filename Cleanup

**Files:**
- Modify: `download_futures_account_status.sh`

- [ ] **Step 1: Ensure `OUTFILE` uses dynamic dates**

The existing code already uses `${START_MONTH}_to_${END_MONTH}`, but verify it picks up the dynamic `END_MONTH`.

- [ ] **Step 2: Add `.superpowers/` to `.gitignore`**

```bash
echo ".superpowers/" >> .gitignore
```

- [ ] **Step 3: Final manual test run**

Run: `./download_futures_account_status.sh`
Verify: Correct filename and automated flow.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: update gitignore and final script polish"
```
