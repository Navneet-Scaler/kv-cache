"""
Tests for Task 5: LRU Eviction

These tests verify LRU (Least Recently Used) eviction:
- Eviction when cache is full
- Correct LRU ordering
- Update of access order on get/put

Run with: python -m pytest tests/test_eviction.py -v
"""

import pytest
from src.cache.store import KVStore
from src.cache.eviction import LRUEvictionPolicy


class TestLRUEvictionPolicy:
    """Test the LRUEvictionPolicy class directly."""

    def test_init(self, lru_cache: LRUEvictionPolicy):
        """Test LRU cache initialization."""
        assert lru_cache.max_size == 5
        assert lru_cache.size() == 0

    def test_init_invalid_size(self):
        """Test initialization with invalid size."""
        with pytest.raises(ValueError):
            LRUEvictionPolicy(max_size=0)

        with pytest.raises(ValueError):
            LRUEvictionPolicy(max_size=-1)

    def test_put_and_get(self, lru_cache: LRUEvictionPolicy):
        """Test basic put and get operations."""
        lru_cache.put("key1", "value1")
        assert lru_cache.get("key1") == "value1"

    def test_get_nonexistent(self, lru_cache: LRUEvictionPolicy):
        """Test get for non-existent key."""
        assert lru_cache.get("nonexistent") is None

    def test_put_updates_existing(self, lru_cache: LRUEvictionPolicy):
        """Test that put updates existing key."""
        lru_cache.put("key1", "value1")
        lru_cache.put("key1", "value2")

        assert lru_cache.get("key1") == "value2"
        assert lru_cache.size() == 1

    def test_eviction_when_full(self, lru_cache: LRUEvictionPolicy):
        """Test eviction when cache is full."""
        # Fill the cache (max_size = 5)
        for i in range(5):
            lru_cache.put(f"key{i}", f"value{i}")

        # Add one more - should evict key0 (LRU)
        evicted = lru_cache.put("key5", "value5")

        assert evicted == "key0"
        assert lru_cache.get("key0") is None
        assert lru_cache.get("key5") == "value5"
        assert lru_cache.size() == 5

    def test_get_updates_lru_order(self, lru_cache: LRUEvictionPolicy):
        """Test that get() updates LRU order."""
        # Fill cache
        for i in range(5):
            lru_cache.put(f"key{i}", f"value{i}")

        # Access key0 to make it MRU
        lru_cache.get("key0")

        # Add new key - should evict key1 (now LRU)
        evicted = lru_cache.put("key5", "value5")

        assert evicted == "key1"
        assert lru_cache.get("key0") == "value0"  # key0 still exists
        assert lru_cache.get("key1") is None  # key1 evicted

    def test_put_existing_updates_lru_order(self, lru_cache: LRUEvictionPolicy):
        """Test that put() on existing key updates LRU order."""
        # Fill cache
        for i in range(5):
            lru_cache.put(f"key{i}", f"value{i}")

        # Update key0 to make it MRU
        lru_cache.put("key0", "updated")

        # Add new key - should evict key1 (now LRU)
        evicted = lru_cache.put("key5", "value5")

        assert evicted == "key1"
        assert lru_cache.get("key0") == "updated"

    def test_delete(self, lru_cache: LRUEvictionPolicy):
        """Test delete operation."""
        lru_cache.put("key1", "value1")

        result = lru_cache.delete("key1")

        assert result is True
        assert lru_cache.get("key1") is None
        assert lru_cache.size() == 0

    def test_delete_nonexistent(self, lru_cache: LRUEvictionPolicy):
        """Test delete of non-existent key."""
        result = lru_cache.delete("nonexistent")
        assert result is False

    def test_contains(self, lru_cache: LRUEvictionPolicy):
        """Test contains() method."""
        lru_cache.put("key1", "value1")

        assert lru_cache.contains("key1") is True
        assert lru_cache.contains("nonexistent") is False

    def test_peek_does_not_update_order(self, lru_cache: LRUEvictionPolicy):
        """Test that peek() doesn't update LRU order."""
        for i in range(5):
            lru_cache.put(f"key{i}", f"value{i}")

        # Peek at key0 (should NOT make it MRU)
        assert lru_cache.peek("key0") == "value0"

        # Add new key - key0 should still be evicted (still LRU)
        evicted = lru_cache.put("key5", "value5")

        assert evicted == "key0"

    def test_evict_lru(self, lru_cache: LRUEvictionPolicy):
        """Test manual evict_lru() method."""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")

        evicted = lru_cache.evict_lru()

        assert evicted == ("key1", "value1")
        assert lru_cache.size() == 1

    def test_evict_lru_empty(self, lru_cache: LRUEvictionPolicy):
        """Test evict_lru() on empty cache."""
        assert lru_cache.evict_lru() is None

    def test_get_lru_key(self, lru_cache: LRUEvictionPolicy):
        """Test get_lru_key() method."""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")

        assert lru_cache.get_lru_key() == "key1"

    def test_get_mru_key(self, lru_cache: LRUEvictionPolicy):
        """Test get_mru_key() method."""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")

        assert lru_cache.get_mru_key() == "key2"

    def test_is_full(self, lru_cache: LRUEvictionPolicy):
        """Test is_full() method."""
        assert lru_cache.is_full() is False

        for i in range(5):
            lru_cache.put(f"key{i}", f"value{i}")

        assert lru_cache.is_full() is True

    def test_clear(self, lru_cache: LRUEvictionPolicy):
        """Test clear() method."""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")

        lru_cache.clear()

        assert lru_cache.size() == 0
        assert lru_cache.get("key1") is None

    def test_get_all_keys(self, lru_cache: LRUEvictionPolicy):
        """Test get_all_keys() returns keys in LRU order."""
        lru_cache.put("key1", "value1")
        lru_cache.put("key2", "value2")
        lru_cache.put("key3", "value3")

        # Access key1 to make it MRU
        lru_cache.get("key1")

        keys = lru_cache.get_all_keys()

        # Order should be: key2 (LRU), key3, key1 (MRU)
        assert keys == ["key2", "key3", "key1"]


