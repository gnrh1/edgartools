"""
Polygon API integration for fetching stock market data.

Provides functionality to fetch stock price data from Polygon API,
manage state persistence, and handle errors gracefully.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx

from edgar.core import log

__all__ = ['fetch_aapl_prices', 'fetch_aapl_last_7_days', 'get_prices_state', 'save_prices_state', 'PolygonAPIError', 'get_prices_state_path', 'detect_price_drop_alert', 'get_alerts_path', 'save_alerts']


# Set up error logging
error_logger = logging.getLogger('polygon_errors')
error_log_file = Path.home() / 'fetch_errors.log'

# Create error logger handler
if not error_logger.handlers:
    handler = logging.FileHandler(error_log_file)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    error_logger.addHandler(handler)
    error_logger.setLevel(logging.ERROR)


class PolygonAPIError(Exception):
    """Exception raised for Polygon API errors."""
    pass


def get_polygon_api_key() -> str:
    """
    Get Polygon API key from environment variable.
    
    Returns:
        str: The API key
        
    Raises:
        PolygonAPIError: If POLYGON_API_KEY is not set
    """
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        error_msg = "POLYGON_API_KEY environment variable not set"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)
    return api_key


def get_prices_state_path() -> Path:
    """
    Get the path to the prices state file.
    
    Returns:
        Path: The absolute path to prices_state.json in the project data directory
    """
    module_dir = Path(__file__).parent
    project_root = module_dir.parent
    data_dir = project_root / 'data' / 'prices_state.json'
    return data_dir


def get_prices_state() -> Dict[str, Any]:
    """
    Load the prices state from file.
    
    Returns:
        dict: The state dictionary with keys: timestamp, prices, last_fetch_timestamp
        Returns empty state if file doesn't exist.
    """
    state_path = get_prices_state_path()
    
    if state_path.exists():
        try:
            with open(state_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            log.warning(f"Could not read prices state file: {e}")
            return get_empty_state()
    
    return get_empty_state()


def get_empty_state() -> Dict[str, Any]:
    """
    Get an empty state dictionary.
    
    Returns:
        dict: Empty state with default structure
    """
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'prices': [],
        'last_fetch_timestamp': None
    }


def save_prices_state(state: Dict[str, Any]) -> None:
    """
    Save the prices state to file.
    
    Args:
        state: Dictionary containing timestamp, prices, and last_fetch_timestamp
    """
    state_path = get_prices_state_path()
    
    try:
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
        log.info(f"Prices state saved to {state_path}")
    except IOError as e:
        error_msg = f"Failed to save prices state: {e}"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)


def fetch_aapl_prices(ticker: str = 'AAPL', days: int = 7, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch AAPL stock prices for the last N days from Polygon API.
    
    Args:
        ticker: Stock ticker symbol (default: 'AAPL')
        days: Number of days to fetch (default: 7)
        api_key: Polygon API key (optional, defaults to env variable)
        
    Returns:
        dict: Dictionary with keys:
            - timestamp: When the fetch was performed
            - prices: List of price dicts with keys: date, close, volume
            - last_fetch_timestamp: ISO format timestamp of fetch
            
    Raises:
        PolygonAPIError: If API call fails or response is invalid
    """
    if not api_key:
        api_key = get_polygon_api_key()
    
    try:
        # Calculate date range
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Construct API URL for aggregates endpoint (handles multiple days)
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
        
        # Make request
        with httpx.Client() as client:
            response = client.get(
                url,
                params={'adjusted': 'true', 'apiKey': api_key},
                timeout=30.0
            )
            response.raise_for_status()
            
            data = response.json()
        
        # Parse response
        if not data.get('status') == 'OK':
            error_msg = f"Polygon API returned non-OK status: {data.get('status')}"
            error_logger.error(error_msg)
            raise PolygonAPIError(error_msg)
        
        # Extract prices
        prices = []
        if 'results' in data:
            # Handle paginated results
            for result in data['results']:
                prices.append({
                    'date': result.get('t') or result.get('date'),
                    'close': result.get('c'),
                    'volume': result.get('v')
                })
        elif 'c' in data:
            # Handle single day response (from open-close endpoint)
            prices.append({
                'date': data.get('from'),
                'close': data.get('c'),
                'volume': data.get('v')
            })
        
        # Create state
        now = datetime.utcnow().isoformat()
        state = {
            'timestamp': now,
            'prices': prices,
            'last_fetch_timestamp': now
        }
        
        # Save state
        save_prices_state(state)
        
        log.info(f"Successfully fetched {len(prices)} price records for {ticker}")
        return state
        
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error fetching Polygon API: {e.response.status_code} - {e}"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)
    except httpx.RequestError as e:
        error_msg = f"Request error fetching Polygon API: {e}"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)
    except (KeyError, ValueError) as e:
        error_msg = f"Error parsing Polygon API response: {e}"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error fetching Polygon prices: {e}"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)


