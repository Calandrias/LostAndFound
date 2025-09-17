from importlib import import_module
from collections import OrderedDict
from pydantic import TypeAdapter, BaseModel
from pathlib import Path
import yaml
import sys

MODEL_SOURCES = {
    "APIResponseModel": "shared.api.response_model:APIResponseModel",
    "LoginChallengeRequest": "shared.api.owner.api_owner_model:LoginChallengeRequest",
    "LoginResponseRequest": "shared.api.owner.api_owner_model:LoginResponseRequest",
    "LoginResponseDataModel": "shared.api.owner.api_owner_model:LoginResponseDataModel",
}
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
SHARED_PATH = Path(__file__).parents[2] / "runtime"
sys.path.insert(0, str(SHARED_PATH))

all_schemas = OrderedDict()
global_defs = OrderedDict()
combined_schema = {}


def dictify(obj):
    # Rekursiv OrderedDict/Listen in normale dict/list konvertieren
    if isinstance(obj, OrderedDict):
        return {k: dictify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dictify(i) for i in obj]
    return dict(obj)


for name, import_path in MODEL_SOURCES.items():
    modulename, classname = import_path.split(":")
    module = import_module(modulename)
    model_class = getattr(module, classname)

    if isinstance(model_class, type) and issubclass(model_class, BaseModel):
        schema = model_class.model_json_schema()
    else:
        schema = TypeAdapter(model_class).json_schema()

    if "$defs" in schema:
        for def_key, def_val in schema["$defs"].items():
            if def_key not in global_defs:
                global_defs[def_key] = def_val
            elif global_defs[def_key] != def_val:
                print(f"Warning: Conflicting definition for {def_key}")

        del schema["$defs"]

    all_schemas[name] = schema
    print(f"Processed: {name}")

    combined_schema = {
        **all_schemas,
        "$defs": dictify(global_defs),
    }

with open(SCHEMA_DIR / "schemas.yaml", "w", encoding="UTF-8") as f:
    f.write("# This file is auto-generated from Pydantic models. Do not edit by hand!\n\n")
    yaml.dump(dictify(combined_schema), f, sort_keys=False)

print(f"Generated combined schema: {SCHEMA_DIR / 'schemas.yaml'}")
