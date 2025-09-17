"""Utilities for shared layer."""

import json
import pathlib
from pydantic import BaseModel
from datetime import datetime, timezone


def dynamodb_decimal_to_int(obj: dict) -> dict:
    from decimal import Decimal
    out = {}
    for k, v in obj.items():
        if isinstance(v, Decimal):
            # pydantic does not like Decimal, convert to int
            v = int(v)
        out[k] = v
    return out


def dump_to_file(model: BaseModel, outfile=None):
    """
    Write the JSON schema of a Pydantic model to a file or stdout.
    - model: the Pydantic model class (not instance!)
    - outfile: path where to write schema (default: model.__name__.schema.json)
    """
    if outfile is None:
        outfile = f"{model.__name__}.schema.json"

    schema = model.model_json_schema()
    path = pathlib.Path(outfile)
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"JSON Schema written to {str(path.resolve())}")


def current_unix_timestamp_utc() -> int:
    """ Return the current Unix timestamp in UTC as an integer. """
    # time zone is always UTC in Unix timestamp
    return int(datetime.now(tz=timezone.utc).timestamp())
