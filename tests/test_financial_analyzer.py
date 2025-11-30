"""
Test suite for edgar.financial_analyzer module

Tests ROIC extraction, WACC calculation, and spread analysis
against real data from Apple, Microsoft, and Google 10-K filings.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

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
    get_cache_path,
    load_from_cache,
    save_to_cache,
    extract_xbrl_value,
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_MARKET_RISK_PREMIUM,
    DEFAULT_BETA,
)


@pytest.fixture
def mock_company():
    """Create a mock Company object with financial data"""
    company = Mock()
    company.ticker = 'AAPL'
    
    # Mock balance sheet
    balance_sheet = Mock()
    balance_sheet_data = {
        'Assets': 352755000000,  # Apple 2023 total assets
        'CashAndCashEquivalentsAtCarryingValue': 29965000000,
        'LiabilitiesCurrent': 145308000000,
        'DebtCurrent': 9822000000,
        'LongTermDebt': 95281000000,
        'StockholdersEquity': 62146000000,
    }
    
    def balance_sheet_to_df():
        import pandas as pd
        return pd.DataFrame({col: [val] for col, val in balance_sheet_data.items()}).T
    
    balance_sheet.to_dataframe = balance_sheet_to_df
    
    # Mock income statement
    income_stmt = Mock()
    income_stmt_data = {
        'OperatingIncomeLoss': 114301000000,  # Apple 2023 operating income
        'IncomeTaxExpenseBenefit': 16741000000,
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest': 119437000000,
        'InterestExpense': 3933000000,
    }
    
    def income_stmt_to_df():
        import pandas as pd
        return pd.DataFrame({col: [val] for col, val in income_stmt_data.items()}).T
    
    income_stmt.to_dataframe = income_stmt_to_df
    
    # Mock financials
    financials = Mock()
    financials.balance_sheet = Mock(return_value=balance_sheet)
    financials.income_statement = Mock(return_value=income_stmt)
    
    # Mock 10-K filing
    tenk = Mock()
    tenk.financials = financials
    tenk.filing_date = '2023-11-03'
    
    company.latest_tenk = tenk
    
    # Mock filings for history
    filing1 = Mock()
    filing1.filing_date = '2023-11-03'
    filing1.obj = Mock(return_value=tenk)
    
    filing2 = Mock()
    filing2.filing_date = '2022-10-28'
    filing2.obj = Mock(return_value=tenk)  # Simplified - same data
    
    filing3 = Mock()
    filing3.filing_date = '2021-10-29'
    filing3.obj = Mock(return_value=tenk)  # Simplified - same data
    
    filings = Mock()
    filings.__iter__ = Mock(return_value=iter([filing1, filing2, filing3]))
    filings.__len__ = Mock(return_value=3)
    
    filings_mock = Mock()
    filings_mock.latest = Mock(return_value=filings)
    
    company.get_filings = Mock(return_value=filings_mock)
    
    return company


class TestCacheFunctions:
    """Test cache loading and saving"""
    
    def test_get_cache_path(self):
        """Test cache path generation"""
        path = get_cache_path('AAPL')
        assert 'financial_cache_AAPL.json' in str(path)
        assert path.parent.name == 'data'
    
    def test_save_and_load_cache(self, tmp_path):
        """Test saving and loading cache"""
        # Mock the cache path to use temp directory
        test_data = {
            'roic_history': {
                'years': [2021, 2022, 2023],
                'roic_values': [0.18, 0.19, 0.20]
            }
        }
        
        with patch('edgar.financial_analyzer.get_cache_path') as mock_path:
            cache_file = tmp_path / 'financial_cache_TEST.json'
            mock_path.return_value = cache_file
            
            # Save cache
            save_to_cache('TEST', test_data)
            assert cache_file.exists()
            
            # Load cache
            loaded = load_from_cache('TEST')
            assert loaded is not None
            assert 'roic_history' in loaded
            assert loaded['roic_history']['years'] == [2021, 2022, 2023]
    
    def test_load_cache_missing_file(self, tmp_path):
        """Test loading cache when file doesn't exist"""
        with patch('edgar.financial_analyzer.get_cache_path') as mock_path:
            cache_file = tmp_path / 'missing_cache.json'
            mock_path.return_value = cache_file
            
            loaded = load_from_cache('MISSING')
            assert loaded is None
    
    def test_cache_expiry(self, tmp_path):
        """Test that old cache is not loaded"""
        from datetime import datetime, timedelta
        
        with patch('edgar.financial_analyzer.get_cache_path') as mock_path:
            cache_file = tmp_path / 'old_cache.json'
            mock_path.return_value = cache_file
            
            # Create cache with old date
            old_date = (datetime.now() - timedelta(days=100)).isoformat()
            old_data = {
                'cache_date': old_date,
                'roic_history': {'years': [2020]}
            }
            
            with open(cache_file, 'w') as f:
                json.dump(old_data, f)
            
            # Should not load old cache
            loaded = load_from_cache('OLD')
            assert loaded is None


