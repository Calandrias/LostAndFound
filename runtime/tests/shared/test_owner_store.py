import pytest
import logging
from moto import mock_aws
import boto3

from pydantic import ValidationError

from runtime.shared.db.owner.owner_model import State
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
        state=State.ACTIVE,
    )

    return owner


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
        loaded = store.get_owner(owner.owner_hash.value)
    except Exception as e:  # pylint disable=
        logger.error(f"unexpected get error: {e}")

    assert loaded is not None
    assert loaded.owner_hash == owner.owner_hash


def test_update_owner_field(ddb_table):
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
