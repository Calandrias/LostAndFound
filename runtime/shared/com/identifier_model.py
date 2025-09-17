from pydantic import Field, BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


from pydantic import Field, BaseModel


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


class OwnerHash(StrRootModel):
    """Hash for owner identifiers (must start with 'owner_')."""
    __root__: str = Field(
        ...,
        min_length=49,
        max_length=49,
        pattern=r'^owner_[A-Za-z0-9_-]{43}$',
        description="owner_hash: 'owner_' + url-safe base64 (43 chars, e.g. SHA256-url-encoded hash)",
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


def session_token_field(**kwargs):
    """Field for session tokens (must start with 'sessiontok_')."""
    prefix = "sessiontok_"
    min_len = 43
    max_len = 86
    prefix_len = len(prefix)
    return Field(
        ...,
        min_length=min_len,
        max_length=max_len,
        pattern=rf'^{prefix}[A-Za-z0-9\-_]{{{min_len - prefix_len},{max_len - prefix_len}}}$',
        description=f"session_token: '{prefix}' + url-safe base64 random value ({min_len - prefix_len}-{max_len - prefix_len} chars)",
        **kwargs,
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
