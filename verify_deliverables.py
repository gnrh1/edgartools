#!/usr/bin/env python3
"""
Verification script to ensure all deliverables are correctly implemented.
"""

import json
import os
import subprocess
from pathlib import Path


def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_check(passed, message):
    """Print check result."""
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")
    return passed


def verify_deliverable_1():
    """Verify DELIVERABLE 1: Dashboard Frontend."""
    print_header("DELIVERABLE 1: Dashboard Frontend (dashboard.html)")
    
    checks = []
    
    # Check file exists
    dashboard_path = Path("dashboard.html")
    checks.append(print_check(dashboard_path.exists(), "dashboard.html exists"))
    
    if not dashboard_path.exists():
        return False
    
    # Check file contains required elements
    content = dashboard_path.read_text()
    
    required_elements = [
        ("prices_state.json", "References prices_state.json"),
        ("alerts.json", "References alerts.json"),
        ("alert_triggered", "Checks alert_triggered status"),
        ("last_fetch_timestamp", "Displays last_fetch_timestamp"),
        ("drop_percentage", "Shows drop percentage"),
        ("firstPrice", "Shows first close price"),
        ("lastPrice", "Shows last close price"),
        ("🔴", "Has red alert indicator"),
        ("🟢", "Has green no-alert indicator"),
        ("<style>", "Contains CSS styling"),
        ("fetch(", "Uses JavaScript fetch API"),
        ("AAPL", "References AAPL ticker")
    ]
    
    for element, description in required_elements:
        checks.append(print_check(element in content, description))
    
    return all(checks)


def verify_deliverable_2():
    """Verify DELIVERABLE 2: Pipeline Script."""
    print_header("DELIVERABLE 2: Pipeline Script (run_pipeline.py)")
    
    checks = []
    
    # Check file exists
    pipeline_path = Path("run_pipeline.py")
    checks.append(print_check(pipeline_path.exists(), "run_pipeline.py exists"))
    
    if not pipeline_path.exists():
        return False
    
    # Check file contains required functionality
    content = pipeline_path.read_text()
    
    required_elements = [
        ("fetch_aapl_last_7_days", "Calls fetch_aapl_last_7_days()"),
        ("detect_price_drop_alert", "Calls detect_price_drop_alert()"),
        ("validate_outputs", "Has validate_outputs() function"),
        ("git_commit", "Has git_commit() function"),
        ("POLYGON_API_KEY", "Checks POLYGON_API_KEY env var"),
        ("prices_state.json", "Validates prices_state.json"),
        ("alerts.json", "Validates alerts.json"),
        ("chore: weekly price update [AAPL]", "Uses correct commit message"),
        ("sys.exit", "Has proper exit codes"),
        ("log(", "Logs steps to stdout"),
        ("try:", "Has error handling")
    ]
    
    for element, description in required_elements:
        checks.append(print_check(element in content, description))
    
    # Check file is executable or can be run with python
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", "run_pipeline.py"],
            capture_output=True,
            text=True,
            check=True
        )
        checks.append(print_check(True, "Script has valid Python syntax"))
    except subprocess.CalledProcessError:
        checks.append(print_check(False, "Script has valid Python syntax"))
    
    return all(checks)


def verify_deliverable_3():
    """Verify DELIVERABLE 3: GitHub Actions Workflow."""
    print_header("DELIVERABLE 3: GitHub Actions Workflow (weekly-update.yml)")
    
    checks = []
    
    # Check file exists
    workflow_path = Path(".github/workflows/weekly-update.yml")
    checks.append(print_check(workflow_path.exists(), "weekly-update.yml exists"))
    
    if not workflow_path.exists():
        return False
    
    # Check file contains required elements
    content = workflow_path.read_text()
    
    required_elements = [
        ("0 8 * * 1", "Has Monday 8 AM UTC cron schedule"),
        ("schedule:", "Has schedule trigger"),
        ("workflow_dispatch:", "Has manual trigger"),
        ("actions/checkout@", "Checks out repository"),
        ("actions/setup-python@", "Sets up Python"),
        ("POLYGON_API_KEY", "Uses POLYGON_API_KEY secret"),
        ("run_pipeline.py", "Runs pipeline script"),
        ("git push", "Pushes changes"),
        ("pip install", "Installs dependencies"),
        ("httpx", "Installs httpx dependency"),
        ("pandas", "Installs pandas dependency")
    ]
    
    for element, description in required_elements:
        checks.append(print_check(element in content, description))
    
    return all(checks)