class TestKVStoreEviction:
    """Test LRU eviction in KVStore."""

    def test_eviction_when_full(self, small_store: KVStore):
        """Test KVStore evicts LRU when full."""
        # Fill the store (max_size = 5)
        for i in range(5):
            small_store.put(f"key{i}", f"value{i}")

        # Add one more - should evict key0
        small_store.put("key5", "value5")

        assert small_store.get("key0") is None
        assert small_store.get("key5") == "value5"
        assert small_store.size() == 5

    def test_get_updates_lru_in_store(self, small_store: KVStore):
        """Test that get() updates LRU order in KVStore."""
        # Fill the store
        for i in range(5):
            small_store.put(f"key{i}", f"value{i}")

        # Access key0 to make it MRU
        small_store.get("key0")

        # Add new key - should evict key1 (now LRU)
        small_store.put("key5", "value5")

        assert small_store.get("key0") == "value0"
        assert small_store.get("key1") is None

    def test_put_updates_lru_in_store(self, small_store: KVStore):
        """Test that put() on existing key updates LRU order."""
        # Fill the store
        for i in range(5):
            small_store.put(f"key{i}", f"value{i}")

        # Update key0 to make it MRU
        small_store.put("key0", "updated")

        # Add new key - should evict key1
        small_store.put("key5", "value5")

        assert small_store.get("key0") == "updated"
        assert small_store.get("key1") is None

    def test_continuous_eviction(self, small_store: KVStore):
        """Test continuous eviction as new keys are added."""
        # Add 10 keys to a store of size 5
        for i in range(10):
            small_store.put(f"key{i}", f"value{i}")

        # Should have exactly 5 keys
        assert small_store.size() == 5

        # Only the last 5 keys should exist
        for i in range(5):
            assert small_store.get(f"key{i}") is None

        for i in range(5, 10):
            assert small_store.get(f"key{i}") == f"value{i}"

    def test_eviction_with_access_pattern(self, small_store: KVStore):
        """Test eviction with specific access pattern."""
        # Add 5 keys
        for i in range(5):
            small_store.put(f"key{i}", f"value{i}")

        # Access keys in specific order: 4, 3, 2, 1, 0
        # After accesses: key4 accessed first (oldest), key0 accessed last (newest)
        # So LRU order: key4, key3, key2, key1, key0
        # Adding new key should evict key4
        for i in range(4, -1, -1):
            small_store.get(f"key{i}")

        small_store.put("key5", "value5")

        assert small_store.get("key4") is None  # Evicted
        assert small_store.get("key0") == "value0"  # MRU, still exists


class TestEvictionEdgeCases:
    """Test edge cases for eviction."""

    def test_single_item_cache(self):
        """Test cache with single item capacity."""
        store = KVStore(max_size=1)

        store.put("key1", "value1")
        assert store.get("key1") == "value1"

        store.put("key2", "value2")
        assert store.get("key1") is None
        assert store.get("key2") == "value2"

    def test_update_does_not_trigger_eviction(self, small_store: KVStore):
        """Test that updating existing key doesn't evict."""
        # Fill the store
        for i in range(5):
            small_store.put(f"key{i}", f"value{i}")

        # Update existing key
        small_store.put("key0", "updated")

        # All 5 keys should still exist
        assert small_store.size() == 5
        assert small_store.get("key0") == "updated"

    def test_delete_creates_space(self, small_store: KVStore):
        """Test that deleting a key creates space without eviction."""
        # Fill the store
        for i in range(5):
            small_store.put(f"key{i}", f"value{i}")

        # Delete a key
        small_store.delete("key0")

        # Add new key - should NOT evict any existing key
        small_store.put("key5", "value5")

        # All keys except key0 should exist
        assert small_store.get("key0") is None  # Deleted
        for i in range(1, 5):
            assert small_store.get(f"key{i}") == f"value{i}"
        assert small_store.get("key5") == "value5"


class TestEvictionWithTTL:
    """Test interaction between eviction and TTL."""

    def test_expired_keys_can_be_evicted(self, small_store: KVStore):
        """Test that expired keys can still be evicted."""
        import time

        # Add key with TTL
        small_store.put("key0", "value0", ttl=1)

        # Fill rest of cache
        for i in range(1, 5):
            small_store.put(f"key{i}", f"value{i}")

        # Wait for expiration
        time.sleep(1.1)

        # key0 is expired but still counts toward size
        # Adding new key should evict key0 (it's LRU)
        small_store.put("key5", "value5")

        assert small_store.size() == 5

    def test_access_expired_key_does_not_update_lru(self, small_store: KVStore):
        """Test that accessing expired key doesn't update LRU."""
        import time

        # Add key with TTL
        small_store.put("key0", "value0", ttl=1)

        # Fill rest of cache
        for i in range(1, 5):
            small_store.put(f"key{i}", f"value{i}")

        time.sleep(1.1)

        # Try to access expired key - should return None
        # and not affect LRU order
        assert small_store.get("key0") is None

        # The expired key was lazily removed, so we have space
        assert small_store.size() == 4
