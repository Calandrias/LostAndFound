# owner_lambda_handler.py
"""Auto-generated Lmabda Hander for for Owner"""

from Owner_handler_impl import OwnerHandler

handler_instance = OwnerHandler()


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

def lambda_handler(event, context):
    method, path = _extract_method_path(event)
    key = (method, path, event.get("queryStringParameters"))
    route = routes.get((method, path))
    if route is None:
        return {"statusCode": 404, "body": "Endpoint not found"}
  
    return response