def verify_deliverable_4():
    """Verify DELIVERABLE 4: Supporting Files."""
    print_header("DELIVERABLE 4: Supporting Files & Documentation")
    
    checks = []
    
    # Check netlify.toml
    netlify_path = Path("netlify.toml")
    checks.append(print_check(netlify_path.exists(), "netlify.toml exists"))
    
    if netlify_path.exists():
        content = netlify_path.read_text()
        checks.append(print_check("publish" in content, "netlify.toml has publish directory"))
    
    # Check deployment documentation
    deployment_path = Path("DEPLOYMENT.md")
    checks.append(print_check(deployment_path.exists(), "DEPLOYMENT.md exists"))
    
    if deployment_path.exists():
        content = deployment_path.read_text()
        required = [
            "POLYGON_API_KEY",
            "Netlify",
            "GitHub Actions",
            "dashboard.html"
        ]
        for item in required:
            checks.append(print_check(item in content, f"DEPLOYMENT.md mentions {item}"))
    
    # Check quick start guide
    quickstart_path = Path("DASHBOARD_QUICKSTART.md")
    checks.append(print_check(quickstart_path.exists(), "DASHBOARD_QUICKSTART.md exists"))
    
    # Check data files exist
    prices_path = Path("data/prices_state.json")
    checks.append(print_check(prices_path.exists(), "data/prices_state.json exists"))
    
    if prices_path.exists():
        try:
            data = json.loads(prices_path.read_text())
            checks.append(print_check("prices" in data, "prices_state.json has valid structure"))
            checks.append(print_check(len(data.get("prices", [])) > 0, "prices_state.json has price data"))
        except json.JSONDecodeError:
            checks.append(print_check(False, "prices_state.json is valid JSON"))
    
    alerts_path = Path("data/alerts.json")
    checks.append(print_check(alerts_path.exists(), "data/alerts.json exists"))
    
    if alerts_path.exists():
        try:
            data = json.loads(alerts_path.read_text())
            checks.append(print_check("alert_triggered" in data, "alerts.json has valid structure"))
        except json.JSONDecodeError:
            checks.append(print_check(False, "alerts.json is valid JSON"))
    
    return all(checks)


def verify_no_hardcoded_secrets():
    """Verify no hardcoded secrets in code."""
    print_header("SECURITY CHECK: No Hardcoded Secrets")
    
    checks = []
    
    files_to_check = [
        "dashboard.html",
        "run_pipeline.py",
        ".github/workflows/weekly-update.yml",
        "DEPLOYMENT.md",
        "DASHBOARD_QUICKSTART.md"
    ]
    
    # Common patterns that might indicate hardcoded secrets
    secret_patterns = [
        "polygon.io/v2/",  # Direct API URLs without variable
        "apiKey=",  # API key in query string
    ]
    
    safe_patterns = [
        "POLYGON_API_KEY",  # Environment variable reference (OK)
        "secrets.POLYGON_API_KEY",  # GitHub secrets reference (OK)
        "your_api_key",  # Placeholder (OK)
        "example.com"  # Example domain (OK)
    ]
    
    all_safe = True
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            has_hardcoded_secret = False
            
            for pattern in secret_patterns:
                if pattern in content:
                    # Check if it's in a safe context
                    is_safe = any(safe in content for safe in safe_patterns)
                    if not is_safe:
                        checks.append(print_check(False, f"{file_path} may contain hardcoded secrets"))
                        has_hardcoded_secret = True
                        all_safe = False
                        break
            
            if not has_hardcoded_secret:
                checks.append(print_check(True, f"{file_path} has no hardcoded secrets"))
    
    return all_safe


def main():
    """Run all verification checks."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "DELIVERABLES VERIFICATION REPORT" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")
    
    results = {
        "Deliverable 1 (Dashboard)": verify_deliverable_1(),
        "Deliverable 2 (Pipeline)": verify_deliverable_2(),
        "Deliverable 3 (GitHub Actions)": verify_deliverable_3(),
        "Deliverable 4 (Supporting Files)": verify_deliverable_4(),
        "Security Check": verify_no_hardcoded_secrets()
    }
    
    print_header("FINAL RESULTS")
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL DELIVERABLES VERIFIED SUCCESSFULLY!")
        print("=" * 70)
        print("\nNext Steps:")
        print("1. Commit and push changes")
        print("2. Set up POLYGON_API_KEY secret in GitHub")
        print("3. Run GitHub Actions workflow manually to test")
        print("4. Deploy to Netlify")
        print("\nFor detailed instructions, see:")
        print("  • DASHBOARD_QUICKSTART.md (5-minute setup)")
        print("  • DEPLOYMENT.md (comprehensive guide)")
        return 0
    else:
        print("❌ SOME DELIVERABLES FAILED VERIFICATION")
        print("=" * 70)
        print("\nPlease review the failures above and fix them.")
        return 1


if __name__ == "__main__":
    exit(main())
