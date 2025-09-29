"""Unit tests for session store functionality."""
from typing import TYPE_CHECKING
import logging
import pytest
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError
from shared.db.session.session_store import (
    SessionDeleteError,
    SessionRetrieveError,
    OwnerSessionHelper,
    VisitorSessionHelper,
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

OWNER_TABLE = "LostAndFound-OwnerSession"
VISITOR_TABLE = "LostAndFound-VisitorSession"

# disable assert warning, we are in tests


@pytest.fixture
def ddb_tables():
    """Create mocked DynamoDB tables for OwnerSession and VisitorSession tests."""
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
    """Test creating, retrieving, and deleting an owner session."""
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
    """Test creating and retrieving a one-time owner session."""
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
    """Test creating, retrieving, and deleting a visitor session."""
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
    """Test retrieving a non-existent owner session returns None."""
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    fake_token = "doesnotexist"
    assert helper.get_owner_session(fake_token) is None


def test_visitor_session_not_found(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test retrieving a non-existent visitor session returns None."""
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    fake_token = "doesnotexist"
    assert helper.get_visitor_session(fake_token) is None


def test_delete_nonexistent_session(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test deleting a non-existent session does not raise an error."""
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    fake_token = "nonexistent-session-token"
    # Should not raise (DynamoDB delete is idempotent)
    helper.delete_session(fake_token)


def test_create_owner_session_invalid_owner_hash(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test creating an owner session with invalid owner_hash raises Exception."""
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    # owner_hash zu kurz/ungültig
    with pytest.raises(Exception):
        helper.create_owner_session(owner_hash="invalid")


def test_create_visitor_session_invalid_tag_code(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test creating a visitor session with invalid tag_code raises Exception."""
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    # tag_code zu kurz/ungültig
    with pytest.raises(Exception):
        helper.create_visitor_session(tag_code="invalid")


def test_get_owner_session_invalid_token(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test retrieving an owner session with invalid token raises SessionRetrieveError or returns None."""
    helper = OwnerSessionHelper(table_name=OWNER_TABLE, ddb_resource=ddb_tables)
    # Token mit ungültigem Format
    assert helper.get_owner_session(12345) is None
    with pytest.raises(SessionRetrieveError):
        helper.get_owner_session("")


def test_get_visitor_session_invalid_token(ddb_tables):  # pylint: disable=redefined-outer-name # useage of fixture
    """Test retrieving a visitor session with invalid token raises SessionRetrieveError or returns None."""
    helper = VisitorSessionHelper(table_name=VISITOR_TABLE, ddb_resource=ddb_tables)
    assert helper.get_visitor_session(12345) is None
    with pytest.raises(SessionRetrieveError):
        helper.get_visitor_session("")


def test_delete_session_client_error(mocker):
    """Test that a ClientError in delete_session raises SessionDeleteError."""
    helper = OwnerSessionHelper(table_name="tbl", ddb_resource=mocker.Mock())
    mocker.patch.object(helper.table, "delete_item", side_effect=ClientError({"Error": {}}, "DeleteItem"))
    with pytest.raises(SessionDeleteError):
        helper.delete_session("token")


def test_get_session_client_error(mocker):
    """Test that a ClientError in get_session raises SessionRetrieveError."""
    helper = OwnerSessionHelper(table_name="tbl", ddb_resource=mocker.Mock())
    mocker.patch.object(helper.table, "get_item", side_effect=ClientError({"Error": {}}, "GetItem"))
    Dummy = type("Dummy", (), {"model_fields": {}, "model_validate": staticmethod(lambda x: x)})
    with pytest.raises(SessionRetrieveError):
        helper.get_session("token", model=Dummy)


def test_create_owner_session_client_error(mocker):
    """Test that a ClientError in create_owner_session raises Exception."""
    helper = OwnerSessionHelper(table_name="tbl", ddb_resource=mocker.Mock())
    mocker.patch.object(helper.table, "put_item", side_effect=ClientError({"Error": {}}, "PutItem"))
    with pytest.raises(Exception):
        helper.create_owner_session(owner_hash="owner_" + "A" * 43)


def test_create_visitor_session_client_error(mocker):
    """Test that a ClientError in create_visitor_session raises Exception."""
    helper = VisitorSessionHelper(table_name="tbl", ddb_resource=mocker.Mock())
    mocker.patch.object(helper.table, "put_item", side_effect=ClientError({"Error": {}}, "PutItem"))
    with pytest.raises(Exception):
        helper.create_visitor_session(tag_code="tag_" + "Z" * 32)
