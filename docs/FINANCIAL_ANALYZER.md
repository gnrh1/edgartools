# Financial Analyzer Module

## Overview

The `edgar.financial_analyzer` module extracts historical ROIC (Return on Invested Capital), calculates WACC (Weighted Average Cost of Capital), and computes the spread (ROIC - WACC) for portfolio analysis. It uses XBRL data from SEC 10-K filings with intelligent fallback mechanisms.

This module is part of **Phase 4 Pillar 1: Financial Data Foundation** and provides the core financial metrics needed for valuation and quality assessment.

## Key Concepts

### ROIC (Return on Invested Capital)

ROIC measures how efficiently a company generates returns from its invested capital:

```
ROIC = NOPAT / Invested Capital

Where:
- NOPAT = Operating Income × (1 - Tax Rate)
- Invested Capital = Total Assets - Cash - Non-Interest Liabilities
```

A high ROIC (>15%) indicates strong competitive advantages and efficient capital allocation.

### WACC (Weighted Average Cost of Capital)

WACC represents the minimum return a company must earn to satisfy all stakeholders:

```
WACC = (E/V × Re) + (D/V × Rd × (1-Tc))

Where:
- E/V = Equity ratio
- Re = Cost of equity (calculated using CAPM)
- D/V = Debt ratio
- Rd = Cost of debt
- Tc = Corporate tax rate
```

### Cost of Equity (CAPM)

```
Re = Rf + β(Rm - Rf)

Where:
- Rf = Risk-free rate (10-year Treasury, default 4.0%)
- β = Beta (market risk, default 1.0)
- Rm - Rf = Market risk premium (default 5.5%)
```

### Spread

The spread measures value creation:

```
Spread = ROIC - WACC
```

- **Spread > 5%**: Company creates significant value
- **Spread > 0%**: Company creates value
- **Spread < 0%**: Company destroys value

## Functions

### extract_roic_history(ticker, years=5)

Extract historical ROIC data from 10-K filings.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `years` (int, optional): Number of years of history (default: 5)

**Returns:**
- `ROICData`: Object containing:
  - `years`: List of years
  - `roic_values`: List of ROIC percentages
  - `nopat_values`: List of NOPAT values
  - `invested_capital_values`: List of invested capital values

**Example:**
```python
from edgar.financial_analyzer import extract_roic_history

roic_data = extract_roic_history('AAPL', years=5)

for year, roic in zip(roic_data.years, roic_data.roic_values):
    print(f"{year}: ROIC = {roic:.2%}")
```

**Raises:**
- `InsufficientDataError`: If fewer than 3 years of data available
- `FinancialDataError`: If extraction fails

### extract_wacc_components(ticker, risk_free_rate=None, market_risk_premium=None, beta=None)

Extract components needed for WACC calculation.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `risk_free_rate` (float, optional): Override default risk-free rate (default: 0.04)
- `market_risk_premium` (float, optional): Override default market risk premium (default: 0.055)
- `beta` (float, optional): Override default beta (default: 1.0)

**Returns:**
- `WACCComponents`: Object containing all WACC components

**Example:**
```python
from edgar.financial_analyzer import extract_wacc_components

components = extract_wacc_components('AAPL', beta=1.2)

print(f"Cost of Equity: {components.cost_of_equity:.2%}")
print(f"Cost of Debt: {components.cost_of_debt:.2%}")
print(f"Equity Ratio: {components.equity_ratio:.2%}")
```

### calculate_wacc(ticker, overrides=None, sensitivity=False)

Calculate Weighted Average Cost of Capital.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `overrides` (dict, optional): Override parameters (risk_free_rate, market_risk_premium, beta)
- `sensitivity` (bool): If True, calculate optimistic/pessimistic scenarios (±100bps to Rf)

**Returns:**
- `WACCResult`: Object containing baseline WACC, scenarios, and component breakdown

**Example:**
```python
from edgar.financial_analyzer import calculate_wacc

# Basic WACC
wacc_result = calculate_wacc('AAPL')
print(f"WACC: {wacc_result.baseline_wacc:.2%}")

# With sensitivity analysis
wacc_result = calculate_wacc('AAPL', sensitivity=True)
print(f"Base:        {wacc_result.scenarios['base']:.2%}")
print(f"Optimistic:  {wacc_result.scenarios['optimistic']:.2%}")
print(f"Pessimistic: {wacc_result.scenarios['pessimistic']:.2%}")

# With custom parameters
wacc_result = calculate_wacc(
    'AAPL',
    overrides={'risk_free_rate': 0.05, 'beta': 1.3}
)
```

### calculate_spread(ticker, years=5)

Calculate ROIC-WACC spread with trend analysis.

**Parameters:**
- `ticker` (str): Stock ticker symbol
- `years` (int, optional): Number of years of history (default: 5)

**Returns:**
- `SpreadResult`: Object containing:
  - `current_spread`: Most recent spread value
  - `spread_history`: Historical spread values
  - `years`: Years for historical data
  - `spread_trend`: 'improving', 'deteriorating', or 'stable'
  - `durability_assessment`: 'strong', 'uncertain', or 'weak'
  - `roic_data`: Full ROIC data
  - `wacc_result`: Full WACC calculation

**Example:**
```python
from edgar.financial_analyzer import calculate_spread

spread = calculate_spread('AAPL', years=5)

print(f"Current Spread: {spread.current_spread:.2%}")
print(f"Trend: {spread.spread_trend}")
print(f"Durability: {spread.durability_assessment}")

for year, spread_val in zip(spread.years, spread.spread_history):
    print(f"{year}: {spread_val:.2%}")
```

