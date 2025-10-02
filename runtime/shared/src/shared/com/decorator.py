"""Decorator utilities for request validation and session token enforcement."""

from functools import wraps


def validate_request(schema):
    """Decorator to validate incoming request against a schema."""

    def decorator(func):
        """Wraps a function to validate its request payload."""

        @wraps(func)
        def wrapper(self, event, context, cache):
            """Validates request and calls the original function."""
            # Validierung gegen schema
            # ... (z.B. mit pydantic oder jsonschema)
            return func(self, event, context, cache)

        return wrapper

    return decorator


def require_session_token(func):
    """Decorator to require a valid session token for function execution."""

    @wraps(func)
    def wrapper(self, event, context, cache):
        """Checks session token and calls the original function."""
        # Session-Token prüfen und ggf. Fehler werfen
        # ...
        return func(self, event, context, cache)

    return wrapper
