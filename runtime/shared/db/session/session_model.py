""" Pydantic models for owner and visitor sessions."""
from pydantic import StrictBool, Field

from shared.com.identifier_model import (
    StrictModel,
    OwnerHash,
    SessionToken,
    TagCode,
    Timestamp,
)


class OwnerSession(StrictModel):
    """Model for owner session records in DynamoDB."""
    session_token: SessionToken
    owner_hash: OwnerHash
    created_at: Timestamp
    expires_at: Timestamp
    onetime: StrictBool = Field(default=False, description="If true, session is valid for one use only and will be deleted after retrieval")
    invalidated_at: Timestamp | None


class VisitorSession(StrictModel):
    """Model for visitor session records in DynamoDB."""
    session_token: SessionToken
    tag_code: TagCode
    created_at: Timestamp
    expires_at: Timestamp
