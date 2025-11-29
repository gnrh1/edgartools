"""Tests for the Polygon API integration module."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from edgar.polygon import (
    PolygonAPIError,
    fetch_aapl_prices,
    fetch_aapl_last_7_days,
    get_prices_state,
    get_prices_state_path,
    save_prices_state,
    get_empty_state,
    get_polygon_api_key,
    detect_price_drop_alert,
    get_alerts_path,
    save_alerts
)


class TestPolygonAPI:
    """Test Polygon API integration."""

    def test_get_prices_state_path(self):
        """Test that prices state path points to correct location."""
        path = get_prices_state_path()
        assert path.name == 'prices_state.json'
        assert 'data' in str(path)

    def test_get_empty_state(self):
        """Test that empty state has correct structure."""
        state = get_empty_state()
        assert 'timestamp' in state
        assert 'prices' in state
        assert 'last_fetch_timestamp' in state
        assert isinstance(state['prices'], list)
        assert len(state['prices']) == 0

    def test_get_prices_state_loads_existing(self):
        """Test that get_prices_state loads existing state file."""
        state = get_prices_state()
        assert isinstance(state, dict)
        assert all(k in state for k in ['timestamp', 'prices', 'last_fetch_timestamp'])

    def test_prices_state_structure(self):
        """Test that loaded state has correct structure."""
        state = get_prices_state()
        if state['prices']:
            price = state['prices'][0]
            assert all(k in price for k in ['date', 'close', 'volume'])

    def test_save_prices_state(self):
        """Test saving prices state."""
        test_state = {
            'timestamp': '2024-01-01T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'close': 150.0, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 151.0, 'volume': 1100000}
            ],
            'last_fetch_timestamp': '2024-01-02T00:00:00'
        }
        
        save_prices_state(test_state)
        
        loaded_state = get_prices_state()
        assert loaded_state['timestamp'] == test_state['timestamp']
        assert len(loaded_state['prices']) == 2
        assert loaded_state['prices'][0]['close'] == 150.0

    def test_get_polygon_api_key_missing(self):
        """Test that missing API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(PolygonAPIError, match="POLYGON_API_KEY"):
                get_polygon_api_key()

    def test_get_polygon_api_key_present(self):
        """Test that API key is retrieved when present."""
        with patch.dict(os.environ, {'POLYGON_API_KEY': 'test-key'}):
            api_key = get_polygon_api_key()
            assert api_key == 'test-key'

    @patch('edgar.polygon.httpx.Client')
    def test_fetch_aapl_prices_success(self, mock_client_class):
        """Test successful AAPL prices fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'from': '2024-01-01',
            'c': 150.0,
            'v': 1000000
        }
        
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        with patch.dict(os.environ, {'POLYGON_API_KEY': 'test-key'}):
            result = fetch_aapl_prices()
            
            assert 'timestamp' in result
            assert 'prices' in result
            assert 'last_fetch_timestamp' in result
            assert len(result['prices']) > 0

    @patch('edgar.polygon.httpx.Client')
    def test_fetch_aapl_prices_with_results(self, mock_client_class):
        """Test fetch with paginated results."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {'date': '2024-01-01', 'close': 150.0, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 151.0, 'volume': 1100000}
            ]
        }
        
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        with patch.dict(os.environ, {'POLYGON_API_KEY': 'test-key'}):
            result = fetch_aapl_prices()
            assert len(result['prices']) == 2

    @patch('edgar.polygon.httpx.Client')
    def test_fetch_aapl_prices_http_error(self, mock_client_class):
        """Test that HTTP errors are handled."""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        with patch.dict(os.environ, {'POLYGON_API_KEY': 'test-key'}):
            with pytest.raises(PolygonAPIError):
                fetch_aapl_prices()

    def test_fetch_aapl_last_7_days(self):
        """Test convenience function for last 7 days."""
        with patch('edgar.polygon.fetch_aapl_prices') as mock_fetch:
            mock_fetch.return_value = {'prices': []}
            
            result = fetch_aapl_last_7_days(api_key='test-key')
            
            mock_fetch.assert_called_once_with(ticker='AAPL', days=7, api_key='test-key')

    def test_error_log_file_creation(self):
        """Test that error log file is created."""
        error_log_file = Path.home() / 'fetch_errors.log'
        
        with patch.dict(os.environ, {}, clear=True):
            try:
                fetch_aapl_prices()
            except PolygonAPIError:
                pass
        
        assert error_log_file.exists()


