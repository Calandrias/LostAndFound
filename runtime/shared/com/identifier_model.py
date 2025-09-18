from pydantic import Field, BaseModel, ConfigDict, StrictStr, StrictInt
from typing import ClassVar


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class OwnerHash(BaseModel):
    """Hash for owner identifiers (must start with 'owner_')."""
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


class TagCode(BaseModel):
    """Field for public QR tag codes (must start with 'tag_')."""
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

class SessionToken(BaseModel):
    """Field for session tokens (must start with 'sessiontok_')."""
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

class Timestamp(BaseModel):
    """Unix timestamp (seconds since epoch)."""
    value: StrictInt = Field(
        ...,
        ge=0,
        le=4102444800,  # Year 2100
        description="Unix timestamp (seconds since epoch)",
    )

class PublicKey(BaseModel):
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
