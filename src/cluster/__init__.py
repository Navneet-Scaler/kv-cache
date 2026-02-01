"""
Cluster module for distributed KV-Cache.

This module provides clustering support including:
- Cluster topology and configuration
- Shard calculation and ownership
- Request routing and forwarding
- Replication logic
"""

from .config import ClusterConfig, get_shard_for_key
from .router import ClusterRouter

__all__ = ['ClusterConfig', 'get_shard_for_key', 'ClusterRouter']
