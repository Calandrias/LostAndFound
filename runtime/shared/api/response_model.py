from typing import Optional, Dict, Literal, Generic, TypeVar
from pydantic import Field

from shared.com.identifier_model import StrictModel

T = TypeVar("T")


class ErrorModel(StrictModel):
    code: str  # Machine-readable error code, e.g., "not_found", "forbidden"
    message: str  # Human-readable error message


class ActionDetailModel(StrictModel):
    endpoint: str = Field(  # The API endpoint to perform this action
        ...,
        pattern=r"^/[^/h].*",
        description="API endpoint starting with / and not allowing external links",
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]  #
    rateLimit: Optional[int] = None  # Number of allowed attempts, if rate limited
    rateWindow: Optional[str] = None  # E.g. "60s" for rate window
    description: str = Field(
        min_length=0,
        max_length=4096,
        pattern=r'^[A-Za-z0-9+/= ]+\n?$',
        description="Action description to be uses in UI ",
    )
    # Extend with more properties as needed: labels, required params, UI hints, etc.


class MetaModel(StrictModel):
    version: Optional[str] = None  # API or response schema version for migrations
    ttlSeconds: Optional[int] = None  # Data validity in seconds (TTL), if relevant
    requestId: Optional[str] = None  # Optional trace/debug field for server logs


class APIResponseModel(Generic[T], StrictModel):
    success: bool = Field(..., description="True on successful request (HTTP 2xx)")
    error: Optional[ErrorModel] = Field(None, description="Error object if success == False")
    data: T  # data model will be refined in each domain
    allowedActions: Dict[str, ActionDetailModel] = Field(
        default_factory=dict,
        description="Contains only allowed actions as keys. May be empty if no actions allowed.",
    )
    meta: Optional[MetaModel] = None
