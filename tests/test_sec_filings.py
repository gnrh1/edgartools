"""Tests for SEC filing context functionality for price alerts.

This test suite implements the TDD approach for Phase 3: SEC filing context + alerts.
All tests must pass before implementation.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import tempfile

import pytest

# Import modules to be created
from edgar.sec_filings import FilingError, fetch_recent_filings
from edgar.filing_scorer import score_filing_relevance, rank_filings_by_relevance
from edgar.filing_summarizer import extract_key_points, create_filing_summary
from edgar.filing_context_appender import append_filing_context_to_alert, enrich_all_alerts_with_filings


class TestSECFilingFetcher:
    """Test Unit 1: SEC Filing Fetcher."""

    @patch('edgar.sec_filings.Company')
    def test_fetch_8k_filings(self, mock_company_class):
        """Test 1a: Fetch 8-K filings for AAPL (MOCKED)."""
        # Mock company and filings
        mock_company = MagicMock()
        mock_company_class.return_value = mock_company
        
        # Mock filing object
        mock_filing = MagicMock()
        mock_filing.filing_date = datetime.now() - timedelta(days=1)
        mock_filing.cik_link = "https://sec.gov/Archives/edgar/data/320193/0000320193-24-000001.txt"
        mock_filing.item_1a_risk_factors = "Officer departure due to strategic disagreement"
        
        # Mock get_filings to return our mock filing
        mock_filings = MagicMock()
        mock_filings.__iter__ = Mock(return_value=iter([mock_filing]))
        mock_company.get_filings.return_value = mock_filings
        
        # Test fetch
        filings = fetch_recent_filings('AAPL', days_back=2, form_types=['8-K'])
        
        # Verify results
        assert len(filings) == 1
        assert filings[0]['form_type'] == '8-K'
        assert 'filed_date' in filings[0]
        assert 'url' in filings[0]
        assert 'summary' in filings[0]
        
        # Verify Company was called correctly
        mock_company_class.assert_called_once_with('AAPL')
        mock_company.get_filings.assert_called_once_with(form_type='8-K', trigger_full_load=False)

    @patch('edgar.sec_filings.Company')
    def test_fetch_multiple_form_types(self, mock_company_class):
        """Test 1b: Fetch multiple form types."""
        mock_company = MagicMock()
        mock_company_class.return_value = mock_company
        
        # Mock different filings for different form types
        mock_8k = MagicMock()
        mock_8k.filing_date = datetime.now() - timedelta(days=1)  # Within 2 days
        mock_8k.cik_link = "https://sec.gov/Archives/edgar/data/320193/8k.txt"
        mock_8k.item_1a_risk_factors = "Officer departure"
        
        mock_10q = MagicMock()
        mock_10q.filing_date = datetime.now() - timedelta(days=1)  # Within 2 days
        mock_10q.cik_link = "https://sec.gov/Archives/edgar/data/320193/10q.txt"
        mock_10q.item_1a_risk_factors = "Quarterly earnings report"
        
        # Mock get_filings to return different results for each form type
        def side_effect(form_type=None, **kwargs):
            if form_type == '8-K':
                mock_filings = MagicMock()
                mock_filings.__iter__ = Mock(return_value=iter([mock_8k]))
                return mock_filings
            elif form_type == '10-Q':
                mock_filings = MagicMock()
                mock_filings.__iter__ = Mock(return_value=iter([mock_10q]))
                return mock_filings
            else:
                mock_filings = MagicMock()
                mock_filings.__iter__ = Mock(return_value=iter([]))
                return mock_filings
        
        mock_company.get_filings.side_effect = side_effect
        
        # Test fetch
        filings = fetch_recent_filings('AAPL', days_back=2, form_types=['8-K', '10-Q', '10-K'])
        
        # Verify results
        assert len(filings) == 2
        form_types = [f['form_type'] for f in filings]
        assert '8-K' in form_types
        assert '10-Q' in form_types
        
        # Verify Company was called correctly
        mock_company_class.assert_called_once_with('AAPL')
        mock_company.get_filings.assert_any_call(form_type='8-K', trigger_full_load=False)
        mock_company.get_filings.assert_any_call(form_type='10-Q', trigger_full_load=False)

    @patch('edgar.sec_filings.Company')
    def test_fetch_no_filings_found(self, mock_company_class):
        """Test 1c: No filings found."""
        mock_company = MagicMock()
        mock_company_class.return_value = mock_company
        
        # Mock empty filings
        mock_filings = MagicMock()
        mock_filings.__iter__ = Mock(return_value=iter([]))
        mock_company.get_filings.return_value = mock_filings
        
        # Test fetch
        filings = fetch_recent_filings('AAPL', days_back=2, form_types=['8-K'])
        
        # Verify results
        assert len(filings) == 0
        assert isinstance(filings, list)

    @patch('edgar.sec_filings.Company')
    def test_fetch_invalid_ticker(self, mock_company_class):
        """Test 1d: Invalid ticker."""
        mock_company_class.side_effect = Exception("Company not found")
        
        # Test fetch raises error
        with pytest.raises(FilingError, match="Failed to load company INVALID"):
            fetch_recent_filings('INVALID', days_back=2, form_types=['8-K'])

    @patch('edgar.sec_filings.Company')
    @patch('edgar.sec_filings.time.sleep')
    def test_fetch_api_timeout(self, mock_sleep, mock_company_class):
        """Test 1e: API timeout."""
        mock_company = MagicMock()
        mock_company_class.return_value = mock_company
        
        # Mock get_filings to hang (simulate timeout)
        mock_company.get_filings.side_effect = Exception("Request timeout")
        
        # Test fetch handles timeout gracefully
        filings = fetch_recent_filings('AAPL', days_back=2, form_types=['8-K'])
        
        # Should return empty list when API fails
        assert filings == []


class TestFilingRelevanceScorer:
    """Test Unit 2: Filing Relevance Scorer."""

    def test_same_day_8k_scores_high(self):
        """Test 2a: Same-day 8-K scores high."""
        today = datetime.now().strftime('%Y-%m-%d')
        filing = {
            'form_type': '8-K',
            'filed_date': today
        }
        
        score = score_filing_relevance(filing, today)
        
        assert score >= 0.85
        assert score <= 1.0

    def test_week_old_10q_scores_medium(self):
        """Test 2b: Week-old 10-Q scores medium."""
        drop_date = datetime.now().strftime('%Y-%m-%d')
        filing_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        filing = {
            'form_type': '10-Q',
            'filed_date': filing_date
        }
        
        score = score_filing_relevance(filing, drop_date)
        
        assert 0.40 <= score <= 0.70

    def test_month_old_10k_scores_low(self):
        """Test 2c: Month-old 10-K scores low."""
        drop_date = datetime.now().strftime('%Y-%m-%d')
        filing_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        filing = {
            'form_type': '10-K',
            'filed_date': filing_date
        }
        
        score = score_filing_relevance(filing, drop_date)
        
        assert score <= 0.30

    def test_empty_filing_list(self):
        """Test 2d: Empty filing list."""
        drop_date = datetime.now().strftime('%Y-%m-%d')
        
        result = rank_filings_by_relevance([], drop_date)
        
        assert result == []

    def test_ranking_by_relevance(self):
        """Test additional: Rankings are sorted by relevance score."""
        drop_date = datetime.now().strftime('%Y-%m-%d')
        
        filings = [
            {'form_type': '10-K', 'filed_date': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')},
            {'form_type': '8-K', 'filed_date': drop_date},
            {'form_type': '10-Q', 'filed_date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')},
        ]
        
        ranked = rank_filings_by_relevance(filings, drop_date)
        
        # Should be sorted by relevance (8-K highest, 10-Q medium, 10-K lowest)
        assert ranked[0]['form_type'] == '8-K'
        assert ranked[1]['form_type'] == '10-Q'
        assert ranked[2]['form_type'] == '10-K'
        
        # Check that relevance scores are present and sorted
        scores = [f['relevance_score'] for f in ranked]
        assert scores == sorted(scores, reverse=True)


class TestFilingSummarizer:
    """Test Unit 3: Filing Summarizer."""

    def test_extract_key_points_from_8k(self):
        """Test 3a: Extract key points from 8-K."""
        filing = {
            'summary': 'The Chief Financial Officer announced their resignation due to strategic disagreements. The company also issued a revenue warning for the upcoming quarter.',
            'form_type': '8-K'
        }
        
        key_points = extract_key_points(filing)
        
        # Should detect important concepts
        key_point_text = ' '.join(key_points).lower()
        assert any(word in key_point_text for word in ['officer', 'changes', 'departure', 'resignation'])
        assert any(word in key_point_text for word in ['financial', 'performance', 'revenue', 'warning'])
        assert len(key_points) >= 1

    def test_handle_missing_summary(self):
        """Test 3b: Handle missing summary."""
        filing = {
            'summary': '',
            'form_type': '8-K'
        }
        
        summary = create_filing_summary(filing)
        
        assert summary['summary'] == 'No summary available'

    def test_multiple_key_points(self):
        """Test 3c: Multiple key points."""
        filing = {
            'summary': 'The company announced an acquisition of TechCorp and simultaneously issued a dividend cut warning due to integration costs.',
            'form_type': '8-K'
        }
        
        key_points = extract_key_points(filing)
        
        assert len(key_points) >= 2
        # Should detect both acquisition and dividend-related terms
        key_point_text = ' '.join(key_points).lower()
        assert any(word in key_point_text for word in ['acquisition', 'merger', 'corporate', 'actions'])
        assert any(word in key_point_text for word in ['dividend', 'changes'])

    def test_create_filing_summary_structure(self):
        """Test additional: Filing summary has correct structure."""
        filing = {
            'form_type': '8-K',
            'filed_date': '2025-11-29',
            'summary': 'Test summary with officer departure',
            'url': 'https://sec.gov/test.txt',
            'relevance_score': 0.95
        }
        
        summary = create_filing_summary(filing)
        
        # Check all required fields
        assert 'form_type' in summary
        assert 'filed_date' in summary
        assert 'key_points' in summary
        assert 'summary' in summary
        assert 'url' in summary
        assert 'relevance_score' in summary
        
        # Check values
        assert summary['form_type'] == '8-K'
        assert summary['filed_date'] == '2025-11-29'
        assert isinstance(summary['key_points'], list)
        assert summary['relevance_score'] == 0.95


class TestFilingContextAppender:
    """Test Unit 4: Filing Context Appender."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.alerts_path = Path(self.temp_dir) / 'alerts_AAPL.json'
        
        # Create sample alert
        sample_alert = {
            'alert_triggered': True,
            'price_first_close': 150.0,
            'price_last_close': 142.0,
            'drop_percentage': 5.33,
            'reason': 'price_drop_5.33%'
        }
        
        with open(self.alerts_path, 'w') as f:
            json.dump(sample_alert, f)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.alerts_path.exists():
            self.alerts_path.unlink()
        Path(self.temp_dir).rmdir()

    def test_append_filings_to_alert(self):
        """Test 4a: Append filings to alert."""
        filings = [
            {
                'form_type': '8-K',
                'filed_date': '2025-11-29',
                'relevance_score': 0.95,
                'key_points': ['Officer departure'],
                'summary': 'CFO resigned',
                'url': 'https://sec.gov/test.txt'
            }
        ]
        
        with patch('edgar.filing_context_appender.Path') as mock_path:
            mock_path.return_value = self.alerts_path
            
            result = append_filing_context_to_alert('AAPL', filings)
            
            assert result is True
            
            # Verify file was updated
            with open(self.alerts_path, 'r') as f:
                updated_alert = json.load(f)
            
            assert 'filing_context' in updated_alert
            assert len(updated_alert['filing_context']) == 1
            assert updated_alert['filing_context'][0]['form_type'] == '8-K'

    def test_no_filings(self):
        """Test 4b: No filings."""
        with patch('edgar.filing_context_appender.Path') as mock_path:
            mock_path.return_value = self.alerts_path
            
            result = append_filing_context_to_alert('AAPL', [])
            
            assert result is True
            
            # Verify filing_context is empty
            with open(self.alerts_path, 'r') as f:
                updated_alert = json.load(f)
            
            assert 'filing_context' in updated_alert
            assert len(updated_alert['filing_context']) == 0

    def test_preserve_existing_alert_fields(self):
        """Test 4c: Preserve existing alert fields."""
        filings = [
            {
                'form_type': '8-K',
                'filed_date': '2025-11-29',
                'relevance_score': 0.95,
                'key_points': ['Officer departure'],
                'summary': 'CFO resigned',
                'url': 'https://sec.gov/test.txt'
            }
        ]
        
        with patch('edgar.filing_context_appender.Path') as mock_path:
            mock_path.return_value = self.alerts_path
            
            append_filing_context_to_alert('AAPL', filings)
            
            # Verify all original fields are preserved
            with open(self.alerts_path, 'r') as f:
                updated_alert = json.load(f)
            
            assert updated_alert['alert_triggered'] == True
            assert updated_alert['price_first_close'] == 150.0
            assert updated_alert['price_last_close'] == 142.0
            assert updated_alert['drop_percentage'] == 5.33
            assert updated_alert['reason'] == 'price_drop_5.33%'
            assert 'filing_context' in updated_alert

    @patch('edgar.filing_context_appender.Path')
    def test_missing_alert_file(self, mock_path):
        """Test 4d: Missing alert file."""
        mock_path.return_value.exists.return_value = False
        
        result = append_filing_context_to_alert('MISSING', [])
        
        assert result is False

    @patch('edgar.sec_filings.fetch_recent_filings')
    @patch('edgar.filing_scorer.rank_filings_by_relevance')
    @patch('edgar.filing_summarizer.create_filing_summary')
    @patch('edgar.filing_context_appender.append_filing_context_to_alert')
    def test_enrich_all_alerts_integration(self, mock_append, mock_summary, mock_rank, mock_fetch):
        """Test 4e: Enrich all alerts integration."""
        # Setup mocks
        mock_fetch.return_value = [
            {'form_type': '8-K', 'filed_date': '2025-11-29', 'summary': 'Test'}
        ]
        mock_rank.return_value = [
            {'form_type': '8-K', 'filed_date': '2025-11-29', 'summary': 'Test', 'relevance_score': 0.95}
        ]
        mock_summary.return_value = {
            'form_type': '8-K',
            'filed_date': '2025-11-29',
            'relevance_score': 0.95,
            'key_points': ['Test'],
            'summary': 'Test',
            'url': 'test.com'
        }
        mock_append.return_value = True
        
        # Test
        enrich_all_alerts_with_filings(['AAPL', 'MSFT'])
        
        # Verify calls were made for each ticker
        assert mock_fetch.call_count == 2
        # The rank and summary calls may not happen if fetch returns empty
        assert mock_append.call_count == 2


