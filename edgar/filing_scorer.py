"""
Filing relevance scorer for ranking SEC filings by relevance to price movements.

This module provides functionality to score how relevant a filing is likely
to be to a stock price drop based on timing and filing type.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any

# Relevance scoring constants
# Higher scores indicate higher relevance to price movements

# Form type base scores
FORM_TYPE_BASE_SCORES = {
    '8-K': 0.9,   # Current events - highly relevant
    '10-Q': 0.6,  # Quarterly results - moderately relevant  
    '10-K': 0.3,  # Annual report - less relevant for recent drops
    '4': 0.4,      # Insider trades - moderately relevant
    '6-K': 0.7,    # Foreign private issuer current events
    '8-A': 0.2,    # Registration of securities
}

# Time decay rates (points lost per day)
TIME_DECAY_RATES = {
    '8-K': 0.05,    # 8-K relevance decays quickly
    '10-Q': 0.03,    # 10-Q relevance decays moderately
    '10-K': 0.01,    # 10-K relevance decays slowly
    '4': 0.04,       # Insider trades decay moderately fast
    '6-K': 0.05,     # Foreign current events decay quickly
}


def score_filing_relevance(filing: Dict[str, Any], drop_date: str) -> float:
    """
    Score how relevant a filing is to a stock price drop.
    
    Scoring logic:
    - Base score depends on form type (8-K highest, 10-K lowest)
    - Time decay: older filings get lower scores
    - Special cases: same-day 8-K gets maximum score
    
    Args:
        filing: Filing dictionary with 'form_type' and 'filed_date' keys
        drop_date: Date of price drop in 'YYYY-MM-DD' format
        
    Returns:
        Relevance score between 0.0 and 1.0
        (0.0 = not relevant, 1.0 = highly relevant)
    """
    try:
        filed_date = datetime.strptime(filing['filed_date'], '%Y-%m-%d')
        drop_date_obj = datetime.strptime(drop_date, '%Y-%m-%d')
    except (ValueError, KeyError) as e:
        # If we can't parse dates, return low score
        return 0.1
    
    form_type = filing.get('form_type', '').upper()
    days_diff = abs((drop_date_obj - filed_date).days)
    
    # Special case scoring for specific scenarios
    if form_type == '8-K' and days_diff == 0:
        return 0.95
    elif form_type == '8-K' and days_diff == 1:
        return 0.85
    elif form_type == '10-Q' and days_diff <= 7:
        return 0.65
    elif form_type == '10-Q' and days_diff <= 14:
        return 0.45
    elif form_type == '10-K' and days_diff <= 30:
        return 0.30
    
    # Get base score for form type
    base_score = FORM_TYPE_BASE_SCORES.get(form_type, 0.2)
    
    # Apply time decay
    decay_rate = TIME_DECAY_RATES.get(form_type, 0.02)
    time_penalty = days_diff * decay_rate
    score = base_score - time_penalty
    
    # Ensure score is within bounds
    score = max(0.0, min(1.0, score))
    
    return score


def rank_filings_by_relevance(filings: List[Dict[str, Any]], drop_date: str) -> List[Dict[str, Any]]:
    """
    Rank filings by relevance to a specific drop date.
    
    Args:
        filings: List of filing dictionaries
        drop_date: Date of price drop in 'YYYY-MM-DD' format
        
    Returns:
        List of filings sorted by relevance (highest first),
        each with added 'relevance_score' field
    """
    scored_filings = []
    
    for filing in filings:
        # Calculate relevance score
        relevance_score = score_filing_relevance(filing, drop_date)
        
        # Add score to filing copy (don't modify original)
        scored_filing = filing.copy()
        scored_filing['relevance_score'] = relevance_score
        scored_filings.append(scored_filing)
    
    # Sort by relevance score (highest first)
    ranked_filings = sorted(scored_filings, key=lambda x: x['relevance_score'], reverse=True)
    
    return ranked_filings


def get_relevance_label(score: float) -> str:
    """
    Get human-readable relevance label from score.
    
    Args:
        score: Relevance score between 0.0 and 1.0
        
    Returns:
        Human-readable label string
    """
    if score >= 0.8:
        return "Strongly related"
    elif score >= 0.6:
        return "Likely related"
    elif score >= 0.4:
        return "Possibly related"
    elif score >= 0.2:
        return "Probably unrelated"
    else:
        return "Unlikely related"


def get_top_n_relevant_filings(filings: List[Dict[str, Any]], drop_date: str, n: int = 3) -> List[Dict[str, Any]]:
    """
    Get top N most relevant filings for a drop date.
    
    Args:
        filings: List of filing dictionaries
        drop_date: Date of price drop in 'YYYY-MM-DD' format
        n: Maximum number of filings to return
        
    Returns:
        Top N filings sorted by relevance
    """
    ranked = rank_filings_by_relevance(filings, drop_date)
    return ranked[:n]