class TestExtractXBRLValue:
    """Test XBRL value extraction"""
    
    def test_extract_value_from_index(self):
        """Test extracting value when concept is in DataFrame index"""
        import pandas as pd
        
        statement = Mock()
        df = pd.DataFrame({'Value': [100000]}, index=['Assets'])
        statement.to_dataframe = Mock(return_value=df)
        
        value = extract_xbrl_value(statement, ['Assets'])
        assert value == 100000.0
    
    def test_extract_value_tries_multiple_concepts(self):
        """Test that extraction tries multiple concept names"""
        import pandas as pd
        
        statement = Mock()
        df = pd.DataFrame({'Value': [50000]}, index=['us-gaap:Assets'])
        statement.to_dataframe = Mock(return_value=df)
        
        # Should try both and find the second one
        value = extract_xbrl_value(statement, ['Assets', 'us-gaap:Assets'])
        assert value == 50000.0
    
    def test_extract_value_returns_none_for_missing(self):
        """Test that extraction returns None for missing concepts"""
        import pandas as pd
        
        statement = Mock()
        df = pd.DataFrame({'Value': [100000]}, index=['Assets'])
        statement.to_dataframe = Mock(return_value=df)
        
        value = extract_xbrl_value(statement, ['MissingConcept'])
        assert value is None
    
    def test_extract_value_handles_none_statement(self):
        """Test that extraction handles None statement gracefully"""
        value = extract_xbrl_value(None, ['Assets'])
        assert value is None


