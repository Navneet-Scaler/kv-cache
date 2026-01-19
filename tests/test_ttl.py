"""
Tests for Task 4: TTL Support

These tests verify Time-To-Live (TTL) functionality:
- Keys expire after specified TTL
- Expired keys return None on get()
- Expired keys return False on exists()
- Cleanup of expired keys

Run with: python -m pytest tests/test_ttl.py -v

Note: Some tests use time.sleep() and may be slow.
Run with -m "not slow" to skip slow tests.
"""

import time
import pytest
from src.cache.store import KVStore


class TestTTLBasic:
    """Test basic TTL functionality."""

    def test_put_with_zero_ttl(self, store: KVStore):
        """Test TTL=0 means no expiration."""
        store.put("key", "value", ttl=0)
        assert store.get("key") == "value"

    def test_put_with_positive_ttl(self, store: KVStore):
        """Test put with positive TTL stores successfully."""
        store.put("key", "value", ttl=60)
        assert store.get("key") == "value"

    def test_key_accessible_before_expiry(self, store: KVStore):
        """Test key is accessible before TTL expires."""
        store.put("key", "value", ttl=10)

        # Should be accessible immediately
        assert store.get("key") == "value"
        assert store.exists("key") is True

    @pytest.mark.slow
    def test_key_expires_after_ttl(self, store: KVStore):
        """Test key expires after TTL seconds."""
        store.put("key", "value", ttl=1)

        # Should exist immediately
        assert store.get("key") == "value"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert store.get("key") is None

    @pytest.mark.slow
    def test_exists_returns_false_after_expiry(self, store: KVStore):
        """Test exists() returns False for expired keys."""
        store.put("key", "value", ttl=1)

        assert store.exists("key") is True

        time.sleep(1.1)

        assert store.exists("key") is False

    @pytest.mark.slow
    def test_delete_expired_key_returns_false(self, store: KVStore):
        """Test deleting expired key returns False."""
        store.put("key", "value", ttl=1)

        time.sleep(1.1)

        # Expired key treated as non-existent
        result = store.delete("key")
        assert result is False


class TestTTLUpdate:
    """Test TTL behavior on updates."""

    @pytest.mark.slow
    def test_update_resets_ttl(self, store: KVStore):
        """Test updating key resets TTL."""
        store.put("key", "value1", ttl=1)

        time.sleep(0.5)

        # Update with new TTL
        store.put("key", "value2", ttl=2)

        time.sleep(0.7)  # Original would have expired

        # Should still exist with new value
        assert store.get("key") == "value2"

    @pytest.mark.slow
    def test_update_removes_ttl(self, store: KVStore):
        """Test updating with TTL=0 removes expiration."""
        store.put("key", "value1", ttl=1)

        # Update without TTL
        store.put("key", "value2", ttl=0)

        time.sleep(1.1)

        # Should still exist (no TTL)
        assert store.get("key") == "value2"

    def test_update_adds_ttl(self, store: KVStore):
        """Test updating without TTL can add TTL."""
        store.put("key", "value1", ttl=0)
        store.put("key", "value2", ttl=60)

        # Should exist with TTL
        assert store.get("key") == "value2"


class TestTTLMultipleKeys:
    """Test TTL with multiple keys."""

    @pytest.mark.slow
    def test_different_ttls(self, store: KVStore):
        """Test multiple keys with different TTLs."""
        store.put("key1", "value1", ttl=1)
        store.put("key2", "value2", ttl=3)
        store.put("key3", "value3", ttl=0)  # No expiration

        time.sleep(1.1)

        assert store.get("key1") is None  # Expired
        assert store.get("key2") == "value2"  # Not expired
        assert store.get("key3") == "value3"  # No TTL

        time.sleep(2)

        assert store.get("key2") is None  # Now expired
        assert store.get("key3") == "value3"  # Still exists

    def test_mix_ttl_and_no_ttl(self, store: KVStore):
        """Test mixing keys with and without TTL."""
        store.put("with_ttl", "value1", ttl=60)
        store.put("no_ttl", "value2", ttl=0)

        assert store.get("with_ttl") == "value1"
        assert store.get("no_ttl") == "value2"


class TestTTLLazyCleanup:
    """Test lazy cleanup of expired keys."""

    @pytest.mark.slow
    def test_get_removes_expired_key(self, store: KVStore):
        """Test get() removes expired key (lazy cleanup)."""
        store.put("key", "value", ttl=1)

        time.sleep(1.1)

        # Get triggers lazy cleanup
        assert store.get("key") is None

        # Key should be removed from internal storage
        assert "key" not in store._store

    @pytest.mark.slow
    def test_exists_removes_expired_key(self, store: KVStore):
        """Test exists() removes expired key (lazy cleanup)."""
        store.put("key", "value", ttl=1)

        time.sleep(1.1)

        # Exists triggers lazy cleanup
        assert store.exists("key") is False

        # Key should be removed
        assert "key" not in store._store


class TestTTLActiveCleanup:
    """Test active cleanup of expired keys."""

    @pytest.mark.slow
    def test_cleanup_expired_removes_keys(self, store: KVStore):
        """Test cleanup_expired() removes all expired keys."""
        store.put("key1", "value1", ttl=1)
        store.put("key2", "value2", ttl=1)
        store.put("key3", "value3", ttl=0)  # No TTL

        time.sleep(1.1)

        removed = store.cleanup_expired()

        assert removed == 2
        assert store.size() == 1
        assert store.get("key3") == "value3"

    def test_cleanup_expired_empty_store(self, store: KVStore):
        """Test cleanup on empty store."""
        removed = store.cleanup_expired()
        assert removed == 0

    def test_cleanup_no_expired_keys(self, store: KVStore):
        """Test cleanup when no keys are expired."""
        store.put("key1", "value1", ttl=60)
        store.put("key2", "value2", ttl=0)

        removed = store.cleanup_expired()

        assert removed == 0
        assert store.size() == 2


class TestTTLStats:
    """Test TTL with stats."""

    @pytest.mark.slow
    def test_get_stats_shows_expired(self, store: KVStore):
        """Test get_stats includes expired key info."""
        store.put("key1", "value1", ttl=1)
        store.put("key2", "value2", ttl=0)

        time.sleep(1.1)

        stats = store.get_stats()

        assert stats["total_keys"] == 2
        assert stats["expired_keys"] == 1
        assert stats["active_keys"] == 1


class TestTTLEdgeCases:
    """Test TTL edge cases."""

    def test_large_ttl(self, store: KVStore):
        """Test with large TTL value."""
        store.put("key", "value", ttl=86400)  # 24 hours
        assert store.get("key") == "value"

    @pytest.mark.slow
    def test_ttl_boundary(self, store: KVStore):
        """Test TTL at exact boundary."""
        store.put("key", "value", ttl=1)

        # Just before expiration
        time.sleep(0.9)
        assert store.get("key") == "value"

        # Just after expiration
        time.sleep(0.2)
        assert store.get("key") is None

    @pytest.mark.slow
    def test_delete_then_reinsert_with_ttl(self, store: KVStore):
        """Test TTL after delete and reinsert."""
        store.put("key", "value1", ttl=1)
        store.delete("key")
        store.put("key", "value2", ttl=60)

        time.sleep(1.1)

        # Should still exist with new TTL
        assert store.get("key") == "value2"
