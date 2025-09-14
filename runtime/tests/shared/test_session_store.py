""" Unit tests for session store functionality."""
from typing import TYPE_CHECKING
import logging
import pytest
import boto3
from moto import mock_aws

from runtime.shared.session_store import (
    OwnerSessionHelper,
    VisitorSessionHelper,
)
from runtime.shared.session_model import OwnerSession, VisitorSession

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

    assert isinstance(session, OwnerSession)
    assert session.owner_hash == owner_hash
    assert session.expires_at > session.created_at
    assert len(session.session_token) >= 43

    # Retrieve
    loaded = helper.get_owner_session(session.session_token)
    assert loaded is not None
    assert loaded.owner_hash == session.owner_hash
    assert loaded.session_token == session.session_token

    # Delete
    helper.delete_session(session.session_token)
    assert helper.get_owner_session(session.session_token) is None


def test_owner_session_onetime(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test creating a one-time owner session. """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    owner_hash = "owner_" + "B" * 43
    session = helper.create_owner_session(owner_hash=owner_hash, onetime=True)

    assert isinstance(session, OwnerSession)
    assert session.onetime is True

    # Retrieve
    loaded = helper.get_owner_session(session.session_token)
    assert loaded is not None
    assert loaded.onetime is True


def test_visitor_session_crud(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test creating, retrieving, and deleting a visitor session. """
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    tag_code = "tag_" + "Z" * 10
    session = helper.create_visitor_session(tag_code=tag_code)
    assert isinstance(session, VisitorSession)
    assert session.tag_code == tag_code
    assert session.expires_at > session.created_at
    assert len(session.session_token) >= 43

    # Retrieve
    loaded = helper.get_visitor_session(session.session_token)
    assert loaded is not None
    assert loaded.tag_code == session.tag_code
    assert loaded.session_token == session.session_token

    # Delete
    helper.delete_session(session.session_token)
    assert helper.get_visitor_session(session.session_token) is None


def test_owner_session_not_found(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test retrieving a non-existent owner session. """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    assert helper.get_owner_session('doesnotexist') is None


def test_visitor_session_not_found(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test retrieving a non-existent visitor session. """
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    assert helper.get_visitor_session('doesnotexist') is None


def test_delete_nonexistent_session(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """ Test deleting a non-existent session (should be no-op). """
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    # Should not raise (DynamoDB delete is idempotent)
    helper.delete_session("nonexistent-session-token")
