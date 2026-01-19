#!/usr/bin/env python3
"""
Benchmark Script for KV-Cache

Measures the performance characteristics of the KVStore implementation
without network overhead. Useful for profiling and optimization.

Usage:
    python scripts/benchmark.py                    # Run all benchmarks
    python scripts/benchmark.py --operations 10000 # Custom operation count
    python scripts/benchmark.py --profile          # Enable cProfile
"""

import argparse
import time
import random
import string
import statistics
from typing import List, Callable, Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cache.store import KVStore
from src.cache.eviction import LRUEvictionPolicy
from src.protocol.parser import ProtocolParser


def random_string(length: int) -> str:
    """Generate a random alphanumeric string."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def measure_time(func: Callable, iterations: int = 1) -> Dict[str, float]:
    """Measure execution time statistics."""
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times.append(elapsed)

    return {
        "min_ms": min(times),
        "max_ms": max(times),
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "total_ms": sum(times),
    }


class Benchmark:
    """Collection of benchmarks for KV-Cache components."""

    def __init__(self, operations: int = 10000, key_size: int = 16, value_size: int = 64):
        self.operations = operations
        self.key_size = key_size
        self.value_size = value_size

        # Pre-generate test data
        self.keys = [random_string(key_size) for _ in range(operations)]
        self.values = [random_string(value_size) for _ in range(operations)]

    def benchmark_put(self) -> Dict[str, Any]:
        """Benchmark PUT operations."""
        store = KVStore(max_size=self.operations * 2)

        def run():
            for i in range(self.operations):
                store.put(self.keys[i], self.values[i])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "PUT"
        stats["count"] = self.operations
        return stats

    def benchmark_get(self) -> Dict[str, Any]:
        """Benchmark GET operations (cache hits)."""
        store = KVStore(max_size=self.operations * 2)

        # Pre-populate
        for i in range(self.operations):
            store.put(self.keys[i], self.values[i])

        def run():
            for i in range(self.operations):
                store.get(self.keys[i])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "GET (hit)"
        stats["count"] = self.operations
        return stats

    def benchmark_get_miss(self) -> Dict[str, Any]:
        """Benchmark GET operations (cache misses)."""
        store = KVStore(max_size=self.operations * 2)
        miss_keys = [random_string(self.key_size) for _ in range(self.operations)]

        def run():
            for key in miss_keys:
                store.get(key)

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "GET (miss)"
        stats["count"] = self.operations
        return stats

    def benchmark_delete(self) -> Dict[str, Any]:
        """Benchmark DELETE operations."""
        store = KVStore(max_size=self.operations * 2)

        # Pre-populate
        for i in range(self.operations):
            store.put(self.keys[i], self.values[i])

        def run():
            for i in range(self.operations):
                store.delete(self.keys[i])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "DELETE"
        stats["count"] = self.operations
        return stats

    def benchmark_exists(self) -> Dict[str, Any]:
        """Benchmark EXISTS operations."""
        store = KVStore(max_size=self.operations * 2)

        # Pre-populate half
        for i in range(self.operations // 2):
            store.put(self.keys[i], self.values[i])

        def run():
            for i in range(self.operations):
                store.exists(self.keys[i])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "EXISTS"
        stats["count"] = self.operations
        return stats

    def benchmark_eviction(self) -> Dict[str, Any]:
        """Benchmark with LRU eviction active."""
        # Small cache to force eviction
        max_size = self.operations // 10
        store = KVStore(max_size=max_size)

        def run():
            for i in range(self.operations):
                store.put(self.keys[i], self.values[i])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "PUT (with eviction)"
        stats["count"] = self.operations
        stats["cache_size"] = max_size
        stats["evictions"] = self.operations - max_size
        return stats

    def benchmark_ttl_put(self) -> Dict[str, Any]:
        """Benchmark PUT with TTL."""
        store = KVStore(max_size=self.operations * 2)

        def run():
            for i in range(self.operations):
                store.put(self.keys[i], self.values[i], ttl=60)

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "PUT (with TTL)"
        stats["count"] = self.operations
        return stats

    def benchmark_mixed_workload(self) -> Dict[str, Any]:
        """Benchmark mixed PUT/GET workload (50/50)."""
        store = KVStore(max_size=self.operations * 2)

        # Pre-populate half
        for i in range(self.operations // 2):
            store.put(self.keys[i], self.values[i])

        def run():
            for i in range(self.operations):
                if i % 2 == 0:
                    store.put(self.keys[i], self.values[i])
                else:
                    store.get(self.keys[i % (self.operations // 2)])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "Mixed (50% PUT, 50% GET)"
        stats["count"] = self.operations
        return stats

    def benchmark_protocol_parse(self) -> Dict[str, Any]:
        """Benchmark protocol parsing."""
        parser = ProtocolParser()
        commands = [
            f"PUT {self.keys[i]} {self.values[i]}"
            for i in range(self.operations)
        ]

        def run():
            for cmd in commands:
                parser.parse_request(cmd)

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "Protocol Parse"
        stats["count"] = self.operations
        return stats

    def benchmark_lru_policy(self) -> Dict[str, Any]:
        """Benchmark LRU policy directly."""
        max_size = self.operations // 10
        lru = LRUEvictionPolicy(max_size=max_size)

        def run():
            for i in range(self.operations):
                lru.put(self.keys[i], self.values[i])

        stats = measure_time(run)
        stats["ops_per_second"] = self.operations / (stats["total_ms"] / 1000)
        stats["operation"] = "LRU Policy PUT"
        stats["count"] = self.operations
        return stats

    def run_all(self) -> List[Dict[str, Any]]:
        """Run all benchmarks."""
        benchmarks = [
            ("PUT", self.benchmark_put),
            ("GET (hit)", self.benchmark_get),
            ("GET (miss)", self.benchmark_get_miss),
            ("DELETE", self.benchmark_delete),
            ("EXISTS", self.benchmark_exists),
            ("PUT (eviction)", self.benchmark_eviction),
            ("PUT (TTL)", self.benchmark_ttl_put),
            ("Mixed workload", self.benchmark_mixed_workload),
            ("Protocol parse", self.benchmark_protocol_parse),
            ("LRU policy", self.benchmark_lru_policy),
        ]

        results = []
        for name, func in benchmarks:
            print(f"Running: {name}...", end=" ", flush=True)
            result = func()
            print(f"{result['ops_per_second']:,.0f} ops/sec")
            results.append(result)

        return results


def print_results(results: List[Dict[str, Any]]):
    """Print benchmark results in a table."""
    print()
    print("=" * 70)
    print("                        BENCHMARK RESULTS")
    print("=" * 70)
    print(f"{'Operation':<30} {'Ops/sec':>12} {'Mean (ms)':>12} {'Total (ms)':>12}")
    print("-" * 70)

    for r in results:
        print(f"{r['operation']:<30} {r['ops_per_second']:>12,.0f} "
              f"{r['mean_ms']:>12.3f} {r['total_ms']:>12.1f}")

    print("=" * 70)

    # Summary
    total_ops = sum(r['count'] for r in results)
    total_time = sum(r['total_ms'] for r in results)
    avg_ops = total_ops / (total_time / 1000)

    print()
    print(f"Total operations: {total_ops:,}")
    print(f"Total time: {total_time / 1000:.2f} seconds")
    print(f"Average throughput: {avg_ops:,.0f} ops/sec")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark KV-Cache components",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--operations", "-n",
        type=int,
        default=10000,
        help="Number of operations per benchmark"
    )
    parser.add_argument(
        "--key-size",
        type=int,
        default=16,
        help="Size of keys"
    )
    parser.add_argument(
        "--value-size",
        type=int,
        default=64,
        help="Size of values"
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Enable cProfile profiling"
    )

    args = parser.parse_args()

    print(f"KV-Cache Benchmark")
    print(f"==================")
    print(f"Operations per test: {args.operations:,}")
    print(f"Key size: {args.key_size}")
    print(f"Value size: {args.value_size}")
    print()

    benchmark = Benchmark(
        operations=args.operations,
        key_size=args.key_size,
        value_size=args.value_size,
    )

    if args.profile:
        import cProfile
        import pstats

        profiler = cProfile.Profile()
        profiler.enable()
        results = benchmark.run_all()
        profiler.disable()

        print_results(results)

        print()
        print("Profiling Results (top 20):")
        print("-" * 70)
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(20)
    else:
        results = benchmark.run_all()
        print_results(results)


if __name__ == "__main__":
    main()