class TestPriceDropAlertDetector:
    """Test price drop alert detection functionality."""

    def test_get_alerts_path(self):
        """Test that alerts path points to correct location."""
        path = get_alerts_path()
        assert path.name == 'alerts.json'
        assert 'data' in str(path)

    def test_save_alerts(self):
        """Test saving alerts to file."""
        test_alert = {
            'alert_triggered': True,
            'price_first_close': 235.50,
            'price_last_close': 223.10,
            'drop_percentage': 5.26,
            'reason': 'price_drop_5.26%'
        }
        
        save_alerts(test_alert)
        
        # Verify file was created and contains correct data
        alerts_path = get_alerts_path()
        assert alerts_path.exists()
        
        with open(alerts_path, 'r') as f:
            saved_alert = json.load(f)
        
        assert saved_alert['alert_triggered'] == True
        assert saved_alert['price_first_close'] == 235.50
        assert saved_alert['drop_percentage'] == 5.26

    def test_detect_price_drop_alert_triggers_correctly(self):
        """Test that 5%+ drop triggers alert correctly (235.50 → 223.10 = 5.26% drop)."""
        # Create test state with 5%+ drop
        test_state = {
            'timestamp': '2024-01-07T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'close': 235.50, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 234.00, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 230.50, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 225.75, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 223.10, 'volume': 1400000},
                {'date': '2024-01-06', 'close': 224.00, 'volume': 1500000},
                {'date': '2024-01-07', 'close': 223.10, 'volume': 1600000}
            ],
            'last_fetch_timestamp': '2024-01-07T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test alert detection
        alert = detect_price_drop_alert()
        
        # Verify alert triggered
        assert alert['alert_triggered'] == True
        assert alert['price_first_close'] == 235.50
        assert alert['price_last_close'] == 223.10
        
        # Verify drop calculation: (235.50 - 223.10) / 235.50 * 100 = 5.26%
        expected_drop = ((235.50 - 223.10) / 235.50) * 100
        assert abs(alert['drop_percentage'] - expected_drop) < 0.01
        assert alert['drop_percentage'] >= 5.0
        assert 'price_drop_' in alert['reason']

    def test_detect_price_drop_alert_no_trigger_under_5_percent(self):
        """Test that <5% drop does NOT trigger alert (235.50 → 233.15 = 1% drop)."""
        # Create test state with <5% drop
        test_state = {
            'timestamp': '2024-01-07T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'close': 235.50, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 235.00, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 234.50, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 234.00, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 233.50, 'volume': 1400000},
                {'date': '2024-01-06', 'close': 233.25, 'volume': 1500000},
                {'date': '2024-01-07', 'close': 233.15, 'volume': 1600000}
            ],
            'last_fetch_timestamp': '2024-01-07T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test alert detection
        alert = detect_price_drop_alert()
        
        # Verify alert NOT triggered
        assert alert['alert_triggered'] == False
        assert alert['price_first_close'] == 235.50
        assert alert['price_last_close'] == 233.15
        
        # Verify drop calculation: (235.50 - 233.15) / 235.50 * 100 = ~1.0%
        expected_drop = ((235.50 - 233.15) / 235.50) * 100
        assert abs(alert['drop_percentage'] - expected_drop) < 0.01
        assert alert['drop_percentage'] < 5.0
        assert 'price_change_' in alert['reason']

    def test_detect_price_drop_alert_insufficient_data(self):
        """Test insufficient data (<5 points) returns alert_triggered=false with 'insufficient_data' reason."""
        # Create test state with only 3 data points
        test_state = {
            'timestamp': '2024-01-03T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'close': 235.50, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 233.15, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 233.15, 'volume': 1200000}
            ],
            'last_fetch_timestamp': '2024-01-03T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test alert detection
        alert = detect_price_drop_alert()
        
        # Verify insufficient data response
        assert alert['alert_triggered'] == False
        assert alert['price_first_close'] == 0.0
        assert alert['price_last_close'] == 0.0
        assert alert['drop_percentage'] == 0.0
        assert alert['reason'] == 'insufficient_data'

    def test_detect_price_drop_alert_missing_file_raises_error(self):
        """Test that missing prices_state.json raises ValueError with descriptive message."""
        # Backup existing file if it exists
        state_path = get_prices_state_path()
        backup_path = state_path.with_suffix('.backup')
        
        if state_path.exists():
            state_path.rename(backup_path)
        
        try:
            # Test that missing file raises ValueError
            with pytest.raises(ValueError, match="prices_state.json not found"):
                detect_price_drop_alert()
        finally:
            # Restore backup if it existed
            if backup_path.exists():
                backup_path.rename(state_path)

    def test_detect_price_drop_alert_malformed_file_raises_error(self):
        """Test that malformed prices_state.json raises ValueError with descriptive message."""
        # Backup existing file
        state_path = get_prices_state_path()
        backup_path = state_path.with_suffix('.backup')
        
        if state_path.exists():
            state_path.rename(backup_path)
        
        try:
            # Create malformed JSON file
            with open(state_path, 'w') as f:
                f.write('{"invalid": json content}')
            
            # Test that malformed file raises ValueError
            with pytest.raises(ValueError, match="Failed to read or parse prices_state.json"):
                detect_price_drop_alert()
        finally:
            # Restore backup if it existed
            if backup_path.exists():
                backup_path.rename(state_path)

    def test_detect_price_drop_alert_invalid_structure_raises_error(self):
        """Test that invalid structure (missing 'prices' field) raises ValueError."""
        # Create state with missing prices field
        test_state = {
            'timestamp': '2024-01-01T00:00:00',
            'last_fetch_timestamp': '2024-01-01T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test that invalid structure raises ValueError
        with pytest.raises(ValueError, match="missing 'prices' field"):
            detect_price_drop_alert()

    def test_detect_price_drop_alert_invalid_price_data_raises_error(self):
        """Test that invalid price data (missing 'close' field) raises ValueError."""
        # Create state with invalid price data
        test_state = {
            'timestamp': '2024-01-07T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'volume': 1000000},  # Missing 'close'
                {'date': '2024-01-02', 'close': 234.00, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 230.50, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 225.75, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 223.10, 'volume': 1400000}
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test that invalid price data raises ValueError
        with pytest.raises(ValueError, match="missing 'close' field"):
            detect_price_drop_alert()

    def test_detect_price_drop_alert_invalid_first_price_raises_error(self):
        """Test that invalid first close price (<= 0) raises ValueError."""
        # Create state with invalid first price
        test_state = {
            'timestamp': '2024-01-07T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'close': 0.0, 'volume': 1000000},  # Invalid price
                {'date': '2024-01-02', 'close': 234.00, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 230.50, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 225.75, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 223.10, 'volume': 1400000}
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test that invalid first price raises ValueError
        with pytest.raises(ValueError, match="Invalid first close price"):
            detect_price_drop_alert()

    def test_detect_price_drop_alert_boundary_case_exactly_5_percent(self):
        """Test boundary case: exactly 5% drop triggers alert."""
        # Create test state with exactly 5% drop: 200.00 → 190.00 = 5% drop
        test_state = {
            'timestamp': '2024-01-07T00:00:00',
            'prices': [
                {'date': '2024-01-01', 'close': 200.00, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 198.00, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 195.00, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 192.00, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 190.00, 'volume': 1400000}
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        # Save test state
        save_prices_state(test_state)
        
        # Test alert detection
        alert = detect_price_drop_alert()
        
        # Verify alert triggered (exactly 5% should trigger)
        assert alert['alert_triggered'] == True
        assert alert['price_first_close'] == 200.00
        assert alert['price_last_close'] == 190.00
        assert abs(alert['drop_percentage'] - 5.0) < 0.01
        assert 'price_drop_' in alert['reason']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
