"""
KV-Cache Configuration Settings

This module contains all configuration constants for the KV-Cache server.
Students should not need to modify this file.
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Server configuration settings."""

    # Network settings
    HOST: str = os.environ.get("KV_CACHE_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("KV_CACHE_PORT", "7171"))

    # Cache settings
    MAX_KEYS: int = int(os.environ.get("KV_CACHE_MAX_KEYS", "10000"))
    MAX_KEY_LENGTH: int = 256
    MAX_VALUE_LENGTH: int = 256

    # TTL settings
    DEFAULT_TTL: int = 0  # 0 means no expiration
    CLEANUP_INTERVAL: int = 60  # Seconds between active cleanup runs

    # Connection settings
    MAX_CONNECTIONS: int = 1000
    READ_BUFFER_SIZE: int = 4096
    CONNECTION_TIMEOUT: int = 300  # Seconds before idle connection is closed

    # Logging settings
    DEBUG: bool = os.environ.get("KV_CACHE_DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.environ.get("KV_CACHE_LOG_LEVEL", "INFO")


# Global settings instance
settings = Settings()
