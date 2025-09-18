""" Unit tests for session store functionality."""
from typing import TYPE_CHECKING
import logging
import pytest
import boto3
from moto import mock_aws

from runtime.shared.db.session.session_store import (
    OwnerSessionHelper,
    VisitorSessionHelper,
)
from runtime.shared.db.session.session_model import OwnerSession, VisitorSession
from runtime.shared.com.identifier_model import OwnerHash, TagCode, SessionToken

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

OWNER_TABLE = "LostAndFound-OwnerSession"
VISITOR_TABLE = "LostAndFound-VisitorSession"

# disable assert warning, we are in tests


@pytest.fixture
def ddb_tables():
    """ Create mocked DynamoDB tables for testing."""
    with mock_aws():
        ddb: DynamoDBServiceResource = boto3.resource("dynamodb")
        # Owner table
        ddb.create_table(
            TableName=OWNER_TABLE,
            KeySchema=[{
                "AttributeName": "session_token",
                "KeyType": "HASH"
            }],
            AttributeDefinitions=[{
                "AttributeName": "session_token",
                "AttributeType": "S"
            }],
            BillingMode="PAY_PER_REQUEST",
        )
        # Visitor table
        ddb.create_table(
            TableName=VISITOR_TABLE,
            KeySchema=[{
                "AttributeName": "session_token",
                "KeyType": "HASH"
            }],
            AttributeDefinitions=[{
                "AttributeName": "session_token",
                "AttributeType": "S"
            }],
            BillingMode="PAY_PER_REQUEST",
        )
        yield ddb


def test_owner_session_crud(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test creating, retrieving, and deleting an owner session. """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    logger.info("Testing owner session CRUD operations.")
    logger.debug(f"helper details: {helper}")

    # Create
    owner_hash = "owner_" + "A" * 43
    session = helper.create_owner_session(owner_hash=owner_hash)

    # Statt isinstance: Felder prüfen
    assert hasattr(session, "session_token") and hasattr(session, "owner_hash")
    assert session.owner_hash.value == owner_hash
    assert session.expires_at.value > session.created_at.value
    assert len(session.session_token.value) >= 43

    # Retrieve
    loaded = helper.get_owner_session(session.session_token.value)
    assert loaded is not None
    assert loaded.owner_hash.value == session.owner_hash.value
    assert loaded.session_token.value == session.session_token.value

    # Delete
    helper.delete_session(session.session_token.value)
    assert helper.get_owner_session(session.session_token.value) is None


def test_owner_session_onetime(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test creating a one-time owner session. """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    owner_hash = "owner_" + "B" * 43
    session = helper.create_owner_session(owner_hash=owner_hash, onetime=True)

    assert hasattr(session, "session_token") and hasattr(session, "owner_hash")
    assert session.onetime is True
    assert session.owner_hash.value == owner_hash

    # Retrieve
    loaded = helper.get_owner_session(session.session_token.value)
    assert loaded is not None
    assert loaded.onetime is True
    assert loaded.owner_hash.value == owner_hash


def test_visitor_session_crud(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test creating, retrieving, and deleting a visitor session. """
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    tag_code = "tag_" + "Z" * 32
    session = helper.create_visitor_session(tag_code=tag_code)
    assert hasattr(session, "session_token") and hasattr(session, "tag_code")
    assert session.tag_code.value == tag_code
    assert session.expires_at.value > session.created_at.value
    assert len(session.session_token.value) >= 43

    # Retrieve
    loaded = helper.get_visitor_session(session.session_token.value)
    assert loaded is not None
    assert loaded.tag_code.value == session.tag_code.value
    assert loaded.session_token.value == session.session_token.value

    # Delete
    helper.delete_session(session.session_token.value)
    assert helper.get_visitor_session(session.session_token.value) is None


def test_owner_session_not_found(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test retrieving a non-existent owner session. """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    fake_token = "doesnotexist"
    assert helper.get_owner_session(fake_token) is None


def test_visitor_session_not_found(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test retrieving a non-existent visitor session. """
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    fake_token = "doesnotexist"
    assert helper.get_visitor_session(fake_token) is None


def test_delete_nonexistent_session(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test deleting a non-existent session (should be no-op). """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    fake_token = "nonexistent-session-token"
    # Should not raise (DynamoDB delete is idempotent)
    helper.delete_session(fake_token)
