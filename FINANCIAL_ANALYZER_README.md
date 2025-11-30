# Financial Analyzer Module - Quick Start

## Overview

The `edgar.financial_analyzer` module extracts ROIC (Return on Invested Capital), calculates WACC (Weighted Average Cost of Capital), and computes the spread (ROIC - WACC) from SEC 10-K filings.

**Status**: ✅ Production Ready (Phase 4 Pillar 1 Complete)

---

## Quick Start

### Installation

The module is already included in the edgartools package. No additional installation needed.

### Basic Usage

```python
from edgar.core import set_identity
from edgar.financial_analyzer import calculate_spread

# Set SEC User-Agent (required)
set_identity("Your Name your.email@example.com")

# Analyze a company
spread = calculate_spread('AAPL', years=5)

print(f"Current Spread: {spread.current_spread:.2%}")
print(f"Trend: {spread.spread_trend}")
print(f"Durability: {spread.durability_assessment}")
```

---

## Key Functions

### 1. `extract_roic_history(ticker, years=5)`

Extract historical Return on Invested Capital.

```python
from edgar.financial_analyzer import extract_roic_history

roic_data = extract_roic_history('AAPL', years=5)

for year, roic in zip(roic_data.years, roic_data.roic_values):
    print(f"{year}: {roic:.2%}")
```

### 2. `calculate_wacc(ticker, overrides=None, sensitivity=False)`

Calculate Weighted Average Cost of Capital.

```python
from edgar.financial_analyzer import calculate_wacc

# Basic WACC
wacc = calculate_wacc('AAPL')
print(f"WACC: {wacc.baseline_wacc:.2%}")

# With sensitivity analysis
wacc = calculate_wacc('AAPL', sensitivity=True)
print(f"Optimistic:  {wacc.scenarios['optimistic']:.2%}")
print(f"Base:        {wacc.scenarios['base']:.2%}")
print(f"Pessimistic: {wacc.scenarios['pessimistic']:.2%}")

# With custom parameters
wacc = calculate_wacc('AAPL', overrides={'beta': 1.2, 'risk_free_rate': 0.045})
```

### 3. `calculate_spread(ticker, years=5)`

Calculate ROIC-WACC spread with trend analysis.

```python
from edgar.financial_analyzer import calculate_spread

spread = calculate_spread('AAPL', years=5)

print(f"Current Spread: {spread.current_spread:.2%}")
print(f"Trend: {spread.spread_trend}")  # improving/deteriorating/stable
print(f"Durability: {spread.durability_assessment}")  # strong/uncertain/weak

# View history
for year, spread_val in zip(spread.years, spread.spread_history):
    print(f"{year}: {spread_val:.2%}")
```

---

## Understanding the Metrics

### ROIC (Return on Invested Capital)

Measures how efficiently a company generates returns:

```
ROIC = NOPAT / Invested Capital

Where:
- NOPAT = Operating Income × (1 - Tax Rate)
- Invested Capital = Total Assets - Cash - Non-Interest Liabilities
```

**Interpretation**:
- ROIC > 15%: Strong competitive advantages
- ROIC > 20%: Exceptional business quality
- ROIC < 10%: Weak competitive position

### WACC (Weighted Average Cost of Capital)

The minimum return required to satisfy stakeholders:

```
WACC = (E/V × Re) + (D/V × Rd × (1-Tc))

Where:
- E/V = Equity ratio
- Re = Cost of equity (from CAPM)
- D/V = Debt ratio
- Rd = Cost of debt
- Tc = Tax rate
```

**Interpretation**:
- Typical WACC: 7-12% for large tech companies
- Higher WACC: Riskier business
- Lower WACC: Safer, more stable business

### Spread (ROIC - WACC)

Value creation measure:

```
Spread = ROIC - WACC
```

**Interpretation**:
- Spread > 5%: Company creates significant value
- Spread > 0%: Company creates value
- Spread < 0%: Company destroys value

### Trend Analysis

Classifies the 3-year trend:
- **Improving**: Spread increased by >2%
- **Deteriorating**: Spread decreased by >2%
- **Stable**: Spread changed by ≤2%

### Durability Assessment

Quality and sustainability:
- **Strong**: Spread > 5% AND improving (high quality, strengthening)
- **Uncertain**: Moderate quality or weakening
- **Weak**: Spread < 0% OR deteriorating badly

---

## Default Assumptions

The module uses industry-standard defaults (all overridable):

- **Risk-free rate (Rf)**: 4.0% (10-year Treasury)
- **Market risk premium (MRP)**: 5.5%
- **Beta (β)**: 1.0 (market risk)

Override with:
```python
calculate_wacc('AAPL', overrides={
    'risk_free_rate': 0.045,
    'market_risk_premium': 0.06,
    'beta': 1.2
})
```

---

## Caching

Results are automatically cached in `/data/financial_cache_{ticker}.json`:

- **Cache validity**: 90 days
- **First run**: ~10-30 seconds (fetches from SEC)
- **Subsequent runs**: <1 second (uses cache)
- **Clear cache**: Delete the cache file to refresh

---

## Testing

### Run Unit Tests

```bash
source .venv/bin/activate
pytest tests/test_financial_analyzer.py -v
```

**Expected**: 31 passed, 3 skipped

### Verify Installation

```bash
python verify_financial_analyzer.py
```

### Integration Tests (Optional)

Tests against real SEC data:

```bash
python test_financial_analyzer_integration.py
```

Note: Requires internet and makes SEC API calls.

---

## Examples

See comprehensive examples:

```bash
python examples/financial_analyzer_example.py
```

Examples include:
1. Basic usage
2. Custom parameters
3. Sensitivity analysis
4. Portfolio analysis
5. Detailed components breakdown
6. Trend analysis

---

## Troubleshooting

### Error: "User-Agent identity is not set"

**Solution**: Call `set_identity()` before using the module:

```python
from edgar.core import set_identity
set_identity("Your Name your.email@example.com")
```

### Error: "InsufficientDataError"

**Cause**: Fewer than 3 years of 10-K data available.

**Solution**: 
- Use fewer years: `extract_roic_history(ticker, years=3)`
- Check if company has filed 10-Ks recently

### Error: "FinancialDataError"

**Cause**: Missing or invalid financial data in 10-K.

**Solution**:
- Check if company files 10-K (not 10-Q)
- Some companies may not have XBRL data in older filings
- Try a different ticker

### Slow Performance

**Solution**:
- Results are cached after first run
- Clear old cache files (>90 days) if needed
- Use fewer years to reduce API calls

---

## Documentation

- **Full documentation**: `docs/FINANCIAL_ANALYZER.md`
- **Implementation details**: `PHASE_4_PILLAR_1_IMPLEMENTATION.md`
- **Module docstrings**: See function docstrings for details

---

## Integration

This module is designed to integrate with:

1. **Valuation Calculator** (Phase 4 Module 3)
   - Uses WACC as DCF discount rate
   - Uses ROIC for growth quality assessment

2. **Dashboard** (Phase 4 Module 4)
   - Displays ROIC, WACC, spread
   - Shows trend and durability badges

3. **Portfolio Analyzer** (Phase 4 Module 5)
   - Compares companies by spread
   - Identifies high-quality investments

---

## Support

For issues or questions:

1. Check the test suite for examples
2. Review full documentation in `docs/FINANCIAL_ANALYZER.md`
3. Run verification script: `python verify_financial_analyzer.py`
4. See example usage: `python examples/financial_analyzer_example.py`

---

## License

Part of edgartools project. See LICENSE.txt for details.
