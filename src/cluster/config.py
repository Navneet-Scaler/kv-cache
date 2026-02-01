"""
Cluster Configuration Module

Defines the static cluster topology with hardcoded shard assignments.
Each node knows the entire cluster topology but only handles requests
for shards it owns (as primary or replica).

Cluster Topology (Static):
- 3 Nodes
- 3 Shards (0, 1, 2)
- Each shard has 1 primary and 1 replica

Shard Assignments:
- Shard 0: Primary=Node1, Replica=Node3
- Shard 1: Primary=Node2, Replica=Node1
- Shard 2: Primary=Node3, Replica=Node2

Node Addresses:
- Node 1: localhost:5001
- Node 2: localhost:5002
- Node 3: localhost:5003
"""

import hashlib
from typing import Dict, Tuple, Optional


# Cluster Constants
NUM_SHARDS = 3
NUM_NODES = 3

# Shard ownership map: shard_id -> (primary_node_id, replica_node_id)
SHARD_MAP: Dict[int, Tuple[int, int]] = {
    0: (1, 3),  # Shard 0: Primary=1, Replica=3
    1: (2, 1),  # Shard 1: Primary=2, Replica=1
    2: (3, 2),  # Shard 2: Primary=3, Replica=2
}

# Node addresses: node_id -> (host, port)
# Uses container names for Docker, but also works with localhost
import os

# Check if we're in Docker (container names) or local (localhost)
_use_docker = os.getenv('DOCKER_ENV', 'false').lower() == 'true'
_host_prefix = '' if _use_docker else 'localhost'

NODE_ADDRESSES: Dict[int, Tuple[str, int]] = {
    1: ('kv-cache-node1' if _use_docker else 'localhost', 5001),
    2: ('kv-cache-node2' if _use_docker else 'localhost', 5002),
    3: ('kv-cache-node3' if _use_docker else 'localhost', 5003),
}


def get_shard_for_key(key: str) -> int:
    """
    Calculate which shard owns a given key.
    
    Uses consistent hashing to ensure the same key always maps to the same shard
    across all nodes in the cluster.
    
    Args:
        key: The key to hash
        
    Returns:
        Shard ID (0, 1, or 2)
        
    Implementation:
        - Use hashlib.sha256 for consistent hashing
        - Convert hash to integer and mod by NUM_SHARDS
    """
    # Use SHA256 for consistent hashing across all nodes
    hash_digest = hashlib.sha256(key.encode('utf-8')).digest()
    # Convert first 8 bytes to int
    hash_int = int.from_bytes(hash_digest[:8], byteorder='big')
    return hash_int % NUM_SHARDS


class ClusterConfig:
    """
    Cluster configuration for a specific node.
    
    This class provides methods to determine:
    - Which shard a key belongs to
    - Whether this node is the primary/replica for a shard
    - Node addresses for forwarding/replication
    """
    
    def __init__(self, node_id: int):
        """
        Initialize cluster config for a specific node.
        
        Args:
            node_id: The ID of this node (1, 2, or 3)
        """
        if node_id not in range(1, NUM_NODES + 1):
            raise ValueError(f"Invalid node_id: {node_id}. Must be 1-{NUM_NODES}")
        
        self.node_id = node_id
        self.num_shards = NUM_SHARDS
        self.shard_map = SHARD_MAP
        self.node_addresses = NODE_ADDRESSES
        
        # Pre-compute which shards this node owns
        self.primary_shards = [shard for shard, (primary, _) in SHARD_MAP.items() if primary == node_id]
        self.replica_shards = [shard for shard, (_, replica) in SHARD_MAP.items() if replica == node_id]
        
    def get_shard(self, key: str) -> int:
        """Get the shard ID for a key."""
        return get_shard_for_key(key)
    
    def is_primary_for_key(self, key: str) -> bool:
        """Check if this node is the primary for the given key."""
        shard = self.get_shard(key)
        primary, _ = self.shard_map[shard]
        return primary == self.node_id
    
    def is_replica_for_key(self, key: str) -> bool:
        """Check if this node is the replica for the given key."""
        shard = self.get_shard(key)
        _, replica = self.shard_map[shard]
        return replica == self.node_id
    
    def get_primary_for_key(self, key: str) -> int:
        """Get the node ID of the primary for the given key."""
        shard = self.get_shard(key)
        primary, _ = self.shard_map[shard]
        return primary
    
    def get_replica_for_key(self, key: str) -> int:
        """Get the node ID of the replica for the given key."""
        shard = self.get_shard(key)
        _, replica = self.shard_map[shard]
        return replica
    
    def get_node_address(self, node_id: int) -> Tuple[str, int]:
        """
        Get the address (host, port) for a node.
        
        Args:
            node_id: The node ID to look up
            
        Returns:
            Tuple of (host, port)
        """
        if node_id not in self.node_addresses:
            raise ValueError(f"Unknown node_id: {node_id}")
        return self.node_addresses[node_id]
    
    def should_handle_key(self, key: str, is_internal: bool = False) -> bool:
        """
        Determine if this node should handle the request for a key.
        
        Args:
            key: The key being accessed
            is_internal: True if this is an internal replication request
            
        Returns:
            True if this node should process the request, False if it should forward
        """
        # Internal replication requests are always handled (no forwarding)
        if is_internal:
            return True
        
        # For client requests, only primary handles them (may need to forward)
        return self.is_primary_for_key(key)
    
    def __repr__(self) -> str:
        return (f"ClusterConfig(node_id={self.node_id}, "
                f"primary_shards={self.primary_shards}, "
                f"replica_shards={self.replica_shards})")
