#!/usr/bin/env python3
"""
Load Test Script for KV-Cache

An asyncio-based load testing script that simulates multiple concurrent clients
sending PUT and GET operations to the KV-Cache server.

Usage:
    python scripts/load_test.py                                    # Default settings
    python scripts/load_test.py --host 1.2.3.4 --port 7171         # Remote server
    python scripts/load_test.py --connections 100 --requests 1000  # Custom load
    python scripts/load_test.py --output results.json              # Save results

Output:
    Prints statistics including throughput, latency percentiles, and error rates.
    Optionally saves detailed results to a JSON file.
"""

import argparse
import asyncio
import json
import random
import string
import time
import statistics
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime


@dataclass
class RequestResult:
    """Result of a single request."""
    operation: str
    success: bool
    latency_ms: float
    error: Optional[str] = None


@dataclass
class LoadTestResults:
    """Aggregated load test results."""
    # Configuration
    host: str
    port: int
    connections: int
    requests_per_connection: int
    put_ratio: float

    # Timing
    start_time: str
    end_time: str
    total_duration_seconds: float

    # Counts
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Operations breakdown
    put_count: int = 0
    get_count: int = 0
    put_success: int = 0
    get_success: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    # Latency stats (milliseconds)
    latency_min: float = 0.0
    latency_max: float = 0.0
    latency_mean: float = 0.0
    latency_median: float = 0.0
    latency_p95: float = 0.0
    latency_p99: float = 0.0
    latency_stddev: float = 0.0

    # Throughput
    requests_per_second: float = 0.0

    # Error rate
    error_rate: float = 0.0

    # Raw latencies for percentile calculation
    latencies: List[float] = field(default_factory=list)

    def calculate_stats(self):
        """Calculate statistics from raw latencies."""
        # Always calculate error rate, even if no successful requests
        self.error_rate = (
            self.failed_requests / self.total_requests * 100
            if self.total_requests > 0 else 0
        )

        if not self.latencies:
            return

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        self.latency_min = sorted_latencies[0]
        self.latency_max = sorted_latencies[-1]
        self.latency_mean = statistics.mean(sorted_latencies)
        self.latency_median = statistics.median(sorted_latencies)

        # Percentiles
        p95_idx = min(int(n * 0.95), n - 1)
        p99_idx = min(int(n * 0.99), n - 1)
        self.latency_p95 = sorted_latencies[p95_idx]
        self.latency_p99 = sorted_latencies[p99_idx]

        if n > 1:
            self.latency_stddev = statistics.stdev(sorted_latencies)

    def to_dict(self) -> dict:
        """Convert to dictionary (excluding raw latencies for JSON output)."""
        d = asdict(self)
        del d['latencies']  # Don't include raw data in JSON
        return d


