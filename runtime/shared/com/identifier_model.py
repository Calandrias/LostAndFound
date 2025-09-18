from pydantic import Field, BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class StrRootModel(BaseModel):
    __root__: str

    def __str__(self):
        return self.__root__

    @property
    def value(self):
        return self.__root__

    def __eq__(self, other):
        if isinstance(other, StrRootModel):
            return self.__root__ == other.__root__
        if isinstance(other, str):
            return self.__root__ == other
        return NotImplemented

    def __hash__(self):
        return hash(self.__root__)


class IntRootModel(BaseModel):
    __root__: int

    def __int__(self):
        return self.__root__


class OwnerHash(StrRootModel):
    """Hash for owner identifiers (must start with 'owner_')."""
    __root__: str = Field(
        ...,
        min_length=49,
        max_length=49,
        pattern=r'^owner_[A-Za-z0-9_-]{43}$',
        description="owner_hash: 'owner_' + url-safe base64 (43 chars, e.g. SHA256-url-encoded hash)",
    )


class TagCode(StrRootModel):
    """Field for public QR tag codes (must start with 'tag_')."""
    __root__: str = Field(
        ...,
        min_length=32,
        max_length=64,
        pattern=r'tag_[A-Z0-9_-]{32,64}$',
        description="tag_code: 'tag_' + public code with 32 to 64 alphanumeric chars)",
    )


def tag_code_field(**kwargs):
    """Field for public QR tag codes (must start with 'tag_')."""
    prefix = "tag_"
    min_code = 8
    max_code = 64
    return Field(
        ...,
        min_length=min_code,
        max_length=max_code,
        pattern=rf'^{prefix}[A-Za-z0-9_-]{{{min_code - len(prefix)},{max_code - len(prefix)}}}$',
        description=f"tag_code: '{prefix}' + public code ({min_code - len(prefix)}-{max_code - len(prefix)} alphanumeric chars)",
        **kwargs,
    )


class SessionToken(StrRootModel):
    """Field for session tokens (must start with 'sessiontok_')."""
    __root__: str = Field(
        min_length=43,
        max_length=86,
        pattern=rf'^sessiontok_[A-Za-z0-9\-_]{43,86}$',
        description="session_token: 'sessiontok_' + url-safe base64 random value with 43 to 86 chars)",
    )


def timestamp_field(**kwargs):
    description = kwargs.pop("description", "Unix timestamp (seconds since epoch)")
    return Field(
        ...,
        ge=0,
        le=4102444800,  # Year 2100
        description=description,
        **kwargs,
    )
