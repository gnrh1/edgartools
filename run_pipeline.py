#!/usr/bin/env python3
"""
Pipeline script for automated multi-stock price monitoring and alerting.

This script orchestrates:
1. Loading monitored stocks from config/tickers.yaml
2. Fetching stock prices for the last 5 working days for each ticker
3. Detecting price drop alerts (5%+ threshold) for each ticker
4. Enriching alerts with SEC filing context (Phase 3)
5. Validating outputs
6. Committing changes to Git

Usage:
    export POLYGON_API_KEY="your_api_key"
    python run_pipeline.py

Exit Codes:
    0: Success
    1: General error (API failure, validation failure, etc.)
    2: Git commit failure
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config.config_loader import load_tickers_config, ConfigError


def log(message: str, level: str = "INFO") -> None:
    """Log message to stdout with timestamp."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] [{level}] {message}")


def validate_environment() -> bool:
    """Validate required environment variables are set."""
    log("Validating environment...")
    
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        log("ERROR: POLYGON_API_KEY environment variable not set", "ERROR")
        return False
    
    log("Environment validation passed")
    return True


def fetch_prices(tickers: list) -> bool:
    """Execute Task 1: Fetch prices for all monitored tickers for last 5 working days."""
    log("=" * 60)
    log(f"TASK 1: Fetching prices for {len(tickers)} tickers")
    log("=" * 60)
    
    try:
        from pipeline.polygon import fetch_last_5_working_days_prices
        
        for ticker in tickers:
            log(f"\nFetching {ticker}...")
            try:
                state = fetch_last_5_working_days_prices(ticker)
                log(f"✓ Successfully fetched {len(state.get('prices', []))} price records for {ticker}")
                if state.get('prices'):
                    log(f"  Date range: {state['prices'][0].get('date')} to {state['prices'][-1].get('date')}")
            except Exception as e:
                log(f"✗ Failed to fetch {ticker}: {e}", "WARNING")
                continue
        
        return True
        
    except Exception as e:
        log(f"Failed to fetch prices: {e}", "ERROR")
        return False


def detect_alerts(tickers: list) -> bool:
    """Execute Task 2: Detect price drop alerts for all monitored tickers."""
    log("=" * 60)
    log(f"TASK 2: Detecting price drop alerts for {len(tickers)} tickers")
    log("=" * 60)
    
    try:
        from pipeline.polygon import detect_price_drop_alert
        
        for ticker in tickers:
            log(f"\nAnalyzing {ticker}...")
            try:
                alert = detect_price_drop_alert(ticker)
                log(f"  - Alert triggered: {alert.get('alert_triggered')}")
                log(f"  - First close: ${alert.get('price_first_close', 0):.2f}")
                log(f"  - Last close: ${alert.get('price_last_close', 0):.2f}")
                log(f"  - Drop percentage: {alert.get('drop_percentage', 0):.2f}%")
                log(f"  - Reason: {alert.get('reason')}")
            except Exception as e:
                log(f"✗ Failed to analyze {ticker}: {e}", "WARNING")
                continue
        
        return True
        
    except Exception as e:
        log(f"Failed to detect alerts: {e}", "ERROR")
        return False


def enrich_with_sec_filings(tickers: list) -> bool:
    """Execute Task 3: Enrich alerts with SEC filing context for all monitored tickers."""
    log("=" * 60)
    log(f"TASK 3: Enriching alerts with SEC filing context for {len(tickers)} tickers")
    log("=" * 60)
    
    try:
        from pipeline.enrichment import safe_enrich_all_alerts
        
        results = safe_enrich_all_alerts(tickers)
        
        successful = len(results['success'])
        failed = len(results['failed'])
        total = len(tickers)
        
        log(f"\nSEC filing enrichment summary:")
        log(f"  - Successful: {successful}/{total}")
        log(f"  - Failed: {failed}/{total}")
        
        if results['success']:
            log(f"  - Successfully enriched: {', '.join(results['success'])}")
        
        if results['failed']:
            log(f"  - Failed to enrich: {', '.join(results['failed'])}", "WARNING")
            for ticker, error in results.get('errors', {}).items():
                log(f"    {ticker}: {error}", "WARNING")
        
        # Consider it successful if at least one ticker succeeded
        return successful > 0
        
    except Exception as e:
        log(f"Failed to enrich with SEC filings: {e}", "ERROR")
        return False


