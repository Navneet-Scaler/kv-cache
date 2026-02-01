#!/bin/bash
# Quick start script for KV-Cache cluster

echo "=== KV-Cache Cluster Quick Start ==="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker first."
    exit 1
fi

echo "Step 1: Building Docker images..."
docker compose build

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed"
    exit 1
fi

echo ""
echo "Step 2: Starting cluster (3 nodes)..."
docker compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start cluster"
    exit 1
fi

echo ""
echo "Step 3: Waiting for nodes to start..."
sleep 5

echo ""
echo "Step 4: Checking node health..."
for port in 5001 5002 5003; do
    if nc -z localhost $port 2>/dev/null; then
        echo "  ✓ Node on port $port is UP"
    else
        echo "  ✗ Node on port $port is DOWN"
    fi
done

echo ""
echo "=== Cluster Started Successfully ==="
echo ""
echo "Node URLs:"
echo "  Node 1: localhost:5001"
echo "  Node 2: localhost:5002"
echo "  Node 3: localhost:5003"
echo ""
echo "Quick test:"
echo "  echo 'PUT test hello' | nc localhost 5001"
echo "  echo 'GET test' | nc localhost 5002"
echo ""
echo "View logs:"
echo "  docker compose logs -f"
echo ""
echo "Stop cluster:"
echo "  docker compose down"
echo ""
