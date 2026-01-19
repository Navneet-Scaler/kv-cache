Assignment 2: In-Memory Key-Value Cache
=======================================

- **Release Date:** 19th January, 2026
- **Due Date:** `11.59 pm`, 25th January, 2026
- **Total Points:** 100

Overview
--------

In this assignment, you will build an **in-memory Key-Value Cache** service using **Python** and **asyncio**. Unlike traditional REST APIs, your service will communicate over raw **TCP sockets** using a custom text-based protocol.

Your cache will support:
- **PUT**: Insert or update a key-value pair (with optional TTL)
- **GET**: Retrieve a value by key
- **DELETE**: Remove a key-value pair
- **EXISTS**: Check if a key exists

The service must listen on **port 7171** and handle multiple concurrent clients efficiently using Python's `asyncio` library.

You will also **deploy and load test** your solution on AWS EC2 to validate its performance under real-world conditions.

Learning Objectives
-------------------

By completing this assignment, you will:

1. **Understand socket programming** — Work with raw TCP connections instead of HTTP
2. **Master asyncio** — Build concurrent applications using Python's async/await syntax
3. **Implement a custom protocol** — Design and parse a text-based communication protocol
4. **Build efficient data structures** — Implement an in-memory cache with O(1) operations
5. **Handle resource constraints** — Implement TTL expiration and LRU eviction
6. **Deploy to cloud infrastructure** — Provision and manage AWS EC2 instances
7. **Perform load testing** — Validate performance under concurrent load

Protocol Specification
----------------------

Your server must implement the following text-based protocol over TCP:

### Request Format
```
<COMMAND> <ARGS...>\n
```

### Commands

1. `PUT <key> <value> [ttl_seconds]`
    - Parameters
      - `key`: String (max 256 chars, no spaces)
      - `value`: String (max 256 chars, no spaces)  
      - `ttl_seconds`: Optional integer (seconds until expiration, 0 = no expiration)
    - Response (on success): `OK stored`
    - Response (on failure): `ERROR <message>`
2. `GET <key>`
    - Response (if found): `OK <value>`
    - Response (if not found or expired): `ERROR key not found`
3. `DELETE <key>`
    - Response (if success): `OK deleted`
    - Response (if key not found): `ERROR key not found`
4. `EXISTS <key>`
    - Response (if key exists and not expired): `OK 1`
    - Response (if key does not exist or is expired): `OK 0`


### Protocol Rules
- All commands are newline (`\n`) terminated
- Keys and values contain no whitespace (space-separated parsing)
- All responses are newline (`\n`) terminated
- Connection remains open for multiple commands (persistent connection)
- Client sends `QUIT\n` to close connection gracefully

Tasks & Scoring
---------------

Complete the following tasks **in order**. Each task builds upon the previous one.

### Task 1: Basic Cache Store (20 points)

**File:** `src/cache/store.py`

Implement the `KVStore` class with the following methods:
- `put(key: str, value: str) -> bool`
- `get(key: str) -> Optional[str]`
- `delete(key: str) -> bool`
- `exists(key: str) -> bool`

**Requirements:**
- All operations must be O(1) average time complexity
- Thread-safe is NOT required (single-threaded async)

**Validation:**
```bash
python -m pytest tests/test_store.py -v
```

### Task 2: Protocol Parser (20 points)

**File:** `src/protocol/parser.py`

Implement the `ProtocolParser` class:
- `parse_request(data: str) -> Command`
- `format_response(response: Response) -> str`

**Requirements:**
- Handle malformed commands gracefully (return ERROR response)
- Validate key/value length constraints (max 256 chars)

**Validation:**
```bash
python -m pytest tests/test_protocol.py -v
```

### Task 3: Async TCP Server (25 points)

**File:** `src/network/tcp_server.py`

Complete the `KVServer` class:
- `handle_client(reader, writer)` - Handle a single client connection
- `start()` - Start the server on port 7171

**Requirements:**
- Use `asyncio.start_server()` 
- Handle multiple concurrent clients
- Gracefully handle client disconnections
- Process multiple commands per connection

**Validation:**
```bash
python -m pytest tests/test_server.py -v
```

**Manual Testing:**
```bash
# Terminal 1: Start server
python -m src.server

# Terminal 2: Test with netcat
nc localhost 7171
PUT mykey myvalue
GET mykey
```

### Task 4: TTL Support (20 points)

**File:** `src/cache/store.py` (extend your Task 1 implementation)

Add Time-To-Live (TTL) support:
- `put(key: str, value: str, ttl: int = 0) -> bool`
  - `ttl=0` means no expiration
  - `ttl>0` means the key expires after `ttl` seconds
- Expired keys should:
  - Return `None` on `get()`
  - Return `False` on `exists()`
  - Be cleaned up lazily (on access) or actively (background task)

**Requirements:**
- Implement lazy expiration (check on access) at minimum
- BONUS: Implement active expiration with a background cleanup task

**Validation:**
```bash
python -m pytest tests/test_ttl.py -v
```

### Task 5: LRU Eviction (15 points)

**File:** `src/cache/eviction.py`

Implement LRU (Least Recently Used) eviction:
- Maximum cache size: configurable (default 10,000 keys)
- When cache is full, evict the least recently used key before inserting new one
- Both `get()` and `put()` should update the "recently used" status

**Requirements:**
- Eviction must be O(1) time complexity
- Hint: Use `collections.OrderedDict` or implement a doubly-linked list with hash map

**Validation:**
```bash
python -m pytest tests/test_eviction.py -v
```


### Task 6: AWS Deployment & Load Testing (Required for Submission)

