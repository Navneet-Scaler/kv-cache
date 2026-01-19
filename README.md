# KV-Cache: In-Memory Key-Value Store

A high-performance, in-memory key-value cache server built with Python and asyncio, communicating over raw TCP sockets.

---

## Table of Contents

- [Project Architecture](#project-architecture)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Running the Server](#running-the-server)
- [Local Testing & Debugging](#local-testing--debugging)
- [AWS Deployment](#aws-deployment)
- [Load Testing](#load-testing)
- [Protocol Reference](#protocol-reference)
- [Troubleshooting](#troubleshooting)

---

## Project Architecture

### High-Level Overview


```
┌──────────────────────────────────────────────────────────────┐
│                         KV-Cache Server                      │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐  │
│  │   Network   │    │   Protocol   │    │      Cache      │  │
│  │   Layer     │───▶│   Handler    │───▶│      Store      │  │
│  │             │    │              │    │                 │  │
│  │ TCP Server  │    │ Parser       │    │ KVStore         │  │
│  │ (asyncio)   │    │ Commands     │    │ TTL Manager     │  │
│  │             │    │ Responses    │    │ LRU Eviction    │  │
│  └─────────────┘    └──────────────┘    └─────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### AWS Deployment Architecture


```
┌───────────────────────────────────────────────────────────┐
│                         AWS VPC                           │
│                                                           │
│  ┌─────────────────────┐         ┌─────────────────────┐  │
│  │   Server Instance   │         │   Client Instance   │  │
│  │   (t3.small)        │◀────────│   (t3.small)        │  │
│  │                     │   TCP   │                     │  │
│  │  ┌───────────────┐  │  :7171  │  ┌───────────────┐  │  │
│  │  │ Docker        │  │         │  │ Load Test     │  │  │
│  │  │ └─ KV-Cache   │  │         │  │ Script        │  │  │
│  │  └───────────────┘  │         │  └───────────────┘  │  │
│  │                     │         │                     │  │
│  └─────────────────────┘         └─────────────────────┘  │
│                                                           │
│  Security Group: Allow TCP 7171, SSH 22 (your IP only)    │
└───────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Network Layer (`src/network/`)
- **`tcp_server.py`**: Async TCP server using `asyncio.start_server()`
- Handles multiple concurrent client connections
- Manages connection lifecycle (connect, read, write, disconnect)
- Non-blocking I/O for high throughput

#### 2. Protocol Layer (`src/protocol/`)
- **commands.py**: Data classes defining command types (PUT, GET, DELETE, EXISTS)
- **parser.py**: Parses raw text into command objects, formats responses
- Validates input constraints (key/value length, format)

#### 3. Cache Layer (`src/cache/`)
- **store.py**: Core key-value storage with O(1) operations
- **ttl.py**: Time-To-Live management for automatic key expiration
- **eviction.py**: LRU (Least Recently Used) eviction policy

### Data Flow

```
Client Request                    Server Response
     │                                  ▲
     ▼                                  │
┌─────────┐                       ┌─────────┐
│  TCP    │  "PUT foo bar 60\n"   │  TCP    │  "OK stored\n"
│ Socket  │──────────────────────▶│ Socket  │◀──────────────
└─────────┘                       └─────────┘
     │                                  ▲
     ▼                                  │
┌─────────────────────────────────────────────────────────┐
│                    Protocol Parser                      │
│   parse_request() ──────────────▶ format_response()     │
└─────────────────────────────────────────────────────────┘
     │                                  ▲
     ▼                                  │
┌─────────────────────────────────────────────────────────┐
│                      KV Store                           │
│   Command(PUT, "foo", "bar", 60) ──▶ Response(OK)       │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Software | Version | Installation                                                                                     |
|----------|---------|--------------------------------------------------------------------------------------------------|
| Python   | 3.10+   | [python.org](https://www.python.org/downloads/)                                                  |
| pip      | Latest  | Included with Python                                                                             |
| Docker   | 20.10+  | [docker.com](https://docs.docker.com/get-docker/)                                                |
| Git      | 2.30+   | [git-scm.com](https://git-scm.com/downloads)                                                     |
| AWS CLI  | 2.x     | [AWS CLI Install](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |

### Verify Installation

```bash
python3 --version  # Should be 3.10 or higher
python3 -m pip --version
docker --version
git --version
aws --version
```

### AWS Prerequisites

- AWS account with billing enabled
- IAM user with EC2 permissions (or admin access)
- AWS CLI configured with credentials

```bash
# Configure AWS CLI
aws configure
# Enter your Access Key ID, Secret Access Key, region (e.g., ap-south-1), and output format (json)

# Verify configuration
aws sts get-caller-identity
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd kv-cache-assignment
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install project dependencies
pip install -r requirements.txt

# Install project in development mode
pip install -e .
```

### 4. Verify Setup

```bash
# Run a quick test to verify everything is set up
python -c "from src.config.settings import Settings; print('Setup successful!')"
```

---

## Running the Server

### Method 1: Direct Python

```bash
# From project root directory
python -m src.server

# With custom port (default is 7171)
python -m src.server --port 7171

# With debug logging
python -m src.server --debug
```

### Method 2: Docker (Local)

```bash
# Build the image
docker build -t kv-cache .

# Run the container
docker run -p 7171:7171 kv-cache

# Run in background
docker run -d -p 7171:7171 --name kv-cache-server kv-cache

# View logs
docker logs -f kv-cache-server

# Stop the container
docker stop kv-cache-server
```

### Verify Server is Running

```bash
# Using netcat
echo "PUT test hello" | nc localhost 7171

# Using the test client
python scripts/client.py
```

---

## Local Testing & Debugging

### Running Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific task tests
python -m pytest tests/test_store.py -v      # Task 1
python -m pytest tests/test_protocol.py -v   # Task 2
python -m pytest tests/test_server.py -v     # Task 3
python -m pytest tests/test_ttl.py -v        # Task 4
python -m pytest tests/test_eviction.py -v   # Task 5

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Run only failed tests from last run
python -m pytest tests/ --lf
```

### Test Output Interpretation

```
tests/test_store.py::TestKVStore::test_put_and_get PASSED      # ✓ Working
tests/test_store.py::TestKVStore::test_delete FAILED           # ✗ Needs work
tests/test_store.py::TestKVStore::test_exists SKIPPED          # - Not implemented
```

### Interactive Testing with Client

```bash
# Start the server in one terminal
python -m src.server

# In another terminal, run the interactive client
python scripts/client.py

# Client commands:
>>> PUT mykey myvalue
OK stored
>>> GET mykey
OK myvalue
>>> PUT tempkey tempval 10
OK stored
>>> EXISTS tempkey
OK 1
>>> DELETE mykey
OK deleted
>>> QUIT
Goodbye!
```

### Manual Testing with Netcat

```bash
# Connect to server
nc localhost 7171

# Type commands manually
PUT foo bar
GET foo
DELETE foo
QUIT
```

### Local Load Testing

```bash
# Basic load test
python scripts/load_test.py

# Custom parameters
python scripts/load_test.py --host localhost --port 7171 --connections 50 --requests 1000
```

### Debugging Tips

#### 1. Enable Debug Logging

```python
# In src/config/settings.py, set:
DEBUG = True
LOG_LEVEL = "DEBUG"
```

Or run with:
```bash
python -m src.server --debug
```

#### 2. Run Single Test with Output

```bash
python -m pytest tests/test_store.py::TestKVStore::test_put_and_get -v -s
```

---

## AWS Deployment

### Quick Start

```bash
# 1. Configure AWS settings
cp scripts/aws/config.sh.example scripts/aws/config.sh
nano scripts/aws/config.sh  # Edit with your Docker image name

# 2. Create EC2 instances (server + client)
./scripts/aws/create-instances.sh

# 3. Deploy your Docker image to server
./scripts/aws/deploy.sh

# 4. Run load test from client instance
./scripts/aws/run-load-test.sh

# 5. IMPORTANT: Teardown when done!
./scripts/aws/teardown.sh
```

### Step-by-Step Guide

#### Step 1: Configure Settings

```bash
cp scripts/config.sh.example scripts/config.sh
```

Edit `scripts/config.sh`:
```bash
# Required: Your Docker Hub image
DOCKER_IMAGE="yourusername/kv-cache:latest"

# Optional: Customize these if needed
AWS_REGION="ap-south-1"
INSTANCE_TYPE="t3.small"
KEY_NAME="kv-cache-key"
```

#### Step 2: Build and Push Docker Image

```bash
# Build your image
docker build -t yourusername/kv-cache:latest .

# Test locally first!
docker run -p 7171:7171 yourusername/kv-cache:latest
# In another terminal: echo "PUT test value" | nc localhost 7171

# Login to Docker Hub
docker login

# Push to Docker Hub
docker push yourusername/kv-cache:latest
```

#### Step 3: Create AWS Instances

```bash
./scripts/aws.sh create
```

This will:
1. Create an EC2 key pair (saved to `~/.ssh/kv-cache-key.pem`)
2. Create a security group allowing TCP 7171 and SSH 22
3. Launch two t3.small instances (server and client)
4. Save instance IPs to `scripts/.instances`

#### Step 4: Deploy Your Application

```bash
./scripts/aws.sh deploy
```

This will:
1. SSH into the server instance
2. Install Docker
3. Pull your Docker image
4. Start the KV-Cache server

#### Step 5: Run Load Test

```bash
./scripts/aws.sh test
```

This will:
1. Copy the load test script to the client instance
2. Run the load test against the server
3. Download results to `results/load_test_results.json`

#### Step 6: Teardown (CRITICAL!)

```bash
./scripts/aws.sh teardown
```

**⚠️ ALWAYS RUN THIS WHEN DONE!**

### Other AWS Commands

```bash
# Check instance status
./scripts/aws.sh status

# SSH into instances for debugging
./scripts/aws.sh ssh server
./scripts/aws.sh ssh client

# Download results again
./scripts/aws.sh results
```

### AWS Cost Estimate

| Resource                    | Cost                      |
|-----------------------------|---------------------------|
| 2x t3.small instances       | $0.0416/hour combined     |
| Data transfer (same region) | Free                      |
| EBS storage                 | ~$0.10/GB/month (minimal) |

**Typical testing session (2 hours):** ~$0.10

**If you forget to teardown (24 hours):** ~$1.00

**If you forget for a week:** ~$7.00

### AWS Script Reference

| Command                       | Purpose                                  |
|-------------------------------|------------------------------------------|
| `./scripts/aws.sh create`     | Provisions server + client EC2 instances |
| `./scripts/aws.sh deploy`     | Deploys Docker image to server instance  |
| `./scripts/aws.sh test`       | Executes load test from client instance  |
| `./scripts/aws.sh ssh server` | SSH into server instance for debugging   |
| `./scripts/aws.sh ssh client` | SSH into client instance for debugging   |
| `./scripts/aws.sh results`    | Download results from client instance    |
| `./scripts/aws.sh status`     | Show instance status                     |
| `./scripts/aws.sh teardown`   | Terminates all AWS resources             |

---

## Load Testing

### Load Test Parameters

| Parameter       | Default   | Description                                 |
|-----------------|-----------|---------------------------------------------|
| `--host`        | localhost | Server hostname                             |
| `--port`        | 7171      | Server port                                 |
| `--connections` | 100       | Number of concurrent connections            |
| `--requests`    | 1000      | Requests per connection                     |
| `--ratio`       | 0.5       | PUT to GET ratio (0.5 = 50% PUTs, 50% GETs) |
| `--key-size`    | 16        | Random key length                           |
| `--value-size`  | 64        | Random value length                         |
| `--ttl`         | 0         | TTL for PUT operations (0 = no TTL)         |
| `--output`      | stdout    | Output file for results (JSON)              |

### Example Commands

```bash
# Basic test
python scripts/load_test.py

# High concurrency test
python scripts/load_test.py --connections 200 --requests 500

# Write-heavy workload
python scripts/load_test.py --ratio 0.8

# With TTL enabled
python scripts/load_test.py --ttl 60

# Save results to file
python scripts/load_test.py --output results/my_test.json
```

### Performance Targets

| Metric          | Target   | Minimum |
|-----------------|----------|---------|
| Requests/second | > 10,000 | ≥ 5,000 |
| Mean latency    | < 1ms    | ≤ 10ms  |
| P99 latency     | < 5ms    | ≤ 20ms  |
| Error rate      | 0%       | 0%      |
| Cache hit rate  | > 99%    | ≥ 99%   |

---

## Protocol Reference

### Quick Reference

| Command | Format                      | Success Response     | Error Response          |
|---------|-----------------------------|----------------------|-------------------------|
| PUT     | `PUT <key> <value> [ttl]\n` | `OK stored\n`        | `ERROR <msg>\n`         |
| GET     | `GET <key>\n`               | `OK <value>\n`       | `ERROR key not found\n` |
| DELETE  | `DELETE <key>\n`            | `OK deleted\n`       | `ERROR key not found\n` |
| EXISTS  | `EXISTS <key>\n`            | `OK 1\n` or `OK 0\n` | `ERROR <msg>\n`         |
| QUIT    | `QUIT\n`                    | (connection closed)  | -                       |

### Constraints

- Keys: 1-256 ASCII characters, no whitespace
- Values: 1-256 ASCII characters, no whitespace
- TTL: 0-2147483647 seconds (0 = no expiration)

---

## Troubleshooting

### Local Issues

| Issue                    | Solution                                             |
|--------------------------|------------------------------------------------------|
| `Address already in use` | Kill existing process: `lsof -ti:7171 \| xargs kill` |
| `Connection refused`     | Ensure server is running on port 7171                |
| `ModuleNotFoundError`    | Run `pip install -e .` from project root             |
| `Tests hang`             | Check for infinite loops in your implementation      |

### Docker Issues

```bash
# Rebuild without cache
docker build --no-cache -t kv-cache .

# Check container logs
docker logs kv-cache-server

# Enter container for debugging
docker exec -it kv-cache-server /bin/bash
```

### AWS Issues

| Issue                    | Solution                                |
|--------------------------|-----------------------------------------|
| `UnauthorizedAccess`     | Check AWS CLI config: `aws configure`   |
| `KeyPair not found`      | Run `create-instances.sh` again         |
| `Connection timeout`     | Check security group allows port 7171   |
| `Instance not reachable` | Wait 1-2 min for instance to initialize |
| `Docker pull fails`      | Ensure image is public on Docker Hub    |

#### Debug AWS Instances

```bash
# SSH into server
./scripts/aws.sh ssh server

# Check Docker status
sudo systemctl status docker
sudo docker ps
sudo docker logs kv-cache

# Check if server is listening
netstat -tlnp | grep 7171
```

### Getting Help

1. **Read the assignment**: `Assignment.md` has detailed requirements.
2. **Review test cases**: Tests show expected behavior
3. Ping your instructor with specific questions
