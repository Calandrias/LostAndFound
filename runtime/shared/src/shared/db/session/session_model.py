"""
Pydantic models for owner and visitor sessions.

All public classes and fields are fully typed and documented.
"""
from pydantic import StrictBool, Field

from shared.com.identifier_model import (
    StrictModel,
    OwnerHash,
    SessionToken,
    TagCode,
    Timestamp,
)


class OwnerSession(StrictModel):
    """
    Model for owner session records in DynamoDB.

    Attributes:
        session_token (SessionToken): Unique session token for the owner session.
        owner_hash (OwnerHash): Owner hash key.
        created_at (Timestamp): Creation timestamp (UTC, seconds).
        expires_at (Timestamp): Expiry timestamp (UTC, seconds).
        onetime (StrictBool): If true, session is valid for one use only and will be deleted after retrieval.
        invalidated_at (Timestamp | None): Timestamp when session was invalidated, or None if still valid.
    """

    session_token: SessionToken
    owner_hash: OwnerHash
    created_at: Timestamp
    expires_at: Timestamp
    onetime: StrictBool = Field(default=False, description="If true, session is valid for one use only and will be deleted after retrieval")
    invalidated_at: Timestamp | None


class VisitorSession(StrictModel):
    """
    Model for visitor session records in DynamoDB.

    Attributes:
        session_token (SessionToken): Unique session token for the visitor session.
        tag_code (TagCode): Tag code associated with the session.
        created_at (Timestamp): Creation timestamp (UTC, seconds).
        expires_at (Timestamp): Expiry timestamp (UTC, seconds).
    """

    session_token: SessionToken
    tag_code: TagCode
    created_at: Timestamp
    expires_at: Timestamp
