from typing import Optional, Dict, Literal, Annotated, Union
from pydantic import Field

from shared.minimal_registry import generic_model
from shared.com.identifier_model import StrictModel, NoData
from shared.api.owner.api_owner_model import OwnerResponseModel


@generic_model()
class ErrorModel(StrictModel):
    """Error details for failed API requests."""
    code: str = Field(..., description="Machine-readable error code, e.g., 'not_found', 'forbidden'.")
    message: str = Field(..., description="Human-readable error message.")


@generic_model()
class ActionDetailModel(StrictModel):
    """Details about allowed actions for the client after a response."""
    endpoint: str = Field(..., pattern=r"^/[^/h].*", description="API endpoint starting with / and not allowing external links.")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(..., description="HTTP method for the action.")
    rateLimit: Optional[int] = Field(None, description="Number of allowed attempts, if rate limited.")
    rateWindow: Optional[str] = Field(None, description="Rate window, e.g. '60s'.")
    description: str = Field(min_length=0, max_length=4096, pattern=r'^[A-Za-z0-9+/= ]+\n?$', description="Action description to be used in UI.")
    # Extend with more properties as needed: labels, required params, UI hints, etc.


@generic_model()
class MetaModel(StrictModel):
    """Metadata for API responses, e.g. version, TTL, requestId, and rate limiting."""
    version: Optional[str] = Field(None, description="API or response schema version for migrations.")
    ttlSeconds: Optional[int] = Field(None, description="Data validity in seconds (TTL), if relevant.")
    requestId: Optional[str] = Field(None, description="Optional trace/debug field for server logs.")
    rateLimit: Optional[int] = Field(None, description="Maximum number of requests allowed in the current window.")
    rateLimitRemaining: Optional[int] = Field(None, description="Number of requests remaining in the current window.")
    rateLimitReset: Optional[int] = Field(None, description="Time when the rate limit window resets (Unix timestamp).")


@generic_model()
class APIResponseModel(StrictModel):
    """Standard API response wrapper for all endpoints."""
    success: bool = Field(..., description="True on successful request (HTTP 2xx).")
    error: Optional[ErrorModel] = Field(None, description="Error object if success == False.")
    data: Annotated[Union[OwnerResponseModel, NoData], Field(discriminator="kind", description="Response data, discriminated by 'kind'.")]
    allowedActions: Dict[str, ActionDetailModel] = Field(default_factory=dict, description="Contains only allowed actions as keys. May be empty if no actions allowed.")
    meta: Optional[MetaModel] = Field(None, description="Optional metadata for the response.")