class LoadTester:
    """Async load tester for KV-Cache."""

    def __init__(
            self,
            host: str = "localhost",
            port: int = 7171,
            connections: int = 100,
            requests_per_connection: int = 1000,
            put_ratio: float = 0.5,
            key_size: int = 16,
            value_size: int = 64,
            ttl: int = 0,
            timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.connections = connections
        self.requests_per_connection = requests_per_connection
        self.put_ratio = put_ratio
        self.key_size = key_size
        self.value_size = value_size
        self.ttl = ttl
        self.timeout = timeout

        # Track keys that have been PUT for realistic GET operations
        self.known_keys: List[str] = []
        self.known_keys_lock = asyncio.Lock()

        # Results
        self.results: List[RequestResult] = []
        self.results_lock = asyncio.Lock()

    def _random_string(self, length: int) -> str:
        """Generate a random alphanumeric string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    async def _send_command(
            self,
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
            command: str
    ) -> tuple:
        """Send a command and measure latency."""
        start_time = time.perf_counter()

        try:
            writer.write(f"{command}\n".encode())
            await writer.drain()

            response = await asyncio.wait_for(
                reader.readline(),
                timeout=self.timeout
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            response_str = response.decode().strip()

            return True, response_str, elapsed_ms

        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return False, "TIMEOUT", elapsed_ms

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return False, str(e), elapsed_ms

    async def _client_task(self, client_id: int) -> List[RequestResult]:
        """Run a single client's workload."""
        results = []

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout
            )
        except Exception as e:
            # Connection failed - record failures for all requests
            for _ in range(self.requests_per_connection):
                results.append(RequestResult(
                    operation="CONNECT",
                    success=False,
                    latency_ms=0,
                    error=str(e)
                ))
            return results

        try:
            local_keys = []

            for _ in range(self.requests_per_connection):
                # Decide operation based on ratio
                if random.random() < self.put_ratio:
                    # PUT operation
                    key = self._random_string(self.key_size)
                    value = self._random_string(self.value_size)

                    if self.ttl > 0:
                        command = f"PUT {key} {value} {self.ttl}"
                    else:
                        command = f"PUT {key} {value}"

                    success, response, latency = await self._send_command(
                        reader, writer, command
                    )

                    if success and response.startswith("OK"):
                        local_keys.append(key)
                        results.append(RequestResult(
                            operation="PUT",
                            success=True,
                            latency_ms=latency
                        ))
                    else:
                        results.append(RequestResult(
                            operation="PUT",
                            success=False,
                            latency_ms=latency,
                            error=response
                        ))
                else:
                    # GET operation
                    # Try to get a known key for realistic testing
                    if local_keys and random.random() < 0.8:
                        # 80% chance to get a key we PUT
                        key = random.choice(local_keys)
                    else:
                        # 20% chance to get a random (likely non-existent) key
                        key = self._random_string(self.key_size)

                    command = f"GET {key}"
                    success, response, latency = await self._send_command(
                        reader, writer, command
                    )

                    if success:
                        is_hit = response.startswith("OK ")
                        results.append(RequestResult(
                            operation="GET_HIT" if is_hit else "GET_MISS",
                            success=True,
                            latency_ms=latency
                        ))
                    else:
                        results.append(RequestResult(
                            operation="GET",
                            success=False,
                            latency_ms=latency,
                            error=response
                        ))

            # Send QUIT
            try:
                writer.write(b"QUIT\n")
                await writer.drain()
            except Exception:
                pass

        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

        return results

    async def run(self) -> LoadTestResults:
        """Run the load test."""
        start_time = datetime.now()
        start_perf = time.perf_counter()

        print(f"\nRunning load test against {self.host}:{self.port}")
        print(f"Connections: {self.connections}")
        print(f"Requests per connection: {self.requests_per_connection}")
        print(f"Total requests: {self.connections * self.requests_per_connection}")
        print(f"PUT/GET ratio: {self.put_ratio:.0%}/{1 - self.put_ratio:.0%}")
        print()

        # Run all clients concurrently
        tasks = [
            self._client_task(i)
            for i in range(self.connections)
        ]

        # Show progress
        print("Running", end="", flush=True)
        all_results = await asyncio.gather(*tasks)
        print(" Done!\n")

        end_perf = time.perf_counter()
        end_time = datetime.now()
        total_duration = end_perf - start_perf

        # Aggregate results
        results = LoadTestResults(
            host=self.host,
            port=self.port,
            connections=self.connections,
            requests_per_connection=self.requests_per_connection,
            put_ratio=self.put_ratio,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            total_duration_seconds=total_duration,
        )

        for client_results in all_results:
            for r in client_results:
                results.total_requests += 1

                if r.success:
                    results.successful_requests += 1
                    results.latencies.append(r.latency_ms)
                else:
                    results.failed_requests += 1

                if r.operation == "PUT":
                    results.put_count += 1
                    if r.success:
                        results.put_success += 1
                elif r.operation in ("GET", "GET_HIT", "GET_MISS"):
                    results.get_count += 1
                    if r.success:
                        results.get_success += 1
                        if r.operation == "GET_HIT":
                            results.cache_hits += 1
                        elif r.operation == "GET_MISS":
                            results.cache_misses += 1

        # Calculate derived stats
        results.calculate_stats()
        results.requests_per_second = (
            results.total_requests / total_duration
            if total_duration > 0 else 0
        )

        return results

    @staticmethod
    def print_results(results: LoadTestResults):
        """Print results in a nice format."""
        print("=" * 60)
        print("                    LOAD TEST RESULTS")
        print("=" * 60)

        success_pct = (results.successful_requests / results.total_requests * 100
                       if results.total_requests > 0 else 0)

        print(f"Total Requests:     {results.total_requests:,}")
        print(f"Successful:         {results.successful_requests:,} ({success_pct:.2f}%)")
        print(f"Failed:             {results.failed_requests:,} ({results.error_rate:.2f}%)")

        print("-" * 60)

        print(f"Total Time:         {results.total_duration_seconds:.2f} seconds")
        print(f"Requests/Second:    {results.requests_per_second:,.2f}")

        print()
        print("Latency (ms):")
        print(f"  Min:              {results.latency_min:.2f}")
        print(f"  Max:              {results.latency_max:.2f}")
        print(f"  Mean:             {results.latency_mean:.2f}")
        print(f"  Median:           {results.latency_median:.2f}")
        print(f"  P95:              {results.latency_p95:.2f}")
        print(f"  P99:              {results.latency_p99:.2f}")

        print()
        print("Operations:")
        print(f"  PUT:              {results.put_count:,} "
              f"(success: {results.put_success:,})")
        print(f"  GET:              {results.get_count:,} "
              f"(success: {results.get_success:,})")

        if results.cache_hits + results.cache_misses > 0:
            hit_rate = results.cache_hits / (results.cache_hits + results.cache_misses) * 100
            print(f"  Cache Hits:       {results.cache_hits:,} ({hit_rate:.2f}%)")
            print(f"  Cache Misses:     {results.cache_misses:,}")

        print("=" * 60)

        # Performance assessment
        print()
        print("Performance Assessment:")

        issues = []
        if results.requests_per_second < 5000:
            issues.append(f"  ⚠ Throughput below 5,000 req/s ({results.requests_per_second:.0f})")
        else:
            print(f"  ✓ Throughput: {results.requests_per_second:.0f} req/s (target: ≥5,000)")

        if results.latency_mean > 10:
            issues.append(f"  ⚠ Mean latency above 10ms ({results.latency_mean:.2f}ms)")
        else:
            print(f"  ✓ Mean latency: {results.latency_mean:.2f}ms (target: ≤10ms)")

        if results.latency_p99 > 20:
            issues.append(f"  ⚠ P99 latency above 20ms ({results.latency_p99:.2f}ms)")
        else:
            print(f"  ✓ P99 latency: {results.latency_p99:.2f}ms (target: ≤20ms)")

        if results.error_rate > 0:
            issues.append(f"  ⚠ Error rate above 0% ({results.error_rate:.2f}%)")
        else:
            print(f"  ✓ Error rate: {results.error_rate:.2f}% (target: 0%)")

        if issues:
            print()
            print("Issues Found:")
            for issue in issues:
                print(issue)
        else:
            print()
            print("  🎉 All performance targets met!")

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Load test the KV-Cache server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7171,
        help="Server port"
    )
    parser.add_argument(
        "--connections", "-c",
        type=int,
        default=100,
        help="Number of concurrent connections"
    )
    parser.add_argument(
        "--requests", "-r",
        type=int,
        default=1000,
        help="Number of requests per connection"
    )
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.5,
        help="PUT to GET ratio (0.5 = 50%% PUT, 50%% GET)"
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=16,
        help="Size of random keys"
    )
    parser.add_argument(
        "--value-size",
        type=int,
        default=64,
        help="Size of random values"
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=0,
        help="TTL for PUT operations (0 = no TTL)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Request timeout in seconds"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file for JSON results"
    )

    args = parser.parse_args()

    # Create and run load tester
    tester = LoadTester(
        host=args.host,
        port=args.port,
        connections=args.connections,
        requests_per_connection=args.requests,
        put_ratio=args.ratio,
        key_size=args.key_size,
        value_size=args.value_size,
        ttl=args.ttl,
        timeout=args.timeout,
    )

    try:
        results = asyncio.run(tester.run())
    except KeyboardInterrupt:
        print("\nLoad test interrupted.")
        return
    except Exception as e:
        print(f"\nLoad test failed: {e}")
        return

    # Check if server was reachable
    if results.successful_requests == 0:
        print("=" * 60)
        print("                       ERROR")
        print("=" * 60)
        print(f"All {results.total_requests:,} requests failed!")
        print()
        print("Possible causes:")
        print("  1. Server is not running")
        print("  2. Wrong host/port")
        print("  3. Firewall blocking connection")
        print()
        print("To start the server:")
        print("  python -m src.server")
        print()
        return

    # Print results
    LoadTester.print_results(results)

    # Save to file if requested
    if args.output:
        output_data = results.to_dict()
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {args.output}")


if __name__ == "__main__":
    main()
