"""Tests for field redaction functionality."""

from fapilog.redactors import (
    _get_nested_value,
    _redact_nested_fields,
    _set_nested_value,
    field_redactor,
)


class TestNestedValueOperations:
    """Test nested value get/set operations."""

    def test_get_nested_value_simple(self):
        """Test getting a simple nested value."""
        data = {"user": {"name": "john", "password": "secret"}}
        assert _get_nested_value(data, "user.name") == "john"
        assert _get_nested_value(data, "user.password") == "secret"

    def test_get_nested_value_deep(self):
        """Test getting deeply nested values."""
        data = {"a": {"b": {"c": {"d": "value"}}}}
        assert _get_nested_value(data, "a.b.c.d") == "value"

    def test_get_nested_value_missing(self):
        """Test getting non-existent nested values."""
        data = {"user": {"name": "john"}}
        assert _get_nested_value(data, "user.password") is None
        assert _get_nested_value(data, "user.name.missing") is None

    def test_set_nested_value_simple(self):
        """Test setting a simple nested value."""
        data = {"user": {"name": "john"}}
        _set_nested_value(data, "user.password", "new_secret")
        assert data["user"]["password"] == "new_secret"

    def test_set_nested_value_deep(self):
        """Test setting deeply nested values."""
        data = {"a": {"b": {}}}
        _set_nested_value(data, "a.b.c.d", "deep_value")
        assert data["a"]["b"]["c"]["d"] == "deep_value"

    def test_set_nested_value_creates_path(self):
        """Test that setting creates missing path elements."""
        data = {}
        _set_nested_value(data, "user.profile.email", "test@example.com")
        assert data["user"]["profile"]["email"] == "test@example.com"


