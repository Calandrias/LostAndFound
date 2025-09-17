from typing import Literal, Optional
from pydantic import Field, StrictStr, StrictInt

from shared.com.identifier_model import StrictModel, timestamp_field, owner_hash_field
from shared.db.owner.owner_model import password_hash_field


class LoginChallengeRequest(StrictModel):
    mode: Literal["challenge"] = Field(..., description="Get a challenge")
    owner_hash: StrictStr = owner_hash_field()
    password_hash: StrictStr = password_hash_field()


class LoginResponseRequest(StrictModel):
    mode: Literal["response"] = Field(..., description="Respond to challenge")
    challenge_response: str


class LoginResponseDataModel(StrictModel):
    # Step 1: Sending challenge
    challenge: Optional[StrictStr] = Field(None, description="Challenge string the client must sign, only present if mode='challenge'")
    expires_at: StrictInt = timestamp_field()
    # Step 2: Returning a session token
    session_token: Optional[StrictStr] = Field(None, description="Session token to be used for all future authenticated requests, only set if mode='response'")
