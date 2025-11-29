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
    get_polygon_api_key
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