def analyze_financials(tickers: list) -> bool:
    """Execute Task 4: Analyze financials (ROIC, WACC, Spread) for all monitored tickers."""
    log("=" * 60)
    log(f"TASK 4: Analyzing financials for {len(tickers)} tickers")
    log("=" * 60)
    
    try:
        from pipeline.financial_analyzer import calculate_spread, FinancialDataError
        
        successful = 0
        failed = 0
        
        for ticker in tickers:
            log(f"\nAnalyzing financials for {ticker}...")
            try:
                # Calculate spread (this also calculates ROIC and WACC and caches everything)
                result = calculate_spread(ticker)
                
                log(f"  - Current Spread: {result.current_spread:.2%}")
                log(f"  - Trend: {result.spread_trend}")
                log(f"  - Durability: {result.durability_assessment}")
                
                successful += 1
                
            except FinancialDataError as e:
                log(f"✗ Failed to analyze {ticker}: {e}", "WARNING")
                failed += 1
            except Exception as e:
                log(f"✗ Unexpected error for {ticker}: {e}", "WARNING")
                failed += 1
        
        log(f"\nFinancial analysis summary:")
        log(f"  - Successful: {successful}/{len(tickers)}")
        log(f"  - Failed: {failed}/{len(tickers)}")
        
        # Consider it successful if at least one ticker succeeded
        return successful > 0
        
    except Exception as e:
        log(f"Failed to analyze financials: {e}", "ERROR")
        return False


def validate_outputs(tickers: list) -> bool:
    """Validate that output files exist for all tickers and contain valid JSON."""
    log("=" * 60)
    log(f"Validating outputs for {len(tickers)} tickers...")
    log("=" * 60)
    
    from pipeline.polygon import get_prices_state_path, get_alerts_path
    
    # Determine project root (where this script is located)
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    
    all_valid = True
    
    for ticker in tickers:
        log(f"\nValidating {ticker}...")
        
        prices_path = get_prices_state_path(ticker)
        alerts_path = get_alerts_path(ticker)
        
        # Check prices file
        if not prices_path.exists():
            log(f"  ERROR: {prices_path} does not exist", "ERROR")
            all_valid = False
            continue
        
        try:
            with open(prices_path, 'r') as f:
                prices_data = json.load(f)
            
            # Validate structure
            if not isinstance(prices_data, dict):
                log(f"  ERROR: prices file is not a valid dictionary", "ERROR")
                all_valid = False
                continue
            
            if 'prices' not in prices_data:
                log(f"  ERROR: prices file missing 'prices' field", "ERROR")
                all_valid = False
                continue
            
            if not isinstance(prices_data['prices'], list) or len(prices_data['prices']) == 0:
                log(f"  ERROR: prices file has empty or invalid prices list", "ERROR")
                all_valid = False
                continue
            
            log(f"  ✓ prices file is valid ({len(prices_data['prices'])} records)")
            
        except json.JSONDecodeError as e:
            log(f"  ERROR: prices file is not valid JSON: {e}", "ERROR")
            all_valid = False
        except Exception as e:
            log(f"  ERROR: Failed to read prices file: {e}", "ERROR")
            all_valid = False
        
        # Check alerts file
        if not alerts_path.exists():
            log(f"  ERROR: {alerts_path} does not exist", "ERROR")
            all_valid = False
            continue
        
        try:
            with open(alerts_path, 'r') as f:
                alerts_data = json.load(f)
            
            # Validate structure
            if not isinstance(alerts_data, dict):
                log(f"  ERROR: alerts file is not a valid dictionary", "ERROR")
                all_valid = False
                continue
            
            required_fields = ['alert_triggered', 'price_first_close', 'price_last_close', 'drop_percentage', 'reason']
            for field in required_fields:
                if field not in alerts_data:
                    log(f"  ERROR: alerts file missing required field '{field}'", "ERROR")
                    all_valid = False
            
            # Check for filing_context field (Phase 3 feature)
            if 'filing_context' not in alerts_data:
                log(f"  WARNING: alerts file missing 'filing_context' field (Phase 3 feature)", "WARNING")
            elif not isinstance(alerts_data['filing_context'], list):
                log(f"  ERROR: alerts file 'filing_context' is not a list", "ERROR")
                all_valid = False
            else:
                # Validate filing_context structure if present
                context_count = len(alerts_data['filing_context'])
                if context_count > 0:
                    log(f"  ✓ filing_context contains {context_count} filings")
                    # Validate structure of each filing
                    for i, filing in enumerate(alerts_data['filing_context']):
                        if not isinstance(filing, dict):
                            log(f"  ERROR: filing_context[{i}] is not a dictionary", "ERROR")
                            all_valid = False
                            continue
                        
                        filing_fields = ['form_type', 'filed_date', 'key_points', 'summary', 'url', 'relevance_score']
                        for field in filing_fields:
                            if field not in filing:
                                log(f"  WARNING: filing_context[{i}] missing field '{field}'", "WARNING")
                else:
                    log(f"  ✓ filing_context is empty (no recent filings)")
            
            log(f"  ✓ alerts file is valid")
            
        except json.JSONDecodeError as e:
            log(f"  ERROR: alerts file is not valid JSON: {e}", "ERROR")
            all_valid = False
            log(f"  ERROR: Failed to read alerts file: {e}", "ERROR")
            all_valid = False

        # Check financial cache file (Phase 4)
        from pipeline.financial_analyzer import get_cache_path as get_financial_cache_path
        financial_path = get_financial_cache_path(ticker)
        
        if not financial_path.exists():
            log(f"  WARNING: {financial_path} does not exist (Financial analysis might have failed)", "WARNING")
            # Don't fail validation yet as this is a new feature
        else:
            try:
                with open(financial_path, 'r') as f:
                    fin_data = json.load(f)
                
                if 'spread_result' in fin_data:
                    log(f"  ✓ financial cache valid (Spread: {fin_data['spread_result'].get('current_spread', 0):.2%})")
                else:
                    log(f"  WARNING: financial cache missing 'spread_result'", "WARNING")
            except Exception as e:
                log(f"  WARNING: Failed to read financial cache: {e}", "WARNING")
    
    if all_valid:
        log("\nOutput validation passed")
    return all_valid


