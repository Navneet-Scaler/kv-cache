"""
Tests for Task 2: Protocol Parser

These tests verify the ProtocolParser class:
- parse_request(): Parse raw commands into Command objects
- format_response(): Format Response objects into protocol strings

Run with: python -m pytest tests/test_protocol.py -v
"""

import pytest
from src.protocol.parser import ProtocolParser
from src.protocol.commands import Command, CommandType, Response, ResponseStatus


class TestParseRequestPUT:
    """Test parsing PUT commands."""

    def test_parse_put_basic(self, parser: ProtocolParser):
        """Test parsing basic PUT command."""
        cmd = parser.parse_request("PUT key value")

        assert cmd.type == CommandType.PUT
        assert cmd.key == "key"
        assert cmd.value == "value"
        assert cmd.ttl == 0

    def test_parse_put_with_ttl(self, parser: ProtocolParser):
        """Test parsing PUT with TTL."""
        cmd = parser.parse_request("PUT key value 60")

        assert cmd.type == CommandType.PUT
        assert cmd.key == "key"
        assert cmd.value == "value"
        assert cmd.ttl == 60

    def test_parse_put_with_newline(self, parser: ProtocolParser):
        """Test parsing PUT with trailing newline."""
        cmd = parser.parse_request("PUT key value\n")

        assert cmd.type == CommandType.PUT
        assert cmd.key == "key"
        assert cmd.value == "value"

    def test_parse_put_case_insensitive(self, parser: ProtocolParser):
        """Test PUT command is case-insensitive."""
        for variant in ["put", "PUT", "Put", "pUt"]:
            cmd = parser.parse_request(f"{variant} key value")
            assert cmd.type == CommandType.PUT, f"Failed for '{variant}'"

    def test_parse_put_missing_value(self, parser: ProtocolParser):
        """Test PUT without value returns UNKNOWN."""
        cmd = parser.parse_request("PUT key")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_put_missing_key_and_value(self, parser: ProtocolParser):
        """Test PUT without key and value returns UNKNOWN."""
        cmd = parser.parse_request("PUT")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_put_invalid_ttl(self, parser: ProtocolParser):
        """Test PUT with non-numeric TTL returns UNKNOWN."""
        cmd = parser.parse_request("PUT key value abc")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_put_negative_ttl(self, parser: ProtocolParser):
        """Test PUT with negative TTL returns UNKNOWN."""
        cmd = parser.parse_request("PUT key value -1")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_put_zero_ttl(self, parser: ProtocolParser):
        """Test PUT with zero TTL (no expiration)."""
        cmd = parser.parse_request("PUT key value 0")

        assert cmd.type == CommandType.PUT
        assert cmd.ttl == 0

    def test_parse_put_large_ttl(self, parser: ProtocolParser):
        """Test PUT with large TTL value."""
        cmd = parser.parse_request("PUT key value 2147483647")

        assert cmd.type == CommandType.PUT
        assert cmd.ttl == 2147483647


class TestParseRequestGET:
    """Test parsing GET commands."""

    def test_parse_get_basic(self, parser: ProtocolParser):
        """Test parsing basic GET command."""
        cmd = parser.parse_request("GET key")

        assert cmd.type == CommandType.GET
        assert cmd.key == "key"

    def test_parse_get_with_newline(self, parser: ProtocolParser):
        """Test parsing GET with trailing newline."""
        cmd = parser.parse_request("GET key\n")

        assert cmd.type == CommandType.GET
        assert cmd.key == "key"

    def test_parse_get_case_insensitive(self, parser: ProtocolParser):
        """Test GET command is case-insensitive."""
        for variant in ["get", "GET", "Get", "gEt"]:
            cmd = parser.parse_request(f"{variant} key")
            assert cmd.type == CommandType.GET

    def test_parse_get_missing_key(self, parser: ProtocolParser):
        """Test GET without key returns UNKNOWN."""
        cmd = parser.parse_request("GET")
        assert cmd.type == CommandType.UNKNOWN


class TestParseRequestDELETE:
    """Test parsing DELETE commands."""

    def test_parse_delete_basic(self, parser: ProtocolParser):
        """Test parsing basic DELETE command."""
        cmd = parser.parse_request("DELETE key")

        assert cmd.type == CommandType.DELETE
        assert cmd.key == "key"

    def test_parse_delete_case_insensitive(self, parser: ProtocolParser):
        """Test DELETE command is case-insensitive."""
        for variant in ["delete", "DELETE", "Delete"]:
            cmd = parser.parse_request(f"{variant} key")
            assert cmd.type == CommandType.DELETE

    def test_parse_delete_missing_key(self, parser: ProtocolParser):
        """Test DELETE without key returns UNKNOWN."""
        cmd = parser.parse_request("DELETE")
        assert cmd.type == CommandType.UNKNOWN


