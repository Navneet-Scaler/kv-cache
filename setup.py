#!/usr/bin/env python3
"""
KV-Cache Setup Script
=====================
Allows installation of the kv-cache package.

Usage:
    pip install -e .           # Development install
    pip install .              # Regular install
"""

from setuptools import setup, find_packages

setup(
    name="kv-cache",
    version="1.0.0",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "kv-cache=src.server:main",
        ],
    },
)
