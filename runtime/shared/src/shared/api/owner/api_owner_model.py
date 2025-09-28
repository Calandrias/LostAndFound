"""Definition of Request and Response models for Owner interactions"""
from typing import Literal, Annotated, Union
from pydantic import Field, StrictStr

from shared.minimal_registry import owner_model
from shared.com.identifier_model import StrictModel, OwnerHash, Timestamp, PublicKey, NoData
from shared.db.owner.owner_model import PasswordHash

# pylint: disable=too-few-public-methods
# Pydantic models are fine without public methods


# Onboarding Flow Models
@owner_model
class OnboardingInitRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["onboarding_init"] = "onboarding_init"
    owner_hash: OwnerHash
    password_hash: PasswordHash


@owner_model
class OnboardingPublicKeyRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["onboarding_public_key"] = "onboarding_public_key"
    public_key: PublicKey = Field(..., description="Owner's public key in PEM format")


@owner_model(req_res="request")
class OnboardingRequest(StrictModel):
    """Combined Request Model"""
    data: Annotated[Union[OnboardingInitRequest, OnboardingPublicKeyRequest], Field(discriminator="kind")]


@owner_model(req_res="response")
class OnboardingInitResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["onboarding_init"] = "onboarding_init"
    random_entropy: StrictStr = Field(..., description="Random entropy for cryptographic purposes")
    expires_at: Timestamp = Field(..., description="Expiration time of the session token")


@owner_model(req_res="response")
class OnboardingPublicKeyResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["onboarding_public_key"] = "onboarding_public_key"
    created_at: Timestamp = Field(..., description="Timestamp when the owner account was created")


# Login Flow Models
@owner_model()
class LoginChallengeRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["login_challenge"] = "login_challenge"
    owner_hash: OwnerHash
    password_hash: PasswordHash


@owner_model()
class LoginResponseRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["login_response"] = "login_response"
    challenge_response: str


@owner_model(req_res="request")
class LoginRequest(StrictModel):
    """Combined Request Model"""
    data: Annotated[Union[LoginChallengeRequest, LoginResponseRequest], Field(discriminator="kind")]


@owner_model(req_res="response")
class LoginChallengeResponseDataModel(StrictModel):
    """Partial Response Model"""
    kind: Literal["login_challenge"] = "login_challenge"
    challenge: StrictStr = Field(..., description="Challenge string the client must sign")
    expires_at: Timestamp = Field(..., description="Expiration time of the challenge and session token")


@owner_model(req_res="response")
class LoginSessionResponseDataModel(StrictModel):
    """Partial Response Model"""
    kind: Literal["login_response"] = "login_response"
    expires_at: Timestamp = Field(..., description="Expiration time of the session token")


# Delete Owner Account Flow


@owner_model
class DeleteOwnerChallengeRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["delete_owner_challange"] = "delete_owner_challange"
    owner_hash: OwnerHash


@owner_model
class DeleteOwnerConfirmRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["delete_owner_confirm"] = "delete_owner_confirm"
    confirmation_text: StrictStr = Field(..., description="User must type 'DELETE-OWNER' to confirm")


@owner_model(req_res="request")
class DeleteOwnerRequest(StrictModel):
    """Combined Request Model"""
    data: Annotated[Union[DeleteOwnerChallengeRequest, DeleteOwnerConfirmRequest], Field(discriminator="kind")]


@owner_model(req_res="response")
class DeleteOwnerChallengeResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["delete_owner_challenge"] = "delete_owner_challenge"
    challenge_text: StrictStr = Field(..., description="Instruction: Type e.g 'DELETE-OWNER' to confirm account deletion")
    expires_at: Timestamp = Field(..., description="Expiration time of the challenge")


@owner_model(req_res="response")
class DeleteOwnerConfirmResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["delete_owner_confirm"] = "delete_owner_confirm"
    deleted: bool = Field(..., description="True if account was deleted")


# Session flow
@owner_model(req_res="request")
class SessionRefreshRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["session_refresh"] = "session_refresh"


@owner_model(req_res="response")
class SessionRefreshResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["session_refresh"] = "session_refresh"
    expires_at: Timestamp = Field(..., description="New expiration time of the refreshed session token")


# Owner pivate storage flow
@owner_model(req_res="request")
class OwnerStorageWriteRequest(StrictModel):
    """Request Model"""
    encrypted_storage: StrictStr = Field(..., description="Base64-encoded, optionally gzip-compressed, encrypted private data")


@owner_model
class OwnerStorageDeleteChallengeRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["storage_delete_challenge"] = "storage_delete_challenge"
    owner_hash: OwnerHash


@owner_model
class OwnerStorageDeleteConfirmRequest(StrictModel):
    """Partial Request Model"""
    kind: Literal["storage_delete_confirm"] = "storage_delete_confirm"
    confirmation_text: StrictStr = Field(..., description="User must type e.g. 'DELETE-STORAGE' to confirm")


@owner_model(req_res="request")
class OwnerStorageDeleteRequest(StrictModel):
    """Combined Request Model"""
    data: Annotated[Union[OwnerStorageDeleteChallengeRequest, OwnerStorageDeleteConfirmRequest], Field(discriminator="kind")]


@owner_model(req_res="response")
class OwnerStorageResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["owner_storage"] = "owner_storage"
    encrypted_storage: StrictStr = Field(..., description="Base64-encoded, optionally gzip-compressed, encrypted private data")
    updated_at: Timestamp = Field(..., description="Timestamp of last update")


@owner_model(req_res="response")
class OwnerStorageDeleteChallangeResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["storage_delete_challenge"] = "storage_delete_challenge"
    challenge_text: StrictStr = Field(..., description="Instruction: Type e.g 'DELETE-STORAGE' to confirm account deletion")
    expires_at: Timestamp = Field(..., description="Expiration time of the challenge")


@owner_model(req_res="response")
class OwnerStorageDeleteConfirmResponse(StrictModel):
    """Partial Response Model"""
    kind: Literal["storage_delete_confirm"] = "storage_delete_confirm"
    deleted: bool = Field(..., description="True if storage was deleted")


# Owner Response Wrapper
class OwnerResponseModel(StrictModel):
    """Combinded Owner Response Model"""
    kind: Literal["owner_response"] = "owner_response"
    data: Annotated[Union[
        LoginChallengeResponseDataModel,
        LoginSessionResponseDataModel,
        OnboardingInitResponse,
        OnboardingPublicKeyResponse,
        DeleteOwnerChallengeResponse,
        DeleteOwnerConfirmResponse,
        SessionRefreshResponse,
        OwnerStorageResponse,
        OwnerStorageDeleteChallangeResponse,
        OwnerStorageDeleteConfirmResponse,
        NoData,
    ],
                    Field(discriminator="kind")]
