"""
SEC filing fetcher for retrieving recent company filings.

This module provides functionality to query edgartools for recent SEC filings
and extract relevant information for price alert context.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

from edgar.core import log
from edgar.entity import Company


class FilingError(Exception):
    """Exception raised for SEC filing-related errors."""
    pass


def fetch_recent_filings(ticker: str, days_back: int = 2, form_types: List[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch recent SEC filings for a ticker.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        days_back: Number of days to look back for filings (default: 2)
        form_types: List of form types to fetch (default: ['8-K', '10-Q', '10-K'])
        
    Returns:
        List of filing dictionaries with keys:
            - form_type: The SEC form type
            - filed_date: Date filed (YYYY-MM-DD format)
            - url: URL to the filing document
            - summary: Brief summary of filing content
            
    Raises:
        FilingError: If company lookup fails or other errors occur
    """
    if form_types is None:
        form_types = ['8-K', '10-Q', '10-K']
    
    try:
        # Get company object from edgartools
        company = Company(ticker)
    except Exception as e:
        raise FilingError(f"Failed to load company {ticker}: {e}")
    
    filings = []
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    for form_type in form_types:
        try:
            # Get filings for this form type
            form_filings = company.get_filings(form=form_type, trigger_full_load=False)
            
            # Process each filing
            for filing in form_filings:
                # Check if filing is within our date range
                # Try different possible date attribute names
                filing_date = None
                date_attrs = ['filing_date', 'date', 'filed_at', 'period']
                
                for attr in date_attrs:
                    if hasattr(filing, attr):
                        filing_date = getattr(filing, attr)
                        break
                
                if filing_date is None:
                    continue
                
                # Convert to datetime if needed
                if isinstance(filing_date, str):
                    try:
                        filing_date = datetime.strptime(filing_date, '%Y-%m-%d')
                    except ValueError:
                        continue
                elif not isinstance(filing_date, datetime):
                    continue
                
                if filing_date >= cutoff_date:
                    filing_info = {
                        'form_type': form_type,
                        'filed_date': filing_date.strftime('%Y-%m-%d'),
                        'url': getattr(filing, 'document_url', getattr(filing, 'url', '')),
                    }
                    
                    # Extract summary from available fields
                    summary = _extract_filing_summary(filing)
                    filing_info['summary'] = summary
                    
                    filings.append(filing_info)
                    
        except Exception as e:
            log.warning(f"Could not fetch {form_type} for {ticker}: {e}")
            continue
    
    return filings


def _extract_filing_summary(filing) -> str:
    """
    Extract a summary from a filing object.
    
    Args:
        filing: edgartools Filing object
        
    Returns:
        String summary of the filing content
    """
    # Try different fields that might contain summary information
    summary_fields = [
        'item_1a_risk_factors',
        'item_1_business', 
        'item_7_mdna',
        'description',
        'title'
    ]
    
    for field in summary_fields:
        if hasattr(filing, field):
            content = getattr(filing, field)
            if content and isinstance(content, str):
                # Truncate to reasonable length for summary
                return content[:200] + "..." if len(content) > 200 else content
    
    # If no summary found, try to get basic info
    if hasattr(filing, 'form_type') and hasattr(filing, 'filing_date'):
        return f"{filing.form_type} filed on {filing.filing_date.strftime('%Y-%m-%d')}"
    
    return "No summary available"


def get_drop_date_from_alert(ticker: str) -> str:
    """
    Get the drop date from alert data for a given ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Date string in YYYY-MM-DD format (defaults to today)
    """
    try:
        from edgar.polygon import get_alerts_path
        import json
        from pathlib import Path
        
        alert_path = get_alerts_path(ticker)
        if alert_path.exists():
            with open(alert_path, 'r') as f:
                alert_data = json.load(f)
            # For now, return today's date - in a real implementation,
            # this might extract the actual alert date from the data
            return datetime.now().strftime('%Y-%m-%d')
    except Exception:
        pass
    
    return datetime.now().strftime('%Y-%m-%d')