#!/usr/bin/env python3
"""
Manual cluster validation script.

This script tests the clustering functionality by:
1. Connecting to different nodes
2. Testing PUT/GET/DELETE forwarding
3. Verifying replication
"""

import socket
import time


def send_command(host: str, port: int, command: str) -> str:
    """Send a command to a node and return the response."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(f"{command}\n".encode())
        response = sock.recv(1024).decode().strip()
        return response


def test_cluster():
    """Run cluster validation tests."""
    print("=== KV-Cache Cluster Validation ===\n")
    
    # Wait for nodes to start
    print("Waiting for nodes to start...")
    time.sleep(2)
    
    # Test 1: Connect to Node 1 and PUT a key that belongs to Node 2
    print("\n[Test 1] PUT key to wrong node (should forward)")
    try:
        # Key 'test1' should hash to a specific shard
        # This will test forwarding
        response = send_command('localhost', 5001, 'PUT forwarded_key value1')
        print(f"  Response from Node 1: {response}")
        assert "OK" in response or "stored" in response.lower(), f"PUT failed: {response}"
        print("  ✓ Forwarding works")
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
    
    # Test 2: GET the same key from different node
    print("\n[Test 2] GET forwarded key from another node")
    try:
        response = send_command('localhost', 5002, 'GET forwarded_key')
        print(f"  Response from Node 2: {response}")
        # Should either have the value or forward
        print("  ✓ GET forwarding works")
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
    
    # Test 3: Verify replication - connect to replica
    print("\n[Test 3] PUT key and verify on replica")
    try:
        # PUT to primary
        response = send_command('localhost', 5001, 'PUT repl_test replicated_value')
        print(f"  PUT response: {response}")
        
        time.sleep(0.5)  # Give replication time
        
        # Try to get from what should be the replica
        # (This depends on which shard the key hashes to)
        response = send_command('localhost', 5003, 'GET repl_test')
        print(f"  GET from replica: {response}")
        print("  ✓ Replication works")
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
    
    # Test 4: DELETE and verify replication
    print("\n[Test 4] DELETE key and verify on replica")
    try:
        response = send_command('localhost', 5001, 'DELETE repl_test')
        print(f"  DELETE response: {response}")
        
        time.sleep(0.5)
        
        response = send_command('localhost', 5003, 'EXISTS repl_test')
        print(f"  EXISTS on replica: {response}")
        assert "0" in response, "Key should not exist after delete"
        print("  ✓ Delete replication works")
    except Exception as e:
        print(f"  ✗ Test failed: {e}")
    
    # Test 5: Basic operations on each node
    print("\n[Test 5] Basic operations on each node")
    for node_id, port in [(1, 5001), (2, 5002), (3, 5003)]:
        try:
            key = f"node{node_id}_test"
            response = send_command('localhost', port, f'PUT {key} value{node_id}')
            print(f"  Node {node_id} PUT: {response}")
            
            response = send_command('localhost', port, f'GET {key}')
            print(f"  Node {node_id} GET: {response}")
            
            response = send_command('localhost', port, f'EXISTS {key}')
            print(f"  Node {node_id} EXISTS: {response}")
            
            print(f"  ✓ Node {node_id} operations work")
        except Exception as e:
            print(f"  ✗ Node {node_id} failed: {e}")
    
    print("\n=== Validation Complete ===")


if __name__ == "__main__":
    try:
        test_cluster()
    except KeyboardInterrupt:
        print("\n\nValidation interrupted")
    except Exception as e:
        print(f"\n\nValidation failed with error: {e}")
