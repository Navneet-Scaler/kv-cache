"""
LRU Eviction Policy Module (Task 5)

This module implements the Least Recently Used (LRU) eviction policy.

The LRU eviction is integrated into KVStore (store.py), but this module
provides the standalone LRU data structure that can be tested independently.

LRU Concept:
- Most recently accessed items are at the END of the OrderedDict
- Least recently accessed items are at the BEGINNING
- On access (get/put), move item to end
- On eviction, remove from beginning

Students must implement all methods marked with TODO.
"""

from collections import OrderedDict
from typing import Optional, Tuple, Any, Dict, List


class LRUEvictionPolicy:
    """
    Least Recently Used (LRU) eviction policy implementation.

    This class provides O(1) time complexity for all operations using
    Python's OrderedDict. The OrderedDict maintains insertion order
    and provides O(1) move_to_end() for reordering.

    Usage:
        lru = LRUEvictionPolicy(max_size=100)
        lru.put("key1", "value1")
        value = lru.get("key1")  # Returns "value1", marks as recently used

    When the cache reaches max_size, the least recently used item
    is automatically evicted when a new item is added.

    Attributes:
        max_size: Maximum number of items allowed before eviction
    """

    def __init__(self, max_size: int):
        """
        Initialize the LRU cache.

        Args:
            max_size: Maximum number of items (must be positive)

        Raises:
            ValueError: If max_size is not positive
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self.max_size = max_size
        self._cache: "OrderedDict[str, Any]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """
        Get an item and mark it as recently used.

        Args:
            key: The key to retrieve

        Returns:
            The value if found, None otherwise

        Time Complexity: O(1)

        Implementation:
        - Return None if key doesn't exist
        - If key exists, move to end (most recently used) and return value
        """
        if key not in self._cache:
            return None

        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: str, value: Any) -> Optional[str]:
        """
        Put an item and handle eviction if necessary.

        Args:
            key: The key to store
            value: The value to store

        Returns:
            The evicted key if eviction occurred, None otherwise

        Time Complexity: O(1)

        Implementation:
        - If key exists, update value and move to end (no eviction)
        - If key is new and cache is full, evict LRU (first item)
        - Add new item at end (most recently used)
        """
        evicted_key = None

        if key in self._cache:
            self._cache[key] = value
            self._cache.move_to_end(key)
            return None

        if len(self._cache) >= self.max_size:
            evicted_key, _ = self._cache.popitem(last=False)

        self._cache[key] = value
        return evicted_key

    def delete(self, key: str) -> bool:
        """
        Delete an item from the cache.

        Args:
            key: The key to delete

        Returns:
            True if deleted, False if not found

        Time Complexity: O(1)
        """
        if key in self._cache:
            self._cache.pop(key, None)
            return True
        return False

    def contains(self, key: str) -> bool:
        """
        Check if key exists (without updating LRU order).

        Args:
            key: The key to check

        Returns:
            True if exists, False otherwise

        Time Complexity: O(1)

        Note: This does NOT update the LRU order, unlike get().
        """
        return key in self._cache

    def peek(self, key: str) -> Optional[Any]:
        """
        Get value without updating LRU order.

        Args:
            key: The key to peek at

        Returns:
            The value if found, None otherwise

        Time Complexity: O(1)

        Note: Unlike get(), this does NOT move the key to MRU position.
        """
        return self._cache.get(key)

    def evict_lru(self) -> Optional[Tuple[str, Any]]:
        """
        Manually evict the least recently used item.

        Returns:
            Tuple of (key, value) that was evicted, or None if cache is empty

        Time Complexity: O(1)
        """
        if not self._cache:
            return None
        return self._cache.popitem(last=False)

    def get_lru_key(self) -> Optional[str]:
        """
        Get the key of the least recently used item without evicting.

        Returns:
            The LRU key, or None if cache is empty

        Time Complexity: O(1)
        """
        if not self._cache:
            return None
        return next(iter(self._cache))

    def get_mru_key(self) -> Optional[str]:
        """
        Get the key of the most recently used item.

        Returns:
            The MRU key, or None if cache is empty

        Time Complexity: O(1)
        """
        if not self._cache:
            return None
        return next(reversed(self._cache))

    def size(self) -> int:
        """Get current number of items in cache."""
        return len(self._cache)

    def is_full(self) -> bool:
        """Check if cache is at maximum capacity."""
        return len(self._cache) >= self.max_size

    def clear(self) -> None:
        """Remove all items from cache."""
        self._cache.clear()

    def get_all_keys(self) -> List[str]:
        """
        Get all keys in LRU order (least recent first).

        Returns:
            List of keys from LRU (oldest) to MRU (newest)
        """
        return list(self._cache.keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0,
            "lru_key": self.get_lru_key(),
            "mru_key": self.get_mru_key(),
        }
