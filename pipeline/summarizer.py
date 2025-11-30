"""
Filing summarizer for extracting key information from SEC filings.

This module provides functionality to extract key points and create
structured summaries from filing data.
"""

import re
from typing import List, Dict, Any

# Key phrases to look for in filing text
# These indicate important events that might affect stock price
KEY_PHRASES = {
    'officer_changes': [
        'officer', 'departure', 'resignation', 'appointment', 'termination',
        'executive', 'management', 'leadership', 'board', 'director'
    ],
    'financial_performance': [
        'earnings', 'revenue', 'profit', 'loss', 'guidance', 'forecast',
        'outlook', 'warning', 'miss', 'beat', 'exceed', 'fall short'
    ],
    'corporate_actions': [
        'acquisition', 'merger', 'takeover', 'buyout', 'divestiture',
        'spin-off', 'split', 'reorganization', 'restructuring'
    ],
    'dividend_changes': [
        'dividend', 'distribution', 'payout', 'split', 'suspension',
        'increase', 'decrease', 'cut', 'eliminate'
    ],
    'legal_regulatory': [
        'lawsuit', 'litigation', 'investigation', 'regulatory', 'compliance',
        'settlement', 'fine', 'penalty', 'violation', 'enforcement'
    ],
    'offering_financing': [
        'offering', 'financing', 'capital', 'raise', 'issue', 'securities',
        'debt', 'equity', 'shares', 'stock', 'convertible'
    ]
}


def extract_key_points(filing: Dict[str, Any]) -> List[str]:
    """
    Extract key points from filing text based on important phrases.
    
    Args:
        filing: Filing dictionary with 'summary' field
        
    Returns:
        List of key point strings (max 3)
    """
    summary = filing.get('summary', '').lower()
    form_type = filing.get('form_type', '').upper()
    
    if not summary:
        return []
    
    key_points = []
    
    # Check each category of key phrases
    for category, phrases in KEY_PHRASES.items():
        found_phrases = []
        
        for phrase in phrases:
            if phrase in summary:
                found_phrases.append(phrase)
        
        if found_phrases:
            # Create a descriptive key point for this category
            key_point = _create_key_point(category, found_phrases, form_type)
            if key_point:
                key_points.append(key_point)
    
    # Also check for individual important words as fallback
    important_words = ['officer', 'departure', 'resignation', 'acquisition', 'merger', 'dividend', 'warning', 'risk']
    for word in important_words:
        if word in summary and not any(word in kp.lower() for kp in key_points):
            key_points.append(word.title())
    
    # Limit to top 3 most important key points
    key_points = key_points[:3]
    
    return key_points


def _create_key_point(category: str, phrases: List[str], form_type: str) -> str:
    """
    Create a descriptive key point from found phrases.
    
    Args:
        category: Category of key phrases
        phrases: List of phrases found in text
        form_type: SEC form type
        
    Returns:
        Descriptive key point string
    """
    category_titles = {
        'officer_changes': 'Officer changes',
        'financial_performance': 'Financial performance',
        'corporate_actions': 'Corporate actions',
        'dividend_changes': 'Dividend changes',
        'legal_regulatory': 'Legal/regulatory',
        'offering_financing': 'Financing activities'
    }
    
    base_title = category_titles.get(category, category.replace('_', ' ').title())
    
    # Add form type context for certain categories
    if form_type == '8-K' and category in ['officer_changes', 'corporate_actions']:
        return f"8-K: {base_title}"
    elif form_type in ['10-Q', '10-K'] and category == 'financial_performance':
        return f"{form_type}: {base_title}"
    
    return base_title


def create_filing_summary(filing: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a structured filing summary for display.
    
    Args:
        filing: Filing dictionary with basic information
        
    Returns:
        Structured summary with all required fields
    """
    return {
        'form_type': filing.get('form_type', 'Unknown'),
        'filed_date': filing.get('filed_date', ''),
        'key_points': extract_key_points(filing),
        'summary': _clean_summary(filing.get('summary', '')),
        'url': filing.get('url', ''),
        'relevance_score': filing.get('relevance_score', 0.5)
    }


def _clean_summary(summary: str) -> str:
    """
    Clean and format summary text for display.
    
    Args:
        summary: Raw summary text
        
    Returns:
        Cleaned summary text
    """
    if not summary or summary.strip() == '':
        return "No summary available"
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', summary.strip())
    
    # Remove common filing boilerplate
    boilerplate_patterns = [
        r'SECURITIES AND EXCHANGE COMMISSION.*?\n',
        r'FORM [0-9A-K-]+.*?\n',
        r'ACCESSION NUMBER.*?\n',
        r'PUBLIC DOCUMENT COUNT.*?\n',
        r'CONFORMED SUBMISSION TYPE.*?\n',
    ]
    
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Truncate if too long
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    
    return cleaned


def extract_financial_metrics(summary: str) -> Dict[str, str]:
    """
    Extract financial metrics from filing summary.
    
    Args:
        summary: Filing summary text
        
    Returns:
        Dictionary of extracted metrics
    """
    metrics = {}
    
    # Look for revenue figures
    revenue_pattern = r'revenue.*?\$?([\d,\.]+)\s*(billion|million|thousand)'
    revenue_match = re.search(revenue_pattern, summary, re.IGNORECASE)
    if revenue_match:
        metrics['revenue'] = f"${revenue_match.group(1)} {revenue_match.group(2)}"
    
    # Look for earnings per share
    eps_pattern = r'eps.*?\$?([\d,\.]+)'
    eps_match = re.search(eps_pattern, summary, re.IGNORECASE)
    if eps_match:
        metrics['eps'] = f"${eps_match.group(1)}"
    
    # Look for percentage changes
    percent_pattern = r'([+-]?\d+\.?\d*)%'
    percent_matches = re.findall(percent_pattern, summary)
    if percent_matches:
        metrics['percent_changes'] = percent_matches
    
    return metrics


def is_earnings_related(filing: Dict[str, Any]) -> bool:
    """
    Check if filing is likely earnings-related.
    
    Args:
        filing: Filing dictionary
        
    Returns:
        True if filing appears to be earnings-related
    """
    form_type = filing.get('form_type', '').upper()
    summary = filing.get('summary', '').lower()
    
    # Form types that are typically earnings-related
    earnings_forms = ['10-Q', '10-K', '8-K']
    
    if form_type not in earnings_forms:
        return False
    
    # Check for earnings keywords
    earnings_keywords = [
        'earnings', 'revenue', 'profit', 'loss', 'quarterly results',
        'financial results', 'operating results', 'net income'
    ]
    
    return any(keyword in summary for keyword in earnings_keywords)