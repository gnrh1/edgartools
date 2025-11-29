"""Configuration loader for multi-stock monitoring system."""

import logging
from pathlib import Path
from typing import List

try:
    import yaml
except ImportError:
    yaml = None


class ConfigError(Exception):
    """Exception raised for configuration loading errors."""
    pass


def load_tickers_config() -> List[str]:
    """
    Load ticker list from config/tickers.yaml.
    
    Returns:
        List[str]: List of ticker symbols (deduplicated and sorted)
        
    Raises:
        ConfigError: If config file is invalid or missing
    """
    if yaml is None:
        raise ConfigError("PyYAML not installed. Please install it with: pip install pyyaml")
    
    config_path = Path(__file__).parent / "tickers.yaml"
    
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML format in {config_path}: {e}")
    except IOError as e:
        raise ConfigError(f"Failed to read {config_path}: {e}")
    
    if not config or 'monitored_stocks' not in config:
        raise ConfigError("Invalid config: missing 'monitored_stocks' key")
    
    tickers = config['monitored_stocks']
    
    if not tickers or len(tickers) == 0:
        raise ConfigError("Config error: no tickers specified")
    
    if not isinstance(tickers, list):
        raise ConfigError(f"Config error: 'monitored_stocks' must be a list, got {type(tickers).__name__}")
    
    tickers = [str(t).upper() for t in tickers]
    
    # Deduplicate while preserving order
    seen = set()
    unique_tickers = []
    for ticker in tickers:
        if ticker not in seen:
            unique_tickers.append(ticker)
            seen.add(ticker)
        else:
            logging.warning(f"Duplicate ticker '{ticker}' in config, skipping")
    
    return unique_tickers
