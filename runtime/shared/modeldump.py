import json
import sys
import pathlib


def dump(model, outfile=None):
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
