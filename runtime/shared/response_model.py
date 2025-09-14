from typing import Generic, Optional, TypeVar, Dict, Any
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class LambdaApiResponse(GenericModel, Generic[T]):
    success: bool = Field(..., description="Operation successful?")
    code: int = Field(..., description="HTTP status code")
    description: Optional[str] = Field(None, description="Optional status description/message")
    data: Optional[T] = Field(None, description="Payload (optional, generic)")
    messages: Optional[list[str]] = Field(None, description="Optional list of messages or hints")
    error: Optional[str] = Field(None, description="Optional error message")
