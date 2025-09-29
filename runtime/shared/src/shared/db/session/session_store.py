"""
Shared session handler functions for owner and visitor sessions.

All public methods and classes are fully typed and documented. All exceptions that may be raised are documented in the docstrings.
"""
import secrets
import os
from typing import TYPE_CHECKING, Optional, TypeVar, Type, Any

import boto3
from pydantic import ValidationError, BaseModel
from botocore.exceptions import ClientError

from shared.db.session.session_model import OwnerSession, VisitorSession
from shared.com.shared_helper import dynamodb_decimal_to_int, current_unix_timestamp_utc
from shared.com.identifier_model import SessionToken, OwnerHash, TagCode, Timestamp

from shared.com.logging_utils import ProjectLogger

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table, DynamoDBServiceResource

DEFAULT_OWNER_SESSION_DURATION = 1 * 60 * 60  # 1 hour
DEFAULT_VISITOR_SESSION_DURATION = 8 * 60 * 60  # 8 hours

logger = ProjectLogger(__name__).get_logger()

# ------------------------
# Exception Hierarchy
# ------------------------


class SessionError(Exception):
    """
    Base error for all session-related exceptions.
    """


class SessionCreateError(SessionError):
    """
    Raised when session creation fails.
    """


class SessionRetrieveError(SessionError):
    """
    Raised when session retrieval fails.
    """


class SessionDeleteError(SessionError):
    """
    Raised when session deletion fails.
    """


# ------------------------
# Base Helper
# ------------------------

T = TypeVar('T', bound=BaseModel)


class SessionHelperBase:
    """
    Base logic for session helpers.
    """

    def __init__(self, table_name: str, ddb_resource: Optional[Any] = None):
        """
        Initialize the session helper base.

        Args:
            table_name (str): DynamoDB table name for sessions.
            ddb_resource (Optional[Any]): boto3 resource (for mocking/testing).
        """
        self.table_name = table_name
        self.ddb: DynamoDBServiceResource = ddb_resource or boto3.resource("dynamodb")
        self.table: Table = self.ddb.Table(self.table_name)

    def delete_session(self, session_token: str) -> None:
        """
        Delete a session by its token.

        Args:
            session_token (str): Session token to delete.
        Raises:
            SessionDeleteError: If deletion fails (database or unknown error).
        """
        try:
            self.table.delete_item(Key={"session_token": session_token})
        except ClientError as e:
            raise SessionDeleteError("Failed to delete session (database error).") from e
        except Exception as e:  #pylint: disable=broad-except # pragma: no cover
            raise SessionDeleteError("Unexpected error during session deletion.") from e

    def get_session(self, session_token: str, model: Type[T]) -> Optional[T]:
        """
        Retrieve and validate a session by its token.

        Args:
            session_token (str): Session token to retrieve.
            model (Type[T]): Pydantic model class for the session.
        Returns:
            Optional[T]: Validated session object if found, else None.
        Raises:
            SessionRetrieveError: If retrieval or validation fails.
        """
        try:
            response = self.table.get_item(Key={"session_token": session_token})
            item = response.get("Item")
            if item:
                item = dynamodb_decimal_to_int(item)
                for field, field_info in model.model_fields.items():
                    field_type = field_info.annotation
                    if field in item and hasattr(field_type, 'model_fields') and hasattr(field_type, 'validate') and field_type:
                        item[field] = field_type(value=item[field])
            return model.model_validate(item) if item else None
        except (ClientError, ValidationError) as e:
            raise SessionRetrieveError("Failed to load session.") from e
        except Exception as e:  #pylint: disable=broad-except # pragma: no cover
            raise SessionRetrieveError("Unknown error during session lookup.") from e

    def create_session_token(self) -> str:
        """
        Generate a unique session token.

        Returns:
            str: A new unique session token.
        """
        prefix = "sessiontok_"
        session_token = (prefix + secrets.token_urlsafe(64))[:86]  # 86 chars total
        logger.debug(f"Generated session token: {session_token}, length: {len(session_token)}")
        return session_token


# ------------------------
# Owner Session Helper
# ------------------------

DEFAULT_OWNER_SESSION_DURATION = 1 * 60 * 60  # 1 hour