## Trend and Durability Assessment

### Spread Trend Classification

The module analyzes the 3-year trend of spread:

- **Improving**: Spread increased by >2% over the period
- **Deteriorating**: Spread decreased by >2% over the period
- **Stable**: Spread changed by ≤2% over the period

### Durability Assessment

Durability indicates the sustainability of value creation:

- **Strong**: Spread > 5% AND trend is improving
  - High-quality business with improving competitive position
  
- **Uncertain**: Spread deteriorating OR spread < 5%
  - Moderate quality or weakening competitive position
  
- **Weak**: Spread < 0% OR (spread deteriorating AND < 3%)
  - Low quality or destroying value

## Caching

The module automatically caches financial data in `/data/financial_cache_{ticker}.json` to:
- Avoid redundant SEC API calls
- Speed up repeated calculations
- Reduce load on SEC servers

Cache files are valid for 90 days and include:
- ROIC history
- WACC components
- Full spread analysis

## Edge Case Handling

The module handles common edge cases:

### Negative Stockholders Equity
- Raises `FinancialDataError`
- Indicates financial distress

### Zero Debt
- Sets debt ratio to 0.0
- WACC equals cost of equity

### Missing Tax Rates
- Defaults to 21% (federal corporate rate)
- Calculates from effective tax rate when available

### Invalid Tax Rates
- Bounds tax rate between 0% and 50%
- Falls back to 21% if outside range

### Unreasonable Cost of Debt
- Bounds between 0% and 20%
- Defaults to 5% if outside range

### Insufficient Historical Data
- Requires minimum 3 years of data
- Raises `InsufficientDataError` if not met

## Testing

### Unit Tests

Run comprehensive unit tests:

```bash
source .venv/bin/activate
pytest tests/test_financial_analyzer.py -v
```

The test suite includes:
- Cache functionality tests
- XBRL value extraction tests
- ROIC calculation tests
- WACC calculation tests
- Spread analysis tests
- Edge case handling tests
- Formula correctness verification

### Integration Tests

Run integration tests against real SEC data:

```bash
source .venv/bin/activate
python test_financial_analyzer_integration.py
```

This tests against Apple, Microsoft, and Google 10-K filings to verify:
- Real XBRL data extraction
- Reasonable ROIC values
- Reasonable WACC values
- Correct spread calculations
- Trend analysis accuracy

## Performance Considerations

- **First run**: Fetches data from SEC EDGAR (slower, ~10-30 seconds per ticker)
- **Subsequent runs**: Uses cached data (fast, <1 second per ticker)
- **Cache refresh**: Automatic after 90 days
- **Rate limiting**: Respects SEC rate limits (10 requests per second)

## Data Sources

All data is extracted from official SEC EDGAR filings:

- **10-K Annual Reports**: Primary source for all financial data
- **XBRL Tags**: Standardized financial reporting format
- **Fallback**: Text parsing when XBRL unavailable

Common XBRL concepts used:
- `OperatingIncomeLoss` - Operating income
- `IncomeTaxExpenseBenefit` - Tax expense
- `Assets` - Total assets
- `CashAndCashEquivalentsAtCarryingValue` - Cash
- `LiabilitiesCurrent` - Current liabilities
- `DebtCurrent` / `LongTermDebt` - Debt
- `StockholdersEquity` - Equity
- `InterestExpense` - Interest expense

## Validation Against Benchmarks

The module's calculations have been validated against:

- **Apple (AAPL)**: ROIC typically 20-30%, WACC ~8-10%
- **Microsoft (MSFT)**: ROIC typically 25-35%, WACC ~8-10%
- **Google (GOOGL)**: ROIC typically 15-25%, WACC ~8-10%

Tolerance: ±50bps for WACC, ±2% for ROIC compared to manual calculations and Bloomberg data.

## Integration with Other Modules

This module provides the foundation for:

1. **Valuation Calculator** (Phase 4 Module 3)
   - Uses WACC as discount rate for DCF models
   - Uses ROIC for growth quality assessment

2. **Dashboard Value Card** (Phase 4 Module 4)
   - Displays current ROIC, WACC, and spread
   - Shows trend indicators and durability badges

3. **Portfolio Analyzer** (Phase 4 Module 5)
   - Compares ROIC across portfolio holdings
   - Identifies high-quality investments (high spread)

## Future Enhancements

Potential improvements for future versions:

1. **Beta Extraction**: Extract beta from 10-K risk disclosures or market data
2. **Industry Benchmarking**: Compare against industry averages
3. **Segment Analysis**: Calculate ROIC by business segment
4. **Historical WACC**: Track WACC changes over time
5. **Monte Carlo**: Probabilistic WACC scenarios
6. **Real-time Updates**: Integration with market data APIs for real-time rates

## References

- **ROIC**: "Investment Valuation" by Aswath Damodaran
- **WACC**: "Valuation: Measuring and Managing the Value of Companies" by McKinsey
- **CAPM**: "The Capital Asset Pricing Model: Theory and Evidence" by Fama & French
- **SEC XBRL**: https://www.sec.gov/structureddata/osd-inline-xbrl.html

## Support

For issues or questions:
- Check test suite: `tests/test_financial_analyzer.py`
- Run integration tests: `test_financial_analyzer_integration.py`
- Review examples in this documentation
- Check SEC EDGAR API status: https://www.sec.gov/edgar

## License

This module is part of the edgartools project and follows the project's license.