class TestRedactNestedFields:
    """Test the main redaction functionality."""

    def test_redact_flat_fields(self):
        """Test redacting top-level fields."""
        data = {"password": "secret", "token": "abc123", "name": "john"}
        fields_to_redact = ["password", "token"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result["password"] == "REDACTED"
        assert result["token"] == "REDACTED"
        assert result["name"] == "john"  # Should remain unchanged

    def test_redact_nested_fields(self):
        """Test redacting nested fields using dot notation."""
        data = {
            "user": {
                "name": "john",
                "password": "secret",
                "profile": {"email": "john@example.com", "api_key": "xyz789"},
            },
            "auth": {"token": "abc123"},
        }
        fields_to_redact = ["user.password", "user.profile.api_key", "auth.token"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result["user"]["password"] == "REDACTED"
        assert result["user"]["profile"]["api_key"] == "REDACTED"
        assert result["auth"]["token"] == "REDACTED"
        assert result["user"]["name"] == "john"  # Should remain unchanged
        assert (
            result["user"]["profile"]["email"] == "john@example.com"
        )  # Should remain unchanged

    def test_redact_custom_replacement(self):
        """Test redacting with custom replacement value."""
        data = {"password": "secret", "token": "abc123"}
        fields_to_redact = ["password", "token"]

        result = _redact_nested_fields(data, fields_to_redact, "***")

        assert result["password"] == "***"
        assert result["token"] == "***"

    def test_redact_empty_fields_list(self):
        """Test that empty fields list returns original data."""
        data = {"password": "secret", "name": "john"}
        result = _redact_nested_fields(data, [])

        assert result == data

    def test_redact_nonexistent_fields(self):
        """Test that non-existent fields don't cause errors."""
        data = {"name": "john"}
        fields_to_redact = ["password", "user.email"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result == data  # Should be unchanged

    def test_redact_nested_lists(self):
        """Test redacting fields in lists of dictionaries."""
        data = {
            "users": [
                {"name": "john", "password": "secret1"},
                {"name": "jane", "password": "secret2"},
            ]
        }
        fields_to_redact = ["users.password"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result["users"][0]["password"] == "REDACTED"
        assert result["users"][1]["password"] == "REDACTED"
        assert result["users"][0]["name"] == "john"  # Should remain unchanged
        assert result["users"][1]["name"] == "jane"  # Should remain unchanged

    def test_redact_mixed_nested_structure(self):
        """Test redacting in complex nested structures."""
        data = {
            "users": [
                {
                    "name": "john",
                    "credentials": {"password": "secret1", "api_key": "key1"},
                },
                {
                    "name": "jane",
                    "credentials": {"password": "secret2", "api_key": "key2"},
                },
            ],
            "global_config": {"admin_token": "admin_secret"},
        }
        fields_to_redact = [
            "users.credentials.password",
            "users.credentials.api_key",
            "global_config.admin_token",
        ]

        result = _redact_nested_fields(data, fields_to_redact)

        # Check that all sensitive fields are redacted
        assert result["users"][0]["credentials"]["password"] == "REDACTED"
        assert result["users"][0]["credentials"]["api_key"] == "REDACTED"
        assert result["users"][1]["credentials"]["password"] == "REDACTED"
        assert result["users"][1]["credentials"]["api_key"] == "REDACTED"
        assert result["global_config"]["admin_token"] == "REDACTED"

        # Check that non-sensitive fields remain unchanged
        assert result["users"][0]["name"] == "john"
        assert result["users"][1]["name"] == "jane"

    def test_redact_does_not_modify_original(self):
        """Test that the original data is not modified."""
        data = {"password": "secret", "name": "john"}
        original_data = data.copy()
        fields_to_redact = ["password"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert data == original_data  # Original should be unchanged
        assert result["password"] == "REDACTED"  # Result should be redacted

    def test_redact_with_non_dict_values_in_list(self):
        """Test redacting when list contains non-dict values."""
        data = {
            "items": [
                {"name": "item1", "secret": "secret1"},
                "not_a_dict",
                {"name": "item2", "secret": "secret2"},
            ]
        }
        fields_to_redact = ["items.secret"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result["items"][0]["secret"] == "REDACTED"
        assert result["items"][1] == "not_a_dict"  # Should remain unchanged
        assert result["items"][2]["secret"] == "REDACTED"

    def test_redact_with_empty_dict(self):
        """Test redacting with empty dictionary."""
        data = {}
        fields_to_redact = ["user.password"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result == data  # Should remain unchanged

    def test_redact_with_none_values(self):
        """Test redacting with None values in data."""
        data = {
            "user": {"name": "john", "password": None},
            "auth": {"token": "abc123"},
        }
        fields_to_redact = ["user.password", "auth.token"]

        result = _redact_nested_fields(data, fields_to_redact)

        assert result["user"]["password"] == "REDACTED"
        assert result["auth"]["token"] == "REDACTED"
        assert result["user"]["name"] == "john"  # Should remain unchanged

    def test_redact_with_complex_list_structure(self):
        """Test redacting in complex list structures."""
        data = {
            "departments": [
                {
                    "name": "Engineering",
                    "employees": [
                        {"name": "alice", "salary": 50000, "ssn": "123-45-6789"},
                        {"name": "bob", "salary": 60000, "ssn": "987-65-4321"},
                    ],
                },
                {
                    "name": "Sales",
                    "employees": [
                        {"name": "charlie", "salary": 45000, "ssn": "111-22-3333"},
                    ],
                },
            ]
        }
        fields_to_redact = ["departments.employees.ssn"]

        result = _redact_nested_fields(data, fields_to_redact)

        # Check that SSNs are redacted
        assert result["departments"][0]["employees"][0]["ssn"] == "REDACTED"
        assert result["departments"][0]["employees"][1]["ssn"] == "REDACTED"
        assert result["departments"][1]["employees"][0]["ssn"] == "REDACTED"

        # Check that other fields remain unchanged
        assert result["departments"][0]["employees"][0]["name"] == "alice"
        assert result["departments"][0]["employees"][0]["salary"] == 50000


class TestFieldRedactor:
    """Test the structlog processor wrapper."""

    def test_field_redactor_processor(self):
        """Test the field redactor as a structlog processor."""
        fields_to_redact = ["password", "user.token"]
        processor = field_redactor(fields_to_redact, "***")

        event_dict = {
            "password": "secret",
            "user": {"name": "john", "token": "abc123"},
            "message": "test",
        }

        result = processor(None, "info", event_dict)

        assert result["password"] == "***"
        assert result["user"]["token"] == "***"
        assert result["user"]["name"] == "john"  # Should remain unchanged
        assert result["message"] == "test"  # Should remain unchanged

    def test_field_redactor_empty_fields(self):
        """Test field redactor with empty fields list."""
        processor = field_redactor([], "REDACTED")

        event_dict = {"password": "secret", "name": "john"}
        result = processor(None, "info", event_dict)

        assert result == event_dict  # Should be unchanged

    def test_field_redactor_default_replacement(self):
        """Test field redactor with default replacement value."""
        processor = field_redactor(["password"])

        event_dict = {"password": "secret"}
        result = processor(None, "info", event_dict)

        assert result["password"] == "REDACTED"  # Default replacement

    def test_field_redactor_with_complex_data(self):
        """Test field redactor with complex nested data."""
        fields_to_redact = ["user.password", "config.api_key", "users.password"]
        processor = field_redactor(fields_to_redact, "***")

        event_dict = {
            "user": {"name": "john", "password": "secret123"},
            "config": {"debug": True, "api_key": "sk-abc123"},
            "users": [
                {"name": "alice", "password": "alice_secret"},
                {"name": "bob", "password": "bob_secret"},
            ],
        }

        result = processor(None, "info", event_dict)

        # Check redacted fields
        assert result["user"]["password"] == "***"
        assert result["config"]["api_key"] == "***"
        assert result["users"][0]["password"] == "***"
        assert result["users"][1]["password"] == "***"

        # Check unchanged fields
        assert result["user"]["name"] == "john"
        assert result["config"]["debug"] is True
        assert result["users"][0]["name"] == "alice"
        assert result["users"][1]["name"] == "bob"
