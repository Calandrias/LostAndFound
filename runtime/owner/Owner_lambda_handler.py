# owner_lambda_handler.py
"""Auto-generated Lmabda Hander for for Owner"""

from Owner_handler_impl import OwnerHandler
from shared.api.response_model import APIResponseModel, ErrorModel
from shared.com.logging_utils import ProjectLogger

handler_instance = OwnerHandler()
logger = ProjectLogger("OwnerLambda").get_logger()

def _extract_method_path(event):
    # REST API v1
    if "httpMethod" in event and "path" in event:
        return event["httpMethod"], event["path"]
    # HTTP API v2
    rc = event.get("requestContext", {}).get("http", {})
    method = rc.get("method")
    path = event.get("rawPath") or rc.get("path")
    return method, path

routes = {
    ("DELETE", "/v1/owner"): handler_instance.owner_delete_account,
    ("GET", "/v1/owner"): handler_instance.owner_get,
    ("POST", "/v1/owner/login"): handler_instance.owner_login,
    ("POST", "/v1/owner/logout"): handler_instance.owner_logout,
    ("POST", "/v1/owner/onboarding"): handler_instance.owner_onboarding,
    ("POST", "/v1/owner/refresh"): handler_instance.owner_session_refresh,
    ("DELETE", "/v1/owner/storage"): handler_instance.owner_storage_delete,
    ("GET", "/v1/owner/storage"): handler_instance.owner_storage_get,
    ("POST", "/v1/owner/storage"): handler_instance.owner_storage
}


# Simple in-memory cache (lives as long as Lambda is warm)
cache = {}

# pylint: disable=too-many-branches
def lambda_handler(event, context):
    method, path = _extract_method_path(event)
    key = (method, path, event.get("queryStringParameters"))
    route = routes.get((method, path))
    if route is None:
        return {"statusCode": 404, "body": "Endpoint not found"}
    try:
        response = route(event, context, cache)
        # Validate response type
        if not isinstance(response, APIResponseModel):
            logger.error(f"Handler for {method} {path} did not return APIResponseModel. Got: {type(response)} | Value: {response}")
            error = ErrorModel(code="internal_error", message="Handler did not return a valid APIResponseModel.")
            return APIResponseModel(success=False, error=error, data=None, allowedActions={}, meta=None).model_dump()
        return response.model_dump() if hasattr(response, 'model_dump') else response
    except Exception as exc:  # pylint: disable=broad-except # Catch all to prevent Lambda crash
        logger.exception(f"Exception in handler for {method} {path}: {exc}")
        error = ErrorModel(code="internal_error", message="An unexpected error occurred.")
        return APIResponseModel(success=False, error=error, data=None, allowedActions={}, meta=None).model_dump()