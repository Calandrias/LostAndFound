"""Pydantic model for Owner data with validation."""
from typing import ClassVar, Set
from enum import Enum
from pydantic import Field, StrictStr, StrictInt

from shared.com.identifier_model import StrictModel, owner_hash_field, timestamp_field


class Status(str, Enum):
    """Enumeration for owner status."""
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    ONBOARDING = 'onboarding'
    IN_DELETION = 'in_deletion'


def password_hash_field(**kwargs) -> StrictStr:
    temp: StrictStr = Field(
        pattern=r'^\$2[aby]\$[0-9]{2}\$[A-Za-z0-9./]{53}$',
        min_length=60,
        max_length=60,
        description="bcrypt hash string, 60 chars",
        **kwargs,
    )
    return temp


class Owner(StrictModel):
    """Pydantic model representing an Owner with validation."""
    owner_hash: StrictStr = owner_hash_field()
    password_hash: StrictStr = password_hash_field()

    salt: StrictStr = Field(
        pattern=r'^[A-Za-z0-9./]{22}$',
        min_length=22,
        max_length=22,
        description="bcrypt salt string",
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
    created_at: StrictInt = timestamp_field()
    status: Status = Field(default=Status.ONBOARDING, description="Owner account status flag: active, blocked, ongoing onboarding or pending deletion")

    ALLOWED_UPDATE_FIELDS: ClassVar[Set[str]] = {"status", "random_entropy", "public_key", "password_hash"}
