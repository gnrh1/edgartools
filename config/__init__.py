"""Configuration module for multi-stock monitoring."""

from config.config_loader import load_tickers_config, ConfigError

__all__ = ['load_tickers_config', 'ConfigError']
