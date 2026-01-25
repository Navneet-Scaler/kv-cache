"""
Protocol Parser Module (Task 2)

This module handles parsing of raw protocol commands and formatting of responses.

Students must implement:
- parse_request(): Parse a raw command string into a Command object
- format_response(): Format a Response object into a protocol string
"""

from .commands import Command, CommandType, Response
from ..config.settings import settings


class ProtocolParser:
    """
    Parser for the KV-Cache text protocol.

    Protocol Format:
        Request:  <COMMAND> [ARGS...]\n
        Response: <STATUS> [DATA]\n

    Commands:
        PUT <key> <value> [ttl]  -> OK stored
        GET <key>                -> OK <value> | ERROR key not found
        DELETE <key>             -> OK deleted | ERROR key not found
        EXISTS <key>             -> OK 1 | OK 0
        QUIT                     -> (connection closed)

    Constraints:
        - Keys: max 256 characters, no whitespace
        - Values: max 256 characters, no whitespace
        - TTL: non-negative integer (0 = no expiration)
    """

    def __init__(self):
        """Initialize the parser with constraints from settings."""
        self.max_key_length = settings.MAX_KEY_LENGTH
        self.max_value_length = settings.MAX_VALUE_LENGTH

    def parse_request(self, data: str) -> Command:
        """
        Parse a raw request string into a Command object.

        Args:
            data: Raw request string (may include trailing newline)

        Returns:
            Command object representing the parsed request.
            Returns Command with type=UNKNOWN for invalid/malformed requests.

        Examples:
            >>> parser = ProtocolParser()
            >>> cmd = parser.parse_request("PUT mykey myvalue 60")
            >>> cmd.type == CommandType.PUT
            True
            >>> cmd.key
            'mykey'
            >>> cmd.value
            'myvalue'
            >>> cmd.ttl
            60

        Implementation hints:
            - Strip whitespace and split the input
            - Identify the command type (case-insensitive)
            - Extract arguments based on command type
            - Validate key/value length constraints
            - Handle errors gracefully (return UNKNOWN command)
        """
        raw = data.strip()
        if not raw:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        parts = raw.split()
        command_name = parts[0].upper()

        if command_name == "PUT":
            return self._parse_put(parts, raw)
        if command_name == "GET":
            return self._parse_get(parts, raw)
        if command_name == "DELETE":
            return self._parse_delete(parts, raw)
        if command_name == "EXISTS":
            return self._parse_exists(parts, raw)
        if command_name == "QUIT":
            # QUIT takes no args
            if len(parts) == 1:
                return Command(type=CommandType.QUIT, raw=raw)
            return Command(type=CommandType.UNKNOWN, raw=raw)

        return Command(type=CommandType.UNKNOWN, raw=raw)

    def _parse_put(self, parts: list, raw: str) -> Command:
        """
        Parse a PUT command.

        Format: PUT <key> <value> [ttl]

        Args:
            parts: List of command parts (already split)
            raw: Original raw command string

        Returns:
            Command object for PUT, or UNKNOWN if invalid
        """
        if len(parts) < 3 or len(parts) > 4:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        key, value = parts[1], parts[2]
        if len(key) > self.max_key_length or len(value) > self.max_value_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        ttl = 0
        if len(parts) == 4:
            try:
                ttl = int(parts[3])
                if ttl < 0:
                    return Command(type=CommandType.UNKNOWN, raw=raw)
            except ValueError:
                return Command(type=CommandType.UNKNOWN, raw=raw)

        return Command(
            type=CommandType.PUT,
            key=key,
            value=value,
            ttl=ttl,
            raw=raw,
        )

    def _parse_get(self, parts: list, raw: str) -> Command:
        """
        Parse a GET command.

        Format: GET <key>
        """
        if len(parts) != 2:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        key = parts[1]
        if len(key) > self.max_key_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        return Command(type=CommandType.GET, key=key, raw=raw)

    def _parse_delete(self, parts: list, raw: str) -> Command:
        """
        Parse a DELETE command.

        Format: DELETE <key>
        """
        if len(parts) != 2:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        key = parts[1]
        if len(key) > self.max_key_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        return Command(type=CommandType.DELETE, key=key, raw=raw)

    def _parse_exists(self, parts: list, raw: str) -> Command:
        """
        Parse an EXISTS command.

        Format: EXISTS <key>
        """
        if len(parts) != 2:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        key = parts[1]
        if len(key) > self.max_key_length:
            return Command(type=CommandType.UNKNOWN, raw=raw)

        return Command(type=CommandType.EXISTS, key=key, raw=raw)

    def format_response(self, response: Response) -> str:
        """
        Format a Response object into a protocol string.

        Args:
            response: Response object to format

        Returns:
            Formatted response string WITH trailing newline.

        Examples:
            >>> parser = ProtocolParser()
            >>> parser.format_response(Response.stored())
            'OK stored\\n'
            >>> parser.format_response(Response.value_response("hello"))
            'OK hello\\n'
            >>> parser.format_response(Response.error("key not found"))
            'ERROR key not found\\n'

        Implementation hints:
            - Format based on response status (OK or ERROR)
            - For GET responses, include the value
            - For other responses, include the message
            - Always end with newline character
        """
        prefix = response.status.value

        # If value is provided (GET), prefer it; otherwise use message
        if response.value is not None:
            body = response.value
        else:
            body = response.message

        # Ensure empty body still results in newline-terminated string
        if body:
            return f"{prefix} {body}\n"
        return f"{prefix}\n"
