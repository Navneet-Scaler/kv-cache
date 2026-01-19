"""
Tests for Task 1: Basic Cache Store

These tests verify the basic KVStore operations:
- put(): Insert or update key-value pairs
- get(): Retrieve values by key
- delete(): Remove key-value pairs
- exists(): Check if key exists

Run with: python -m pytest tests/test_store.py -v
"""

import pytest
from src.cache.store import KVStore


class TestKVStorePut:
    """Test put() method."""

    def test_put_new_key(self, store: KVStore):
        """Test inserting a new key-value pair."""
        result = store.put("key1", "value1")
        assert result is True
        assert store.size() == 1

    def test_put_returns_true(self, store: KVStore):
        """Test that put always returns True on success."""
        assert store.put("key", "value") is True

    def test_put_update_existing_key(self, store: KVStore):
        """Test updating an existing key's value."""
        store.put("key1", "value1")
        result = store.put("key1", "value2")

        assert result is True
        assert store.get("key1") == "value2"
        assert store.size() == 1  # Size should not increase

    def test_put_multiple_keys(self, store: KVStore):
        """Test inserting multiple different keys."""
        store.put("key1", "value1")
        store.put("key2", "value2")
        store.put("key3", "value3")

        assert store.size() == 3
        assert store.get("key1") == "value1"
        assert store.get("key2") == "value2"
        assert store.get("key3") == "value3"

    def test_put_overwrite_multiple_times(self, store: KVStore):
        """Test overwriting the same key multiple times."""
        for i in range(10):
            store.put("key", f"value{i}")

        assert store.get("key") == "value9"
        assert store.size() == 1


class TestKVStoreGet:
    """Test get() method."""

    def test_get_existing_key(self, store: KVStore):
        """Test retrieving an existing key."""
        store.put("mykey", "myvalue")
        result = store.get("mykey")
        assert result == "myvalue"

    def test_get_nonexistent_key(self, store: KVStore):
        """Test retrieving a key that doesn't exist returns None."""
        result = store.get("nonexistent")
        assert result is None

    def test_get_empty_store(self, store: KVStore):
        """Test get on empty store returns None."""
        assert store.get("anything") is None

    def test_get_after_update(self, store: KVStore):
        """Test that get returns the most recent value after update."""
        store.put("key", "original")
        store.put("key", "updated")
        assert store.get("key") == "updated"

    def test_get_multiple_keys(self, store: KVStore):
        """Test getting multiple different keys."""
        store.put("a", "1")
        store.put("b", "2")
        store.put("c", "3")

        assert store.get("a") == "1"
        assert store.get("b") == "2"
        assert store.get("c") == "3"


class TestKVStoreDelete:
    """Test delete() method."""

    def test_delete_existing_key(self, store: KVStore):
        """Test deleting an existing key."""
        store.put("key1", "value1")
        result = store.delete("key1")

        assert result is True
        assert store.get("key1") is None
        assert store.size() == 0

    def test_delete_nonexistent_key(self, store: KVStore):
        """Test deleting a key that doesn't exist returns False."""
        result = store.delete("nonexistent")
        assert result is False

    def test_delete_then_get(self, store: KVStore):
        """Test that get returns None after delete."""
        store.put("key", "value")
        store.delete("key")
        assert store.get("key") is None

    def test_delete_then_reinsert(self, store: KVStore):
        """Test that a deleted key can be reinserted."""
        store.put("key", "value1")
        store.delete("key")
        store.put("key", "value2")

        assert store.get("key") == "value2"
        assert store.size() == 1

    def test_delete_one_of_many(self, store: KVStore):
        """Test deleting one key doesn't affect others."""
        store.put("key1", "value1")
        store.put("key2", "value2")
        store.put("key3", "value3")

        store.delete("key2")

        assert store.get("key1") == "value1"
        assert store.get("key2") is None
        assert store.get("key3") == "value3"
        assert store.size() == 2


class TestKVStoreExists:
    """Test exists() method."""

    def test_exists_with_existing_key(self, store: KVStore):
        """Test exists returns True for existing key."""
        store.put("key1", "value1")
        assert store.exists("key1") is True

    def test_exists_with_nonexistent_key(self, store: KVStore):
        """Test exists returns False for non-existent key."""
        assert store.exists("nonexistent") is False

    def test_exists_empty_store(self, store: KVStore):
        """Test exists on empty store returns False."""
        assert store.exists("anything") is False

    def test_exists_after_delete(self, store: KVStore):
        """Test exists returns False after deletion."""
        store.put("key", "value")
        store.delete("key")
        assert store.exists("key") is False

    def test_exists_after_reinsert(self, store: KVStore):
        """Test exists returns True after reinserting deleted key."""
        store.put("key", "value1")
        store.delete("key")
        store.put("key", "value2")
        assert store.exists("key") is True