Deploy your solution to AWS and validate performance under load.

#### 6.1 Build and Push Docker Image

```bash
# Build your image
docker build -t <your-dockerhub-username>/kv-cache:latest .

# Test locally first
docker run -p 7171:7171 <your-dockerhub-username>/kv-cache:latest

# Push to Docker Hub
docker login
docker push <your-dockerhub-username>/kv-cache:latest
```

#### 6.2 Deploy to AWS

Use the provided script to deploy:

```bash
# Configure your settings
cp scripts/config.sh.example scripts/config.sh
# Edit config.sh with your Docker image name

# Create server and client instances
./scripts/aws.sh create

# Deploy your Docker image to the server
./scripts/aws.sh deploy

# Run load test from client instance
./scripts/aws.sh test

# View results
cat results/load_test_results.json
```

#### 6.3 Performance Requirements

Your solution must meet these **minimum thresholds**:

| Metric          | Minimum Requirement |
|-----------------|---------------------|
| Requests/second | ≥ 5,000             |
| Average latency | ≤ 10ms              |
| P99 latency     | ≤ 20ms              |
| Error rate      | 0%                  |

#### 6.4 Teardown (CRITICAL!)

**⚠️ IMPORTANT: Always teardown your instances when done to avoid charges!**

```bash
./scripts/aws.sh teardown
```

**AWS charges `~$0.02/hour` per `t3.small` instance.** Two instances running 24/7 = `~$30/month`.


Scoring Summary
---------------

| Task                      | Points | Cumulative |
|---------------------------|--------|------------|
| Task 1: Basic Cache Store | 20     | 20         |
| Task 2: Protocol Parser   | 20     | 40         |
| Task 3: Async TCP Server  | 25     | 65         |
| Task 4: TTL Support       | 20     | 85         |
| Task 5: LRU Eviction      | 15     | 100        |

**Note:** Task 6 (AWS Deployment) is required for submission but not separately scored. Your solution must pass the performance thresholds to receive credit for Tasks 1-5.

**Grading:**
- We will run automated tests against your submission
- Each task's tests must pass completely for full points
- Partial credit may be awarded for partially working implementations
- Solutions that fail performance thresholds or crash under load receive 0 points
- Code quality and documentation are considered for borderline cases



Submission Guidelines
---------------------

### Required Files
Your submission must include:
1. All source files in `src/` directory
2. `Dockerfile` that builds and runs your solution
3. `README.md` with:
   - Your design choices and optimizations
   - Any assumptions you made
   - Instructions to build and run
   - Load test results summary from AWS

### Required Evidence
Include in your submission:
1. **Load test results file:** `results/load_test_results.json`
2. Your solution code.

### Docker Requirements
Your Docker image must:
- Expose port 7171
- Run with: `docker run -p 7171:7171 <your_image_name>`
- Start the server automatically on container start
- Be publicly accessible on Docker Hub

### Submission Process

1. Submit your code via the form: https://forms.gle/397yYWM5q9swTG3U9
2. GitHub Repository MUST be **Private**.  
   Provide read access to: [AgarwalPragy](https://github.com/AgarwalPragy) and [anshumansingh](https://github.com/anshumansingh).
3. Ensure your Docker image is pushed to Docker Hub (public)
4. Include your load test results in the `results/` directory
5. **Due Date:** `11.59 pm`, 25th January, 2026


Resources
---------

### Provided Files
- `src/` — Stub files with TODO markers
- `tests/` — Test files for validation
- `scripts/load_test.py` — Load testing script
- `scripts/client.py` — Simple test client
- `scripts/aws.sh` — AWS deployment script (create, deploy, test, teardown)

### Documentation
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html)
- [collections.OrderedDict](https://docs.python.org/3/library/collections.html#collections.OrderedDict)
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/latest/userguide/)
- [Docker Hub Documentation](https://docs.docker.com/docker-hub/)

### Tips
1. Start with Task 1 and ensure tests pass before moving on
2. Use the provided test client (`scripts/client.py`) for manual testing
3. Read the stub files carefully — they contain hints
4. Run load tests **locally first** before deploying to AWS
5. Always run `./scripts/aws.sh teardown` when done with AWS testing

Academic Integrity
------------------

- This is an **individual** assignment
- You may discuss approaches with classmates but must write your own code
- Copying code from previous cohorts is prohibited
- Violations will result in a score of 0 and academic misconduct report

FAQ
---

**Q: Can I use additional Python libraries?**
A: You may use standard library modules. External packages require approval.

**Q: What if my tests pass locally but fail during grading?**
A: Ensure your Docker image works correctly. Test with a fresh container and on AWS.

**Q: Can I change the stub file structure?**
A: No. Keep the function signatures as provided. You may add helper functions.

**Q: How do I handle values with spaces?**
A: For this assignment, keys and values cannot contain spaces. This simplifies parsing. In general protocols, you would use length-prefixing or escaping.

**Q: How much will AWS cost?**
A: Two `t3.small` instances cost `~$0.04/hour` combined. Budget `~$1-2` for testing if you teardown promptly.

**Q: What if I forget to teardown?**
A: Set a billing alert in AWS! The scripts will remind you, but it's your responsibility.

**Q: Can I use a different AWS region?**
A: Yes, update `scripts/aws/config.sh`. We recommend your nearest region for lower latency.

**Q: Can I use AI assistants to help with the assignment?**
A: Yes! However during vivas, you will be expected to explain every line of code that you've submitted, and every decision that you've made. If you're unable to do so, your assignment score will be set to **zero**. 

---

Good luck! 🚀