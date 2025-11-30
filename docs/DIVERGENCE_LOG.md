# Divergence Log

This file tracks all modifications made to the core `edgar/` library code that deviate from the original `edgartools` v4.0.0 base.

## 2025-11-30: SEC Filing Enrichment Fixes

### 1. Fix Date Type Checking in `fetch_recent_filings`
-   **File**: `edgar/sec_filings.py`
-   **Change**: Updated `fetch_recent_filings` to handle `datetime.date` objects returned by the underlying library.
-   **Reason**: The original code strictly checked for `datetime.datetime`, causing valid filings to be skipped.
-   **Status**: Custom fix (Upstream status unknown).

### 2. Increase Lookback Period for Alerts
-   **File**: `edgar/filing_context_appender.py`
-   **Change**: Increased default `days_back` from 2 to 90 in `enrich_all_alerts_with_filings` and `safe_enrich_all_alerts`.
-   **Reason**: A 2-day lookback is insufficient for a weekly pipeline; 90 days ensures quarterly (10-Q) and annual (10-K) filings are captured.
-   **Status**: Custom configuration change.

### 3. Architectural Refactoring (2025-11-30)
-   **Change**: Moved custom application logic out of `edgar/` and into `pipeline/`.
-   **Files Moved**:
    -   `edgar/filing_context_appender.py` -> `pipeline/enrichment.py`
    -   `edgar/filing_scorer.py` -> `pipeline/scoring.py`
    -   `edgar/filing_summarizer.py` -> `pipeline/summarizer.py`
    -   `edgar/polygon.py` -> `pipeline/polygon.py`
    -   `edgar/financial_analyzer.py` -> `pipeline/financial_analyzer.py`
    -   `edgar/sec_filings.py` -> `pipeline/sec_filings.py`
-   **Impact**: `edgar/` directory now contains only core library code (plus the `sec_filings.py` fix which is now in `pipeline/` but was originally a library file).
    -   *Note*: `sec_filings.py` was moved to `pipeline/` to keep all custom/modified code together, even though it started as a library file. This means `edgar/` is now effectively pristine upstream code (minus the missing `sec_filings.py`).
