#!/usr/bin/env python3
"""
Quick verification script for financial_analyzer module.

This script performs basic smoke tests to ensure the module is working correctly.
"""

import sys
from pathlib import Path

# Ensure module can be imported
try:
    from edgar.financial_analyzer import (
        extract_roic_history,
        extract_wacc_components,
        calculate_wacc,
        calculate_spread,
        ROICData,
        WACCComponents,
        WACCResult,
        SpreadResult,
        FinancialDataError,
        InsufficientDataError,
        DEFAULT_RISK_FREE_RATE,
        DEFAULT_MARKET_RISK_PREMIUM,
        DEFAULT_BETA,
    )
    print("✓ Module imports successfully")
except ImportError as e:
    print(f"✗ Failed to import module: {e}")
    sys.exit(1)

# Verify constants
print("\n=== Constants ===")
print(f"Default Risk-Free Rate: {DEFAULT_RISK_FREE_RATE:.2%}")
print(f"Default Market Risk Premium: {DEFAULT_MARKET_RISK_PREMIUM:.2%}")
print(f"Default Beta: {DEFAULT_BETA}")

# Verify data classes can be instantiated
print("\n=== Data Classes ===")

try:
    roic = ROICData(
        years=[2021, 2022, 2023],
        roic_values=[0.18, 0.19, 0.20],
        nopat_values=[100000, 110000, 120000],
        invested_capital_values=[555556, 578947, 600000]
    )
    print(f"✓ ROICData: {len(roic.years)} years")
    
    components = WACCComponents(
        cost_of_equity=0.095,
        cost_of_debt=0.04,
        tax_rate=0.21,
        debt_ratio=0.30,
        equity_ratio=0.70,
        total_debt=100000000,
        total_equity=200000000,
        risk_free_rate=0.04,
        beta=1.0,
        market_risk_premium=0.055
    )
    print(f"✓ WACCComponents: CoE={components.cost_of_equity:.2%}, CoD={components.cost_of_debt:.2%}")
    
    wacc_result = WACCResult(
        baseline_wacc=0.0815,
        scenarios={'base': 0.0815},
        components_breakdown=components
    )
    print(f"✓ WACCResult: WACC={wacc_result.baseline_wacc:.2%}")
    
    spread_result = SpreadResult(
        current_spread=0.12,
        spread_history=[0.10, 0.11, 0.12],
        years=[2021, 2022, 2023],
        spread_trend='improving',
        durability_assessment='strong',
        roic_data=roic,
        wacc_result=wacc_result
    )
    print(f"✓ SpreadResult: Spread={spread_result.current_spread:.2%}, Trend={spread_result.spread_trend}")
    
except Exception as e:
    print(f"✗ Data class instantiation failed: {e}")
    sys.exit(1)

# Verify serialization
print("\n=== Serialization ===")

try:
    roic_dict = roic.to_dict()
    assert 'years' in roic_dict
    assert 'roic_values' in roic_dict
    print("✓ ROICData.to_dict() works")
    
    components_dict = components.to_dict()
    assert 'cost_of_equity' in components_dict
    assert 'debt_ratio' in components_dict
    print("✓ WACCComponents.to_dict() works")
    
    wacc_dict = wacc_result.to_dict()
    assert 'baseline_wacc' in wacc_dict
    assert 'scenarios' in wacc_dict
    print("✓ WACCResult.to_dict() works")
    
    spread_dict = spread_result.to_dict()
    assert 'current_spread' in spread_dict
    assert 'spread_trend' in spread_dict
    print("✓ SpreadResult.to_dict() works")
    
except Exception as e:
    print(f"✗ Serialization failed: {e}")
    sys.exit(1)

# Verify exception classes
print("\n=== Exception Classes ===")

try:
    try:
        raise FinancialDataError("Test error")
    except FinancialDataError:
        print("✓ FinancialDataError works")
    
    try:
        raise InsufficientDataError("Test error")
    except InsufficientDataError:
        print("✓ InsufficientDataError works")
    
except Exception as e:
    print(f"✗ Exception handling failed: {e}")
    sys.exit(1)

# Verify cache path generation
print("\n=== Cache System ===")

try:
    from edgar.financial_analyzer import get_cache_path
    
    cache_path = get_cache_path('AAPL')
    assert 'financial_cache_AAPL.json' in str(cache_path)
    assert cache_path.parent.name == 'data'
    print(f"✓ Cache path: {cache_path.name}")
    
except Exception as e:
    print(f"✗ Cache system failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 60)
print("✓ ALL VERIFICATION CHECKS PASSED")
print("=" * 60)
print("\nThe financial_analyzer module is correctly installed and configured.")
print("To run full tests: pytest tests/test_financial_analyzer.py -v")
print("To run integration tests: python test_financial_analyzer_integration.py")
print("To see examples: python examples/financial_analyzer_example.py")

sys.exit(0)
