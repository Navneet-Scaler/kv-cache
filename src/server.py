#!/usr/bin/env python3
"""
KV-Cache Server Entry Point

This is the main entry point for starting the KV-Cache server.

Usage:
    python -m src.server                    # Default settings (0.0.0.0:7171)
    python -m src.server --port 8080        # Custom port
    python -m src.server --host 127.0.0.1   # Custom host
    python -m src.server --debug            # Enable debug logging
    python -m src.server --max-keys 5000    # Custom cache size

Environment Variables:
    KV_CACHE_HOST       - Server bind address
    KV_CACHE_PORT       - Server port
    KV_CACHE_MAX_KEYS   - Maximum cache size
    KV_CACHE_DEBUG      - Enable debug mode (true/false)
"""

import argparse
import asyncio
import logging
import os
import signal
import sys

from .cache.store import KVStore
from .cluster.config import ClusterConfig
from .config.settings import settings
from .network.tcp_server import KVServer


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="KV-Cache: In-Memory Key-Value Store Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--host",
        type=str,
        default=settings.HOST,
        help="Host address to bind to",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=settings.PORT,
        help="Port number to listen on",
    )

    parser.add_argument(
        "--max-keys",
        type=int,
        default=settings.MAX_KEYS,
        help="Maximum number of keys in cache",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    return parser.parse_args()


def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


def main() -> None:
    """Main entry point for the server."""
    args = parse_args()
    
    # Read cluster configuration from environment
    node_id = int(os.getenv('NODE_ID', '0'))  # 0 = non-clustered mode
    env_port = os.getenv('PORT')
    
    # Override port from environment if set
    if env_port:
        args.port = int(env_port)
    
    # Initialize cluster config if NODE_ID is set
    cluster_config = None
    if node_id > 0:
        cluster_config = ClusterConfig(node_id)
        print(f'Node {node_id} starting on port {args.port}')
        print(f'  Primary for shards: {cluster_config.primary_shards}')
        print(f'  Replica for shards: {cluster_config.replica_shards}')
    else:
        print(f'Starting in standalone mode on port {args.port}')

    # Setup logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    # Create store with specified max size
    store = KVStore(max_size=args.max_keys)

    # Create server with cluster config
    server = KVServer(
        host=args.host, 
        port=args.port, 
        store=store,
        cluster_config=cluster_config
    )

    # Get or create event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    async def shutdown(sig: signal.Signals) -> None:
        """Handle shutdown signal."""
        logger.info(f"Received signal {sig.name}, initiating shutdown...")
        await server.stop()
        shutdown_event.set()

    # Register signal handlers (Unix only)
    if sys.platform != 'win32':
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(shutdown(s))
            )

    # Log startup info
    logger.info(f"Starting KV-Cache server")
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  Max keys: {args.max_keys}")
    logger.info(f"  Debug: {args.debug}")

    # Run the server
    try:
        loop.run_until_complete(server.start())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        loop.run_until_complete(server.stop())
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        # Cleanup
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    main()
