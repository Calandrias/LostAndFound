"""Utilities for shared layer."""

from decimal import Decimal
from datetime import datetime, timezone


def dynamodb_decimal_to_int(obj: dict) -> dict:
    out = {}
    for k, v in obj.items():
        if isinstance(v, Decimal):
            # pydantic does not like Decimal, convert to int
            v = int(v)
        out[k] = v
    return out


def current_unix_timestamp_utc() -> int:
    """ Return the current Unix timestamp in UTC as an integer. """
    # time zone is always UTC in Unix timestamp
    return int(datetime.now(tz=timezone.utc).timestamp())
