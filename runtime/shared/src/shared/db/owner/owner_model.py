"""
Pydantic model for Owner data with validation.

All public classes and fields are fully typed and documented.
"""
from typing import ClassVar, Set
from enum import Enum
from pydantic import Field, StrictStr

from shared.com.identifier_model import StrictModel, OwnerHash, Timestamp, PublicKey


class State(str, Enum):
    """
    Enumeration for owner state.

    Values:
        ACTIVE: Owner is active.
        BLOCKED: Owner is blocked.
        ONBOARDING: Owner is onboarding.
        IN_DELETION: Owner is being deleted.
    """
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    ONBOARDING = 'onboarding'
    IN_DELETION = 'in_deletion'


class PasswordHash(StrictModel):
    """
    Pydantic model representing a password hash with validation.

    Attributes:
        value (StrictStr): bcrypt hash string, 60 chars, pattern enforced.
    """
    pattern: ClassVar[str] = r'^\$2[aby]\$[0-9]{2}\$[A-Za-z0-9./]{53}$'
    min_length: ClassVar[int] = 60
    max_length: ClassVar[int] = 60
    description: ClassVar[str] = "bcrypt hash string, 60 chars"

    value: StrictStr = Field(
        ...,
        pattern=pattern,
        min_length=min_length,
        max_length=max_length,
        description=description,
    )


class Owner(StrictModel):
    """
    Pydantic model representing an Owner with validation.

    Attributes:
        owner_hash (OwnerHash): Unique owner hash.
        password_hash (PasswordHash): Hashed password.
        public_key (PublicKey): Public key string.
        created_at (Timestamp): Creation timestamp (UTC, seconds).
        salt (StrictStr): bcrypt salt string.
        random_entropy (StrictStr): Random hex-encoded entropy (32-64 chars).
        owner_encrypted_storage (StrictStr): Base64-encoded encrypted storage for owner's private data.
        state (State): Owner account state flag.

    Class Attributes:
        ALLOWED_UPDATE_FIELDS (Set[str]): Fields allowed to be updated in DB.
    """
    owner_hash: OwnerHash
    password_hash: PasswordHash
    public_key: PublicKey
    created_at: Timestamp

    salt: StrictStr = Field(
        pattern=r'^[A-Za-z0-9./]{22}$',
        min_length=22,
        max_length=22,
        description="bcrypt salt string",
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

    state: State = Field(default=State.ONBOARDING, description="Owner account state flag: active, blocked, ongoing onboarding or pending deletion")

    ALLOWED_UPDATE_FIELDS: ClassVar[Set[str]] = {"state", "random_entropy", "public_key", "password_hash"}
