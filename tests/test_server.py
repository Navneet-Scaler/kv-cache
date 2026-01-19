"""
Tests for Task 3: Async TCP Server

These tests verify the KVServer class:
- Server starts and accepts connections
- Handle multiple concurrent clients
- Process commands correctly
- Handle disconnections gracefully

Run with: python -m pytest tests/test_server.py -v
"""

import asyncio
import pytest
from tests.conftest import AsyncClient


@pytest.mark.asyncio
class TestServerConnection:
    """Test server connection handling."""

    async def test_server_accepts_connection(self, server, server_port):
        """Test that server accepts connections."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            assert client.reader is not None
            assert client.writer is not None

    async def test_server_handles_disconnect(self, server, server_port):
        """Test server handles client disconnect gracefully."""
        reader, writer = await asyncio.open_connection('127.0.0.1', server_port)

        # Send a command
        writer.write(b"PUT key value\n")
        await writer.drain()
        response = await reader.readline()
        assert response == b"OK stored\n"

        # Disconnect
        writer.close()
        await writer.wait_closed()

        # Server should still accept new connections
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("GET key")
            assert response == "OK value"

    async def test_server_handles_quit(self, server, server_port):
        """Test QUIT command closes connection gracefully."""
        reader, writer = await asyncio.open_connection('127.0.0.1', server_port)

        writer.write(b"PUT key value\n")
        await writer.drain()
        await reader.readline()

        # Send QUIT
        writer.write(b"QUIT\n")
        await writer.drain()

        # Give server time to process
        await asyncio.sleep(0.1)

        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
class TestServerCommands:
    """Test command execution through server."""

    async def test_put_command(self, server, server_port):
        """Test PUT command."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("PUT key1 value1")
            assert response == "OK stored"

    async def test_get_command_found(self, server, server_port):
        """Test GET command for existing key."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            await client.send_command("PUT key1 value1")
            response = await client.send_command("GET key1")
            assert response == "OK value1"

    async def test_get_command_not_found(self, server, server_port):
        """Test GET command for non-existent key."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("GET nonexistent")
            assert response == "ERROR key not found"

    async def test_delete_command_found(self, server, server_port):
        """Test DELETE command for existing key."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            await client.send_command("PUT key1 value1")
            response = await client.send_command("DELETE key1")
            assert response == "OK deleted"

            # Verify deletion
            response = await client.send_command("GET key1")
            assert response == "ERROR key not found"

    async def test_delete_command_not_found(self, server, server_port):
        """Test DELETE command for non-existent key."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("DELETE nonexistent")
            assert response == "ERROR key not found"

    async def test_exists_command_found(self, server, server_port):
        """Test EXISTS command for existing key."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            await client.send_command("PUT key1 value1")
            response = await client.send_command("EXISTS key1")
            assert response == "OK 1"

    async def test_exists_command_not_found(self, server, server_port):
        """Test EXISTS command for non-existent key."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("EXISTS nonexistent")
            assert response == "OK 0"

    async def test_invalid_command(self, server, server_port):
        """Test invalid command returns error."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("INVALID command")
            assert response.startswith("ERROR")

    async def test_malformed_put(self, server, server_port):
        """Test malformed PUT returns error."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("PUT onlykey")
            assert response.startswith("ERROR")


@pytest.mark.asyncio
class TestServerMultipleCommands:
    """Test multiple commands on single connection."""

    async def test_multiple_commands_sequence(self, server, server_port):
        """Test sending multiple commands."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            assert await client.send_command("PUT key1 value1") == "OK stored"
            assert await client.send_command("PUT key2 value2") == "OK stored"
            assert await client.send_command("GET key1") == "OK value1"
            assert await client.send_command("GET key2") == "OK value2"
            assert await client.send_command("EXISTS key1") == "OK 1"
            assert await client.send_command("DELETE key1") == "OK deleted"
            assert await client.send_command("EXISTS key1") == "OK 0"

    async def test_put_with_ttl(self, server, server_port):
        """Test PUT with TTL."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("PUT tempkey tempvalue 60")
            assert response == "OK stored"

            response = await client.send_command("GET tempkey")
            assert response == "OK tempvalue"


@pytest.mark.asyncio
class TestServerConcurrency:
    """Test concurrent client handling."""

    async def test_two_clients(self, server, server_port):
        """Test two simultaneous clients."""
        async with AsyncClient('127.0.0.1', server_port) as client1:
            async with AsyncClient('127.0.0.1', server_port) as client2:
                # Client 1 stores
                await client1.send_command("PUT key1 value1")

                # Client 2 reads
                response = await client2.send_command("GET key1")
                assert response == "OK value1"

                # Client 2 stores
                await client2.send_command("PUT key2 value2")

                # Client 1 reads
                response = await client1.send_command("GET key2")
                assert response == "OK value2"

    async def test_many_concurrent_clients(self, server, server_port):
        """Test many concurrent clients."""
        num_clients = 10

        async def client_task(client_id: int):
            async with AsyncClient('127.0.0.1', server_port) as client:
                key = f"key{client_id}"
                value = f"value{client_id}"

                response = await client.send_command(f"PUT {key} {value}")
                assert response == "OK stored"

                response = await client.send_command(f"GET {key}")
                assert response == f"OK {value}"

        tasks = [client_task(i) for i in range(num_clients)]
        await asyncio.gather(*tasks)

    async def test_concurrent_writes_same_key(self, server, server_port):
        """Test concurrent writes to same key."""
        async with AsyncClient('127.0.0.1', server_port) as client1:
            async with AsyncClient('127.0.0.1', server_port) as client2:
                await asyncio.gather(
                    client1.send_command("PUT shared value1"),
                    client2.send_command("PUT shared value2"),
                )

                # One value should win
                response = await client1.send_command("GET shared")
                assert response in ["OK value1", "OK value2"]


@pytest.mark.asyncio
class TestServerEdgeCases:
    """Test edge cases."""

    async def test_empty_command(self, server, server_port):
        """Test empty command."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            response = await client.send_command("")
            assert response.startswith("ERROR")

    async def test_case_insensitive_commands(self, server, server_port):
        """Test commands are case-insensitive."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            assert await client.send_command("put key1 value1") == "OK stored"
            assert await client.send_command("GET key1") == "OK value1"
            assert await client.send_command("Put key2 value2") == "OK stored"
            assert await client.send_command("get key2") == "OK value2"

    async def test_rapid_connect_disconnect(self, server, server_port):
        """Test rapid connection cycles."""
        for _ in range(10):
            async with AsyncClient('127.0.0.1', server_port) as client:
                await client.send_command("PUT key value")

    async def test_special_characters(self, server, server_port):
        """Test keys with special characters."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            keys = ["key-dash", "key_under", "key.dot", "key:colon"]

            for i, key in enumerate(keys):
                await client.send_command(f"PUT {key} value{i}")

            for i, key in enumerate(keys):
                response = await client.send_command(f"GET {key}")
                assert response == f"OK value{i}"
