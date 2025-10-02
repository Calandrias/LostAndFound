"""Identifier models for Lost & Found platform."""

from pydantic import Field, BaseModel, ConfigDict, StrictStr, StrictInt
from typing import ClassVar, Literal

from shared.minimal_registry import generic_model


class StrictModel(BaseModel):
    """Base model with strict validation for all fields."""
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class NoData(StrictModel):
    """Model representing an empty payload."""
    kind: Literal["no_data"] = "no_data"


@generic_model
class OwnerHash(BaseModel):
    """Model for owner hash identifier."""
    prefix: ClassVar[str] = "owner_"
    code_length: ClassVar[int] = 43
    pattern: ClassVar[str] = fr'^{prefix}[A-Za-z0-9_-]{{{code_length}}}$'
    value: str = Field(
        ...,
        min_length=len(prefix) + code_length,
        max_length=len(prefix) + code_length,
        pattern=pattern,
        description=f"owner_hash: '{prefix}' + url-safe base64 ({code_length} chars, e.g. SHA256-url-encoded hash)",
    )


@generic_model
class TagCode(BaseModel):
    """Model for tag code identifier."""
    prefix: ClassVar[str] = "tag_"
    min_code: ClassVar[int] = 32
    max_code: ClassVar[int] = 64
    pattern: ClassVar[str] = fr'^{prefix}[A-Z0-9_-]{{{min_code},{max_code}}}$'
    value: str = Field(
        ...,
        min_length=len(prefix) + min_code,
        max_length=len(prefix) + max_code,
        pattern=pattern,
        description=f"tag_code: '{prefix}' + public code with {min_code} to {max_code} alphanumeric chars",
    )


@generic_model
class SessionToken(BaseModel):
    """Model for session token identifier."""
    prefix: ClassVar[str] = "sessiontok_"
    min_length: ClassVar[int] = 43
    max_length: ClassVar[int] = 86
    pattern: ClassVar[str] = fr'^{prefix}[A-Za-z0-9\-_]{{{min_length},{max_length}}}$'
    value: str = Field(
        ...,
        min_length=len(prefix) + min_length,
        max_length=len(prefix) + max_length,
        pattern=pattern,
        description=f"session_token: '{prefix}' + url-safe base64 random value with {min_length} to {max_length} chars",
    )


@generic_model
class Timestamp(BaseModel):
    """Model for timestamp value."""
    value: StrictInt = Field(
        ...,
        ge=1735689600,  # 2025-01-01
        le=2556057599,  # 2050-12-31
        description="Unix timestamp (seconds since epoch) between 2025-01-01 and 2050-12-31",
    )


@generic_model
class PublicKey(BaseModel):
    """Model for public key value."""
    pattern: ClassVar[str] = r'^-----BEGIN PUBLIC KEY-----(.|\n)+-----END PUBLIC KEY-----\n?$'
    min_length: ClassVar[int] = 272
    max_length: ClassVar[int] = 800
    description: ClassVar[str] = "PEM encoded public key"

    value: StrictStr = Field(
        ...,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        description=description,
    )