class OwnerSessionHelper(SessionHelperBase):
    """
    Helper for managing owner sessions.
    """

    def __init__(self, table_name: Optional[str] = None, ddb_resource: Optional[Any] = None):
        """
        Initialize the owner session helper.

        Args:
            table_name (Optional[str]): DynamoDB table name for owner sessions.
            ddb_resource (Optional[Any]): boto3 resource (for mocking/testing).
        """
        super().__init__(table_name or os.environ.get("OWNER_SESSION_TABLE_NAME", "LostAndFound-OwnerSession"), ddb_resource=ddb_resource)

    def create_owner_session(self, owner_hash: str, duration_seconds: int = DEFAULT_OWNER_SESSION_DURATION, onetime: bool = False) -> OwnerSession:
        """
        Create a new owner session with a unique token and expiration.

        Args:
            owner_hash (str): Owner hash key.
            duration_seconds (int): Session duration in seconds (default: 1 hour).
            onetime (bool): If true, session is valid for one use only.
        Returns:
            OwnerSession: The created owner session object.
        Raises:
            SessionCreateError: If creation fails (database or validation error).
        """
        session_token = self.create_session_token()
        logger.debug(f"Generated session token: {session_token}, length: {len(session_token)})")
        current_time = current_unix_timestamp_utc()
        expires_at = current_time + duration_seconds
        session = OwnerSession(
            session_token=SessionToken(value=session_token),
            owner_hash=OwnerHash(value=owner_hash),
            created_at=Timestamp(value=current_time),
            expires_at=Timestamp(value=expires_at),
            onetime=onetime,
            invalidated_at=None,
        )
        try:
            item = session.model_dump()
            item["session_token"] = session.session_token.value
            item["owner_hash"] = session.owner_hash.value
            item["created_at"] = session.created_at.value
            item["expires_at"] = session.expires_at.value
            self.table.put_item(Item=item)
            return session
        except (ClientError, ValidationError) as e:
            raise SessionCreateError("Failed to create owner session.") from e
        except Exception as e:  #pylint: disable=broad-except # pragma: no cover
            raise SessionCreateError("Unexpected error during owner session creation.") from e

    def get_owner_session(self, session_token: str) -> Optional[OwnerSession]:
        """
        Retrieve and validate an owner session by its token.

        Args:
            session_token (str): Session token to retrieve.
        Returns:
            Optional[OwnerSession]: Validated owner session if found, else None.
        Raises:
            SessionRetrieveError: If retrieval or validation fails.
        """
        return self.get_session(session_token, OwnerSession)


# ------------------------
# Visitor Session Helper
# ------------------------

DEFAULT_VISITOR_SESSION_DURATION = 8 * 60 * 60  # 8 hours


class VisitorSessionHelper(SessionHelperBase):
    """
    Helper for managing visitor sessions.
    """

    def __init__(self, table_name: Optional[str] = None, ddb_resource: Optional[Any] = None):
        """
        Initialize the visitor session helper.

        Args:
            table_name (Optional[str]): DynamoDB table name for visitor sessions.
            ddb_resource (Optional[Any]): boto3 resource (for mocking/testing).
        """
        super().__init__(table_name or os.environ.get("VISITOR_SESSION_TABLE_NAME", "LostAndFound-VisitorSession"), ddb_resource=ddb_resource)

    def create_visitor_session(self, tag_code: str, duration_seconds: int = DEFAULT_VISITOR_SESSION_DURATION) -> VisitorSession:
        """
        Create a new visitor session with a unique token and expiration.

        Args:
            tag_code (str): Tag code associated with the session.
            duration_seconds (int): Session duration in seconds (default: 8 hours).
        Returns:
            VisitorSession: The created visitor session object.
        Raises:
            SessionCreateError: If creation fails (database or validation error).
        """
        session_token = self.create_session_token()
        current_time = current_unix_timestamp_utc()
        expires_at = current_time + duration_seconds
        session = VisitorSession(
            session_token=SessionToken(value=session_token),
            tag_code=TagCode(value=tag_code),
            created_at=Timestamp(value=current_time),
            expires_at=Timestamp(value=expires_at),
        )
        try:
            item = session.model_dump()
            item["session_token"] = session.session_token.value
            item["tag_code"] = session.tag_code.value
            item["created_at"] = session.created_at.value
            item["expires_at"] = session.expires_at.value
            self.table.put_item(Item=item)
            return session
        except (ClientError, ValidationError) as e:
            raise SessionCreateError("Failed to create visitor session.") from e
        except Exception as e:  #pylint: disable=broad-except # pragma: no cover
            raise SessionCreateError("Unexpected error during visitor session creation.") from e

    def get_visitor_session(self, session_token: str) -> Optional[VisitorSession]:
        """
        Retrieve and validate a visitor session by its token.

        Args:
            session_token (str): Session token to retrieve.
        Returns:
            Optional[VisitorSession]: Validated visitor session if found, else None.
        Raises:
            SessionRetrieveError: If retrieval or validation fails.
        """
        return self.get_session(session_token, VisitorSession)
