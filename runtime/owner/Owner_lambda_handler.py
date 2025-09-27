# lambda_handler.py

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
    ("DELETE", "/v1/owner"): handler_instance.ownerDeleteAccount,
    ("GET", "/v1/owner"): handler_instance.ownerGet,
    ("POST", "/v1/owner/login"): handler_instance.ownerLogin,
    ("POST", "/v1/owner/logout"): handler_instance.ownerLogout,
    ("POST", "/v1/owner/onboarding"): handler_instance.ownerOnboarding,
    ("POST", "/v1/owner/refresh"): handler_instance.ownerSessionRefresh,
    ("DELETE", "/v1/owner/storage"): handler_instance.ownerStorageDelete,
    ("GET", "/v1/owner/storage"): handler_instance.ownerStorageGet,
    ("POST", "/v1/owner/storage"): handler_instance.ownerStorage
}


# Simple in-memory cache (lives as long as Lambda is warm)
cache = {}

def lambda_handler(event, context):
    method, path = _extract_method_path(event)
    key = (method, path, event.get("queryStringParameters"))
    route = routes.get((method, path))
    if route is None:
        return {"statusCode": 404, "body": "Endpoint not found"}
    if method == "GET":
        cached = _cache_get(key)
    if cached is not None:
        return cached
    
    response = route(event, context, cache)
    if method == "GET" and isinstance(response, dict) and response.get("statusCode") == 200:
        _cache_put(key, response)
    return response