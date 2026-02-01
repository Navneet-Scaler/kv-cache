"""
Async TCP Server Module (Task 3)

This module implements the asynchronous TCP server for KV-Cache.

Students must implement:
- handle_client(): Handle a single client connection
- start(): Start the server and accept connections

Key asyncio concepts needed:
- asyncio.start_server(): Create a TCP server
- StreamReader.readline(): Read a line from client
- StreamWriter.write() / drain(): Send data to client
- Proper connection cleanup with writer.close() / wait_closed()
"""

import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from typing import Optional

from ..cache.store import KVStore
from ..cluster.config import ClusterConfig
from ..cluster.router import ClusterRouter
from ..config.settings import settings
from ..protocol.commands import CommandType, Response
from ..protocol.parser import ProtocolParser

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KVServer:
    """
    Asynchronous TCP server for the KV-Cache service.

    This server handles multiple concurrent clients using asyncio.
    Each client connection is handled in a separate coroutine,
    allowing for high concurrency without threading.

    Features:
    - Non-blocking I/O with asyncio
    - Persistent connections (multiple commands per connection)
    - Graceful error handling and connection cleanup
    - Shared KVStore across all connections

    Usage:
        server = KVServer(host='0.0.0.0', port=7171)
        await server.start()  # Runs forever

    Attributes:
        host: Server bind address (e.g., '0.0.0.0')
        port: Server port number (e.g., 7171)
        store: The KVStore instance shared by all connections
        parser: The ProtocolParser for parsing commands
    """

    def __init__(
            self,
            host: str = None,
            port: int = None,
            store: KVStore = None,
            cluster_config: ClusterConfig = None,
    ):
        """
        Initialize the server.

        Args:
            host: Bind address (default from settings)
            port: Port number (default from settings)
            store: KVStore instance (creates new one if not provided)
            cluster_config: ClusterConfig instance for clustering support
        """
        self.host = host if host is not None else settings.HOST
        self.port = port if port is not None else settings.PORT
        self.store = store if store is not None else KVStore()
        self.parser = ProtocolParser()
        
        # Clustering support
        self.cluster_config = cluster_config
        self.router = ClusterRouter(cluster_config) if cluster_config else None

        # Server state
        self._server: Optional[asyncio.Server] = None
        self._running = False
        self._connection_count = 0
        self._total_requests = 0

    async def handle_client(
            self,
            reader: StreamReader,
            writer: StreamWriter
    ) -> None:
        """
        Handle a single client connection.

        This coroutine is called for each new client connection.
        It reads commands from the client, processes them, and sends
        responses until the client disconnects or sends QUIT.

        Args:
            reader: StreamReader for reading from the client
            writer: StreamWriter for writing to the client

        Protocol flow:
            1. Read a line (command) from the client
            2. Parse the command using ProtocolParser
            3. Execute the command on the KVStore
            4. Format and send the response
            5. Repeat until QUIT or client disconnects

        Implementation requirements:
        - Get client address for logging (writer.get_extra_info('peername'))
        - Loop reading lines until empty data (disconnect) or QUIT
        - Handle decode errors gracefully
        - Always close the writer in a finally block
        - Handle ConnectionResetError and other exceptions
        """
        addr = writer.get_extra_info('peername')
        self._connection_count += 1
        logger.debug(f"Client connected: {addr}")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    # Client disconnected
                    logger.debug(f"Client disconnected: {addr}")
                    break

                try:
                    raw = data.decode().rstrip('\r\n')
                except UnicodeDecodeError:
                    response = Response.error("invalid encoding")
                    writer.write(self.parser.format_response(response).encode())
                    await writer.drain()
                    continue

                command = self.parser.parse_request(raw)

                if command.type == CommandType.QUIT:
                    logger.debug(f"Client requested quit: {addr}")
                    break

                if not command.is_valid:
                    response = Response.error("invalid command")
                else:
                    self._total_requests += 1
                    response = self._execute_command(command)
                    
                    # Handle forwarding if needed (clustered mode)
                    if response.message == "FORWARD_TO_PRIMARY" and self.router:
                        response = await self.router.forward_to_primary(command)
                    
                    # Handle replication for successful writes (primary only)
                    elif self.cluster_config and self.cluster_config.is_primary_for_key(command.key):
                        if command.type == CommandType.PUT and response.message == "stored":
                            # Replicate and require success before returning OK
                            repl_success = await self.router.replicate_put(command.key, command.value, command.ttl)
                            if not repl_success:
                                logger.warning(f"Replication failed for PUT {command.key}")
                                response = Response.error("replication failed")

                        elif command.type == CommandType.DELETE and response.message == "deleted":
                            # Replicate delete and require success
                            repl_success = await self.router.replicate_delete(command.key)
                            if not repl_success:
                                logger.warning(f"Replication failed for DELETE {command.key}")
                                response = Response.error("replication failed")

                writer.write(self.parser.format_response(response).encode())
                await writer.drain()

        except ConnectionResetError:
            logger.debug(f"Connection reset by client: {addr}")
        except Exception as exc:  # Log unexpected errors but keep server alive
            logger.exception(f"Error handling client {addr}: {exc}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _execute_command(self, command) -> Response:
        """
        Execute a parsed command on the store.

        This is a helper method that routes commands to the appropriate
        KVStore method and returns the formatted response.
        
        With clustering enabled:
        - Client requests are forwarded to primary if needed
        - Primary replicates writes to replica
        - Replication commands are executed locally

        Args:
            command: The Command object to execute

        Returns:
            Response object with the result
        """
        # Handle replication commands (internal only - never forward)
        if command.type == CommandType.REPL_PUT:
            self.store.put(command.key, command.value, ttl=command.ttl)
            return Response.stored()
        
        if command.type == CommandType.REPL_DELETE:
            deleted = self.store.delete(command.key)
            return Response.deleted() if deleted else Response.key_not_found()
        
        # If clustering is disabled, execute locally
        if not self.cluster_config:
            return self._execute_local(command)
        
        # Client commands - may need forwarding
        if command.type in (CommandType.PUT, CommandType.DELETE):
            # Check if this node is the primary
            if not self.cluster_config.is_primary_for_key(command.key):
                # Forward to primary
                logger.debug(f"Forwarding {command.type.name} {command.key} to primary")
                # Use asyncio to forward (we'll handle this in handle_client)
                return Response.error("FORWARD_TO_PRIMARY")
            
            # This node is primary - execute and replicate
            if command.type == CommandType.PUT:
                # Store locally
                self.store.put(command.key, command.value, ttl=command.ttl)
                # Replicate to replica (will be done async in handle_client)
                return Response.stored()
            
            if command.type == CommandType.DELETE:
                # Delete locally
                deleted = self.store.delete(command.key)
                if deleted:
                    # Replicate delete (will be done async in handle_client)
                    return Response.deleted()
                return Response.key_not_found()
        
        # GET and EXISTS can be handled locally or forwarded
        if command.type == CommandType.GET:
            if not self.cluster_config.is_primary_for_key(command.key):
                # Forward to primary
                logger.debug(f"Forwarding GET {command.key} to primary")
                return Response.error("FORWARD_TO_PRIMARY")
            
            value = self.store.get(command.key)
            return Response.value_response(value) if value is not None else Response.key_not_found()
        
        if command.type == CommandType.EXISTS:
            if not self.cluster_config.is_primary_for_key(command.key):
                logger.debug(f"Forwarding EXISTS {command.key} to primary")
                return Response.error("FORWARD_TO_PRIMARY")
            
            exists = self.store.exists(command.key)
            return Response.exists_response(exists)
        
        return Response.error("invalid command")
    
    def _execute_local(self, command) -> Response:
        """Execute command locally (non-clustered mode)."""
        if command.type == CommandType.PUT:
            self.store.put(command.key, command.value, ttl=command.ttl)
            return Response.stored()

        if command.type == CommandType.GET:
            value = self.store.get(command.key)
            return Response.value_response(value) if value is not None else Response.key_not_found()

        if command.type == CommandType.DELETE:
            deleted = self.store.delete(command.key)
            return Response.deleted() if deleted else Response.key_not_found()

        if command.type == CommandType.EXISTS:
            exists = self.store.exists(command.key)
            return Response.exists_response(exists)

        return Response.error("invalid command")

    async def start(self) -> None:
        """
        Start the server and begin accepting connections.

        This method creates the asyncio server and runs forever
        (or until cancelled). It should be called from asyncio.run()
        or within an existing event loop.

        Implementation:
        - Use asyncio.start_server() with self.handle_client as callback
        - Log the server address when started
        - Use server.serve_forever() to run indefinitely

        Example:
            server = KVServer(port=7171)
            asyncio.run(server.start())
        """
        if self._running:
            return

        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
            limit=settings.READ_BUFFER_SIZE,
        )
        self._running = True

        addrs = ', '.join(str(sock.getsockname()) for sock in self._server.sockets or [])
        logger.info(f"Serving on {addrs}")

        try:
            async with self._server:
                await self._server.serve_forever()
        except asyncio.CancelledError:
            # Expected during shutdown/fixture cleanup
            logger.debug("Server start cancelled")
        finally:
            self._running = False

    async def stop(self) -> None:
        """
        Stop the server gracefully.

        Closes the server and waits for it to fully shut down.
        """
        if self._server is None:
            return

        self._server.close()
        try:
            await self._server.wait_closed()
        finally:
            self._server = None
            self._running = False

    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._running

    def get_stats(self) -> dict:
        """
        Get server statistics.

        Returns:
            Dictionary with server stats including connection counts,
            request counts, and store statistics.
        """
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "total_connections": self._connection_count,
            "total_requests": self._total_requests,
            "store_stats": self.store.get_stats(),
        }


async def run_server(host: str = None, port: int = None) -> None:
    """
    Convenience function to create and run the server.

    Args:
        host: Bind address (default from settings)
        port: Port number (default from settings)

    Usage:
        asyncio.run(run_server(port=7171))
    """
    server = KVServer(host=host, port=port)

    try:
        await server.start()
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    finally:
        await server.stop()
