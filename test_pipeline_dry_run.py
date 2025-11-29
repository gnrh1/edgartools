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
    
    # Import validation function
    sys.path.insert(0, str(Path(__file__).parent))
    from run_pipeline import validate_outputs
    
    # Check that current data files are valid
    result = validate_outputs()
    
    if result:
        print("✅ Output validation passed")
        return True
    else:
        print("❌ Output validation failed")
        return False


def test_polygon_functions():
    """Test that polygon module functions are accessible."""
    print("\nTesting polygon module functions...")
    
    try:
        from edgar.polygon import (
            fetch_aapl_prices,
            fetch_aapl_last_7_days,
            get_prices_state,
            save_prices_state,
            detect_price_drop_alert,
            get_alerts_path,
            save_alerts,
            PolygonAPIError
        )
        print("✅ All polygon module functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import polygon functions: {e}")
        return False


def test_data_files_structure():
    """Test that data files have correct structure."""
    print("\nTesting data files structure...")
    
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    
    # Test prices_state.json
    prices_path = data_dir / "prices_state.json"
    if not prices_path.exists():
        print(f"❌ {prices_path} does not exist")
        return False
    
    with open(prices_path, 'r') as f:
        prices_data = json.load(f)
    
    required_fields = ['timestamp', 'prices', 'last_fetch_timestamp']
    for field in required_fields:
        if field not in prices_data:
            print(f"❌ prices_state.json missing field: {field}")
            return False
    
    print(f"✅ prices_state.json structure valid ({len(prices_data['prices'])} prices)")
    
    # Test alerts.json
    alerts_path = data_dir / "alerts.json"
    if not alerts_path.exists():
        print(f"❌ {alerts_path} does not exist")
        return False
    
    with open(alerts_path, 'r') as f:
        alerts_data = json.load(f)
    
    required_fields = ['alert_triggered', 'price_first_close', 'price_last_close', 'drop_percentage', 'reason']
    for field in required_fields:
        if field not in alerts_data:
            print(f"❌ alerts.json missing field: {field}")
            return False
    
    print(f"✅ alerts.json structure valid (alert_triggered={alerts_data['alert_triggered']})")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("PIPELINE DRY-RUN TEST")
    print("=" * 60)
    
    tests = [
        test_polygon_functions,
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
