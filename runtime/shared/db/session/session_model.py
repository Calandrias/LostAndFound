""" Pydantic models for owner and visitor sessions."""
from pydantic import StrictStr, StrictInt, StrictBool, Field

from shared.com.identifier_model import (
    StrictModel,
    owner_hash_field,
    session_token_field,
    tag_code_field,
    timestamp_field,
)


class OwnerSession(StrictModel):
    """ Model for owner session records in DynamoDB."""
    session_token: StrictStr = session_token_field()
    owner_hash: StrictStr = owner_hash_field()
    created_at: StrictInt = timestamp_field(description="Unix timestamp (UTC) when owner session was started")
    expires_at: StrictInt = timestamp_field(description="Unix timestamp (UTC), used for DynamoDB TTL and privacy auto-cleanup")
    onetime: StrictBool = Field(default=False, description="If true, session is valid for one use only and will be deleted after retrieval")


class VisitorSession(StrictModel):
    """ Model for visitor session records in DynamoDB."""
    session_token: StrictStr = session_token_field()
    tag_code: StrictStr = tag_code_field()
    created_at: StrictInt = timestamp_field(description="Unix timestamp (UTC) when visitor session was started")
    expires_at: StrictInt = timestamp_field(description="Unix timestamp (UTC), used for DynamoDB TTL and privacy auto-cleanup")
