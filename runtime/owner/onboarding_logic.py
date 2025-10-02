"""
Business logic for Owner onboarding (registration) in the Lost & Found platform.

This module provides a function to handle the onboarding process, including validation, salt/entropy generation, and database write.
"""
import json
import secrets
import time
from typing import Any, Optional, Dict
from shared.db.owner.owner_store import OwnerStore
from shared.db.owner.owner_model import Owner, State
from shared.api.owner.api_owner_model import OnboardingRequest, OnboardingInitResponse

ddb = OwnerStore()


def generate_entropy(length: int = 32) -> str:
    """Generate hex-encoded cryptographic entropy."""
    return secrets.token_hex(length)


def onboarding_logic(event: Dict[str, Any], logger: Any, cache: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Handle the onboarding (registration) of a new Owner.

    Args:
        event (Dict[str, Any]): The Lambda event (API Gateway proxy event).
        logger (Any): Logger instance for logging (must support .info/.exception/.append_keys).
        cache (Optional[Dict[str, Any]]): Optional cache dict for dependency injection/testing. (unused, required for interface)
    Returns:
        Dict[str, Any]: API Gateway-compatible response dict.
    """

    logger.info(f"Event: {json.dumps(event)}")
    # touch cache to avoid unused argument pylint warning
    _ = cache
    try:
        if event.get("httpMethod") != "POST":
            return {"statusCode": 405, "body": json.dumps({"message": "Method Not Allowed"})}

        req = OnboardingRequest.model_validate_json(event["body"])
        logger.append_keys(owner_hash=req.user_hash)

        # Check if Owner exists
        if ddb.get_owner(req.user_hash):
            return {"statusCode": 409, "body": json.dumps({"message": "Owner already exists"})}

        salt = secrets.token_urlsafe(16)[:22]  # bcrypt salt requirement (see model)
        random_entropy = generate_entropy(32)  # produces 64 hex chars
        #session_token generation should be handled by session logic
        session_token = secrets.token_urlsafe(32)

        owner = Owner(
            owner_hash=req.user_hash,
            salt=salt,
            password_hash=req.password_hash,
            public_key="",  # Not yet set!
            random_entropy=random_entropy,
            owner_encrypted_storage="",  # Not yet set!
            created_at=int(time.time()),
            status=State.ONBOARDING)
        ddb.put_owner(owner)

        resp = OnboardingInitResponse(success=True, session_token=session_token, random_entropy=random_entropy)
        return {"statusCode": 201, "headers": {"Content-Type": "application/json"}, "body": resp.json()}

    except (ValueError, KeyError, TypeError) as exc:
        logger.exception(f"Known error during owner onboarding: {type(exc).__name__}: {exc}")
        return {"statusCode": 400, "body": json.dumps({"message": "Bad request"})}
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # unexpected error
        logger.exception("Unexpected error during owner onboarding")
        return {"statusCode": 500, "body": json.dumps({"message": "Internal server error"})}
