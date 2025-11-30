"""
Financial Data Extraction and Analysis Module

This module extracts historical ROIC, calculates WACC, and computes spread (ROIC - WACC)
for portfolio analysis. It uses XBRL data from 10-K filings with fallback to text parsing.

Key Functions:
- extract_roic_history: Extract NOPAT and Invested Capital to calculate ROIC
- extract_wacc_components: Extract cost of equity, cost of debt, and capital structure
- calculate_wacc: Calculate Weighted Average Cost of Capital with sensitivity analysis
- calculate_spread: Calculate ROIC-WACC spread with trend analysis

Formulas:
- ROIC = NOPAT / Invested Capital
- NOPAT = Operating Income × (1 - Tax Rate)
- Invested Capital = Total Assets - Cash - Non-Interest Liabilities
- Cost of Equity: Re = Rf + β(Rm - Rf)
- Cost of Debt: Rd = Interest Expense / Total Debt
- WACC = (E/V × Re) + (D/V × Rd × (1-Tc))
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from dataclasses import dataclass, asdict

from edgar.core import get_identity, set_identity
from edgar.entity.core import Company

log = logging.getLogger(__name__)

# Default assumptions for WACC calculation
DEFAULT_RISK_FREE_RATE = 0.040  # 4.0% (10-year Treasury)
DEFAULT_MARKET_RISK_PREMIUM = 0.055  # 5.5%
DEFAULT_BETA = 1.0  # Market beta


class FinancialDataError(Exception):
    """Base exception for financial data extraction errors"""
    pass


class InsufficientDataError(FinancialDataError):
    """Exception raised when insufficient data is available"""
    pass


@dataclass
class ROICData:
    """Data class for ROIC history"""
    years: List[int]
    roic_values: List[float]
    nopat_values: List[float]
    invested_capital_values: List[float]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WACCComponents:
    """Data class for WACC components"""
    cost_of_equity: float
    cost_of_debt: float
    tax_rate: float
    debt_ratio: float  # D/V
    equity_ratio: float  # E/V
    total_debt: float
    total_equity: float
    risk_free_rate: float
    beta: float
    market_risk_premium: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WACCResult:
    """Data class for WACC calculation result"""
    baseline_wacc: float
    scenarios: Dict[str, float]  # base, pessimistic, optimistic
    components_breakdown: WACCComponents
    
    def to_dict(self) -> Dict:
        result = {
            'baseline_wacc': self.baseline_wacc,
            'scenarios': self.scenarios,
            'components_breakdown': self.components_breakdown.to_dict()
        }
        return result


@dataclass
class SpreadResult:
    """Data class for ROIC-WACC spread analysis"""
    current_spread: float
    spread_history: List[float]
    years: List[int]
    spread_trend: str  # 'improving', 'deteriorating', 'stable'
    durability_assessment: str  # 'strong', 'uncertain', 'weak'
    roic_data: ROICData
    wacc_result: WACCResult
    
    def to_dict(self) -> Dict:
        return {
            'current_spread': self.current_spread,
            'spread_history': self.spread_history,
            'years': self.years,
            'spread_trend': self.spread_trend,
            'durability_assessment': self.durability_assessment,
            'roic_data': self.roic_data.to_dict(),
            'wacc_result': self.wacc_result.to_dict()
        }


def get_cache_path(ticker: str) -> Path:
    """Get the cache file path for a ticker"""
    return Path(__file__).parent.parent / "data" / f"financial_cache_{ticker}.json"


def load_from_cache(ticker: str) -> Optional[Dict]:
    """Load cached financial data for a ticker"""
    cache_path = get_cache_path(ticker)
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                # Check if cache is recent (within 90 days)
                cache_date = datetime.fromisoformat(data.get('cache_date', '2000-01-01'))
                days_old = (datetime.now() - cache_date).days
                if days_old < 90:
                    log.info(f"Loaded cached financial data for {ticker} ({days_old} days old)")
                    return data
                else:
                    log.info(f"Cache for {ticker} is {days_old} days old, refreshing...")
        except Exception as e:
            log.warning(f"Failed to load cache for {ticker}: {e}")
    return None


def save_to_cache(ticker: str, data: Dict) -> None:
    """Save financial data to cache"""
    cache_path = get_cache_path(ticker)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    data['cache_date'] = datetime.now().isoformat()
    data['ticker'] = ticker
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=2)
        log.info(f"Saved financial data to cache for {ticker}")
    except Exception as e:
        log.warning(f"Failed to save cache for {ticker}: {e}")


def extract_xbrl_value(statement: Any, concepts: List[str], period: str = None) -> Optional[float]:
    """
    Extract a value from an XBRL statement by trying multiple concept names.
    
    Args:
        statement: XBRL statement object
        concepts: List of GAAP concept names to try
        period: Specific period to extract (if None, uses most recent)
    
    Returns:
        Extracted value or None if not found
    """
    if statement is None:
        return None
    
    try:
        # Convert statement to DataFrame for easier manipulation
        df = statement.to_dataframe() if hasattr(statement, 'to_dataframe') else None
        if df is None or df.empty:
            return None
        
        # Try each concept
        for concept in concepts:
            # Normalize concept (replace : with _) as edgar-tools uses underscores
            normalized_concept = concept.replace(':', '_')
            
            # Check if concept column exists
            if 'concept' in df.columns:
                # Find row matching the concept
                match = df[df['concept'] == normalized_concept]
                if not match.empty:
                    # Get the first match
                    row = match.iloc[0]
                    
                    # Find date columns (columns that are not metadata)
                    # Metadata columns usually include: concept, label, level, abstract, dimension
                    metadata_cols = ['concept', 'label', 'level', 'abstract', 'dimension']
                    date_cols = [c for c in df.columns if c not in metadata_cols]
                    
                    # Sort date columns to get the most recent one? 
                    # Actually, edgar-tools usually puts most recent first, but let's be safe.
                    # But the columns are strings 'YYYY-MM-DD'.
                    # Let's just iterate through date columns and take the first non-null value
                    
                    for date_col in date_cols:
                        val = row[date_col]
                        # Check if valid number
                        if pd.notna(val) and isinstance(val, (int, float, str)):
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                continue
            
            # Fallback for index-based (if behavior changes or for other libraries)
            elif concept in df.index:
                values = df.loc[concept]
                if isinstance(values, (int, float)):
                    return float(values)
                if hasattr(values, 'dropna'):
                    values = values.dropna()
                    if len(values) > 0:
                        return float(values.iloc[-1] if hasattr(values, 'iloc') else values[-1])
        
        # If we get here, we failed to find any concept
        return None
    except Exception as e:
        log.debug(f"Error extracting XBRL value: {e}")
        return None


def extract_roic_history(ticker: str, years: int = 5) -> ROICData:
    """
    Extract historical ROIC (Return on Invested Capital) for a ticker.
    
    ROIC Formula:
    ROIC = NOPAT / Invested Capital
    
    Where:
    - NOPAT = Operating Income × (1 - Tax Rate)
    - Invested Capital = Total Assets - Cash - Non-Interest Liabilities
    - Non-Interest Liabilities ≈ Current Liabilities - Short-term Debt
    
    Args:
        ticker: Stock ticker symbol
        years: Number of years of history to extract (default: 5)
    
    Returns:
        ROICData object with years, ROIC values, NOPAT, and Invested Capital
    
    Raises:
        InsufficientDataError: If unable to extract minimum required data
    """
    # Check cache first
    cache = load_from_cache(ticker)
    if cache and 'roic_history' in cache:
        cached_roic = cache['roic_history']
        return ROICData(
            years=cached_roic['years'],
            roic_values=cached_roic['roic_values'],
            nopat_values=cached_roic['nopat_values'],
            invested_capital_values=cached_roic['invested_capital_values']
        )
    
    try:
        # Ensure SEC identity is set
        if not get_identity():
            # Ensure identity is set
            if not get_identity():
                import os
                identity = os.environ.get("EDGAR_IDENTITY")
                if identity:
                    set_identity(identity)
                else:
                    log.warning("EDGAR_IDENTITY not set. SEC API calls may fail.")
        
        company = Company(ticker)
        
        # Get multiple years of 10-K filings
        filings = company.get_filings(form='10-K').latest(years)
        
        if len(filings) == 0:
            raise InsufficientDataError(f"No 10-K filings found for {ticker}")
        
        roic_years = []
        roic_values = []
        nopat_values = []
        invested_capital_values = []
        
        for filing in filings:
            try:
                # Get financials from the filing
                tenk = filing.obj()
                financials = tenk.financials if hasattr(tenk, 'financials') else None
                
                if financials is None:
                    log.warning(f"No financials available for {ticker} filing {filing.filing_date}")
                    continue
                
                # Extract income statement data
                income_stmt = financials.income_statement()
                balance_sheet = financials.balance_sheet()
                
                if income_stmt is None or balance_sheet is None:
                    log.warning(f"Missing financial statements for {ticker} filing {filing.filing_date}")
                    continue
                
                # Extract Operating Income (multiple possible GAAP names)
                operating_income = extract_xbrl_value(income_stmt, [
                    'OperatingIncomeLoss',
                    'us-gaap:OperatingIncomeLoss',
                    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
                ])
                
                # Extract Tax Rate (calculate from effective tax rate or use expense/income)
                income_tax_expense = extract_xbrl_value(income_stmt, [
                    'IncomeTaxExpenseBenefit',
                    'us-gaap:IncomeTaxExpenseBenefit'
                ])
                
                income_before_tax = extract_xbrl_value(income_stmt, [
                    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                    'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
                ])
                
                # Calculate tax rate
                tax_rate = 0.21  # Default federal corporate tax rate
                if income_tax_expense and income_before_tax and income_before_tax != 0:
                    tax_rate = abs(income_tax_expense / income_before_tax)
                    # Sanity check - tax rate should be between 0 and 50%
                    if tax_rate < 0 or tax_rate > 0.5:
                        tax_rate = 0.21
                
                # Calculate NOPAT
                if operating_income is None:
                    log.warning(f"No operating income found for {ticker} filing {filing.filing_date}")
                    continue
                
                nopat = operating_income * (1 - tax_rate)
                
                # Extract Balance Sheet data for Invested Capital
                total_assets = extract_xbrl_value(balance_sheet, [
                    'Assets',
                    'us-gaap:Assets'
                ])
                
                cash_and_equivalents = extract_xbrl_value(balance_sheet, [
                    'CashAndCashEquivalentsAtCarryingValue',
                    'us-gaap:CashAndCashEquivalentsAtCarryingValue',
                    'Cash',
                    'us-gaap:Cash'
                ]) or 0
                
                current_liabilities = extract_xbrl_value(balance_sheet, [
                    'LiabilitiesCurrent',
                    'us-gaap:LiabilitiesCurrent'
                ]) or 0
                
                short_term_debt = extract_xbrl_value(balance_sheet, [
                    'ShortTermBorrowings',
                    'us-gaap:ShortTermBorrowings',
                    'DebtCurrent',
                    'us-gaap:DebtCurrent'
                ]) or 0
                
                # Calculate Invested Capital
                # Invested Capital = Total Assets - Cash - Non-Interest Liabilities
                # Non-Interest Liabilities ≈ Current Liabilities - Short-term Debt
                non_interest_liabilities = max(0, current_liabilities - short_term_debt)
                
                if total_assets is None:
                    log.warning(f"No total assets found for {ticker} filing {filing.filing_date}")
                    continue
                
                invested_capital = total_assets - cash_and_equivalents - non_interest_liabilities
                
                # Sanity check
                if invested_capital <= 0:
                    log.warning(f"Invalid invested capital ({invested_capital}) for {ticker} filing {filing.filing_date}")
                    continue
                
                # Calculate ROIC
                roic = nopat / invested_capital
                
                # Extract year from filing date
                # filing.filing_date is a string in some versions, date in others
                if isinstance(filing.filing_date, str):
                    year = int(filing.filing_date.split('-')[0])
                else:
                    year = filing.filing_date.year
                
                roic_years.append(year)
                roic_values.append(roic)
                nopat_values.append(nopat)
                invested_capital_values.append(invested_capital)
                
                log.info(f"Extracted ROIC for {ticker} {year}: {roic:.2%}")
                
            except Exception as e:
                log.warning(f"Error processing filing {filing.filing_date} for {ticker}: {e}")
                continue
        
        # Check if we have minimum data
        if len(roic_years) < 3:
            raise InsufficientDataError(
                f"Insufficient ROIC data for {ticker}: only {len(roic_years)} years available (need at least 3)"
            )
        
        # Sort by year
        sorted_data = sorted(zip(roic_years, roic_values, nopat_values, invested_capital_values))
        roic_years, roic_values, nopat_values, invested_capital_values = zip(*sorted_data)
        
        result = ROICData(
            years=list(roic_years),
            roic_values=list(roic_values),
            nopat_values=list(nopat_values),
            invested_capital_values=list(invested_capital_values)
        )
        
        # Cache the result
        cache_data = cache or {}
        cache_data['roic_history'] = result.to_dict()
        save_to_cache(ticker, cache_data)
        
        return result
        
    except InsufficientDataError:
        raise
    except Exception as e:
        raise FinancialDataError(f"Failed to extract ROIC history for {ticker}: {e}")


def extract_wacc_components(
    ticker: str,
    risk_free_rate: Optional[float] = None,
    market_risk_premium: Optional[float] = None,
    beta: Optional[float] = None
) -> WACCComponents:
    """
    Extract components needed for WACC calculation.
    
    Components:
    - Cost of Equity: Re = Rf + β(Rm - Rf)
      * Rf: Risk-free rate (10-year Treasury, default 4.0%)
      * β: Beta from market data or 10-K risk disclosures (default 1.0)
      * Rm - Rf: Market risk premium (default 5.5%)
    
    - Cost of Debt: Rd = Interest Expense / Total Debt
      * Total Debt: Short-term + Long-term debt from balance sheet
      * Interest Expense: From income statement
    
    - Capital Structure: E/V and D/V
      * E: Market value of equity (or book value as proxy)
      * D: Total debt
      * V: E + D
    
    Args:
        ticker: Stock ticker symbol
        risk_free_rate: Override for risk-free rate (default: 4.0%)
        market_risk_premium: Override for market risk premium (default: 5.5%)
        beta: Override for beta (default: 1.0)
    
    Returns:
        WACCComponents object with all necessary data
    
    Raises:
        FinancialDataError: If unable to extract required data
    """
    # Check cache first
    cache = load_from_cache(ticker)
    if cache and 'wacc_components' in cache:
        cached_wacc = cache['wacc_components']
        return WACCComponents(**cached_wacc)
    
    try:
        # Ensure SEC identity is set
        if not get_identity():
            # Ensure identity is set
            if not get_identity():
                import os
                identity = os.environ.get("EDGAR_IDENTITY")
                if identity:
                    set_identity(identity)
                else:
                    log.warning("EDGAR_IDENTITY not set. SEC API calls may fail.")
        
        company = Company(ticker)
        
        # Get latest 10-K filing
        latest_10k = company.latest_tenk
        
        if latest_10k is None:
            raise FinancialDataError(f"No 10-K filing found for {ticker}")
        
        financials = latest_10k.financials
        if financials is None:
            raise FinancialDataError(f"No financials available for {ticker}")
        
        income_stmt = financials.income_statement()
        balance_sheet = financials.balance_sheet()
        
        if income_stmt is None or balance_sheet is None:
            raise FinancialDataError(f"Missing financial statements for {ticker}")
        
        # Extract debt data
        short_term_debt = extract_xbrl_value(balance_sheet, [
            'DebtCurrent',
            'us-gaap:DebtCurrent',
            'ShortTermBorrowings',
            'us-gaap:ShortTermBorrowings'
        ]) or 0
        
        long_term_debt = extract_xbrl_value(balance_sheet, [
            'LongTermDebt',
            'us-gaap:LongTermDebt',
            'LongTermDebtNoncurrent',
            'us-gaap:LongTermDebtNoncurrent'
        ]) or 0
        
        total_debt = short_term_debt + long_term_debt
        
        # Extract interest expense
        interest_expense = extract_xbrl_value(income_stmt, [
            'InterestExpense',
            'us-gaap:InterestExpense',
            'InterestExpenseDebt',
            'us-gaap:InterestExpenseDebt'
        ])
        
        # Calculate cost of debt
        cost_of_debt = 0.05  # Default 5%
        if interest_expense and total_debt > 0:
            cost_of_debt = abs(interest_expense) / total_debt
            # Sanity check - cost of debt should be reasonable (0-20%)
            if cost_of_debt < 0 or cost_of_debt > 0.20:
                cost_of_debt = 0.05
        
        # Extract equity data
        stockholders_equity = extract_xbrl_value(balance_sheet, [
            'StockholdersEquity',
            'us-gaap:StockholdersEquity',
            'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
            'us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
        ])
        
        if stockholders_equity is None or stockholders_equity <= 0:
            raise FinancialDataError(f"Invalid stockholders equity for {ticker}")
        
        total_equity = stockholders_equity
        
        # Extract tax rate
        income_tax_expense = extract_xbrl_value(income_stmt, [
            'IncomeTaxExpenseBenefit',
            'us-gaap:IncomeTaxExpenseBenefit'
        ])
        
        income_before_tax = extract_xbrl_value(income_stmt, [
            'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
            'us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest'
        ])
        
        tax_rate = 0.21  # Default federal corporate tax rate
        if income_tax_expense and income_before_tax and income_before_tax != 0:
            tax_rate = abs(income_tax_expense / income_before_tax)
            # Sanity check
            if tax_rate < 0 or tax_rate > 0.5:
                tax_rate = 0.21
        
        # Calculate capital structure
        total_capital = total_equity + total_debt
        if total_capital <= 0:
            raise FinancialDataError(f"Invalid total capital for {ticker}")
        
        equity_ratio = total_equity / total_capital
        debt_ratio = total_debt / total_capital
        
        # Use provided values or defaults for cost of equity calculation
        rf = risk_free_rate if risk_free_rate is not None else DEFAULT_RISK_FREE_RATE
        mrp = market_risk_premium if market_risk_premium is not None else DEFAULT_MARKET_RISK_PREMIUM
        b = beta if beta is not None else DEFAULT_BETA
        
        # Calculate cost of equity using CAPM
        cost_of_equity = rf + b * mrp
        
        result = WACCComponents(
            cost_of_equity=cost_of_equity,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate,
            debt_ratio=debt_ratio,
            equity_ratio=equity_ratio,
            total_debt=total_debt,
            total_equity=total_equity,
            risk_free_rate=rf,
            beta=b,
            market_risk_premium=mrp
        )
        
        # Cache the result
        cache_data = cache or {}
        cache_data['wacc_components'] = result.to_dict()
        save_to_cache(ticker, cache_data)
        
        return result
        
    except FinancialDataError:
        raise
    except Exception as e:
        raise FinancialDataError(f"Failed to extract WACC components for {ticker}: {e}")


def calculate_wacc(
    ticker: str,
    overrides: Optional[Dict[str, float]] = None,
    sensitivity: bool = False
) -> WACCResult:
    """
    Calculate Weighted Average Cost of Capital (WACC).
    
    WACC Formula:
    WACC = (E/V × Re) + (D/V × Rd × (1-Tc))
    
    Where:
    - E/V: Equity ratio
    - Re: Cost of equity
    - D/V: Debt ratio
    - Rd: Cost of debt
    - Tc: Corporate tax rate
    
    Args:
        ticker: Stock ticker symbol
        overrides: Optional dict with overrides for 'risk_free_rate', 'market_risk_premium', 'beta'
        sensitivity: If True, calculate pessimistic and optimistic scenarios (±100bps to risk-free rate)
    
    Returns:
        WACCResult object with baseline WACC, scenarios, and component breakdown
    
    Raises:
        FinancialDataError: If unable to calculate WACC
    """
    overrides = overrides or {}
    
    try:
        # Extract WACC components
        components = extract_wacc_components(
            ticker,
            risk_free_rate=overrides.get('risk_free_rate'),
            market_risk_premium=overrides.get('market_risk_premium'),
            beta=overrides.get('beta')
        )
        
        # Calculate baseline WACC
        wacc_equity_component = components.equity_ratio * components.cost_of_equity
        wacc_debt_component = components.debt_ratio * components.cost_of_debt * (1 - components.tax_rate)
        baseline_wacc = wacc_equity_component + wacc_debt_component
        
        scenarios = {
            'base': baseline_wacc
        }
        
        # Calculate sensitivity scenarios if requested
        if sensitivity:
            # Pessimistic: +100bps to risk-free rate (higher discount rate)
            pessimistic_rf = components.risk_free_rate + 0.01
            pessimistic_re = pessimistic_rf + components.beta * components.market_risk_premium
            pessimistic_wacc = (components.equity_ratio * pessimistic_re + 
                               components.debt_ratio * components.cost_of_debt * (1 - components.tax_rate))
            scenarios['pessimistic'] = pessimistic_wacc
            
            # Optimistic: -100bps to risk-free rate (lower discount rate)
            optimistic_rf = max(0, components.risk_free_rate - 0.01)
            optimistic_re = optimistic_rf + components.beta * components.market_risk_premium
            optimistic_wacc = (components.equity_ratio * optimistic_re + 
                              components.debt_ratio * components.cost_of_debt * (1 - components.tax_rate))
            scenarios['optimistic'] = optimistic_wacc
        
        result = WACCResult(
            baseline_wacc=baseline_wacc,
            scenarios=scenarios,
            components_breakdown=components
        )
        
        log.info(f"Calculated WACC for {ticker}: {baseline_wacc:.2%}")
        
        return result
        
    except Exception as e:
        raise FinancialDataError(f"Failed to calculate WACC for {ticker}: {e}")


def calculate_spread(ticker: str, years: int = 5) -> SpreadResult:
    """
    Calculate ROIC-WACC spread with trend analysis.
    
    Spread = ROIC - WACC
    
    Trend Analysis:
    - Calculate 3-year CAGR of spread
    - Classify as 'improving', 'deteriorating', or 'stable'
    
    Durability Assessment:
    - Strong: spread > 5% AND trend improving
    - Uncertain: spread deteriorating OR spread < 5%
    - Weak: spread < 0% OR spread deteriorating significantly
    
    Args:
        ticker: Stock ticker symbol
        years: Number of years of history to analyze (default: 5)
    
    Returns:
        SpreadResult object with current spread, history, trend, and durability
    
    Raises:
        FinancialDataError: If unable to calculate spread
    """
    try:
        # Get ROIC history
        roic_data = extract_roic_history(ticker, years)
        
        # Calculate WACC
        wacc_result = calculate_wacc(ticker, sensitivity=True)
        
        # Calculate spreads for each year
        spread_history = [roic - wacc_result.baseline_wacc for roic in roic_data.roic_values]
        
        current_spread = spread_history[-1] if spread_history else 0.0
        
        # Analyze trend (if we have at least 3 years)
        spread_trend = 'stable'
        if len(spread_history) >= 3:
            # Calculate simple slope over last 3 years
            recent_spreads = spread_history[-3:]
            slope = (recent_spreads[-1] - recent_spreads[0]) / 2  # Change over 2 year periods
            
            if slope > 0.02:  # Improving by more than 2% over period
                spread_trend = 'improving'
            elif slope < -0.02:  # Deteriorating by more than 2% over period
                spread_trend = 'deteriorating'
        
        # Assess durability
        if current_spread > 0.05 and spread_trend == 'improving':
            durability = 'strong'
        elif current_spread < 0 or (spread_trend == 'deteriorating' and current_spread < 0.03):
            durability = 'weak'
        else:
            durability = 'uncertain'
        
        result = SpreadResult(
            current_spread=current_spread,
            spread_history=spread_history,
            years=roic_data.years,
            spread_trend=spread_trend,
            durability_assessment=durability,
            roic_data=roic_data,
            wacc_result=wacc_result
        )
        
        log.info(f"Calculated spread for {ticker}: {current_spread:.2%} ({durability}, {spread_trend})")
        
        # Cache the full result
        cache_data = load_from_cache(ticker) or {}
        cache_data['spread_result'] = result.to_dict()
        save_to_cache(ticker, cache_data)
        
        return result
        
    except Exception as e:
        raise FinancialDataError(f"Failed to calculate spread for {ticker}: {e}")


__all__ = [
    'extract_roic_history',
    'extract_wacc_components',
    'calculate_wacc',
    'calculate_spread',
    'ROICData',
    'WACCComponents',
    'WACCResult',
    'SpreadResult',
    'FinancialDataError',
    'InsufficientDataError',
    'DEFAULT_RISK_FREE_RATE',
    'DEFAULT_MARKET_RISK_PREMIUM',
    'DEFAULT_BETA',
]
