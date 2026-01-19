"""
Pytest Configuration and Fixtures

This module provides shared fixtures and configuration for all tests.
"""

import asyncio
import socket
import pytest
import pytest_asyncio
from contextlib import closing
from typing import AsyncGenerator

from src.cache.store import KVStore
from src.cache.eviction import LRUEvictionPolicy
from src.protocol.parser import ProtocolParser
from src.network.tcp_server import KVServer


def find_free_port() -> int:
    """Find an available port for testing."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


# ============================================================================
# KVStore Fixtures
# ============================================================================

@pytest.fixture
def store() -> KVStore:
    """Create a fresh KVStore instance with default size (100 keys)."""
    return KVStore(max_size=100)


@pytest.fixture
def large_store() -> KVStore:
    """Create a KVStore with larger capacity (10000 keys)."""
    return KVStore(max_size=10000)


@pytest.fixture
def small_store() -> KVStore:
    """Create a KVStore with small capacity for eviction testing (5 keys)."""
    return KVStore(max_size=5)


# ============================================================================
# Protocol Fixtures
# ============================================================================

@pytest.fixture
def parser() -> ProtocolParser:
    """Create a ProtocolParser instance."""
    return ProtocolParser()


# ============================================================================
# LRU Cache Fixtures
# ============================================================================

@pytest.fixture
def lru_cache() -> LRUEvictionPolicy:
    """Create an LRU cache for testing (5 items max)."""
    return LRUEvictionPolicy(max_size=5)


# ============================================================================
# Server Fixtures
# ============================================================================

@pytest.fixture
def server_port() -> int:
    """Get a free port for server testing."""
    return find_free_port()


@pytest_asyncio.fixture
async def server(server_port: int) -> AsyncGenerator[KVServer, None]:
    """
    Create and start a server instance for testing.

    This fixture:
    1. Creates a KVServer on a random free port
    2. Starts it in a background task
    3. Yields the server for testing
    4. Cleans up after the test
    """
    srv = KVServer(host='127.0.0.1', port=server_port)

    # Start server in background task
    server_task = asyncio.create_task(srv.start())

    # Wait for server to be ready
    await asyncio.sleep(0.1)

    yield srv

    # Cleanup
    await srv.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


# ============================================================================
# Client Fixtures
# ============================================================================

class AsyncClient:
    """
    Helper class for testing server interactions.

    Provides a simple async context manager interface for
    sending commands and receiving responses.

    Usage:
        async with AsyncClient('127.0.0.1', 7171) as client:
            response = await client.send_command("PUT key value")
            assert response == "OK stored"
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self) -> None:
        """Establish connection to server."""
        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port
        )

    async def disconnect(self) -> None:
        """Close connection to server."""
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass

    async def send_command(self, command: str) -> str:
        """
        Send a command and receive the response.

        Args:
            command: Command string (newline will be added if missing)

        Returns:
            Response string (stripped of trailing newline)
        """
        if not command.endswith('\n'):
            command += '\n'

        self.writer.write(command.encode())
        await self.writer.drain()

        response = await self.reader.readline()
        return response.decode().strip()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


@pytest.fixture
def client_factory(server_port: int):
    """
    Factory fixture to create test clients.

    Usage:
        async def test_something(server, client_factory):
            async with client_factory() as client:
                response = await client.send_command("GET key")
    """
    def factory() -> AsyncClient:
        return AsyncClient('127.0.0.1', server_port)
    return factory


@pytest_asyncio.fixture
async def client_reader_writer(
    server: KVServer,
    server_port: int
) -> AsyncGenerator[tuple, None]:
    """
    Create a raw reader/writer pair connected to the server.

    Useful for low-level protocol testing.
    """
    reader, writer = await asyncio.open_connection('127.0.0.1', server_port)

    yield reader, writer

    writer.close()
    await writer.wait_closed()


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


# Configure asyncio mode for pytest-asyncio
pytest_plugins = ['pytest_asyncio']