def fetch_aapl_last_7_days(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to fetch AAPL prices for the last 7 days.
    
    Args:
        api_key: Polygon API key (optional, defaults to env variable)
        
    Returns:
        dict: State dictionary with prices
        
    Raises:
        PolygonAPIError: If API call fails
    """
    return fetch_aapl_prices(ticker='AAPL', days=7, api_key=api_key)


def get_alerts_path() -> Path:
    """
    Get the path to the alerts file.
    
    Returns:
        Path: The absolute path to alerts.json in the project data directory
    """
    module_dir = Path(__file__).parent
    project_root = module_dir.parent
    data_dir = project_root / 'data' / 'alerts.json'
    return data_dir


def save_alerts(alerts: Dict[str, Any]) -> None:
    """
    Save the alerts to file.
    
    Args:
        alerts: Dictionary containing alert information
    """
    alerts_path = get_alerts_path()
    
    try:
        with open(alerts_path, 'w') as f:
            json.dump(alerts, f, indent=2)
        log.info(f"Alerts saved to {alerts_path}")
    except IOError as e:
        error_msg = f"Failed to save alerts: {e}"
        log.error(error_msg)
        error_logger.error(error_msg)
        raise PolygonAPIError(error_msg)


def detect_price_drop_alert() -> Dict[str, Any]:
    """
    Detect price drop alerts based on prices_state.json data.
    
    Reads prices_state.json and calculates 7-day price change.
    Alert triggers if drop >= 5%.
    
    Returns:
        dict: Alert information with structure:
            {
                'alert_triggered': bool,
                'price_first_close': float,
                'price_last_close': float,
                'drop_percentage': float,
                'reason': str
            }
            
    Raises:
        ValueError: If prices_state.json is missing or malformed
        PolygonAPIError: If there are file access issues
    """
    # Load prices state
    state_path = get_prices_state_path()
    
    # Check if file exists
    if not state_path.exists():
        error_msg = f"prices_state.json not found at {state_path}. Please run price fetching first."
        log.error(error_msg)
        raise ValueError(error_msg)
    
    # Load and validate state
    try:
        state = get_prices_state()
    except Exception as e:
        error_msg = f"Failed to read or parse prices_state.json: {e}"
        log.error(error_msg)
        raise ValueError(error_msg)
    
    # Check if we got empty state (indicating parsing failure)
    if not state.get('prices') and state_path.exists():
        # Try to read the file directly to detect parsing errors
        try:
            with open(state_path, 'r') as f:
                content = f.read()
                json.loads(content)  # This will raise JSONDecodeError if malformed
        except (json.JSONDecodeError, IOError) as e:
            error_msg = f"Failed to read or parse prices_state.json: {e}"
            log.error(error_msg)
            raise ValueError(error_msg)
    
    # Validate state structure
    if not isinstance(state, dict) or 'prices' not in state:
        error_msg = "prices_state.json has invalid structure: missing 'prices' field"
        log.error(error_msg)
        raise ValueError(error_msg)
    
    prices = state['prices']
    
    # Check minimum data points requirement
    if not isinstance(prices, list) or len(prices) < 5:
        reason = "insufficient_data"
        log.warning(f"Insufficient price data: {len(prices) if isinstance(prices, list) else 0} points (minimum 5 required)")
        return {
            'alert_triggered': False,
            'price_first_close': 0.0,
            'price_last_close': 0.0,
            'drop_percentage': 0.0,
            'reason': reason
        }
    
    # Validate price data structure
    try:
        # Sort prices by date to ensure chronological order
        sorted_prices = sorted(prices, key=lambda p: p['date'])
        
        # Get first and last close prices
        first_price = sorted_prices[0]
        last_price = sorted_prices[-1]
        
        if 'close' not in first_price or 'close' not in last_price:
            error_msg = "Price data missing 'close' field"
            log.error(error_msg)
            raise ValueError(error_msg)
        
        price_first_close = float(first_price['close'])
        price_last_close = float(last_price['close'])
        
        # Validate price values
        if price_first_close <= 0:
            error_msg = f"Invalid first close price: {price_first_close} (must be > 0)"
            log.error(error_msg)
            raise ValueError(error_msg)
        
    except (KeyError, TypeError, ValueError) as e:
        error_msg = f"Invalid price data structure: {e}"
        log.error(error_msg)
        raise ValueError(error_msg)
    
    # Calculate drop percentage
    drop_percentage = ((price_first_close - price_last_close) / price_first_close) * 100
    
    # Determine if alert should trigger
    alert_triggered = drop_percentage >= 5.0
    
    # Generate reason
    if alert_triggered:
        reason = f"price_drop_{drop_percentage:.2f}%"
    else:
        reason = f"price_change_{drop_percentage:.2f}%"
    
    # Create alert
    alert = {
        'alert_triggered': alert_triggered,
        'price_first_close': price_first_close,
        'price_last_close': price_last_close,
        'drop_percentage': drop_percentage,
        'reason': reason
    }
    
    log.info(f"Price drop analysis: {drop_percentage:.2f}% change, alert_triggered={alert_triggered}")
    
    # Save alert
    save_alerts(alert)
    
    return alert