class TestParseRequestEXISTS:
    """Test parsing EXISTS commands."""

    def test_parse_exists_basic(self, parser: ProtocolParser):
        """Test parsing basic EXISTS command."""
        cmd = parser.parse_request("EXISTS key")

        assert cmd.type == CommandType.EXISTS
        assert cmd.key == "key"

    def test_parse_exists_case_insensitive(self, parser: ProtocolParser):
        """Test EXISTS command is case-insensitive."""
        for variant in ["exists", "EXISTS", "Exists"]:
            cmd = parser.parse_request(f"{variant} key")
            assert cmd.type == CommandType.EXISTS

    def test_parse_exists_missing_key(self, parser: ProtocolParser):
        """Test EXISTS without key returns UNKNOWN."""
        cmd = parser.parse_request("EXISTS")
        assert cmd.type == CommandType.UNKNOWN


class TestParseRequestQUIT:
    """Test parsing QUIT command."""

    def test_parse_quit(self, parser: ProtocolParser):
        """Test parsing QUIT command."""
        cmd = parser.parse_request("QUIT")
        assert cmd.type == CommandType.QUIT

    def test_parse_quit_with_newline(self, parser: ProtocolParser):
        """Test parsing QUIT with newline."""
        cmd = parser.parse_request("QUIT\n")
        assert cmd.type == CommandType.QUIT

    def test_parse_quit_case_insensitive(self, parser: ProtocolParser):
        """Test QUIT is case-insensitive."""
        for variant in ["quit", "QUIT", "Quit"]:
            cmd = parser.parse_request(variant)
            assert cmd.type == CommandType.QUIT


class TestParseRequestEdgeCases:
    """Test edge cases for parse_request."""

    def test_parse_unknown_command(self, parser: ProtocolParser):
        """Test unknown command returns UNKNOWN."""
        cmd = parser.parse_request("INVALID key value")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_empty_input(self, parser: ProtocolParser):
        """Test empty input returns UNKNOWN."""
        cmd = parser.parse_request("")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_whitespace_only(self, parser: ProtocolParser):
        """Test whitespace-only input returns UNKNOWN."""
        cmd = parser.parse_request("   \n\t  ")
        assert cmd.type == CommandType.UNKNOWN

    def test_parse_extra_whitespace(self, parser: ProtocolParser):
        """Test handling of extra whitespace between parts."""
        cmd = parser.parse_request("  PUT   key   value  ")

        assert cmd.type == CommandType.PUT
        assert cmd.key == "key"
        assert cmd.value == "value"

    def test_parse_preserves_raw(self, parser: ProtocolParser):
        """Test that raw command is preserved."""
        raw = "PUT key value 60"
        cmd = parser.parse_request(raw)
        assert cmd.raw == raw

    def test_parse_key_max_length(self, parser: ProtocolParser):
        """Test key at maximum length (256 chars)."""
        long_key = "k" * 256
        cmd = parser.parse_request(f"GET {long_key}")

        assert cmd.type == CommandType.GET
        assert cmd.key == long_key

    def test_parse_key_over_max_length(self, parser: ProtocolParser):
        """Test key over maximum length returns UNKNOWN."""
        long_key = "k" * 257
        cmd = parser.parse_request(f"GET {long_key}")

        assert cmd.type == CommandType.UNKNOWN

    def test_parse_value_max_length(self, parser: ProtocolParser):
        """Test value at maximum length."""
        long_value = "v" * 256
        cmd = parser.parse_request(f"PUT key {long_value}")

        assert cmd.type == CommandType.PUT
        assert cmd.value == long_value

    def test_parse_value_over_max_length(self, parser: ProtocolParser):
        """Test value over maximum length returns UNKNOWN."""
        long_value = "v" * 257
        cmd = parser.parse_request(f"PUT key {long_value}")

        assert cmd.type == CommandType.UNKNOWN


