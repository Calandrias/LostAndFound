import pytest

from runtime.shared.com.identifier_model import OwnerHash, Timestamp, PublicKey
from runtime.shared.db.owner.owner_model import PasswordHash
from runtime.shared.db.owner.owner_store import OwnerHelper


@pytest.fixture
def valid_owner_values():
    """Fixture with valid owner data."""
    return {
        "owner_hash": "owner_" + "A" * 43,
        "salt": "B" * 22,
        "password_hash": "$2a$12$" + "C" * 53,
        "public_key": "-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n",
        "random_entropy": "F" * 32,
        "created_at": 1672531200,
        "owner_encrypted_storage": "SGVsbG8gV29ybGQ=",  # base64 for "Hello World"
        "state": "active"
    }


@pytest.mark.parametrize(
    "field_name,value,expected_result",
    [
        # Positive cases:
        ("owner_hash", "owner_" + "A" * 43, True),
        ("password_hash", "$2a$12$" + "C" * 53, True),
        ("public_key", "-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n", True),
        ("created_at", 1672531200, True),
        # Negative cases:
        ("owner_hash", "short", False),
        ("password_hash", "invalid_hash", False),
        ("public_key", "invalid_key", False),
        ("created_at", -1, False),
    ])
def test_validate_field_parametrized(field_name, value, expected_result):
    """Test field validation with various valid and invalid values."""
    result = OwnerHelper.validate_field(field_name, value)
    assert result == expected_result, f"Field '{field_name}' with value '{value}' should return {expected_result}"


@pytest.mark.parametrize("field_name", [
    "non_existent_field",
    "",
    None,
])
def test_validate_field_invalid_field_names(field_name):
    """Test for robust fail behavior on invalid field names."""
    result = OwnerHelper.validate_field(field_name, "dummy_value")
    assert result is False


def test_validate_field_real_owner(valid_owner_values):
    """All fields of a real owner should validate as True."""
    for field_name, value in valid_owner_values.items():
        assert OwnerHelper.validate_field(field_name, value) is True


def test_validate_field_state_enum():
    """The enum itself is accepted, not just its string value."""
    from runtime.shared.db.owner.owner_model import State
    for s in State:
        assert OwnerHelper.validate_field("state", s.value) is True


def test_field_helpers_raise_on_invalid_input():
    """Check if OwnerHelper rejects obviously invalid values."""
    assert OwnerHelper.validate_field("salt", None) is False
    assert OwnerHelper.validate_field("random_entropy", 42) is False
