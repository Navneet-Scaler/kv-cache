"""
Integration Tests

End-to-end tests that verify the complete system works together.

Run with: python -m pytest tests/test_integration.py -v
"""

import asyncio
import time
import pytest
from tests.conftest import AsyncClient


@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""

    async def test_complete_workflow(self, server, server_port):
        """Test a complete user workflow."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            # Create multiple keys
            assert await client.send_command("PUT user:1 alice") == "OK stored"
            assert await client.send_command("PUT user:2 bob") == "OK stored"
            assert await client.send_command("PUT user:3 charlie") == "OK stored"

            # Read all keys
            assert await client.send_command("GET user:1") == "OK alice"
            assert await client.send_command("GET user:2") == "OK bob"
            assert await client.send_command("GET user:3") == "OK charlie"

            # Check existence
            assert await client.send_command("EXISTS user:1") == "OK 1"
            assert await client.send_command("EXISTS user:99") == "OK 0"

            # Update a key
            assert await client.send_command("PUT user:1 alice_updated") == "OK stored"
            assert await client.send_command("GET user:1") == "OK alice_updated"

            # Delete a key
            assert await client.send_command("DELETE user:2") == "OK deleted"
            assert await client.send_command("GET user:2") == "ERROR key not found"
            assert await client.send_command("EXISTS user:2") == "OK 0"

    async def test_ttl_through_server(self, server, server_port):
        """Test TTL functionality through server."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            # Store key with TTL
            assert await client.send_command("PUT tempkey tempvalue 2") == "OK stored"

            # Key should exist
            assert await client.send_command("GET tempkey") == "OK tempvalue"
            assert await client.send_command("EXISTS tempkey") == "OK 1"

            # Wait for expiration
            await asyncio.sleep(2.5)

            # Key should be expired
            assert await client.send_command("GET tempkey") == "ERROR key not found"
            assert await client.send_command("EXISTS tempkey") == "OK 0"

    async def test_multiple_clients_shared_state(self, server, server_port):
        """Test that multiple clients share the same cache state."""
        async with AsyncClient('127.0.0.1', server_port) as client1:
            async with AsyncClient('127.0.0.1', server_port) as client2:
                # Client 1 stores data
                await client1.send_command("PUT shared:key shared:value")

                # Client 2 can read it
                response = await client2.send_command("GET shared:key")
                assert response == "OK shared:value"

                # Client 2 updates it
                await client2.send_command("PUT shared:key updated:value")

                # Client 1 sees the update
                response = await client1.send_command("GET shared:key")
                assert response == "OK updated:value"

                # Client 1 deletes it
                await client1.send_command("DELETE shared:key")

                # Client 2 can't find it
                response = await client2.send_command("GET shared:key")
                assert response == "ERROR key not found"

    async def test_concurrent_updates(self, server, server_port):
        """Test concurrent updates from multiple clients."""
        num_clients = 5
        num_operations = 20

        async def client_operations(client_id: int):
            async with AsyncClient('127.0.0.1', server_port) as client:
                for i in range(num_operations):
                    key = f"key:{client_id}:{i}"
                    value = f"value:{client_id}:{i}"

                    response = await client.send_command(f"PUT {key} {value}")
                    assert response == "OK stored"

                    response = await client.send_command(f"GET {key}")
                    assert response == f"OK {value}"

        # Run all clients concurrently
        tasks = [client_operations(i) for i in range(num_clients)]
        await asyncio.gather(*tasks)

    async def test_error_recovery(self, server, server_port):
        """Test that server recovers from errors gracefully."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            # Send invalid commands
            await client.send_command("INVALID")
            await client.send_command("PUT")
            await client.send_command("GET")

            # Server should still work normally
            assert await client.send_command("PUT key value") == "OK stored"
            assert await client.send_command("GET key") == "OK value"

    async def test_rapid_operations(self, server, server_port):
        """Test rapid succession of operations."""
        async with AsyncClient('127.0.0.1', server_port) as client:
            # Rapid PUT operations
            for i in range(100):
                response = await client.send_command(f"PUT key{i} value{i}")
                assert response == "OK stored"

            # Rapid GET operations
            for i in range(100):
                response = await client.send_command(f"GET key{i}")
                assert response == f"OK value{i}"


@pytest.mark.asyncio
@pytest.mark.integration
class TestProtocolCompliance:
    """Test protocol compliance."""

    async def test_response_format(self, server, server_port):
        """Test that responses follow the protocol format."""
        reader, writer = await asyncio.open_connection('127.0.0.1', server_port)

        try:
            # PUT response
            writer.write(b"PUT key value\n")
            await writer.drain()
            response = await reader.readline()
            assert response == b"OK stored\n"

            # GET response
            writer.write(b"GET key\n")
            await writer.drain()
            response = await reader.readline()
            assert response == b"OK value\n"

            # DELETE response
            writer.write(b"DELETE key\n")
            await writer.drain()
            response = await reader.readline()
            assert response == b"OK deleted\n"

            # GET not found
            writer.write(b"GET key\n")
            await writer.drain()
            response = await reader.readline()
            assert response == b"ERROR key not found\n"

        finally:
            writer.close()
            await writer.wait_closed()

    async def test_newline_handling(self, server, server_port):
        """Test proper newline handling."""
        reader, writer = await asyncio.open_connection('127.0.0.1', server_port)

        try:
            # Commands should work with \n
            writer.write(b"PUT key1 value1\n")
            await writer.drain()
            response = await reader.readline()
            assert response.endswith(b"\n")

            # Multiple commands in quick succession
            writer.write(b"PUT key2 value2\nPUT key3 value3\n")
            await writer.drain()

            response1 = await reader.readline()
            response2 = await reader.readline()

            assert response1 == b"OK stored\n"
            assert response2 == b"OK stored\n"

        finally:
            writer.close()
            await writer.wait_closed()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
class TestStress:
    """Stress tests for the system."""

    async def test_high_connection_count(self, server, server_port):
        """Test handling many concurrent connections."""
        num_connections = 50

        async def quick_operation():
            try:
                reader, writer = await asyncio.open_connection(
                    '127.0.0.1', server_port
                )
                writer.write(b"PUT test value\n")
                await writer.drain()
                await reader.readline()
                writer.close()
                await writer.wait_closed()
                return True
            except Exception:
                return False

        results = await asyncio.gather(*[
            quick_operation() for _ in range(num_connections)
        ])

        # All connections should succeed
        assert all(results)

    async def test_sustained_load(self, server, server_port):
        """Test sustained load over time."""
        duration = 2  # seconds

        async def load_generator():
            end_time = time.time() + duration
            count = 0

            async with AsyncClient('127.0.0.1', server_port) as client:
                while time.time() < end_time:
                    key = f"key:{count}"
                    await client.send_command(f"PUT {key} value")
                    await client.send_command(f"GET {key}")
                    count += 1

            return count

        # Run multiple load generators
        results = await asyncio.gather(*[
            load_generator() for _ in range(5)
        ])

        total_operations = sum(results) * 2  # Each iteration does PUT and GET

        # Should handle reasonable throughput
        assert total_operations > 100
