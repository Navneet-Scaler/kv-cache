"""
Key-Value Store Module (Tasks 1 & 4)

This module implements the core key-value storage functionality.

Students must implement:
- Task 1: Basic operations (put, get, delete, exists)
- Task 4: TTL (Time-To-Live) support for automatic key expiration
"""

import time
from collections import OrderedDict
from typing import Optional, Tuple, Dict, Any

from ..config.settings import settings


class KVStore:
    """
    In-memory key-value store with TTL and LRU eviction support.

    This class provides O(1) average-case time complexity for:
    - put: Insert or update a key-value pair
    - get: Retrieve a value by key
    - delete: Remove a key-value pair
    - exists: Check if a key exists

    Features:
    - TTL (Time-To-Live): Keys can automatically expire after a specified time
    - LRU Eviction: When cache is full, least recently used keys are evicted

    Internal Storage:
        Uses OrderedDict for O(1) operations with LRU ordering.
        Format: key -> (value, expiration_timestamp)
        expiration_timestamp = 0 means no expiration

    Attributes:
        max_size: Maximum number of keys allowed in the store
    """

    def __init__(self, max_size: int = None):
        """
        Initialize the KV store.

        Args:
            max_size: Maximum number of keys (default from settings.MAX_KEYS)
        """
        self.max_size = max_size if max_size is not None else settings.MAX_KEYS

        # === TODO START: Initialize internal storage ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def put(self, key: str, value: str, ttl: int = 0) -> bool:
        """
        Insert or update a key-value pair.

        Args:
            key: The key to store
            value: The value to associate with the key
            ttl: Time-to-live in seconds (0 = no expiration)

        Returns:
            True on success

        Time Complexity: O(1) average

        Implementation requirements:
        - Task 1: Store the key-value pair, return True
        - Task 4: Calculate and store expiration time if ttl > 0
        - Task 5: Handle LRU - update position for existing keys,
                  evict LRU item if cache full when adding new key
        """
        # === TODO START: Implement put with TTL and LRU ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve the value for a given key.

        Args:
            key: The key to look up

        Returns:
            The value if found and not expired, None otherwise

        Time Complexity: O(1) average

        Implementation requirements:
        - Task 1: Return value if key exists, None otherwise
        - Task 4: Check if key has expired; if so, delete it and return None
        - Task 5: Update LRU order - move accessed key to most recent
        """
        # === TODO START: Implement get with TTL check and LRU update ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def delete(self, key: str) -> bool:
        """
        Delete a key-value pair.

        Args:
            key: The key to delete

        Returns:
            True if key was deleted, False if key didn't exist

        Time Complexity: O(1) average

        Implementation requirements:
        - Task 1: Remove key if exists, return True; return False if not found
        - Task 4: Expired keys should be treated as non-existent (return False)
        """
        # === TODO START: Implement delete with expiration check ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def exists(self, key: str) -> bool:
        """
        Check if a key exists (and is not expired).

        Args:
            key: The key to check

        Returns:
            True if key exists and is not expired, False otherwise

        Time Complexity: O(1) average

        Implementation requirements:
        - Task 1: Return True if key exists, False otherwise
        - Task 4: Return False for expired keys; perform lazy cleanup
        """
        # === TODO START: Implement exists with expiration check ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def size(self) -> int:
        """
        Get the current number of keys in the store.

        Note: This may include expired keys that haven't been cleaned up yet.

        Returns:
            Number of keys currently stored
        """
        return len(self._store)

    def clear(self) -> None:
        """Remove all keys from the store."""
        # === TODO START: Implement clear ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def cleanup_expired(self) -> int:
        """
        Remove all expired keys from the store (active expiration).

        This method can be called periodically by a background task
        for proactive cleanup of expired keys.

        Returns:
            Number of keys removed

        Task 4 Bonus: Implement this for active expiration cleanup.
        """
        # === TODO START: Implement cleanup_expired (Bonus) ===
        raise NotImplementedError("TODO: Implement this method")
        # === TODO END ===

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the store.

        Returns:
            Dictionary containing:
            - total_keys: Total keys in store
            - expired_keys: Count of expired (but not yet cleaned) keys
            - active_keys: Count of non-expired keys
            - max_size: Maximum capacity
            - utilization: Current usage as fraction of max_size
        """
        now = time.time()
        total = len(self._store)
        expired = sum(1 for _, (_, expires_at) in self._store.items() if 0 < expires_at < now)

        return {
            "total_keys": total,
            "expired_keys": expired,
            "active_keys": total - expired,
            "max_size": self.max_size,
            "utilization": total / self.max_size if self.max_size > 0 else 0,
        }
