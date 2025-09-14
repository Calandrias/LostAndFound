"""Pydantic model for Owner data with validation."""
from typing import ClassVar, Set
from enum import Enum
from pydantic import BaseModel, Field, StrictStr, StrictInt, ConfigDict

from shared.identifier_model import owner_hash_field


class Status(str, Enum):
    """Enumeration for owner status."""
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    ONBOARDING = 'onboarding'
    IN_DELETION = 'in_deletion'


class Owner(BaseModel):
    """Pydantic model representing an Owner with validation."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    owner_hash: StrictStr = owner_hash_field()

    salt: StrictStr = Field(
        pattern=r'^[A-Za-z0-9./]{22}$',
        min_length=22,
        max_length=22,
        description="bcrypt salt string",
    )
    password_hash: StrictStr = Field(
        pattern=r'^\$2[aby]\$[0-9]{2}\$[A-Za-z0-9./]{53}$',
        min_length=60,
        max_length=60,
        description="bcrypt hash string, 60 chars",
    )
    public_key: StrictStr = Field(
        min_length=272,
        max_length=800,
        pattern=r'^-----BEGIN PUBLIC KEY-----(.|\n)+-----END PUBLIC KEY-----\n?$',
        description="PEM encoded public key",
    )
    random_entropy: StrictStr = Field(
        min_length=32,
        max_length=64,
        pattern=r'^[A-Fa-f0-9]{32,64}$',
        description="Random hex-encoded entropy (32-64 chars, for cryptographic purposes)",
    )

    owner_encrypted_storage: StrictStr = Field(
        min_length=0,
        max_length=4096,
        pattern=r'^[A-Za-z0-9+/=]+\n?$',
        description="Base64-encoded encrypted storage for owner's private data",
    )
    created_at: StrictInt = Field(description="Unix timestamp when the owner was created")
    status: Status = Field(default=Status.ONBOARDING, description="Owner account status flag: active, blocked, ongoing onboarding or pending deletion")

    ALLOWED_UPDATE_FIELDS: ClassVar[Set[str]] = {"status", "random_entropy", "public_key", "password_hash"}
