#!/usr/bin/env python3
"""
Submission Validation Script

Validates that your submission is complete and ready for grading.
Run this before submitting to catch common issues.

Usage:
    python scripts/validate_submission.py
"""

import os
import sys
from pathlib import Path

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(text: str):
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}{text:^60}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")


def print_check(name: str, passed: bool, message: str = ""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"  {status}  {name}")
    if message and not passed:
        print(f"         {YELLOW}{message}{RESET}")


def main():
    print(f"{BOLD}KV-Cache Submission Validator{RESET}")
    print("=" * 60)

    # Find project root (go up from scripts/ directory)
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    os.chdir(project_root)

    print(f"Project directory: {project_root}")

    errors = 0

    # =========================================================================
    # Check Project Structure
    # =========================================================================
    print_header("Project Structure")

    required_files = [
        "src/__init__.py",
        "src/server.py",
        "src/cache/__init__.py",
        "src/cache/store.py",
        "src/cache/eviction.py",
        "src/protocol/__init__.py",
        "src/protocol/commands.py",
        "src/protocol/parser.py",
        "src/network/__init__.py",
        "src/network/tcp_server.py",
        "src/config/__init__.py",
        "src/config/settings.py",
        "Dockerfile",
        "requirements.txt",
        "setup.py",
    ]

    for filepath in required_files:
        exists = Path(filepath).exists()
        print_check(f"File: {filepath}", exists, f"Not found: {filepath}")
        if not exists:
            errors += 1

    # =========================================================================
    # Check Python Syntax
    # =========================================================================
    print_header("Python Syntax")

    for pyfile in Path("src").rglob("*.py"):
        try:
            with open(pyfile) as f:
                compile(f.read(), pyfile, 'exec')
            print_check(f"Syntax: {pyfile}", True)
        except SyntaxError as e:
            print_check(f"Syntax: {pyfile}", False, str(e))
            errors += 1

    # =========================================================================
    # Check Imports
    # =========================================================================
    print_header("Module Imports")

    sys.path.insert(0, str(project_root))

    imports = [
        ("src.cache.store", "KVStore"),
        ("src.cache.eviction", "LRUEvictionPolicy"),
        ("src.protocol.parser", "ProtocolParser"),
        ("src.protocol.commands", "Command"),
        ("src.network.tcp_server", "KVServer"),
        ("src.config.settings", "Settings"),
    ]

    for module, class_name in imports:
        try:
            mod = __import__(module, fromlist=[class_name])
            cls = getattr(mod, class_name, None)
            if cls:
                print_check(f"Import: {module}.{class_name}", True)
            else:
                print_check(f"Import: {module}.{class_name}", False, "Class not found")
                errors += 1
        except Exception as e:
            print_check(f"Import: {module}.{class_name}", False, str(e))
            errors += 1

    # =========================================================================
    # Check Implementation (not NotImplementedError)
    # =========================================================================
    print_header("Implementation Check")

    try:
        from src.cache.store import KVStore
        store = KVStore()

        # Test put
        try:
            store.put("test", "value")
            print_check("KVStore.put implemented", True)
        except NotImplementedError:
            print_check("KVStore.put implemented", False, "NotImplementedError")
            errors += 1

        # Test get
        try:
            store.get("test")
            print_check("KVStore.get implemented", True)
        except NotImplementedError:
            print_check("KVStore.get implemented", False, "NotImplementedError")
            errors += 1

        # Test delete
        try:
            store.delete("test")
            print_check("KVStore.delete implemented", True)
        except NotImplementedError:
            print_check("KVStore.delete implemented", False, "NotImplementedError")
            errors += 1

        # Test exists
        try:
            store.exists("test")
            print_check("KVStore.exists implemented", True)
        except NotImplementedError:
            print_check("KVStore.exists implemented", False, "NotImplementedError")
            errors += 1

    except Exception as e:
        print_check("KVStore", False, str(e))
        errors += 1

    try:
        from src.protocol.parser import ProtocolParser
        from src.protocol.commands import Response
        parser = ProtocolParser()

        try:
            parser.parse_request("PUT key value")
            print_check("ProtocolParser.parse_request implemented", True)
        except NotImplementedError:
            print_check("ProtocolParser.parse_request implemented", False, "NotImplementedError")
            errors += 1

        try:
            parser.format_response(Response.stored())
            print_check("ProtocolParser.format_response implemented", True)
        except NotImplementedError:
            print_check("ProtocolParser.format_response implemented", False, "NotImplementedError")
            errors += 1

    except Exception as e:
        print_check("ProtocolParser", False, str(e))
        errors += 1

    # =========================================================================
    # Check Docker
    # =========================================================================
    print_header("Docker Configuration")

    dockerfile = Path("Dockerfile")
    if dockerfile.exists():
        content = dockerfile.read_text()

        checks = [
            ("FROM", "Missing FROM instruction"),
            ("EXPOSE", "Missing EXPOSE instruction"),
            ("CMD", "Missing CMD instruction"),
            ("7171", "Port 7171 not found"),
        ]

        for keyword, msg in checks:
            found = keyword in content
            print_check(f"Dockerfile has {keyword}", found, msg)
            if not found:
                errors += 1
    else:
        print_check("Dockerfile exists", False, "Create Dockerfile")
        errors += 1

    # =========================================================================
    # Check Results
    # =========================================================================
    print_header("Load Test Results")

    results_file = Path("results/load_test_results.json")
    if results_file.exists():
        print_check("Results file exists", True)

        try:
            import json
            with open(results_file) as f:
                results = json.load(f)

            # Check performance
            rps = results.get("requests_per_second", 0)
            latency = results.get("latency_mean", 999)
            p99 = results.get("latency_p99", 999)
            err = results.get("error_rate", 100)

            print_check(f"Throughput >= 5000 ({rps:.0f})", rps >= 5000)
            print_check(f"Mean latency <= 10ms ({latency:.2f}ms)", latency <= 10)
            print_check(f"P99 latency <= 20ms ({p99:.2f}ms)", p99 <= 20)
            print_check(f"Error rate = 0% ({err:.2f}%)", err == 0)

        except Exception as e:
            print_check("Results file valid", False, str(e))
    else:
        print(f"  {YELLOW}⚠ No results yet{RESET} - Run load test on AWS")

    # =========================================================================
    # Summary
    # =========================================================================
    print_header("Summary")

    if errors == 0:
        print(f"{GREEN}{BOLD}All checks passed!{RESET}")
        print("\nBefore submitting, make sure to:")
        print("  1. Push Docker image to Docker Hub (public)")
        print("  2. Run load test on AWS")
        print("  3. Terminate AWS instances")
        return 0
    else:
        print(f"{RED}{BOLD}{errors} issue(s) found.{RESET}")
        print("\nFix the issues above before submitting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
