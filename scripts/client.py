#!/usr/bin/env python3
"""
Interactive Test Client for KV-Cache

A simple command-line client for manually testing the KV-Cache server.

Usage:
    python scripts/client.py                  # Connect to localhost:7171
    python scripts/client.py --host 1.2.3.4   # Connect to specific host
    python scripts/client.py --port 8080      # Connect to specific port

Commands:
    PUT <key> <value> [ttl]   - Store a key-value pair
    GET <key>                 - Retrieve a value
    DELETE <key>              - Delete a key
    EXISTS <key>              - Check if key exists
    QUIT                      - Close connection
    help                      - Show this help
    exit                      - Exit client
"""

import argparse
import socket
import sys

# Enable command history with arrow keys (works on Unix systems)
try:
    import readline
except ImportError:
    pass  # readline not available on Windows by default


class KVCacheClient:
    """Simple TCP client for KV-Cache."""

    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None

    def connect(self) -> bool:
        """Connect to the server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

    def send_command(self, command: str) -> str:
        """Send a command and receive response."""
        if not self.socket:
            return "ERROR: Not connected"

        try:
            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'

            self.socket.sendall(command.encode('utf-8'))

            # Receive response
            response = b''
            while not response.endswith(b'\n'):
                chunk = self.socket.recv(4096)
                if not chunk:
                    return "ERROR: Connection closed by server"
                response += chunk

            return response.decode('utf-8').strip()

        except socket.timeout:
            return "ERROR: Request timed out"
        except Exception as e:
            return f"ERROR: {e}"

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def print_help():
    """Print help message."""
    print("""
KV-Cache Commands:
------------------
  PUT <key> <value> [ttl]   Store a key-value pair (optional TTL in seconds)
  GET <key>                 Retrieve the value for a key
  DELETE <key>              Delete a key-value pair
  EXISTS <key>              Check if a key exists (returns 1 or 0)
  QUIT                      Close connection and exit

Client Commands:
----------------
  help                      Show this help message
  exit                      Exit the client
  reconnect                 Reconnect to the server
  status                    Show connection status

Examples:
---------
  PUT mykey myvalue         Store "myvalue" under "mykey"
  PUT tempkey tempval 60    Store with 60 second TTL
  GET mykey                 Get value for "mykey"
  EXISTS mykey              Check if "mykey" exists
  DELETE mykey              Delete "mykey"
""")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive test client for KV-Cache"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Server host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7171,
        help="Server port (default: 7171)"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Socket timeout in seconds (default: 5.0)"
    )

    args = parser.parse_args()

    print(f"KV-Cache Client")
    print(f"===============")
    print(f"Connecting to {args.host}:{args.port}...")

    client = KVCacheClient(args.host, args.port, args.timeout)

    if not client.connect():
        print("Failed to connect. Is the server running?")
        print(f"  Try: python -m src.server --port {args.port}")
        sys.exit(1)

    print("Connected! Type 'help' for commands.\n")

    try:
        while True:
            try:
                # Read input
                command = input(">>> ").strip()

                if not command:
                    continue

                # Handle client-side commands
                lower_cmd = command.lower()

                if lower_cmd == "help":
                    print_help()
                    continue

                if lower_cmd in ("exit", "quit"):
                    # Send QUIT to server
                    try:
                        client.send_command("QUIT")
                    except Exception:
                        pass
                    print("Goodbye!")
                    break

                if lower_cmd == "reconnect":
                    client.disconnect()
                    if client.connect():
                        print("Reconnected!")
                    else:
                        print("Reconnection failed.")
                    continue

                if lower_cmd == "status":
                    status = "Connected" if client.socket else "Disconnected"
                    print(f"Status: {status}")
                    print(f"Server: {args.host}:{args.port}")
                    continue

                # Send command to server
                response = client.send_command(command)
                print(response)

                # Check for QUIT response
                if lower_cmd.startswith("quit"):
                    print("Goodbye!")
                    break

            except EOFError:
                print("\nGoodbye!")
                break

    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