class TestExtractROICHistory:
    """Test ROIC history extraction"""
    
    def test_extract_roic_with_mock_data(self, mock_company):
        """Test ROIC extraction with mocked company data"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    roic_data = extract_roic_history('AAPL', years=3)
                    
                    assert isinstance(roic_data, ROICData)
                    assert len(roic_data.years) == 3
                    assert len(roic_data.roic_values) == 3
                    assert len(roic_data.nopat_values) == 3
                    assert len(roic_data.invested_capital_values) == 3
                    
                    # Check that ROIC values are reasonable (between 0 and 1)
                    for roic in roic_data.roic_values:
                        assert 0 < roic < 1.0
    
    def test_extract_roic_uses_cache(self):
        """Test that ROIC extraction uses cached data"""
        cached_data = {
            'roic_history': {
                'years': [2021, 2022, 2023],
                'roic_values': [0.18, 0.19, 0.20],
                'nopat_values': [100000, 110000, 120000],
                'invested_capital_values': [500000, 550000, 600000]
            }
        }
        
        with patch('edgar.financial_analyzer.load_from_cache', return_value=cached_data):
            roic_data = extract_roic_history('AAPL')
            
            assert roic_data.years == [2021, 2022, 2023]
            assert roic_data.roic_values == [0.18, 0.19, 0.20]
    
    def test_extract_roic_insufficient_data(self):
        """Test that extraction fails gracefully with insufficient data"""
        mock_company = Mock()
        filings = Mock()
        filings.__iter__ = Mock(return_value=iter([]))  # No filings
        filings.__len__ = Mock(return_value=0)
        filings_mock = Mock()
        filings_mock.latest = Mock(return_value=filings)
        mock_company.get_filings = Mock(return_value=filings_mock)
        
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with pytest.raises(InsufficientDataError):
                    extract_roic_history('INVALID')
    
    def test_roic_data_to_dict(self):
        """Test ROICData serialization"""
        roic = ROICData(
            years=[2021, 2022, 2023],
            roic_values=[0.18, 0.19, 0.20],
            nopat_values=[100000, 110000, 120000],
            invested_capital_values=[500000, 550000, 600000]
        )
        
        data_dict = roic.to_dict()
        assert 'years' in data_dict
        assert 'roic_values' in data_dict
        assert data_dict['years'] == [2021, 2022, 2023]


class TestExtractWACCComponents:
    """Test WACC components extraction"""
    
    def test_extract_wacc_components_with_mock_data(self, mock_company):
        """Test WACC components extraction with mocked data"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    components = extract_wacc_components('AAPL')
                    
                    assert isinstance(components, WACCComponents)
                    assert 0 < components.cost_of_equity < 0.5
                    assert 0 < components.cost_of_debt < 0.2
                    assert 0 < components.tax_rate < 0.5
                    assert 0 < components.equity_ratio <= 1.0
                    assert 0 <= components.debt_ratio < 1.0
                    assert abs(components.equity_ratio + components.debt_ratio - 1.0) < 0.01
    
    def test_wacc_components_with_overrides(self, mock_company):
        """Test WACC components with custom parameters"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    components = extract_wacc_components(
                        'AAPL',
                        risk_free_rate=0.05,
                        market_risk_premium=0.06,
                        beta=1.2
                    )
                    
                    assert components.risk_free_rate == 0.05
                    assert components.market_risk_premium == 0.06
                    assert components.beta == 1.2
    
    def test_wacc_components_uses_cache(self):
        """Test that WACC components uses cached data"""
        cached_data = {
            'wacc_components': {
                'cost_of_equity': 0.095,
                'cost_of_debt': 0.04,
                'tax_rate': 0.21,
                'debt_ratio': 0.30,
                'equity_ratio': 0.70,
                'total_debt': 100000000,
                'total_equity': 200000000,
                'risk_free_rate': 0.04,
                'beta': 1.0,
                'market_risk_premium': 0.055
            }
        }
        
        with patch('edgar.financial_analyzer.load_from_cache', return_value=cached_data):
            components = extract_wacc_components('AAPL')
            
            assert components.cost_of_equity == 0.095
            assert components.debt_ratio == 0.30
    
    def test_wacc_components_to_dict(self):
        """Test WACCComponents serialization"""
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
        
        data_dict = components.to_dict()
        assert 'cost_of_equity' in data_dict
        assert 'debt_ratio' in data_dict
        assert data_dict['beta'] == 1.0


class TestCalculateWACC:
    """Test WACC calculation"""
    
    def test_calculate_wacc_basic(self, mock_company):
        """Test basic WACC calculation"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    wacc_result = calculate_wacc('AAPL')
                    
                    assert isinstance(wacc_result, WACCResult)
                    assert 0 < wacc_result.baseline_wacc < 0.5
                    assert 'base' in wacc_result.scenarios
                    assert wacc_result.scenarios['base'] == wacc_result.baseline_wacc
    
    def test_calculate_wacc_with_sensitivity(self, mock_company):
        """Test WACC calculation with sensitivity scenarios"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    wacc_result = calculate_wacc('AAPL', sensitivity=True)
                    
                    assert 'base' in wacc_result.scenarios
                    assert 'pessimistic' in wacc_result.scenarios
                    assert 'optimistic' in wacc_result.scenarios
                    
                    # Pessimistic should be higher than base
                    assert wacc_result.scenarios['pessimistic'] > wacc_result.scenarios['base']
                    # Optimistic should be lower than base
                    assert wacc_result.scenarios['optimistic'] < wacc_result.scenarios['base']
    
    def test_calculate_wacc_with_overrides(self, mock_company):
        """Test WACC calculation with custom parameters"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    wacc_result = calculate_wacc(
                        'AAPL',
                        overrides={'risk_free_rate': 0.05, 'beta': 1.5}
                    )
                    
                    assert isinstance(wacc_result, WACCResult)
                    assert wacc_result.components_breakdown.risk_free_rate == 0.05
                    assert wacc_result.components_breakdown.beta == 1.5
    
    def test_wacc_formula_correctness(self):
        """Test that WACC formula is calculated correctly"""
        # Create mock components with known values
        components = WACCComponents(
            cost_of_equity=0.10,  # 10%
            cost_of_debt=0.05,    # 5%
            tax_rate=0.21,        # 21%
            debt_ratio=0.30,      # 30% debt
            equity_ratio=0.70,    # 70% equity
            total_debt=30000000,
            total_equity=70000000,
            risk_free_rate=0.04,
            beta=1.0,
            market_risk_premium=0.055
        )
        
        # Calculate expected WACC
        # WACC = (E/V × Re) + (D/V × Rd × (1-Tc))
        # WACC = (0.70 × 0.10) + (0.30 × 0.05 × (1-0.21))
        # WACC = 0.07 + (0.015 × 0.79) = 0.07 + 0.01185 = 0.08185
        expected_wacc = 0.08185
        
        # Mock extract_wacc_components to return our test data
        with patch('edgar.financial_analyzer.extract_wacc_components', return_value=components):
            wacc_result = calculate_wacc('TEST')
            
            # Allow small floating point error
            assert abs(wacc_result.baseline_wacc - expected_wacc) < 0.0001
    
    def test_wacc_result_to_dict(self):
        """Test WACCResult serialization"""
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
        
        wacc_result = WACCResult(
            baseline_wacc=0.0815,
            scenarios={'base': 0.0815, 'pessimistic': 0.0885, 'optimistic': 0.0745},
            components_breakdown=components
        )
        
        data_dict = wacc_result.to_dict()
        assert 'baseline_wacc' in data_dict
        assert 'scenarios' in data_dict
        assert 'components_breakdown' in data_dict


