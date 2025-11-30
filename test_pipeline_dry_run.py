#!/usr/bin/env python3
"""
Dry-run test for pipeline script to verify functionality without API calls.
"""

import json
import sys
from pathlib import Path


def test_output_validation():
    """Test that the validation logic works correctly."""
    print("Testing output validation...")
    
    # Import validation function and config loader
    sys.path.insert(0, str(Path(__file__).parent))
    from run_pipeline import validate_outputs
    from config.config_loader import load_tickers_config
    
    try:
        # Load tickers from config
        tickers = load_tickers_config()
        print(f"Loaded {len(tickers)} tickers: {', '.join(tickers)}")
        
        # Check that current data files are valid
        result = validate_outputs(tickers)
        
        if result:
            print("✅ Output validation passed")
            return True
        else:
            print("❌ Output validation failed")
            return False
    except Exception as e:
        print(f"❌ Output validation test failed: {e}")
        return False


def test_polygon_functions():
    """Test that polygon module functions are accessible."""
    print("\nTesting polygon module functions...")
    
    try:
        from pipeline.polygon import (
            fetch_last_5_working_days_prices,
            detect_price_drop_alert,
            get_prices_state_path,
            get_alerts_path,
            PolygonAPIError
        )
        print("✅ All polygon module functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import polygon functions: {e}")
        return False


def test_phase3_functions():
    """Test that Phase 3 SEC filing functions are accessible."""
    print("\nTesting Phase 3 SEC filing functions...")
    
    try:
        from edgar.sec_filings import fetch_recent_filings, FilingError
        from edgar.filing_scorer import rank_filings_by_relevance, get_top_n_relevant_filings
        from edgar.filing_summarizer import create_filing_summary, extract_key_points
        from edgar.filing_context_appender import (
            append_filing_context_to_alert, 
            enrich_all_alerts_with_filings,
            safe_enrich_all_alerts,
            get_filing_context_from_alert
        )
        print("✅ All Phase 3 SEC filing functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Phase 3 functions: {e}")
        return False


def test_data_files_structure():
    """Test that data files have correct structure."""
    print("\nTesting data files structure...")
    
    # Import config loader
    sys.path.insert(0, str(Path(__file__).parent))
    from config.config_loader import load_tickers_config
    from edgar.polygon import get_prices_state_path, get_alerts_path
    
    try:
        # Load tickers from config
        tickers = load_tickers_config()
        
        script_dir = Path(__file__).parent
        
        for ticker in tickers:
            print(f"\n  Testing {ticker} files...")
            
            # Test prices_{ticker}.json
            prices_path = get_prices_state_path(ticker)
            if not prices_path.exists():
                print(f"❌ {prices_path} does not exist")
                return False
            
            with open(prices_path, 'r') as f:
                prices_data = json.load(f)
            
            required_fields = ['timestamp', 'prices', 'last_fetch_timestamp']
            for field in required_fields:
                if field not in prices_data:
                    print(f"❌ prices_{ticker}.json missing field: {field}")
                    return False
            
            print(f"  ✅ prices_{ticker}.json structure valid ({len(prices_data['prices'])} prices)")
            
            # Test alerts_{ticker}.json
            alerts_path = get_alerts_path(ticker)
            if not alerts_path.exists():
                print(f"❌ {alerts_path} does not exist")
                return False
            
            with open(alerts_path, 'r') as f:
                alerts_data = json.load(f)
            
            required_fields = ['alert_triggered', 'price_first_close', 'price_last_close', 'drop_percentage', 'reason']
            for field in required_fields:
                if field not in alerts_data:
                    print(f"❌ alerts_{ticker}.json missing field: {field}")
                    return False
            
            # Check for Phase 3 filing_context field
            if 'filing_context' in alerts_data:
                context = alerts_data['filing_context']
                if isinstance(context, list):
                    print(f"  ✅ alerts_{ticker}.json structure valid (alert_triggered={alerts_data['alert_triggered']}, filing_context={len(context)} items)")
                else:
                    print(f"  ❌ alerts_{ticker}.json filing_context is not a list")
                    return False
            else:
                print(f"  ✅ alerts_{ticker}.json structure valid (alert_triggered={alerts_data['alert_triggered']}, no filing_context yet)")
        
        return True
        
    except Exception as e:
        print(f"❌ Data files structure test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("PIPELINE DRY-RUN TEST (WITH PHASE 3)")
    print("=" * 60)
    
    tests = [
        test_polygon_functions,
        test_phase3_functions,
        test_data_files_structure,
        test_output_validation
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
