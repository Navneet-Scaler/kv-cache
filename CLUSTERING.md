# KV-Cache Cluster Implementation

This document describes the distributed clustering implementation for the KV-Cache project.

## Overview

The KV-Cache cluster consists of 3 nodes with 3 shards, each having a primary and replica for high availability and data redundancy.

### Cluster Topology

- **3 Nodes**: Node 1, Node 2, Node 3
- **3 Shards**: Shard 0, Shard 1, Shard 2
- **Replication**: Each shard has 1 primary and 1 replica

#### Shard Assignment

| Shard | Primary | Replica |
|-------|---------|---------|
| 0     | Node 1  | Node 3  |
| 1     | Node 2  | Node 1  |
| 2     | Node 3  | Node 2  |

#### Node Addresses

| Node | Host      | Port |
|------|-----------|------|
| 1    | localhost | 5001 |
| 2    | localhost | 5002 |
| 3    | localhost | 5003 |

## Features Implemented

### ✅ Task 1: Cluster Identity
- Each node reads `NODE_ID` and `PORT` from environment variables
- Nodes print their identity and shard ownership on startup
- Example: `Node 1 starting on port 5001`

### ✅ Task 2: Hardcoded Cluster Configuration
- Static cluster topology defined in `src/cluster/config.py`
- `NUM_SHARDS = 3` with fixed shard assignments
- Node addresses hardcoded for localhost development

### ✅ Task 3: Shard Calculation
- Implemented `get_shard_for_key(key)` using SHA256 hashing
- Formula: `shard_id = hash(key) % NUM_SHARDS`
- Ensures consistent shard assignment across all nodes

### ✅ Task 4: Ownership Determination
- Helper methods in `ClusterConfig`:
  - `is_primary_for_key(key)` - Check if this node is primary
  - `is_replica_for_key(key)` - Check if this node is replica
  - `get_primary_for_key(key)` - Get primary node ID
  - `get_replica_for_key(key)` - Get replica node ID

### ✅ Task 5: Request Forwarding
- Non-primary nodes forward client requests to the primary
- Forwarding is transparent to clients
- Implemented in `ClusterRouter.forward_to_primary()`

### ✅ Task 6: Internal Request Marking
- Replication commands: `REPL_PUT` and `REPL_DELETE`
- Internal commands are never forwarded (prevents loops)
- Only accepted by replica nodes

### ✅ Task 7: Replication Commands
- `REPL_PUT <key> <value> [ttl]` - Replicate PUT operation
- `REPL_DELETE <key>` - Replicate DELETE operation
- Added to `CommandType` enum in protocol layer

### ✅ Task 8: Synchronous Replication
- Primary waits for replica acknowledgment before returning success
- PUT flow: store locally → replicate → return OK
- DELETE flow: delete locally → replicate → return OK
- Replication failures are logged but don't block client response

### ✅ Task 9: Restrict Client Writes
- Replicas reject direct client PUT/DELETE requests
- Only accept internal REPL_PUT/REPL_DELETE commands
- Client writes are forwarded to primary

### ✅ Task 10: Dockerization
- `docker-compose.yml` with 3 service definitions
- Each node has unique `NODE_ID` and `PORT`
- All nodes on same `kv-cache-cluster` network
- Health checks configured for all nodes

## Architecture

### Module Structure

```
src/
├── cluster/
│   ├── __init__.py       # Cluster module exports
│   ├── config.py         # Cluster topology and configuration
│   └── router.py         # Request forwarding and replication
├── network/
│   └── tcp_server.py     # Updated with clustering support
├── protocol/
│   ├── commands.py       # Added REPL_PUT, REPL_DELETE
│   └── parser.py         # Parse replication commands
└── server.py             # Read NODE_ID, initialize cluster
```

### Request Flow

#### Client PUT (Forwarding)
```
Client → Node X
  ↓ (not primary?)
  Forward to Primary → Node Y
  ↓ (execute PUT)
  Store locally
  ↓
  Replicate to Replica → Node Z
  ↓
  Return OK to Node X → Return to Client
```

#### Direct PUT (Primary)
```
Client → Primary Node
  ↓
  Store locally
  ↓
  Replicate to Replica (REPL_PUT)
  ↓
  Return OK to Client
```

#### Replication PUT
```
Primary → Replica (REPL_PUT)
  ↓
  Store locally (no forward)
  ↓
  Return OK to Primary
```

