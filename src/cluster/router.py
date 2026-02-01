"""
Cluster Router Module

Handles request forwarding and replication between nodes.
Provides TCP client functionality to communicate with other nodes.
"""

import asyncio
import logging
from typing import Optional, Tuple

from ..protocol.commands import Command, Response, CommandType
from ..protocol.parser import ProtocolParser
from .config import ClusterConfig

logger = logging.getLogger(__name__)


class ClusterRouter:
    """
    Routes requests to appropriate nodes and handles replication.
    
    Responsibilities:
    - Forward client requests to the primary node
    - Send replication commands to replica nodes
    - Handle TCP connections to other nodes
    """
    
    def __init__(self, cluster_config: ClusterConfig):
        """
        Initialize the cluster router.
        
        Args:
            cluster_config: The cluster configuration for this node
        """
        self.config = cluster_config
        self.parser = ProtocolParser()
        
    async def forward_to_primary(self, command: Command) -> Response:
        """
        Forward a command to the primary node for the key.
        
        Args:
            command: The command to forward
            
        Returns:
            The response from the primary node
        """
        primary_node = self.config.get_primary_for_key(command.key)
        host, port = self.config.get_node_address(primary_node)
        
        logger.debug(f"Forwarding {command.type.name} {command.key} to node {primary_node}")
        
        try:
            response = await self._send_command(host, port, command)
            return response
        except Exception as e:
            logger.error(f"Failed to forward to node {primary_node}: {e}")
            return Response.error(f"forwarding failed: {e}")
    
    async def replicate_put(self, key: str, value: str, ttl: int = 0) -> bool:
        """
        Replicate a PUT operation to the replica node.
        
        Args:
            key: The key being stored
            value: The value to store
            ttl: Time-to-live in seconds
            
        Returns:
            True if replication succeeded, False otherwise
        """
        replica_node = self.config.get_replica_for_key(key)
        host, port = self.config.get_node_address(replica_node)
        
        logger.debug(f"Replicating PUT {key} to replica node {replica_node}")
        
        # Create internal replication command
        repl_command = Command(
            type=CommandType.REPL_PUT,
            key=key,
            value=value,
            ttl=ttl,
            raw=f"REPL_PUT {key} {value} {ttl}"
        )
        
        try:
            response = await self._send_command(host, port, repl_command)
            if response.status.value == "OK":
                logger.debug(f"Replication PUT {key} succeeded")
                return True
            else:
                logger.error(f"Replication PUT {key} failed: {response.message}")
                return False
        except Exception as e:
            logger.error(f"Failed to replicate PUT to node {replica_node}: {e}")
            return False
    
    async def replicate_delete(self, key: str) -> bool:
        """
        Replicate a DELETE operation to the replica node.
        
        Args:
            key: The key being deleted
            
        Returns:
            True if replication succeeded, False otherwise
        """
        replica_node = self.config.get_replica_for_key(key)
        host, port = self.config.get_node_address(replica_node)
        
        logger.debug(f"Replicating DELETE {key} to replica node {replica_node}")
        
        # Create internal replication command
        repl_command = Command(
            type=CommandType.REPL_DELETE,
            key=key,
            raw=f"REPL_DELETE {key}"
        )
        
        try:
            response = await self._send_command(host, port, repl_command)
            if response.status.value == "OK":
                logger.debug(f"Replication DELETE {key} succeeded")
                return True
            else:
                logger.error(f"Replication DELETE {key} failed: {response.message}")
                return False
        except Exception as e:
            logger.error(f"Failed to replicate DELETE to node {replica_node}: {e}")
            return False
    
    async def _send_command(self, host: str, port: int, command: Command, timeout: float = 5.0) -> Response:
        """
        Send a command to another node via TCP.
        
        Args:
            host: Target host
            port: Target port
            command: Command to send
            timeout: Connection timeout in seconds
            
        Returns:
            Response from the target node
        """
        try:
            # Open connection to target node
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            
            try:
                # Format and send command
                formatted_cmd = self._format_command(command)
                writer.write(formatted_cmd.encode())
                await writer.drain()
                
                # Read response
                data = await asyncio.wait_for(reader.readline(), timeout=timeout)
                if not data:
                    return Response.error("empty response from node")
                
                # Parse response
                response_str = data.decode().strip()
                response = self._parse_response(response_str)
                return response
                
            finally:
                writer.close()
                await writer.wait_closed()
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to {host}:{port}")
            return Response.error("connection timeout")
        except Exception as e:
            logger.error(f"Error sending command to {host}:{port}: {e}")
            return Response.error(f"connection error: {e}")
    
    def _format_command(self, command: Command) -> str:
        """
        Format a command for sending over the wire.
        
        Args:
            command: The command to format
            
        Returns:
            Formatted command string with newline
        """
        if command.type == CommandType.PUT:
            if command.ttl > 0:
                return f"PUT {command.key} {command.value} {command.ttl}\n"
            return f"PUT {command.key} {command.value}\n"
        elif command.type == CommandType.GET:
            return f"GET {command.key}\n"
        elif command.type == CommandType.DELETE:
            return f"DELETE {command.key}\n"
        elif command.type == CommandType.EXISTS:
            return f"EXISTS {command.key}\n"
        elif command.type == CommandType.REPL_PUT:
            if command.ttl > 0:
                return f"REPL_PUT {command.key} {command.value} {command.ttl}\n"
            return f"REPL_PUT {command.key} {command.value}\n"
        elif command.type == CommandType.REPL_DELETE:
            return f"REPL_DELETE {command.key}\n"
        else:
            return command.raw + "\n"
    
    def _parse_response(self, response_str: str) -> Response:
        """
        Parse a response string from another node.
        
        Args:
            response_str: Raw response string
            
        Returns:
            Parsed Response object
        """
        # Simple response parsing
        # Expected formats:
        # - "OK STORED"
        # - "OK DELETED"
        # - "OK <value>"
        # - "OK EXISTS"
        # - "OK NOT_EXISTS"
        # - "ERROR <message>"
        # - "ERROR KEY_NOT_FOUND"
        
        parts = response_str.split(None, 1)
        if not parts:
            return Response.error("invalid response")

        status = parts[0].upper()
        message = parts[1] if len(parts) > 1 else ""
        message_lower = message.lower()

        if status == "OK":
            if message_lower == "stored":
                return Response.stored()
            if message_lower == "deleted":
                return Response.deleted()
            if message in ("1", "0"):
                return Response.exists_response(message == "1")
            if message:
                # Value response
                return Response.value_response(message)
            return Response.ok()
        if status == "ERROR":
            if message_lower in ("key not found", "key_not_found"):
                return Response.key_not_found()
            return Response.error(message)
        return Response.error(f"unknown status: {status}")
