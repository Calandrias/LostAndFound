from pydantic import BaseModel, Field, StrictStr, StrictInt, ConfigDict, validator
from enum import Enum


class Status(Enum):
    active = 'active'
    blocked = 'blocked'
    in_deletion = 'in_deletion'


class Owner(BaseModel):
    model_config = ConfigDict(extra='forbid')

    owner_hash: StrictStr = Field(
        pattern=r'^[A-Za-z0-9_-]{43}$',
        min_length=43,
        max_length=43,
        description="URL-safe base64 (43 chars, e.g. for SHA256-url-encoded hash) as unique pseudonymous ID",
    )
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
    created_at: StrictInt = Field(description="Unix timestamp when the owner was created")
    status: Status = Field(default=Status.active, description="Owner account status flag: active, blocked, or pending deletion")


if __name__ == "__main__":
    import modeldump
    modeldump.dump(Owner)
