# runtime/shared/com/decorators.py
from functools import wraps


def validate_request(schema):

    def decorator(func):

        @wraps(func)
        def wrapper(self, event, context, cache):
            # Validierung gegen schema
            # ... (z.B. mit pydantic oder jsonschema)
            return func(self, event, context, cache)

        return wrapper

    return decorator


def require_session_token(func):

    @wraps(func)
    def wrapper(self, event, context, cache):
        # Session-Token prüfen und ggf. Fehler werfen
        # ...
        return func(self, event, context, cache)

    return wrapper
