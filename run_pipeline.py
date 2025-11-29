#!/usr/bin/env python3
"""
Pipeline script for automated AAPL price monitoring and alerting.

This script orchestrates:
1. Fetching AAPL stock prices for the last 7 days
2. Detecting price drop alerts (5%+ threshold)
3. Validating outputs
4. Committing changes to Git

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


def fetch_prices() -> bool:
    """Execute Task 1: Fetch AAPL prices for last 7 days."""
    log("=" * 60)
    log("TASK 1: Fetching AAPL prices for last 7 days...")
    log("=" * 60)
    
    try:
        from edgar.polygon import fetch_aapl_last_7_days
        
        # Fetch prices and save to prices_state.json
        state = fetch_aapl_last_7_days()
        
        log(f"Successfully fetched {len(state.get('prices', []))} price records")
        log(f"Date range: {state.get('prices', [{}])[0].get('date')} to {state.get('prices', [{}])[-1].get('date')}")
        log(f"State saved to prices_state.json")
        
        return True
        
    except Exception as e:
        log(f"Failed to fetch prices: {e}", "ERROR")
        return False


def detect_alerts() -> bool:
    """Execute Task 2: Detect price drop alerts."""
    log("=" * 60)
    log("TASK 2: Detecting price drop alerts...")
    log("=" * 60)
    
    try:
        from edgar.polygon import detect_price_drop_alert
        
        # Detect alerts and save to alerts.json
        alert = detect_price_drop_alert()
        
        log(f"Alert analysis complete:")
        log(f"  - Alert triggered: {alert.get('alert_triggered')}")
        log(f"  - First close: ${alert.get('price_first_close', 0):.2f}")
        log(f"  - Last close: ${alert.get('price_last_close', 0):.2f}")
        log(f"  - Drop percentage: {alert.get('drop_percentage', 0):.2f}%")
        log(f"  - Reason: {alert.get('reason')}")
        log(f"Alert saved to alerts.json")
        
        return True
        
    except Exception as e:
        log(f"Failed to detect alerts: {e}", "ERROR")
        return False


def validate_outputs() -> bool:
    """Validate that both output files exist and contain valid JSON."""
    log("=" * 60)
    log("Validating outputs...")
    log("=" * 60)
    
    # Determine project root (where this script is located)
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    
    prices_path = data_dir / "prices_state.json"
    alerts_path = data_dir / "alerts.json"
    
    # Check prices_state.json
    if not prices_path.exists():
        log(f"ERROR: {prices_path} does not exist", "ERROR")
        return False
    
    try:
        with open(prices_path, 'r') as f:
            prices_data = json.load(f)
        
        # Validate structure
        if not isinstance(prices_data, dict):
            log("ERROR: prices_state.json is not a valid dictionary", "ERROR")
            return False
        
        if 'prices' not in prices_data:
            log("ERROR: prices_state.json missing 'prices' field", "ERROR")
            return False
        
        if not isinstance(prices_data['prices'], list) or len(prices_data['prices']) == 0:
            log("ERROR: prices_state.json has empty or invalid prices list", "ERROR")
            return False
        
        log(f"✓ prices_state.json is valid ({len(prices_data['prices'])} records)")
        
    except json.JSONDecodeError as e:
        log(f"ERROR: prices_state.json is not valid JSON: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"ERROR: Failed to read prices_state.json: {e}", "ERROR")
        return False
    
    # Check alerts.json
    if not alerts_path.exists():
        log(f"ERROR: {alerts_path} does not exist", "ERROR")
        return False
    
    try:
        with open(alerts_path, 'r') as f:
            alerts_data = json.load(f)
        
        # Validate structure
        if not isinstance(alerts_data, dict):
            log("ERROR: alerts.json is not a valid dictionary", "ERROR")
            return False
        
        required_fields = ['alert_triggered', 'price_first_close', 'price_last_close', 'drop_percentage', 'reason']
        for field in required_fields:
            if field not in alerts_data:
                log(f"ERROR: alerts.json missing required field '{field}'", "ERROR")
                return False
        
        log(f"✓ alerts.json is valid")
        
    except json.JSONDecodeError as e:
        log(f"ERROR: alerts.json is not valid JSON: {e}", "ERROR")
        return False
    except Exception as e:
        log(f"ERROR: Failed to read alerts.json: {e}", "ERROR")
        return False
    
    log("Output validation passed")
    return True


def git_commit() -> bool:
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
        
        # Add data files
        subprocess.run(
            ["git", "add", "data/prices_state.json", "data/alerts.json"],
            cwd=repo_dir,
            check=True
        )
        log("✓ Added data files to staging")
        
        # Commit with standardized message
        commit_message = "chore: weekly price update [AAPL]"
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
    log("AAPL PRICE MONITORING PIPELINE")
    log("=" * 60)
    log(f"Start time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Step 1: Validate environment
    if not validate_environment():
        log("Pipeline failed: Environment validation failed", "ERROR")
        return 1
    
    # Step 2: Fetch prices
    if not fetch_prices():
        log("Pipeline failed: Price fetching failed", "ERROR")
        return 1
    
    # Step 3: Detect alerts
    if not detect_alerts():
        log("Pipeline failed: Alert detection failed", "ERROR")
        return 1
    
    # Step 4: Validate outputs
    if not validate_outputs():
        log("Pipeline failed: Output validation failed", "ERROR")
        return 1
    
    # Step 5: Git commit
    if not git_commit():
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
