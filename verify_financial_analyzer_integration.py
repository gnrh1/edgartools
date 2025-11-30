#!/usr/bin/env python3
"""
Integration test for financial_analyzer module with real SEC data.

This script tests the financial analyzer against real 10-K filings
for Apple, Microsoft, and Google to verify ROIC, WACC, and spread calculations.

Usage:
    python test_financial_analyzer_integration.py

Note: Requires SEC User-Agent to be set and internet connectivity.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from edgar.core import set_identity, get_identity
from pipeline.financial_analyzer import (
    extract_roic_history,
    extract_wacc_components,
    calculate_wacc,
    calculate_spread,
    FinancialDataError,
    InsufficientDataError,
)


def test_ticker(ticker: str, years: int = 3):
    """Test financial analysis for a ticker"""
    print(f"\n{'='*60}")
    print(f"Testing {ticker}")
    print(f"{'='*60}")
    
    try:
        # Test ROIC extraction
        print(f"\n1. Extracting ROIC history ({years} years)...")
        roic_data = extract_roic_history(ticker, years=years)
        
        print(f"   ✓ ROIC Data:")
        for year, roic, nopat, ic in zip(
            roic_data.years,
            roic_data.roic_values,
            roic_data.nopat_values,
            roic_data.invested_capital_values
        ):
            print(f"     {year}: ROIC={roic:6.2%}, NOPAT=${nopat/1e9:,.1f}B, IC=${ic/1e9:,.1f}B")
        
        # Test WACC components
        print(f"\n2. Extracting WACC components...")
        wacc_components = extract_wacc_components(ticker)
        
        print(f"   ✓ WACC Components:")
        print(f"     Cost of Equity: {wacc_components.cost_of_equity:6.2%}")
        print(f"     Cost of Debt:   {wacc_components.cost_of_debt:6.2%}")
        print(f"     Tax Rate:       {wacc_components.tax_rate:6.2%}")
        print(f"     Equity Ratio:   {wacc_components.equity_ratio:6.2%}")
        print(f"     Debt Ratio:     {wacc_components.debt_ratio:6.2%}")
        print(f"     Total Equity:   ${wacc_components.total_equity/1e9:,.1f}B")
        print(f"     Total Debt:     ${wacc_components.total_debt/1e9:,.1f}B")
        print(f"     Beta:           {wacc_components.beta:.2f}")
        
        # Test WACC calculation
        print(f"\n3. Calculating WACC (with sensitivity)...")
        wacc_result = calculate_wacc(ticker, sensitivity=True)
        
        print(f"   ✓ WACC Results:")
        print(f"     Baseline:     {wacc_result.baseline_wacc:6.2%}")
        print(f"     Optimistic:   {wacc_result.scenarios['optimistic']:6.2%}")
        print(f"     Pessimistic:  {wacc_result.scenarios['pessimistic']:6.2%}")
        
        # Test spread calculation
        print(f"\n4. Calculating ROIC-WACC spread...")
        spread_result = calculate_spread(ticker, years=years)
        
        print(f"   ✓ Spread Analysis:")
        print(f"     Current Spread:  {spread_result.current_spread:6.2%}")
        print(f"     Trend:           {spread_result.spread_trend}")
        print(f"     Durability:      {spread_result.durability_assessment}")
        print(f"     Spread History:")
        for year, spread in zip(spread_result.years, spread_result.spread_history):
            print(f"       {year}: {spread:6.2%}")
        
        print(f"\n   ✓ All tests passed for {ticker}!")
        return True
        
    except InsufficientDataError as e:
        print(f"\n   ✗ Insufficient data error: {e}")
        return False
    except FinancialDataError as e:
        print(f"\n   ✗ Financial data error: {e}")
        return False
    except Exception as e:
        print(f"\n   ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_results(ticker: str, spread_result):
    """Validate that results are reasonable"""
    print(f"\n5. Validating {ticker} results...")
    
    issues = []
    
    # Check ROIC is reasonable (typically 5-50% for good companies)
    current_roic = spread_result.roic_data.roic_values[-1]
    if current_roic < -0.5 or current_roic > 1.0:
        issues.append(f"ROIC {current_roic:.2%} is outside reasonable range")
    
    # Check WACC is reasonable (typically 5-15% for large tech companies)
    wacc = spread_result.wacc_result.baseline_wacc
    if wacc < 0.03 or wacc > 0.25:
        issues.append(f"WACC {wacc:.2%} is outside reasonable range")
    
    # Check spread is calculated correctly
    expected_spread = current_roic - wacc
    if abs(spread_result.current_spread - expected_spread) > 0.001:
        issues.append(f"Spread calculation mismatch: {spread_result.current_spread:.2%} vs {expected_spread:.2%}")
    
    # Check capital structure sums to 100%
    components = spread_result.wacc_result.components_breakdown
    capital_sum = components.equity_ratio + components.debt_ratio
    if abs(capital_sum - 1.0) > 0.01:
        issues.append(f"Capital structure doesn't sum to 100%: {capital_sum:.2%}")
    
    if issues:
        print(f"   ⚠ Validation issues found:")
        for issue in issues:
            print(f"     - {issue}")
        return False
    else:
        print(f"   ✓ All validation checks passed")
        return True


def main():
    """Run integration tests"""
    print("=" * 60)
    print("Financial Analyzer Integration Test")
    print("=" * 60)
    
    # Set SEC identity if not already set
    if not get_identity():
        import os
        identity = os.environ.get("EDGAR_IDENTITY")
        if identity:
            set_identity(identity)
        else:
            print("\nWarning: EDGAR_IDENTITY not set. Using placeholder...")
            set_identity("Financial Analyzer Integration Test test@example.com")
    
    print(f"Using SEC User-Agent: {get_identity()}")
    
    # Test tickers (major tech companies with good financial data)
    test_tickers = [
        ('AAPL', 3),   # Apple - 3 years
        ('MSFT', 3),   # Microsoft - 3 years
        ('GOOGL', 3),  # Google - 3 years
    ]
    
    results = {}
    
    for ticker, years in test_tickers:
        success = test_ticker(ticker, years)
        results[ticker] = success
    
    # Detailed validation for Apple (as reference case)
    print(f"\n{'='*60}")
    print("Detailed Validation (Apple as reference)")
    print(f"{'='*60}")
    
    try:
        spread_result = calculate_spread('AAPL', years=3)
        validation_passed = validate_results('AAPL', spread_result)
        results['AAPL_validation'] = validation_passed
    except Exception as e:
        print(f"Validation failed: {e}")
        results['AAPL_validation'] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    for ticker, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {ticker:20s} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n{'='*60}")
        print("✓ ALL INTEGRATION TESTS PASSED")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("✗ SOME TESTS FAILED")
        print(f"{'='*60}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
