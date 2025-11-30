# Pipeline Fixes - December 2025

## Issue Summary
Manual weekly workflow run on 2025-11-30 failed with multiple cascading errors:

1. **Price Data Not Being Parsed Correctly**: All prices showed as $0.00 with "insufficient_data" reason
2. **User-Agent Header Not Set**: Company ticker fetches failed with "User-Agent identity is not set" errors

## Root Causes

### Issue 1: Price Data Parsing
- **Root Cause**: Code required minimum of 5 price records, but Thanksgiving holiday (Nov 27) resulted in only 4 trading days
- **Location**: `edgar/polygon.py`, line 478
- **Original Logic**: 
  ```python
  if not isinstance(prices, list) or len(prices) < 5:
      # Return 0.0 values with insufficient_data
  ```

### Issue 2: SEC User-Agent
- **Root Cause**: `run_pipeline.py` never called `set_identity()` before using edgartools `Company` class
- **Location**: `run_pipeline.py`, main function
- **Impact**: All SEC filing enrichment tasks failed because API requires User-Agent header

## Solutions Implemented

### Fix 1: Reduce Minimum Price Requirement (edgar/polygon.py)
**Change**: Reduced minimum required price records from 5 to 2

**Rationale**: 
- We only need 2 data points (first and last) to calculate a price drop percentage
- Requirement of 5 was too strict and failed during holiday weeks
- New threshold is more flexible while still providing meaningful price analysis

**Code Changes**:
```python
# Before
if not isinstance(prices, list) or len(prices) < 5:
    reason = "insufficient_data"
    log.warning(f"Insufficient price data: {len(prices)} points (minimum 5 required)")

# After  
if not isinstance(prices, list) or len(prices) < 2:
    reason = "insufficient_data"
    log.warning(f"Insufficient price data: {len(prices)} points (minimum 2 required)")
```

**Additional Changes**:
- Updated docstring in `fetch_last_5_working_days_prices()` to document that fewer than 5 records may be returned
- Updated test `test_detect_price_drop_alert_insufficient_data` to test with 1 record instead of 3

### Fix 2: Set SEC User-Agent Identity (run_pipeline.py)
**Change**: Added `set_identity()` call at pipeline startup

**Code Changes**:
```python
def main() -> int:
    """Main pipeline execution."""
    log("=" * 60)
    log("MULTI-STOCK PRICE MONITORING PIPELINE")
    log("=" * 60)
    log(f"Start time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Step 0a: Set SEC User-Agent identity (required for SEC API access)
    from edgar import set_identity, get_identity
    identity = get_identity()
    set_identity(identity)
    log(f"SEC User-Agent set to: {identity}")
    
    # Step 0b: Load config
    # ... rest of pipeline
```

**Rationale**:
- SEC requires User-Agent header on all API requests
- `get_identity()` already returns the correct identity string
- We just needed to call `set_identity()` to register it with edgartools before any SEC API calls

## Testing

### Unit Tests
All existing tests pass:
- **test_polygon.py**: 31/31 tests pass
- **test_multi_ticker.py**: 19/19 tests pass

### Integration Testing
Created `test_pipeline_integration.py` to verify:
1. Config loading works
2. Price analysis works with < 5 records
3. SEC Company instantiation works with User-Agent set
4. Output file validation passes

### Manual Verification
```bash
# Test price analysis with existing data
python3 -c "from edgar.polygon import detect_price_drop_alert; \
            alert = detect_price_drop_alert('AAPL'); \
            print(f'AAPL: \${alert[\"price_first_close\"]:.2f} -> \${alert[\"price_last_close\"]:.2f}')"
# Output: AAPL: $275.92 -> $278.85 (real prices, not 0.00)

# Test SEC Company instantiation
python3 -c "from edgar import set_identity, get_identity; \
            from edgar.entity import Company; \
            set_identity(get_identity()); \
            c = Company('AAPL'); \
            print(c.name)"
# Output: Apple Inc. (no User-Agent error)
```

## Impact Assessment

### Positive Impacts
- Pipeline now handles market holidays gracefully
- SEC filing enrichment can proceed without User-Agent errors
- More robust against varying numbers of trading days

### Backward Compatibility
- All existing functionality maintained
- Tests updated to reflect new minimum requirement
- No breaking changes to API or data structures

### Potential Issues
- None identified. The relaxed requirement (2 instead of 5) is strictly more permissive
- If only 1 record is available, still returns insufficient_data as expected

## Files Modified

1. **edgar/polygon.py**
   - Line 478: Changed minimum requirement from 5 to 2
   - Line 84-86: Updated docstring to document behavior

2. **run_pipeline.py**
   - Lines 337-341: Added set_identity() call at pipeline startup

3. **tests/test_polygon.py**
   - Lines 262-284: Updated test to use 1 record instead of 3

## Verification Checklist

- [x] Both root causes identified and fixed
- [x] All unit tests pass (50/50)
- [x] Integration tests pass
- [x] Manual testing confirms fixes work
- [x] Documentation updated
- [x] No backward compatibility issues
- [x] Code follows existing patterns and style

## Next Steps

1. Run full pipeline with real API keys to verify end-to-end functionality
2. Monitor next scheduled run for any issues
3. Consider adding alerting if price data is consistently < 2 records
