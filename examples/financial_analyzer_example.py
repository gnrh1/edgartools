#!/usr/bin/env python3
"""
Example usage of edgar.financial_analyzer module

This script demonstrates how to extract ROIC, calculate WACC, and analyze
the ROIC-WACC spread for portfolio stocks.
"""

from edgar.core import set_identity
from edgar.financial_analyzer import (
    extract_roic_history,
    extract_wacc_components,
    calculate_wacc,
    calculate_spread,
)


def example_basic_usage():
    """Basic usage example"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Set SEC User-Agent (required)
    set_identity("Example User example@example.com")
    
    ticker = 'AAPL'
    
    # Extract ROIC history
    print(f"\n1. ROIC History for {ticker}:")
    roic_data = extract_roic_history(ticker, years=3)
    
    for year, roic in zip(roic_data.years, roic_data.roic_values):
        print(f"   {year}: {roic:.2%}")
    
    # Calculate WACC
    print(f"\n2. WACC for {ticker}:")
    wacc_result = calculate_wacc(ticker)
    print(f"   {wacc_result.baseline_wacc:.2%}")
    
    # Calculate spread
    print(f"\n3. Spread Analysis for {ticker}:")
    spread = calculate_spread(ticker, years=3)
    print(f"   Current Spread: {spread.current_spread:.2%}")
    print(f"   Trend: {spread.spread_trend}")
    print(f"   Durability: {spread.durability_assessment}")


def example_custom_parameters():
    """Example with custom WACC parameters"""
    print("\n" + "=" * 60)
    print("Example 2: Custom WACC Parameters")
    print("=" * 60)
    
    ticker = 'MSFT'
    
    # Calculate WACC with custom beta and risk-free rate
    print(f"\nWACC for {ticker} with custom parameters:")
    
    wacc_result = calculate_wacc(
        ticker,
        overrides={
            'risk_free_rate': 0.045,  # 4.5% Treasury rate
            'beta': 1.2,              # Higher beta than default
            'market_risk_premium': 0.06  # 6% market risk premium
        }
    )
    
    print(f"   WACC: {wacc_result.baseline_wacc:.2%}")
    print(f"   Cost of Equity: {wacc_result.components_breakdown.cost_of_equity:.2%}")
    print(f"   Cost of Debt: {wacc_result.components_breakdown.cost_of_debt:.2%}")


def example_sensitivity_analysis():
    """Example with WACC sensitivity analysis"""
    print("\n" + "=" * 60)
    print("Example 3: WACC Sensitivity Analysis")
    print("=" * 60)
    
    ticker = 'GOOGL'
    
    # Calculate WACC with sensitivity scenarios
    print(f"\nWACC Sensitivity for {ticker}:")
    
    wacc_result = calculate_wacc(ticker, sensitivity=True)
    
    print(f"   Optimistic:  {wacc_result.scenarios['optimistic']:.2%}")
    print(f"   Base:        {wacc_result.scenarios['base']:.2%}")
    print(f"   Pessimistic: {wacc_result.scenarios['pessimistic']:.2%}")


def example_portfolio_analysis():
    """Example analyzing multiple stocks"""
    print("\n" + "=" * 60)
    print("Example 4: Portfolio Analysis")
    print("=" * 60)
    
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    
    print("\nSpread Analysis for Portfolio:")
    print(f"{'Ticker':<10} {'ROIC':<10} {'WACC':<10} {'Spread':<10} {'Durability':<15}")
    print("-" * 60)
    
    for ticker in tickers:
        try:
            spread = calculate_spread(ticker, years=3)
            roic = spread.roic_data.roic_values[-1]
            wacc = spread.wacc_result.baseline_wacc
            
            print(f"{ticker:<10} {roic:<10.2%} {wacc:<10.2%} {spread.current_spread:<10.2%} {spread.durability_assessment:<15}")
        except Exception as e:
            print(f"{ticker:<10} Error: {e}")


def example_detailed_components():
    """Example showing detailed WACC components"""
    print("\n" + "=" * 60)
    print("Example 5: Detailed WACC Components")
    print("=" * 60)
    
    ticker = 'AAPL'
    
    print(f"\nDetailed WACC breakdown for {ticker}:")
    
    components = extract_wacc_components(ticker)
    
    print(f"\n  Cost of Capital:")
    print(f"    Cost of Equity:    {components.cost_of_equity:.2%}")
    print(f"    Cost of Debt:      {components.cost_of_debt:.2%}")
    print(f"    After-tax CoD:     {components.cost_of_debt * (1 - components.tax_rate):.2%}")
    
    print(f"\n  Capital Structure:")
    print(f"    Equity:            ${components.total_equity/1e9:.1f}B ({components.equity_ratio:.1%})")
    print(f"    Debt:              ${components.total_debt/1e9:.1f}B ({components.debt_ratio:.1%})")
    print(f"    Total:             ${(components.total_equity + components.total_debt)/1e9:.1f}B")
    
    print(f"\n  CAPM Inputs:")
    print(f"    Risk-free rate:    {components.risk_free_rate:.2%}")
    print(f"    Beta:              {components.beta:.2f}")
    print(f"    Market premium:    {components.market_risk_premium:.2%}")
    
    print(f"\n  Tax:")
    print(f"    Tax rate:          {components.tax_rate:.2%}")


def example_trend_analysis():
    """Example analyzing ROIC and spread trends"""
    print("\n" + "=" * 60)
    print("Example 6: Trend Analysis")
    print("=" * 60)
    
    ticker = 'AAPL'
    
    print(f"\nROIC and Spread trends for {ticker}:")
    
    spread = calculate_spread(ticker, years=5)
    
    print(f"\n{'Year':<10} {'ROIC':<10} {'WACC':<10} {'Spread':<10}")
    print("-" * 40)
    
    wacc = spread.wacc_result.baseline_wacc
    
    for year, roic, spread_val in zip(
        spread.years,
        spread.roic_data.roic_values,
        spread.spread_history
    ):
        print(f"{year:<10} {roic:<10.2%} {wacc:<10.2%} {spread_val:<10.2%}")
    
    print(f"\nTrend: {spread.spread_trend}")
    print(f"Assessment: {spread.durability_assessment}")
    
    # Calculate CAGR
    if len(spread.spread_history) >= 2:
        years_span = len(spread.spread_history) - 1
        spread_cagr = (spread.spread_history[-1] / max(spread.spread_history[0], 0.001)) ** (1/years_span) - 1
        print(f"Spread CAGR: {spread_cagr:.2%}")


def main():
    """Run all examples"""
    try:
        # Basic usage
        example_basic_usage()
        
        # Custom parameters
        example_custom_parameters()
        
        # Sensitivity analysis
        example_sensitivity_analysis()
        
        # Portfolio analysis
        example_portfolio_analysis()
        
        # Detailed components
        example_detailed_components()
        
        # Trend analysis
        example_trend_analysis()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
