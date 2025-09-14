import pytest
import logging
from moto import mock_aws
import boto3

from runtime.shared.owner_model import Owner, Status
from runtime.shared.owner_store import OwnerStore

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
    return Owner(owner_hash="owner_" + "A" * 43,
                 salt="B" * 22,
                 password_hash="$2a$12$" + "C" * 53,
                 public_key="-----BEGIN PUBLIC KEY-----\n" + "X" * 272 + "\n-----END PUBLIC KEY-----\n",
                 random_entropy="F" * 32,
                 created_at=1672531200,
                 owner_encrypted_storage="0",
                 status=Status.ACTIVE)


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
    except Exception as e:  # pylint disable=
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
    assert loaded.status == "blocked"
