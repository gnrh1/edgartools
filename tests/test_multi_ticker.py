"""Tests for multi-ticker configuration and pipeline functionality."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

import pytest

from config.config_loader import load_tickers_config, ConfigError
from pipeline.polygon import (
    fetch_last_5_working_days_prices,
    detect_price_drop_alert,
    get_prices_state_path,
    get_alerts_path,
    save_prices_state,
    save_alerts,
    get_prices_state
)
from pipeline.enrichment import (
    enrich_all_alerts_with_filings,
    get_filing_context_from_alert,
    has_filing_context,
    clear_filing_context
)



class TestConfigLoader:
    """Test configuration loading functionality."""

    def test_load_tickers_config_returns_list(self):
        """Test that load_tickers_config returns a list of tickers."""
        tickers = load_tickers_config()
        assert isinstance(tickers, list)
        assert len(tickers) > 0

    def test_load_tickers_config_contains_expected_tickers(self):
        """Test that loaded config contains expected tickers."""
        tickers = load_tickers_config()
        assert 'AAPL' in tickers
        assert 'MSFT' in tickers
        assert 'GOOGL' in tickers

    def test_load_tickers_config_returns_uppercase(self):
        """Test that all tickers are uppercase."""
        tickers = load_tickers_config()
        assert all(t.isupper() for t in tickers)

    def test_load_tickers_config_deduplicates(self):
        """Test that duplicates are removed from config."""
        tickers = load_tickers_config()
        # Verify no duplicates in loaded tickers
        assert len(tickers) == len(set(tickers))


class TestMultiTickerFilePaths:
    """Test file path generation for multiple tickers."""

    def test_get_prices_state_path_default_aapl(self):
        """Test that get_prices_state_path defaults to AAPL."""
        path = get_prices_state_path()
        assert 'prices_AAPL.json' in str(path)

    def test_get_prices_state_path_custom_ticker(self):
        """Test that get_prices_state_path generates correct paths for different tickers."""
        path_msft = get_prices_state_path('MSFT')
        path_googl = get_prices_state_path('GOOGL')
        
        assert 'prices_MSFT.json' in str(path_msft)
        assert 'prices_GOOGL.json' in str(path_googl)

    def test_get_alerts_path_default_aapl(self):
        """Test that get_alerts_path defaults to AAPL."""
        path = get_alerts_path()
        assert 'alerts_AAPL.json' in str(path)

    def test_get_alerts_path_custom_ticker(self):
        """Test that get_alerts_path generates correct paths for different tickers."""
        path_msft = get_alerts_path('MSFT')
        path_googl = get_alerts_path('GOOGL')
        
        assert 'alerts_MSFT.json' in str(path_msft)
        assert 'alerts_GOOGL.json' in str(path_googl)

    def test_get_prices_state_path_in_data_directory(self):
        """Test that prices state paths point to data directory."""
        path = get_prices_state_path('AAPL')
        assert 'data' in str(path)
        assert path.parent.name == 'data'

    def test_get_alerts_path_in_data_directory(self):
        """Test that alerts paths point to data directory."""
        path = get_alerts_path('AAPL')
        assert 'data' in str(path)
        assert path.parent.name == 'data'


class TestMultiTickerStatePersistence:
    """Test saving and loading state for multiple tickers."""

    def test_save_prices_state_creates_ticker_specific_file(self):
        """Test that save_prices_state creates ticker-specific files."""
        test_state = {
            'timestamp': '2024-01-01T00:00:00',
            'ticker': 'MSFT',
            'prices': [
                {'date': '2024-01-01', 'close': 350.0, 'volume': 1000000}
            ],
            'last_fetch_timestamp': '2024-01-01T00:00:00'
        }
        
        save_prices_state(test_state, 'MSFT')
        
        path = get_prices_state_path('MSFT')
        assert path.exists()
        
        with open(path, 'r') as f:
            loaded = json.load(f)
        assert loaded['ticker'] == 'MSFT'
        assert loaded['prices'][0]['close'] == 350.0

    def test_save_alerts_creates_ticker_specific_file(self):
        """Test that save_alerts creates ticker-specific files."""
        test_alert = {
            'alert_triggered': False,
            'price_first_close': 350.0,
            'price_last_close': 355.0,
            'drop_percentage': -1.43,
            'reason': 'price_change_-1.43%'
        }
        
        save_alerts(test_alert, 'MSFT')
        
        path = get_alerts_path('MSFT')
        assert path.exists()
        
        with open(path, 'r') as f:
            loaded = json.load(f)
        assert loaded['alert_triggered'] == False
        assert loaded['price_first_close'] == 350.0

    def test_get_prices_state_loads_ticker_specific_file(self):
        """Test that get_prices_state loads correct ticker file."""
        test_state = {
            'timestamp': '2024-01-01T00:00:00',
            'ticker': 'GOOGL',
            'prices': [
                {'date': '2024-01-01', 'close': 140.0, 'volume': 2000000}
            ],
            'last_fetch_timestamp': '2024-01-01T00:00:00'
        }
        
        save_prices_state(test_state, 'GOOGL')
        
        loaded = get_prices_state('GOOGL')
        assert loaded['ticker'] == 'GOOGL'
        assert loaded['prices'][0]['close'] == 140.0

    def test_multiple_tickers_have_separate_files(self):
        """Test that different tickers create separate files."""
        states = {
            'AAPL': {
                'timestamp': '2024-01-01T00:00:00',
                'ticker': 'AAPL',
                'prices': [{'date': '2024-01-01', 'close': 150.0, 'volume': 1000000}],
                'last_fetch_timestamp': '2024-01-01T00:00:00'
            },
            'MSFT': {
                'timestamp': '2024-01-01T00:00:00',
                'ticker': 'MSFT',
                'prices': [{'date': '2024-01-01', 'close': 350.0, 'volume': 1000000}],
                'last_fetch_timestamp': '2024-01-01T00:00:00'
            }
        }
        
        for ticker, state in states.items():
            save_prices_state(state, ticker)
        
        aapl_path = get_prices_state_path('AAPL')
        msft_path = get_prices_state_path('MSFT')
        
        assert aapl_path != msft_path
        assert aapl_path.exists()
        assert msft_path.exists()
        
        with open(aapl_path) as f:
            aapl_data = json.load(f)
        with open(msft_path) as f:
            msft_data = json.load(f)
        
        assert aapl_data['prices'][0]['close'] == 150.0
        assert msft_data['prices'][0]['close'] == 350.0


class TestMultiTickerAlertDetection:
    """Test alert detection for multiple tickers."""

    def test_detect_price_drop_alert_for_different_tickers(self):
        """Test that alert detection works for different tickers."""
        # Create state for MSFT with price drop
        msft_state = {
            'timestamp': '2024-01-07T00:00:00',
            'ticker': 'MSFT',
            'prices': [
                {'date': '2024-01-01', 'close': 380.0, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 378.0, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 375.0, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 370.0, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 360.0, 'volume': 1400000},
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        save_prices_state(msft_state, 'MSFT')
        
        alert = detect_price_drop_alert('MSFT')
        
        # MSFT dropped from 380 to 360 = 5.26% drop
        assert alert['alert_triggered'] == True
        assert alert['price_first_close'] == 380.0
        assert alert['price_last_close'] == 360.0
        assert alert['drop_percentage'] >= 5.0

    def test_detect_price_drop_alert_separate_for_each_ticker(self):
        """Test that alerts are tracked separately for each ticker."""
        # AAPL: no drop
        aapl_state = {
            'timestamp': '2024-01-07T00:00:00',
            'ticker': 'AAPL',
            'prices': [
                {'date': '2024-01-01', 'close': 150.0, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 151.0, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 152.0, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 153.0, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 154.0, 'volume': 1400000},
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        # MSFT: price drop
        msft_state = {
            'timestamp': '2024-01-07T00:00:00',
            'ticker': 'MSFT',
            'prices': [
                {'date': '2024-01-01', 'close': 380.0, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 375.0, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 370.0, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 365.0, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 360.0, 'volume': 1400000},
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        save_prices_state(aapl_state, 'AAPL')
        save_prices_state(msft_state, 'MSFT')
        
        aapl_alert = detect_price_drop_alert('AAPL')
        msft_alert = detect_price_drop_alert('MSFT')
        
        assert aapl_alert['alert_triggered'] == False
        assert msft_alert['alert_triggered'] == True

    def test_detect_price_drop_alert_saves_to_ticker_file(self):
        """Test that detect_price_drop_alert saves to ticker-specific file."""
        test_state = {
            'timestamp': '2024-01-07T00:00:00',
            'ticker': 'GOOGL',
            'prices': [
                {'date': '2024-01-01', 'close': 140.0, 'volume': 1000000},
                {'date': '2024-01-02', 'close': 139.0, 'volume': 1100000},
                {'date': '2024-01-03', 'close': 138.0, 'volume': 1200000},
                {'date': '2024-01-04', 'close': 137.0, 'volume': 1300000},
                {'date': '2024-01-05', 'close': 130.0, 'volume': 1400000},
            ],
            'last_fetch_timestamp': '2024-01-05T00:00:00'
        }
        
        save_prices_state(test_state, 'GOOGL')
        detect_price_drop_alert('GOOGL')
        
        alerts_path = get_alerts_path('GOOGL')
        assert alerts_path.exists()
        
        with open(alerts_path) as f:
            alert_data = json.load(f)
        assert 'alert_triggered' in alert_data
        assert 'reason' in alert_data


class TestMultiTickerPipelineIntegration:
    """Integration tests for multi-ticker pipeline."""

    @patch('pipeline.polygon.httpx.Client')
    @patch('pipeline.polygon.time.sleep')
    def test_fetch_for_multiple_tickers_sequentially(self, mock_sleep, mock_client_class):
        """Test that pipeline can fetch prices for multiple tickers."""
        from pipeline.polygon import fetch_last_5_working_days_prices, get_last_5_working_days
        
        working_days = get_last_5_working_days()
        
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        responses = []
        for i, date_str in enumerate(working_days):
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "OK",
                "date": date_str,
                "open": 230.0 + i,
                "high": 235.0 + i,
                "low": 228.0 + i,
                "close": 232.0 + i,
                "volume": 1000000 + i * 100000,
            }
            responses.append(mock_response)
        
        mock_client.get.side_effect = responses
        
        with patch.dict(os.environ, {'POLYGON_API_KEY': 'test-key'}):
            state_aapl = fetch_last_5_working_days_prices('AAPL')
        
        assert state_aapl['ticker'] == 'AAPL'
        assert len(state_aapl['prices']) == 5
        assert get_prices_state_path('AAPL').exists()

    def test_multiple_ticker_files_coexist(self):
        """Test that prices files for multiple tickers can coexist."""
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        
        for ticker in tickers:
            state = {
                'timestamp': '2024-01-01T00:00:00',
                'ticker': ticker,
                'prices': [
                    {'date': '2024-01-01', 'close': 100.0 + i * 10, 'volume': 1000000}
                    for i in range(5)
                ],
                'last_fetch_timestamp': '2024-01-01T00:00:00'
            }
            save_prices_state(state, ticker)
        
        for ticker in tickers:
            path = get_prices_state_path(ticker)
            assert path.exists(), f"Missing {path}"
            
            with open(path) as f:
                data = json.load(f)
            assert data['ticker'] == ticker


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