def git_commit(tickers: list) -> bool:
    """Commit changes to Git with standardized message."""
    log("=" * 60)
    log("Committing changes to Git...")
    log("=" * 60)
    
    try:
        # Get current directory
        repo_dir = Path(__file__).parent
        
        # Check if we have changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not result.stdout.strip():
            log("No changes to commit")
            return True
        
        log(f"Changes detected:\n{result.stdout}")
        
        # Add data files for all tickers (only if they exist)
        data_files = []
        for ticker in tickers:
            for file_pattern in [f"data/prices_{ticker}.json", f"data/alerts_{ticker}.json", f"data/financial_cache_{ticker}.json"]:
                if os.path.exists(os.path.join(repo_dir, file_pattern)):
                    data_files.append(file_pattern)
        
        subprocess.run(
            ["git", "add", "-f"] + data_files,
            cwd=repo_dir,
            check=True
        )
        log(f"✓ Added data files to staging for {len(tickers)} tickers")
        
        # Commit with standardized message
        ticker_list = ", ".join(tickers)
        commit_message = f"chore: weekly price update [{ticker_list}]"
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=repo_dir,
            check=True
        )
        log(f"✓ Committed with message: {commit_message}")
        
        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = result.stdout.strip()[:8]
        log(f"✓ Commit hash: {commit_hash}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"Git command failed: {e}", "ERROR")
        if e.stderr:
            log(f"Git error output: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}", "ERROR")
        return False
    except Exception as e:
        log(f"Failed to commit changes: {e}", "ERROR")
        return False


def main() -> int:
    """Main pipeline execution."""
    log("=" * 60)
    log("MULTI-STOCK PRICE MONITORING PIPELINE")
    log("=" * 60)
    log(f"Start time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Step 0a: Set SEC User-Agent identity (required for SEC API access)
    from edgar import set_identity, get_identity
    identity = get_identity()
    set_identity(identity)
    log(f"SEC User-Agent set to: {identity}")
    
    # Step 0b: Load config
    try:
        tickers = load_tickers_config()
        log(f"Loaded {len(tickers)} tickers from config: {', '.join(tickers)}")
    except ConfigError as e:
        log(f"Pipeline failed: Failed to load config: {e}", "ERROR")
        return 1
    
    # Step 1: Validate environment
    if not validate_environment():
        log("Pipeline failed: Environment validation failed", "ERROR")
        return 1
    
    # Step 2: Fetch prices
    if not fetch_prices(tickers):
        log("Pipeline failed: Price fetching failed", "ERROR")
        return 1
    
    # Step 3: Detect alerts
    if not detect_alerts(tickers):
        log("Pipeline failed: Alert detection failed", "ERROR")
        return 1
    
    # Step 4: Enrich with SEC filings (Phase 3)
    if not enrich_with_sec_filings(tickers):
        log("Pipeline failed: SEC filing enrichment failed", "ERROR")
        return 1
    
    # Step 5: Analyze financials (Phase 4 - Pillar 1)
    if not analyze_financials(tickers):
        log("Pipeline failed: Financial analysis failed", "ERROR")
        return 1
    
    # Step 6: Validate outputs
    if not validate_outputs(tickers):
        log("Pipeline failed: Output validation failed", "ERROR")
        return 1
    
    # Step 6: Git commit
    if not git_commit(tickers):
        log("Pipeline failed: Git commit failed", "ERROR")
        return 2
    
    # Success
    log("=" * 60)
    log("PIPELINE COMPLETED SUCCESSFULLY")
    log("=" * 60)
    log(f"End time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
