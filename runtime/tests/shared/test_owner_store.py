import pytest
import logging
from moto import mock_aws
import boto3

from pydantic import ValidationError

from runtime.shared.db.owner.owner_model import Status
from runtime.shared.db.owner.owner_store import OwnerStore, OwnerHelper

OWNER_TABLE = "LostAndFound-Owner"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.fixture
def ddb_table():
    """ Create mocked DynamoDB tables for testing."""
    with mock_aws():
        table = boto3.resource("dynamodb")
        # Owner table
        table.create_table(
            TableName=OWNER_TABLE,
            KeySchema=[{
                "AttributeName": "owner_hash",
                "KeyType": "HASH"
            }],
            AttributeDefinitions=[{
                "AttributeName": "owner_hash",
                "AttributeType": "S"
            }],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


def make_owner():
    """ Helper to create a valid Owner instance. """
    owner = OwnerHelper.create_owner(
        owner_hash="owner_" + "A" * 43,
        salt="B" * 22,
        password_hash="$2a$12$" + "C" * 53,
        public_key="-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n",
        random_entropy="F" * 32,
        created_at=1672531200,
        owner_encrypted_storage="0",
        status=Status.ACTIVE,
    )
    return owner


def valid_owner_dict():
    """Return a dict with valid owner fields."""
    return {
        "owner_hash": "owner_" + "A" * 43,
        "salt": "B" * 22,
        "password_hash": "$2a$12$" + "C" * 53,
        "public_key": "-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n",
        "random_entropy": "F" * 32,
        "owner_encrypted_storage": "TWFu",  # Base64 for "Man"
        "created_at": 1672531200,
        "status": Status.ACTIVE,
    }


def test_put_and_get_owner(ddb_table):
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    logger.debug(f"created owner: {owner}")
    try:
        store.put_owner(owner)
    except Exception as e:
        logger.error(f"unexpected put error: {e}")
    loaded = None
    try:
        loaded = store.get_owner(owner.owner_hash)
    except Exception as e:
        logger.error(f"unexpected get error: {e}")
    assert loaded is not None
    assert loaded.owner_hash == owner.owner_hash


def test_update_owner_field(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    updated = store.update_owner_field(owner.owner_hash, "status", "blocked")
    assert updated == "blocked"
    loaded = store.get_owner(owner.owner_hash)
    logger.debug(f"owner: {loaded}")
    assert loaded is not None
    assert loaded.status.value == "blocked"


@pytest.mark.parametrize(
    "field,invalid_value",
    [
        ("owner_hash", "owner_short"),  # too short
        ("owner_hash", "ownr_" + "A" * 43),  # wrong prefix
        ("salt", "B" * 10),  # too short
        ("salt", "invalid salt!"),  # invalid chars
        ("password_hash", "short"),  # too short
        ("password_hash", "notvalid$2a$pattern"),  # wrong pattern
        ("public_key", "no_key_headers"),  # missing PEM format
        ("random_entropy", "Z" * 31),  # too short
        ("random_entropy", "Y" * 65),  # too long
        ("random_entropy", "abc!@#"),  # invalid chars
        ("owner_encrypted_storage", "!@#$"),  # not base64
        ("created_at", -1),  # negative timestamp
        ("status", "not-a-status"),  # invalid enum member
    ])
def test_invalid_owner_fields(field, invalid_value):
    data = valid_owner_dict()
    data[field] = invalid_value
    with pytest.raises((ValidationError, ValueError)):
        OwnerHelper.create_owner(**data)


def test_missing_required_fields():
    data = valid_owner_dict()
    for f in data.keys():
        d = dict(data)
        d.pop(f)
        with pytest.raises((ValidationError, TypeError)):
            OwnerHelper.create_owner(**d)


def test_ownerhelper_validate_owner_valid():
    owner = OwnerHelper.create_owner(**valid_owner_dict())
    assert OwnerHelper.validate_owner(owner) == True


def test_ownerhelper_validate_owner_invalid():
    owner = OwnerHelper.create_owner(**valid_owner_dict())
    owner.owner_hash = "bad"
    assert OwnerHelper.validate_owner(owner) == False


def test_ownerhelper_validate_field_valid_and_invalid():
    assert OwnerHelper.validate_field("owner_hash", "owner_" + "A" * 43)
    assert not OwnerHelper.validate_field("owner_hash", "own_BAD")
    assert OwnerHelper.validate_field("status", Status.ACTIVE)
    assert not OwnerHelper.validate_field("status", "no-status")


def test_ownerhelper_status_checks():
    owner = OwnerHelper.create_owner(**valid_owner_dict())
    assert OwnerHelper.is_active(owner)
    owner.status = Status.BLOCKED
    assert OwnerHelper.is_blocked(owner)
    owner.status = Status.IN_DELETION
    assert OwnerHelper.is_in_deletion(owner)


def test_update_owner_field_with_illegal_field(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    with pytest.raises(ValidationError):
        store.update_owner_field(owner.owner_hash, "illegal_field", "value")


def test_update_owner_field_with_invalid_value(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    with pytest.raises(ValidationError):
        # status must be enum; "none" is not valid
        store.update_owner_field(owner.owner_hash, "status", "none")


def test_update_owner_fields_with_multiple_keys(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    updates = {"status": "active", "random_entropy": "F" * 32}
    resp = store.update_owner_fields(owner.owner_hash, updates)
    assert resp["status"] == "active"
    assert resp["random_entropy"] == "F" * 32


def test_get_owner_field_not_exists(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    assert store.get_owner_field(owner.owner_hash, "somethingthatdoesntexist") is None


def test_get_owner_field_invalid_owner(ddb_table):
    store = OwnerStore(ddb_resource=ddb_table)
    assert store.get_owner_field("owner_invalid" + "A" * 37, "status") is None
