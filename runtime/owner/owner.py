import json
import secrets
import time
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from owner_store import OwnerStore
from owner_model import Owner, Status
from models import OwnerOnboardingRequest, OwnerOnboardingResponse

logger = Logger()
tracer = Tracer()

ddb = OwnerStore()  # Handles all table operations


def generate_entropy(length: int = 32) -> str:
    """Generate hex-encoded cryptographic entropy."""
    return secrets.token_hex(length)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info(f"Event: {json.dumps(event)}")

    try:
        if event.get("httpMethod") != "POST":
            return {"statusCode": 405, "body": json.dumps({"message": "Method Not Allowed"})}

        req = OwnerOnboardingRequest.parse_raw(event["body"])
        logger.append_keys(owner_hash=req.user_hash)

        # Check if Owner exists
        if ddb.get_owner(req.user_hash):
            return {"statusCode": 409, "body": json.dumps({"message": "Owner already exists"})}

        # Minimal salt (bcrypt salt, 22-char), random_entropy (hex, 32-64 chars)
        salt = secrets.token_urlsafe(16)[:22]  # bcrypt salt requirement (see model)
        random_entropy = generate_entropy(32)  # produces 64 hex chars
        session_token = generate_session_token(32)  # url token, for session

        owner = Owner(
            owner_hash=req.user_hash,
            salt=salt,
            password_hash=req.password_hash,
            public_key="",  # Not yet set!
            random_entropy=random_entropy,
            owner_encrypted_storage="",  # Not yet set!
            created_at=int(time.time()),
            status=Status.ONBOARDING)
        ddb.put_owner(owner)

        resp = OwnerOnboardingResponse(success=True, session_token=session_token, random_entropy=random_entropy)

        return {"statusCode": 201, "headers": {"Content-Type": "application/json"}, "body": resp.json()}

    except Exception as exc:
        logger.exception("Error during owner onboarding")
        return {"statusCode": 500, "body": json.dumps({"message": "Internal server error"})}
