# Futures Automation Update - Design Document

Update the futures account status download script to support dynamic end dates and automatic navigation to the target inquiry page.

## 1. Problem Statement
The current script `download_futures_account_status.sh` uses hardcoded dates and requires the user to manually navigate to the correct page in Chrome before running. This limits automation and requires manual intervention for monthly reports.

## 2. Requirements
- **Dynamic End Date**: Default to the month before the current date (e.g., if current is April, default is March).
- **Auto-Navigation**: Automatically navigate to the target inquiry page if it's not already open in the active tab.
- **Maintain Flexibility**: Allow overriding dates via command-line arguments.

## 3. Proposed Solution

### 3.1 Dynamic Date Calculation
Use the macOS `date` command to calculate the default end month.
- `DEFAULT_END=$(date -v-1m +%Y-%m)`
- Update variable assignments:
  ```bash
  START_MONTH="${1:-2024-09}"
  END_MONTH="${2:-$DEFAULT_END}"
  ```

### 3.2 Automatic Navigation
Inject JavaScript into the active tab to check the URL and navigate if necessary.
- Target URL: `https://investorservice.cfmmc.com/customer/setupViewCustomerMonthDataFromCompanyAuto.do`
- Logic:
  1. Check `window.location.href`.
  2. If it doesn't match the target, set `window.location.href = target`.
  3. Return a status like `"NAVIGATING"`.
  4. In the shell script, wait for the page to load (indicated by the presence of the `tradeDate` select element).

### 3.3 Robustness & Feedback
- The `OUTFILE` path will automatically reflect the calculated dates.
- Add a check to ensure the page is fully loaded before attempting to interact with elements.

## 4. Implementation Plan (High Level)
1. Update `download_futures_account_status.sh` with the new date logic.
2. Refactor the navigation and loading check into a reusable function or initial step.
3. Update the `chrome_js` calls to handle navigation and wait states.
4. Verify by running the script with and without arguments.

## 5. Verification Plan
- **Test 1**: Run without arguments. Verify `END_MONTH` is last month and output filename is correct.
- **Test 2**: Run on a different website (e.g., google.com). Verify it redirects to the cfmmc.com page.
- **Test 3**: Run with explicit arguments. Verify the arguments override defaults.
