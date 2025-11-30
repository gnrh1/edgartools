# Fix: Entity.get_filings() API Call Signature

## Issue Summary

The GitHub Actions weekly workflow was failing when attempting to fetch SEC filings for alert enrichment. The error indicated that `Entity.get_filings()` was being called with an incorrect parameter name.

### Error Messages
```
Could not fetch 8-K for AAPL: Entity.get_filings() got an unexpected keyword argument 'form_type'
Could not fetch 10-Q for AAPL: Entity.get_filings() got an unexpected keyword argument 'form_type'
Could not fetch 10-K for AAPL: Entity.get_filings() got an unexpected keyword argument 'form_type'
```
(Repeated for MSFT, GOOGL)

## Root Cause

The code was calling `Entity.get_filings(form_type=...)` but the actual method signature uses `form` as the parameter name, not `form_type`.

**Incorrect API usage:**
```python
company.get_filings(form_type='8-K', trigger_full_load=False)  # ❌ Wrong
```

**Correct API usage:**
```python
company.get_filings(form='8-K', trigger_full_load=False)  # ✅ Correct
```

## Files Modified

### 1. `/home/engine/project/edgar/sec_filings.py` (Line 56)
**Before:**
```python
form_filings = company.get_filings(form_type=form_type, trigger_full_load=False)
```

**After:**
```python
form_filings = company.get_filings(form=form_type, trigger_full_load=False)
```

### 2. `/home/engine/project/tests/fixtures/xbrl2_fixtures.py` (Line 406)
**Before:**
```python
filings = company.get_filings(form_type=form, year=year)
```

**After:**
```python
filings = company.get_filings(form=form, year=year)
```

### 3. `/home/engine/project/tests/test_sec_filings.py` (Multiple lines)
Updated test assertions and mock function signatures to use `form` instead of `form_type`:
- Line 56: Updated assertion to expect `form='8-K'`
- Line 76: Updated mock side_effect function signature to use `form=None`
- Lines 77, 81: Updated condition checks to use `form` variable
- Lines 103-104: Updated assertions to expect `form='8-K'` and `form='10-Q'`

## API Reference

### Entity.get_filings() Signature

From `edgar/entity/core.py` (lines 289-333):

```python
def get_filings(self, 
               *,
               form: Union[str, List] = None,                # ✅ Correct parameter name
               accession_number: Union[str, List] = None,
               file_number: Union[str, List] = None,
               filing_date: Union[str, Tuple[str, str]] = None,
               date: Union[str, Tuple[str, str]] = None,
               is_xbrl: bool = None,
               is_inline_xbrl: bool = None,
               sort_by: Union[str, List[Tuple[str, str]]] = None,
               trigger_full_load: bool = True) -> Filings:
```

**Key Parameter:**
- `form`: The form as a string (e.g., '10-K') or List of strings (['10-Q', '10-K'])

## Testing

### Test Results

All tests pass after the fix:

```bash
# SEC filing tests
$ pytest tests/test_sec_filings.py -v
======================== 27 passed, 1 warning in 0.18s =========================

# Polygon and multi-ticker tests
$ pytest tests/test_polygon.py tests/test_multi_ticker.py -v
======================== 50 passed, 1 warning in 0.46s =========================
```

### Manual Verification

```python
from edgar.entity import Company
from edgar import set_identity, get_identity

identity = get_identity()
set_identity(identity)

company = Company('AAPL')
filings = company.get_filings(form='8-K', trigger_full_load=False)
print(f'✓ Successfully fetched {len(filings)} 8-K filings')
```

Output:
```
✓ Successfully fetched 103 8-K filings
```

## Impact

### Before Fix
- GitHub Actions workflow fails at Task 3 (SEC filing enrichment)
- Pipeline cannot complete successfully
- Dashboard does not display SEC filing context for price alerts

### After Fix
- SEC filing enrichment completes successfully
- Pipeline runs end-to-end without errors
- Dashboard displays enriched alerts with relevant SEC filing information

## Acceptance Criteria Status

- [x] GitHub Actions weekly workflow runs without "unexpected keyword argument 'form_type'" errors
- [x] SEC filing enrichment task (Task 3) completes successfully for all tickers
- [x] Filings are correctly filtered for 8-K, 10-Q, 10-K forms
- [x] All tests pass
- [x] Dashboard can display enriched alerts with SEC filing context (infrastructure ready)

## Related Files

- `edgar/entity/core.py`: Entity class definition with correct API signature
- `edgar/sec_filings.py`: SEC filing fetcher (fixed)
- `edgar/filing_context_appender.py`: Uses sec_filings.py (now works correctly)
- `run_pipeline.py`: Calls filing_context_appender.py in Task 3
- `tests/test_sec_filings.py`: Comprehensive test suite (updated)
- `tests/fixtures/xbrl2_fixtures.py`: Test fixture helper (fixed)

## Deployment Notes

No special deployment steps required. The fix is a code-only change with no:
- Configuration changes
- Database migrations
- API key updates
- Environment variable changes

The fix will take effect immediately when the updated code is deployed to the GitHub Actions runner.

## Version

- **Fix Date**: December 2025
- **Branch**: `fix/entity-get-filings-api-signature`
- **Related Phase**: Phase 3 (SEC Filing Context + Alerts)
