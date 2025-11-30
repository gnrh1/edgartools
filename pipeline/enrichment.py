"""
Filing context appender for adding SEC filing context to price alerts.

This module provides functionality to enrich alert data with relevant
SEC filing information and save the enhanced alerts.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from edgar.core import log
from pipeline.polygon import get_alerts_path


def append_filing_context_to_alert(ticker: str, filings: List[Dict[str, Any]]) -> bool:
    """
    Append filing context to alerts_{TICKER}.json file.
    
    Args:
        ticker: Stock ticker symbol
        filings: List of filing summaries to append
        
    Returns:
        True if successful, False otherwise
    """
    alert_file = Path(get_alerts_path(ticker))
    
    # Check if alert file exists
    if not alert_file.exists():
        log.error(f"Alert file not found: {alert_file}")
        return False
    
    try:
        # Load existing alert data
        with open(alert_file, 'r') as f:
            alert_data = json.load(f)
        
        # Add filing context (empty if no filings)
        alert_data['filing_context'] = filings
        
        # Save enhanced alert data
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
        
        log.info(f"Added {len(filings)} filing contexts to {ticker} alert")
        return True
        
    except (json.JSONDecodeError, IOError) as e:
        log.error(f"Failed to update alert file {alert_file}: {e}")
        return False
    except Exception as e:
        log.error(f"Unexpected error updating alert file {alert_file}: {e}")
        return False


def enrich_all_alerts_with_filings(tickers: List[str]) -> Dict[str, List[str]]:
    """
    For each ticker: fetch filings, score them, append to alert JSON.
    
    This is the main integration function that combines all units:
    1. Fetch recent filings for each ticker
    2. Score relevance to price drops
    3. Create summaries
    4. Append to alert files
    
    Args:
        tickers: List of ticker symbols to process
        
    Returns:
        Dictionary with 'success' and 'failed' ticker lists
    """
    from pipeline.sec_filings import fetch_recent_filings, get_drop_date_from_alert
    from pipeline.scoring import rank_filings_by_relevance, get_top_n_relevant_filings
    from pipeline.summarizer import create_filing_summary
    
    results = {'success': [], 'failed': []}
    
    for ticker in tickers:
        try:
            log.info(f"Processing {ticker} for SEC filing context...")
            
            # Step 1: Fetch recent filings
            # Increased days_back to 90 to ensure we capture relevant quarterly/annual filings
            filings = fetch_recent_filings(ticker, days_back=90, form_types=['8-K', '10-Q', '10-K'])
            
            if not filings:
                log.info(f"No recent filings found for {ticker}")
                # Still append empty context to maintain consistency
                append_filing_context_to_alert(ticker, [])
                results['success'].append(ticker)
                continue
            
            # Step 2: Get drop date from alert
            drop_date = get_drop_date_from_alert(ticker)
            
            # Step 3: Score and rank filings by relevance
            ranked_filings = rank_filings_by_relevance(filings, drop_date)
            
            # Step 4: Get top 3 most relevant
            top_filings = get_top_n_relevant_filings(ranked_filings, drop_date, n=3)
            
            # Step 5: Create structured summaries
            summaries = [create_filing_summary(filing) for filing in top_filings]
            
            # Step 6: Append to alert file
            success = append_filing_context_to_alert(ticker, summaries)
            
            if success:
                results['success'].append(ticker)
                log.info(f"✓ Enriched {ticker} with {len(summaries)} filing contexts")
            else:
                results['failed'].append(ticker)
                log.error(f"✗ Failed to save enriched alert for {ticker}")
                
        except Exception as e:
            results['failed'].append(ticker)
            log.error(f"✗ Failed to enrich alerts for {ticker}: {e}")
    
    # Log summary
    total = len(tickers)
    successful = len(results['success'])
    failed = len(results['failed'])
    
    log.info(f"SEC filing enrichment complete: {successful}/{total} successful, {failed} failed")
    
    return results


def get_filing_context_from_alert(ticker: str) -> List[Dict[str, Any]]:
    """
    Retrieve filing context from an alert file.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        List of filing contexts (empty if none or file not found)
    """
    alert_file = Path(get_alerts_path(ticker))
    
    if not alert_file.exists():
        return []
    
    try:
        with open(alert_file, 'r') as f:
            alert_data = json.load(f)
        
        return alert_data.get('filing_context', [])
        
    except (json.JSONDecodeError, IOError):
        log.warning(f"Could not read filing context from {ticker} alert file")
        return []


def has_filing_context(ticker: str) -> bool:
    """
    Check if an alert has filing context.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        True if filing context exists and is not empty
    """
    context = get_filing_context_from_alert(ticker)
    return len(context) > 0


def clear_filing_context(ticker: str) -> bool:
    """
    Remove filing context from an alert file.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        True if successful, False otherwise
    """
    return append_filing_context_to_alert(ticker, [])


def get_filing_context_summary(ticker: str) -> str:
    """
    Get a brief summary of filing context for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Human-readable summary string
    """
    context = get_filing_context_from_alert(ticker)
    
    if not context:
        return "No recent filings"
    
    # Count by form type
    form_counts = {}
    for filing in context:
        form_type = filing.get('form_type', 'Unknown')
        form_counts[form_type] = form_counts.get(form_type, 0) + 1
    
    # Create summary
    parts = []
    for form_type, count in form_counts.items():
        parts.append(f"{count} {form_type}")
    
    return f"{len(context)} recent filings: {', '.join(parts)}"


def validate_filing_context_structure(context: List[Dict[str, Any]]) -> bool:
    """
    Validate that filing context has the correct structure.
    
    Args:
        context: List of filing context dictionaries
        
    Returns:
        True if structure is valid, False otherwise
    """
    if not isinstance(context, list):
        return False
    
    required_fields = ['form_type', 'filed_date', 'key_points', 'summary', 'url', 'relevance_score']
    
    for filing in context:
        if not isinstance(filing, dict):
            return False
        
        # Check all required fields exist
        for field in required_fields:
            if field not in filing:
                return False
        
        # Check field types
        if not isinstance(filing['form_type'], str):
            return False
        if not isinstance(filing['filed_date'], str):
            return False
        if not isinstance(filing['key_points'], list):
            return False
        if not isinstance(filing['summary'], str):
            return False
        if not isinstance(filing['url'], str):
            return False
        if not isinstance(filing['relevance_score'], (int, float)):
            return False
    
    return True


def safe_enrich_all_alerts(tickers: List[str]) -> Dict[str, List[str]]:
    """
    Enrich alerts with comprehensive error handling and validation.
    
    This is a production-ready version that includes additional safety checks:
    - Validates filing context structure before saving
    - Handles partial failures gracefully
    - Provides detailed error reporting
    
    Args:
        tickers: List of ticker symbols to process
        
    Returns:
        Dictionary with 'success', 'failed', and 'errors' keys
    """
    from pipeline.sec_filings import fetch_recent_filings, get_drop_date_from_alert, FilingError
    from pipeline.scoring import rank_filings_by_relevance, get_top_n_relevant_filings
    from pipeline.summarizer import create_filing_summary
    
    results = {
        'success': [],
        'failed': [],
        'errors': {}
    }
    
    for ticker in tickers:
        try:
            log.info(f"Processing {ticker} for SEC filing context...")
            
            # Step 1: Fetch recent filings
            try:
                # Increased days_back to 90 to ensure we capture relevant quarterly/annual filings
                filings = fetch_recent_filings(ticker, days_back=90, form_types=['8-K', '10-Q', '10-K'])
            except FilingError as e:
                results['failed'].append(ticker)
                results['errors'][ticker] = f"Filing fetch failed: {e}"
                continue
            
            if not filings:
                log.info(f"No recent filings found for {ticker}")
                # Still append empty context to maintain consistency
                if append_filing_context_to_alert(ticker, []):
                    results['success'].append(ticker)
                else:
                    results['failed'].append(ticker)
                    results['errors'][ticker] = "Failed to save empty context"
                continue
            
            # Step 2: Get drop date from alert
            drop_date = get_drop_date_from_alert(ticker)
            
            # Step 3: Score and rank filings by relevance
            ranked_filings = rank_filings_by_relevance(filings, drop_date)
            
            # Step 4: Get top 3 most relevant
            top_filings = get_top_n_relevant_filings(ranked_filings, drop_date, n=3)
            
            # Step 5: Create structured summaries
            summaries = [create_filing_summary(filing) for filing in top_filings]
            
            # Step 6: Validate structure before saving
            if not validate_filing_context_structure(summaries):
                results['failed'].append(ticker)
                results['errors'][ticker] = "Invalid filing context structure"
                continue
            
            # Step 7: Append to alert file
            success = append_filing_context_to_alert(ticker, summaries)
            
            if success:
                results['success'].append(ticker)
                log.info(f"✓ Enriched {ticker} with {len(summaries)} filing contexts")
            else:
                results['failed'].append(ticker)
                results['errors'][ticker] = "Failed to save enriched alert"
                
        except Exception as e:
            results['failed'].append(ticker)
            results['errors'][ticker] = f"Unexpected error: {e}"
            log.error(f"✗ Unexpected error for {ticker}: {e}")
    
    # Log summary
    total = len(tickers)
    successful = len(results['success'])
    failed = len(results['failed'])
    
    log.info(f"SEC filing enrichment complete: {successful}/{total} successful, {failed} failed")
    
    if failed > 0:
        log.warning(f"Failed tickers: {', '.join(results['failed'])}")
    
    return results