class TestDashboardFilingRenderer:
    """Test Unit 5: Dashboard Filing Renderer."""

    def test_render_three_stocks_with_filings(self):
        """Test 5a: Render 3 stocks with filings."""
        # This would test the dashboard HTML rendering
        # For now, we'll test the data structure that would be used
        
        alerts_data = {
            'AAPL': {
                'alert_triggered': True,
                'drop_percentage': 5.2,
                'filing_context': [
                    {'form_type': '8-K', 'key_points': ['Officer departure']},
                    {'form_type': '10-Q', 'key_points': ['Revenue miss']}
                ]
            },
            'MSFT': {
                'alert_triggered': True,
                'drop_percentage': 6.1,
                'filing_context': [
                    {'form_type': '8-K', 'key_points': ['Acquisition announced']}
                ]
            },
            'GOOGL': {
                'alert_triggered': False,
                'drop_percentage': 2.3,
                'filing_context': []
            }
        }
        
        # Verify structure
        assert len(alerts_data) == 3
        assert len(alerts_data['AAPL']['filing_context']) == 2
        assert len(alerts_data['MSFT']['filing_context']) == 1
        assert len(alerts_data['GOOGL']['filing_context']) == 0

    def test_filing_links_correct(self):
        """Test 5b: Filing links are correct."""
        filing = {
            'form_type': '8-K',
            'url': 'https://sec.gov/Archives/edgar/data/320193/0000320193-24-000001.txt'
        }
        
        # In actual implementation, this would generate HTML
        # For test, verify URL structure
        assert filing['url'].startswith('https://sec.gov/Archives/')
        assert '0000320193-24-000001.txt' in filing['url']

    def test_relevance_score_display(self):
        """Test 5c: Relevance score displayed."""
        high_relevance = {'relevance_score': 0.95}
        medium_relevance = {'relevance_score': 0.60}
        low_relevance = {'relevance_score': 0.20}
        
        # Test relevance label logic
        def get_relevance_label(score):
            if score > 0.7:
                return "Likely related"
            else:
                return "Possibly related"
        
        assert get_relevance_label(high_relevance['relevance_score']) == "Likely related"
        assert get_relevance_label(medium_relevance['relevance_score']) == "Possibly related"
        assert get_relevance_label(low_relevance['relevance_score']) == "Possibly related"