class TestFormatResponse:
    """Test format_response method."""

    def test_format_ok_stored(self, parser: ProtocolParser):
        """Test formatting 'stored' response."""
        response = Response.stored()
        result = parser.format_response(response)
        assert result == "OK stored\n"

    def test_format_ok_deleted(self, parser: ProtocolParser):
        """Test formatting 'deleted' response."""
        response = Response.deleted()
        result = parser.format_response(response)
        assert result == "OK deleted\n"

    def test_format_ok_value(self, parser: ProtocolParser):
        """Test formatting GET value response."""
        response = Response.value_response("myvalue")
        result = parser.format_response(response)
        assert result == "OK myvalue\n"

    def test_format_ok_exists_true(self, parser: ProtocolParser):
        """Test formatting EXISTS true response."""
        response = Response.exists_response(True)
        result = parser.format_response(response)
        assert result == "OK 1\n"

    def test_format_ok_exists_false(self, parser: ProtocolParser):
        """Test formatting EXISTS false response."""
        response = Response.exists_response(False)
        result = parser.format_response(response)
        assert result == "OK 0\n"

    def test_format_error_key_not_found(self, parser: ProtocolParser):
        """Test formatting 'key not found' error."""
        response = Response.key_not_found()
        result = parser.format_response(response)
        assert result == "ERROR key not found\n"

    def test_format_error_custom(self, parser: ProtocolParser):
        """Test formatting custom error."""
        response = Response.error("custom error")
        result = parser.format_response(response)
        assert result == "ERROR custom error\n"

    def test_format_ends_with_newline(self, parser: ProtocolParser):
        """Test all responses end with newline."""
        responses = [
            Response.stored(),
            Response.deleted(),
            Response.value_response("test"),
            Response.exists_response(True),
            Response.exists_response(False),
            Response.key_not_found(),
            Response.error("error"),
        ]

        for response in responses:
            result = parser.format_response(response)
            assert result.endswith("\n"), f"Response doesn't end with newline: {result}"


class TestCommandClass:
    """Test Command class helper methods."""

    def test_command_is_valid_put_complete(self):
        """Test is_valid for complete PUT."""
        cmd = Command(type=CommandType.PUT, key="key", value="value")
        assert cmd.is_valid is True

    def test_command_is_valid_put_missing_value(self):
        """Test is_valid for PUT without value."""
        cmd = Command(type=CommandType.PUT, key="key", value="")
        assert cmd.is_valid is False

    def test_command_is_valid_put_missing_key(self):
        """Test is_valid for PUT without key."""
        cmd = Command(type=CommandType.PUT, key="", value="value")
        assert cmd.is_valid is False

    def test_command_is_valid_get_complete(self):
        """Test is_valid for complete GET."""
        cmd = Command(type=CommandType.GET, key="key")
        assert cmd.is_valid is True

    def test_command_is_valid_get_missing_key(self):
        """Test is_valid for GET without key."""
        cmd = Command(type=CommandType.GET, key="")
        assert cmd.is_valid is False

    def test_command_is_valid_quit(self):
        """Test is_valid for QUIT (always valid)."""
        cmd = Command(type=CommandType.QUIT)
        assert cmd.is_valid is True

    def test_command_is_valid_unknown(self):
        """Test is_valid for UNKNOWN (always invalid)."""
        cmd = Command(type=CommandType.UNKNOWN)
        assert cmd.is_valid is False


class TestResponseClass:
    """Test Response class factory methods."""

    def test_response_ok(self):
        """Test Response.ok() factory."""
        resp = Response.ok(message="success")
        assert resp.status == ResponseStatus.OK
        assert resp.message == "success"

    def test_response_error(self):
        """Test Response.error() factory."""
        resp = Response.error(message="failure")
        assert resp.status == ResponseStatus.ERROR
        assert resp.message == "failure"

    def test_response_stored(self):
        """Test Response.stored() factory."""
        resp = Response.stored()
        assert resp.status == ResponseStatus.OK
        assert resp.message == "stored"

    def test_response_deleted(self):
        """Test Response.deleted() factory."""
        resp = Response.deleted()
        assert resp.status == ResponseStatus.OK
        assert resp.message == "deleted"

    def test_response_key_not_found(self):
        """Test Response.key_not_found() factory."""
        resp = Response.key_not_found()
        assert resp.status == ResponseStatus.ERROR
        assert resp.message == "key not found"

    def test_response_value_response(self):
        """Test Response.value_response() factory."""
        resp = Response.value_response("myvalue")
        assert resp.status == ResponseStatus.OK
        assert resp.value == "myvalue"

    def test_response_exists_true(self):
        """Test Response.exists_response(True)."""
        resp = Response.exists_response(True)
        assert resp.status == ResponseStatus.OK
        assert resp.message == "1"

    def test_response_exists_false(self):
        """Test Response.exists_response(False)."""
        resp = Response.exists_response(False)
        assert resp.status == ResponseStatus.OK
        assert resp.message == "0"
