"""Configuration management for the e-ink dashboard."""
import yaml
import os
from pathlib import Path


class Config:
    """Handles loading and accessing configuration settings."""

    def __init__(self, config_path=None):
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key_path, default=None):
        """
        Get configuration value using dot notation.

        Example: config.get('weather.latitude')
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_enabled_widgets(self):
        """Get list of enabled widgets."""
        return self.get('widgets', [])

    def get_display_size(self):
        """Get display dimensions as (width, height) tuple."""
        return (
            self.get('display.width', 250),
            self.get('display.height', 122)
        )

    def get_refresh_interval(self):
        """Get refresh interval in seconds."""
        minutes = self.get('refresh.interval_minutes', 15)
        return minutes * 60