class TestKVStoreSizeAndClear:
    """Test size() and clear() methods."""

    def test_size_empty_store(self, store: KVStore):
        """Test size of empty store is 0."""
        assert store.size() == 0

    def test_size_after_puts(self, store: KVStore):
        """Test size increases with each new key."""
        assert store.size() == 0
        store.put("key1", "value1")
        assert store.size() == 1
        store.put("key2", "value2")
        assert store.size() == 2

    def test_size_after_update(self, store: KVStore):
        """Test size doesn't increase when updating existing key."""
        store.put("key", "value1")
        store.put("key", "value2")
        assert store.size() == 1

    def test_size_after_delete(self, store: KVStore):
        """Test size decreases after delete."""
        store.put("key1", "value1")
        store.put("key2", "value2")
        store.delete("key1")
        assert store.size() == 1

    def test_clear(self, store: KVStore):
        """Test clear removes all keys."""
        store.put("key1", "value1")
        store.put("key2", "value2")
        store.put("key3", "value3")

        store.clear()

        assert store.size() == 0
        assert store.get("key1") is None
        assert store.get("key2") is None
        assert store.get("key3") is None

    def test_clear_empty_store(self, store: KVStore):
        """Test clear on empty store doesn't error."""
        store.clear()  # Should not raise
        assert store.size() == 0


class TestKVStoreEdgeCases:
    """Test edge cases."""

    def test_empty_key(self, store: KVStore):
        """Test empty string as key."""
        result = store.put("", "value")
        assert result is True
        assert store.get("") == "value"

    def test_empty_value(self, store: KVStore):
        """Test empty string as value."""
        result = store.put("key", "")
        assert result is True
        assert store.get("key") == ""

    def test_special_characters_in_key(self, store: KVStore):
        """Test keys with special characters."""
        special_keys = [
            "key-with-dashes",
            "key_with_underscores",
            "key.with.dots",
            "key:with:colons",
            "key123numbers",
            "123startswithnumber",
            "UPPERCASE",
            "MiXeDcAsE",
        ]

        for i, key in enumerate(special_keys):
            store.put(key, f"value{i}")

        for i, key in enumerate(special_keys):
            assert store.get(key) == f"value{i}"

    def test_long_key(self, store: KVStore):
        """Test with maximum length key (256 chars)."""
        long_key = "k" * 256
        store.put(long_key, "value")
        assert store.get(long_key) == "value"

    def test_long_value(self, store: KVStore):
        """Test with maximum length value (256 chars)."""
        long_value = "v" * 256
        store.put("key", long_value)
        assert store.get("key") == long_value

    def test_case_sensitive_keys(self, store: KVStore):
        """Test that keys are case-sensitive."""
        store.put("Key", "value1")
        store.put("KEY", "value2")
        store.put("key", "value3")

        assert store.get("Key") == "value1"
        assert store.get("KEY") == "value2"
        assert store.get("key") == "value3"
        assert store.size() == 3


class TestKVStoreStress:
    """Stress tests."""

    def test_many_keys(self, large_store: KVStore):
        """Test inserting many keys."""
        num_keys = 1000

        for i in range(num_keys):
            large_store.put(f"key{i}", f"value{i}")

        assert large_store.size() == num_keys

        # Verify random samples
        assert large_store.get("key0") == "value0"
        assert large_store.get("key500") == "value500"
        assert large_store.get("key999") == "value999"

    def test_many_updates_same_key(self, store: KVStore):
        """Test rapidly updating the same key."""
        for i in range(1000):
            store.put("key", f"value{i}")

        assert store.get("key") == "value999"
        assert store.size() == 1

    def test_interleaved_operations(self, store: KVStore):
        """Test interleaved put/get/delete/exists."""
        for i in range(100):
            key = f"key{i}"
            store.put(key, f"value{i}")

            # Verify immediately
            assert store.get(key) == f"value{i}"
            assert store.exists(key) is True

            # Delete some keys
            if i % 3 == 0:
                store.delete(key)
                assert store.exists(key) is False