## Running the Cluster

### Using Docker Compose (Recommended)

```bash
# Build and start all 3 nodes
docker compose up --build

# Expected logs:
# kv-cache-node1  | Node 1 starting on port 5001
# kv-cache-node1  |   Primary for shards: [0, 1]
# kv-cache-node1  |   Replica for shards: [1]
# kv-cache-node2  | Node 2 starting on port 5002
# kv-cache-node2  |   Primary for shards: [1]
# kv-cache-node2  |   Replica for shards: [2]
# kv-cache-node3  | Node 3 starting on port 5003
# kv-cache-node3  |   Primary for shards: [2, 0]
# kv-cache-node3  |   Replica for shards: [0]
```

### Manual Local Testing

Start each node in a separate terminal:

```bash
# Terminal 1 - Node 1
NODE_ID=1 PORT=5001 python -m src.server

# Terminal 2 - Node 2
NODE_ID=2 PORT=5002 python -m src.server

# Terminal 3 - Node 3
NODE_ID=3 PORT=5003 python -m src.server
```

### Standalone Mode (No Clustering)

```bash
# Run without NODE_ID to disable clustering
python -m src.server --port 7171
```

## Testing

### Manual Validation

Use the provided test script:

```bash
# Make sure cluster is running first
docker compose up -d

# Run validation tests
python test_cluster.py
```

### Manual Testing with netcat

```bash
# Connect to Node 1
nc localhost 5001

# Test commands
PUT mykey myvalue
GET mykey
EXISTS mykey
DELETE mykey
QUIT
```

### Test Scenarios

1. **Forwarding Test**
   - Connect to Node 1
   - PUT a key owned by Node 2
   - Verify it's forwarded and stored

2. **Replication Test**
   - PUT a key to primary
   - Verify it exists on replica

3. **Delete Replication**
   - DELETE a key from primary
   - Verify it's deleted on replica

4. **Multi-Node GET**
   - PUT from one node
   - GET from another node
   - Verify data consistency

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NODE_ID` | Cluster node ID (1-3) | 0 (standalone) | For clustering |
| `PORT` | Server port | 5000 | Yes |
| `DOCKER_ENV` | Use Docker network | false | For Docker |
| `KV_CACHE_HOST` | Bind address | 0.0.0.0 | No |
| `KV_CACHE_PORT` | Legacy port config | 7171 | No |
| `KV_CACHE_MAX_KEYS` | Cache size | 10000 | No |

### Cluster Configuration

Edit `src/cluster/config.py` to change:
- `NUM_SHARDS` - Number of shards
- `SHARD_MAP` - Primary/replica assignments
- `NODE_ADDRESSES` - Node host:port mappings

## Implementation Details

### Shard Calculation

```python
def get_shard_for_key(key: str) -> int:
    hash_digest = hashlib.sha256(key.encode('utf-8')).digest()
    hash_int = int.from_bytes(hash_digest[:8], byteorder='big')
    return hash_int % NUM_SHARDS
```

### Replication Logic

```python
# Primary node on PUT
self.store.put(key, value, ttl)
success = await self.router.replicate_put(key, value, ttl)
return Response.stored()
```

### Forwarding Logic

```python
# Non-primary node on client request
if not self.cluster_config.is_primary_for_key(key):
    response = await self.router.forward_to_primary(command)
    return response
```

## Troubleshooting

### Nodes can't communicate
- Check `DOCKER_ENV=true` is set in docker-compose.yml
- Verify all nodes are on the same network
- Check firewall settings

### Replication failures
- Check replica node is running
- Verify network connectivity
- Check logs for timeout errors

### Forwarding loops
- Verify REPL_PUT/REPL_DELETE are never forwarded
- Check cluster config has correct node ID

### Port conflicts
- Ensure ports 5001-5003 are available
- Use `netstat -an | grep 500` to check

## Future Enhancements

- [ ] Dynamic cluster discovery
- [ ] Configurable replication factor
- [ ] Read from replica support
- [ ] Consistency levels (strong/eventual)
- [ ] Automatic failover
- [ ] Cluster rebalancing
- [ ] Monitoring and metrics

## References

- Assignment: `ASSIGNMENT.md`
- Main README: `README.md`
- Test validation: `test_cluster.py`