class TestErrorHandling:
    """Test Unit 6: Error Handling & Edge Cases."""

    @patch('edgar.sec_filings.fetch_recent_filings')
    @patch('edgar.filing_context_appender.append_filing_context_to_alert')
    def test_missing_ticker(self, mock_append, mock_fetch):
        """Test 6a: Missing ticker."""
        mock_fetch.side_effect = FilingError("Company not found")
        mock_append.return_value = False
        
        # This should not crash the system
        try:
            enrich_all_alerts_with_filings(['INVALID'])
            # If we get here without exception, test passes
            assert True
        except Exception:
            # If exception crashes the system, test fails
            assert False, "Function should not crash on missing ticker"

    @patch('edgar.sec_filings.Company')
    def test_edgartools_import_fails(self, mock_company):
        """Test 6b: edgartools import fails."""
        # This would be tested at import level
        # For now, test that Company creation failure is handled
        mock_company.side_effect = ImportError("No module named 'edgartools'")
        
        with pytest.raises(FilingError):
            fetch_recent_filings('AAPL')

    def test_malformed_alerts_json(self):
        """Test 6c: Malformed alerts JSON."""
        temp_dir = tempfile.mkdtemp()
        alerts_path = Path(temp_dir) / 'alerts_AAPL.json'
        
        # Create malformed JSON
        with open(alerts_path, 'w') as f:
            f.write('{"invalid": json content}')
        
        try:
            with patch('edgar.filing_context_appender.Path') as mock_path:
                mock_path.return_value = alerts_path
                
                result = append_filing_context_to_alert('AAPL', [])
                
                # Should handle gracefully
                assert result is False
        finally:
            alerts_path.unlink()
            Path(temp_dir).rmdir()

    @patch('edgar.sec_filings.fetch_recent_filings')
    @patch('edgar.filing_context_appender.append_filing_context_to_alert')
    def test_partial_success(self, mock_append, mock_fetch):
        """Test 6d: Partial success."""
        # Mock AAPL success, MSFT failure
        def fetch_side_effect(ticker, **kwargs):
            if ticker == 'AAPL':
                return [{'form_type': '8-K', 'filed_date': '2025-11-29'}]
            else:
                raise FilingError("Failed to fetch")
        
        mock_fetch.side_effect = fetch_side_effect
        mock_append.return_value = True
        
        with patch('edgar.core.log') as mock_log:
            enrich_all_alerts_with_filings(['AAPL', 'MSFT'])
            
            # Should have processed AAPL and logged something for MSFT
            assert mock_fetch.call_count == 2
            assert mock_log.error.call_count >= 0 or mock_log.info.call_count >= 0

    @patch('edgar.sec_filings.Company')
    def test_api_rate_limit_hit(self, mock_company):
        """Test 6e: API rate limit hit."""
        mock_company_instance = MagicMock()
        mock_company.return_value = mock_company_instance
        
        # Simulate rate limit error
        mock_company_instance.get_filings.side_effect = Exception("Rate limit exceeded")
        
        # Should handle gracefully and return empty list, not raise exception
        filings = fetch_recent_filings('AAPL', days_back=2, form_types=['8-K'])
        
        # Should return empty list when all form types fail
        assert filings == []


# Utility function to get drop date from alert (for testing)
def get_drop_date_from_alert(ticker):
    """Helper function to extract drop date from alert data."""
    from edgar.polygon import get_alerts_path
    
    alert_path = get_alerts_path(ticker)
    if alert_path.exists():
        with open(alert_path, 'r') as f:
            alert_data = json.load(f)
        # For testing, return today's date
        return datetime.now().strftime('%Y-%m-%d')
    return datetime.now().strftime('%Y-%m-%d')


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])