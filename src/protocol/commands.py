"""
Protocol Command and Response Definitions

This module defines the data structures for protocol commands and responses.
Students should NOT modify this file.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class CommandType(Enum):
    """Enumeration of supported command types."""
    PUT = auto()
    GET = auto()
    DELETE = auto()
    EXISTS = auto()
    QUIT = auto()
    UNKNOWN = auto()


class ResponseStatus(Enum):
    """Enumeration of response statuses."""
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class Command:
    """
    Represents a parsed protocol command.

    Attributes:
        type: The type of command (PUT, GET, DELETE, EXISTS, QUIT, UNKNOWN)
        key: The key for the operation (may be empty for QUIT)
        value: The value for PUT operations (empty for other operations)
        ttl: Time-to-live in seconds for PUT operations (0 = no expiration)
        raw: The original raw command string
    """
    type: CommandType
    key: str = ""
    value: str = ""
    ttl: int = 0
    raw: str = ""

    def __post_init__(self):
        """Validate command after initialization."""
        # Ensure key and value are strings
        self.key = str(self.key) if self.key else ""
        self.value = str(self.value) if self.value else ""

    @property
    def is_valid(self) -> bool:
        """Check if the command is valid for its type."""
        if self.type == CommandType.UNKNOWN:
            return False
        if self.type == CommandType.QUIT:
            return True
        if self.type in (CommandType.GET, CommandType.DELETE, CommandType.EXISTS):
            return bool(self.key)
        if self.type == CommandType.PUT:
            return bool(self.key) and bool(self.value)
        return False


@dataclass
class Response:
    """
    Represents a protocol response.

    Attributes:
        status: OK or ERROR
        message: Response message or error description
        value: The value returned (for GET operations)
    """
    status: ResponseStatus
    message: str = ""
    value: Optional[str] = None

    @classmethod
    def ok(cls, message: str = "", value: Optional[str] = None) -> "Response":
        """Create a successful response."""
        return cls(status=ResponseStatus.OK, message=message, value=value)

    @classmethod
    def error(cls, message: str) -> "Response":
        """Create an error response."""
        return cls(status=ResponseStatus.ERROR, message=message)

    @classmethod
    def stored(cls) -> "Response":
        """Create a 'stored' response for PUT operations."""
        return cls.ok(message="stored")

    @classmethod
    def deleted(cls) -> "Response":
        """Create a 'deleted' response for DELETE operations."""
        return cls.ok(message="deleted")

    @classmethod
    def key_not_found(cls) -> "Response":
        """Create a 'key not found' error response."""
        return cls.error(message="key not found")

    @classmethod
    def exists_response(cls, exists: bool) -> "Response":
        """Create an EXISTS response."""
        return cls.ok(message="1" if exists else "0")

    @classmethod
    def value_response(cls, value: str) -> "Response":
        """Create a GET response with a value."""
        return cls.ok(value=value)
