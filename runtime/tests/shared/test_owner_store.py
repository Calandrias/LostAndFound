import pytest
import logging
from moto import mock_aws
import boto3
from botocore.exceptions import ClientError

from shared.db.owner.owner_model import State
from shared.db.owner.owner_store import OwnerStore, OwnerHelper

OWNER_TABLE = "LostAndFound-Owner"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@pytest.fixture
def ddb_table():
    """Create mocked DynamoDB tables for OwnerStore tests."""
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


def make_owner(state=State.ACTIVE):
    """Helper to create a valid Owner instance for tests."""
    owner = OwnerHelper.create_owner(
        owner_hash="owner_" + "A" * 43,
        salt="B" * 22,
        password_hash="$2a$12$" + "C" * 53,
        public_key="-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n",
        random_entropy="F" * 32,
        created_at=1735689600,  # 1.1.2025
        owner_encrypted_storage="0",
        state=state,
    )

    return owner


def test_put_and_get_owner(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test putting and retrieving an owner from the store."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    logger.debug(f"created owner: {owner}")
    try:
        store.put_owner(owner)
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"known put error: {type(e).__name__}: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"unexpected put error: {type(e).__name__}: {e}")

    loaded = None
    try:
        loaded = store.get_owner(owner.owner_hash.value)
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"known get error: {type(e).__name__}: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"unexpected get error: {type(e).__name__}: {e}")

    assert loaded is not None
    assert loaded.owner_hash == owner.owner_hash


def test_update_owner_field(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test updating a single field (state) of an owner."""
    store = OwnerStore(ddb_resource=ddb_table)
    owner = make_owner()
    assert OwnerHelper.is_active(owner) is True

    store.put_owner(owner)
    store.update_owner_field(owner.owner_hash.value, "state", "blocked")
    loaded = store.get_owner(owner.owner_hash.value)
    assert loaded is not None
    assert OwnerHelper.validate_owner(loaded)
    assert loaded.state == "blocked" or getattr(loaded.state, "value", None) == "blocked"
    assert OwnerHelper.is_blocked(loaded) is True
    assert OwnerHelper.is_in_deletion(loaded) is False


def test_create_owner_and_duplicate(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test creating an owner and handling duplicate creation error."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    store.create_owner(owner)
    with pytest.raises(Exception):
        store.create_owner(owner)


def test_delete_owner(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test deleting an owner and verifying removal."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    store.delete_owner(owner.owner_hash.value)
    assert store.get_owner(owner.owner_hash.value) is None


def test_update_owner_fields(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test updating multiple fields of an owner."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    updates = {"state": "blocked", "random_entropy": "F" * 40}
    attrs = store.update_owner_fields(owner.owner_hash.value, updates)
    assert "state" in attrs and attrs["state"] == "blocked"
    assert "random_entropy" in attrs and attrs["random_entropy"] == "F" * 40
    loaded = store.get_owner(owner.owner_hash.value)
    assert loaded.state == "blocked" or getattr(loaded.state, "value", None) == "blocked"
    assert loaded.random_entropy == "F" * 40


def test_get_owner_field(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test retrieving individual fields from an owner record."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    val = store.get_owner_field(owner.owner_hash.value, "state")
    assert val == "active" or getattr(val, "value", None) == "active"
    val2 = store.get_owner_field(owner.owner_hash.value, "random_entropy")
    assert val2 == "F" * 32
    assert store.get_owner_field(owner.owner_hash.value, "doesnotexist") is None


def test_update_owner_field_invalid(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test updating a non-allowed field raises ValueError."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    with pytest.raises(ValueError):
        store.update_owner_field(owner.owner_hash.value, "not_allowed_field", "value")


def test_update_owner_fields_invalid(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test updating multiple fields with at least one invalid field raises ValueError."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    owner = make_owner()
    store.put_owner(owner)
    updates = {"state": "blocked", "not_allowed_field": "value"}
    with pytest.raises(ValueError):
        store.update_owner_fields(owner.owner_hash.value, updates)


def test_delete_nonexistent_owner(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test deleting a non-existent owner does not raise an error."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    # Sollte kein Fehler werfen
    store.delete_owner("owner_DOES_NOT_EXIST")


def test_get_owner_not_found(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test retrieving a non-existent owner returns None."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    assert store.get_owner("owner_DOES_NOT_EXIST") is None


def test_get_owner_field_not_found(ddb_table):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test retrieving a non-existent field from a non-existent owner returns None."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=ddb_table)
    assert store.get_owner_field("owner_DOES_NOT_EXIST", "state") is None


def test_get_owner_client_error(mocker):
    """Test that a ClientError in get_owner is raised and handled."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=mocker.Mock())
    mocker.patch.object(store.table, "get_item", side_effect=ClientError({"Error": {}}, "GetItem"))
    with pytest.raises(ClientError):
        store.get_owner("owner_" + "A" * 43)


def test_delete_owner_client_error(mocker):
    """Test that a ClientError in delete_owner is raised and handled."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=mocker.Mock())
    mocker.patch.object(store.table, "delete_item", side_effect=ClientError({"Error": {}}, "DeleteItem"))
    with pytest.raises(ClientError):
        store.delete_owner("owner_" + "A" * 43)


def test_get_owner_field_client_error(mocker):
    """Test that a ClientError in get_owner_field is raised and handled."""
    store = OwnerStore(table_name=OWNER_TABLE, ddb_resource=mocker.Mock())
    mocker.patch.object(store.table, "get_item", side_effect=ClientError({"Error": {}}, "GetItem"))
    with pytest.raises(ClientError):
        store.get_owner_field("owner_" + "A" * 43, "state")