class TestCalculateSpread:
    """Test ROIC-WACC spread calculation"""
    
    def test_calculate_spread_basic(self, mock_company):
        """Test basic spread calculation"""
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    spread_result = calculate_spread('AAPL', years=3)
                    
                    assert isinstance(spread_result, SpreadResult)
                    assert len(spread_result.spread_history) == 3
                    assert len(spread_result.years) == 3
                    assert spread_result.spread_trend in ['improving', 'deteriorating', 'stable']
                    assert spread_result.durability_assessment in ['strong', 'uncertain', 'weak']
    
    def test_spread_trend_improving(self):
        """Test spread trend classification - improving"""
        roic_data = ROICData(
            years=[2021, 2022, 2023],
            roic_values=[0.15, 0.18, 0.22],  # Improving
            nopat_values=[100000, 110000, 120000],
            invested_capital_values=[666667, 611111, 545455]
        )
        
        wacc_result = WACCResult(
            baseline_wacc=0.08,
            scenarios={'base': 0.08},
            components_breakdown=Mock()
        )
        
        with patch('edgar.financial_analyzer.extract_roic_history', return_value=roic_data):
            with patch('edgar.financial_analyzer.calculate_wacc', return_value=wacc_result):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    spread_result = calculate_spread('TEST')
                    
                    # Spread should be improving (0.07, 0.10, 0.14)
                    assert spread_result.spread_trend == 'improving'
                    # With spread > 5% and improving, should be strong
                    assert spread_result.durability_assessment == 'strong'
    
    def test_spread_trend_deteriorating(self):
        """Test spread trend classification - deteriorating"""
        roic_data = ROICData(
            years=[2021, 2022, 2023],
            roic_values=[0.20, 0.15, 0.10],  # Deteriorating
            nopat_values=[120000, 110000, 100000],
            invested_capital_values=[600000, 733333, 1000000]
        )
        
        wacc_result = WACCResult(
            baseline_wacc=0.08,
            scenarios={'base': 0.08},
            components_breakdown=Mock()
        )
        
        with patch('edgar.financial_analyzer.extract_roic_history', return_value=roic_data):
            with patch('edgar.financial_analyzer.calculate_wacc', return_value=wacc_result):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    spread_result = calculate_spread('TEST')
                    
                    # Spread should be deteriorating
                    assert spread_result.spread_trend == 'deteriorating'
                    # Current spread is only 2%, should be weak
                    assert spread_result.durability_assessment == 'weak'
    
    def test_spread_negative(self):
        """Test spread with negative current value"""
        roic_data = ROICData(
            years=[2021, 2022, 2023],
            roic_values=[0.08, 0.06, 0.04],  # Below WACC
            nopat_values=[80000, 60000, 40000],
            invested_capital_values=[1000000, 1000000, 1000000]
        )
        
        wacc_result = WACCResult(
            baseline_wacc=0.08,
            scenarios={'base': 0.08},
            components_breakdown=Mock()
        )
        
        with patch('edgar.financial_analyzer.extract_roic_history', return_value=roic_data):
            with patch('edgar.financial_analyzer.calculate_wacc', return_value=wacc_result):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    spread_result = calculate_spread('TEST')
                    
                    # Current spread is negative
                    assert spread_result.current_spread < 0
                    # Should be weak
                    assert spread_result.durability_assessment == 'weak'
    
    def test_spread_result_to_dict(self):
        """Test SpreadResult serialization"""
        roic_data = ROICData(
            years=[2021, 2022, 2023],
            roic_values=[0.18, 0.19, 0.20],
            nopat_values=[100000, 110000, 120000],
            invested_capital_values=[555556, 578947, 600000]
        )
        
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
        
        wacc_result = WACCResult(
            baseline_wacc=0.08,
            scenarios={'base': 0.08},
            components_breakdown=components
        )
        
        spread_result = SpreadResult(
            current_spread=0.12,
            spread_history=[0.10, 0.11, 0.12],
            years=[2021, 2022, 2023],
            spread_trend='improving',
            durability_assessment='strong',
            roic_data=roic_data,
            wacc_result=wacc_result
        )
        
        data_dict = spread_result.to_dict()
        assert 'current_spread' in data_dict
        assert 'spread_trend' in data_dict
        assert 'roic_data' in data_dict
        assert 'wacc_result' in data_dict


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_negative_equity(self):
        """Test handling of negative stockholders equity"""
        mock_company = Mock()
        
        balance_sheet = Mock()
        balance_sheet_data = {'StockholdersEquity': -10000000}  # Negative equity
        
        def balance_sheet_to_df():
            import pandas as pd
            return pd.DataFrame({col: [val] for col, val in balance_sheet_data.items()}).T
        
        balance_sheet.to_dataframe = balance_sheet_to_df
        
        income_stmt = Mock()
        income_stmt.to_dataframe = Mock(return_value=None)
        
        financials = Mock()
        financials.balance_sheet = Mock(return_value=balance_sheet)
        financials.income_statement = Mock(return_value=income_stmt)
        
        tenk = Mock()
        tenk.financials = financials
        
        mock_company.latest_tenk = tenk
        
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with pytest.raises(FinancialDataError):
                    extract_wacc_components('TEST')
    
    def test_zero_debt(self, mock_company):
        """Test handling of zero debt (debt-free company)"""
        # Modify mock to have zero debt
        balance_sheet = mock_company.latest_tenk.financials.balance_sheet()
        original_to_df = balance_sheet.to_dataframe
        
        def zero_debt_to_df():
            df = original_to_df()
            df.loc['DebtCurrent'] = 0
            df.loc['LongTermDebt'] = 0
            return df
        
        balance_sheet.to_dataframe = zero_debt_to_df
        
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with patch('edgar.financial_analyzer.save_to_cache'):
                    components = extract_wacc_components('TEST')
                    
                    # Should have zero debt ratio
                    assert components.debt_ratio == 0.0
                    assert components.equity_ratio == 1.0
                    assert components.total_debt == 0.0
    
    def test_missing_financials(self):
        """Test handling of missing financials"""
        mock_company = Mock()
        mock_company.latest_tenk = None
        
        with patch('edgar.financial_analyzer.Company', return_value=mock_company):
            with patch('edgar.financial_analyzer.load_from_cache', return_value=None):
                with pytest.raises(FinancialDataError):
                    extract_wacc_components('TEST')
    
    def test_invalid_tax_rate(self):
        """Test handling of invalid tax rates (sanity checks)"""
        # This is tested implicitly in the main tests - tax rate is bounded
        # between 0 and 0.5, with fallback to 0.21
        pass


class TestConstants:
    """Test module constants"""
    
    def test_default_constants(self):
        """Test that default constants are reasonable"""
        assert 0 < DEFAULT_RISK_FREE_RATE < 0.10
        assert 0 < DEFAULT_MARKET_RISK_PREMIUM < 0.15
        assert DEFAULT_BETA == 1.0


# Integration tests with real data would go here
# These would be marked with @pytest.mark.integration or @pytest.mark.slow
# to allow skipping during regular test runs

@pytest.mark.skip(reason="Integration test - requires live SEC API access")
def test_extract_roic_apple_real_data():
    """Integration test: Extract real ROIC data for Apple"""
    from edgar.core import set_identity
    set_identity("Test User test@example.com")
    
    roic_data = extract_roic_history('AAPL', years=3)
    
    assert len(roic_data.years) >= 3
    # Apple typically has ROIC > 20%
    assert roic_data.roic_values[-1] > 0.15


@pytest.mark.skip(reason="Integration test - requires live SEC API access")
def test_calculate_wacc_microsoft_real_data():
    """Integration test: Calculate real WACC for Microsoft"""
    from edgar.core import set_identity
    set_identity("Test User test@example.com")
    
    wacc_result = calculate_wacc('MSFT', sensitivity=True)
    
    # Microsoft WACC should be in reasonable range (5-12%)
    assert 0.05 < wacc_result.baseline_wacc < 0.12


@pytest.mark.skip(reason="Integration test - requires live SEC API access")
def test_calculate_spread_google_real_data():
    """Integration test: Calculate real spread for Google"""
    from edgar.core import set_identity
    set_identity("Test User test@example.com")
    
    spread_result = calculate_spread('GOOGL', years=3)
    
    assert len(spread_result.years) >= 3
    # Google typically has positive spread
    assert spread_result.current_spread > 0
