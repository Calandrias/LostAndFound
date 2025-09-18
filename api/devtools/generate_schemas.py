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
    "Owner": "shared.db.owner.owner_model:Owner",
    "OwnerSession": "shared.db.session.session_model:OwnerSession",
    "VisitorSession": "shared.db.session.session_model:VisitorSession",
    "PasswordHash": "shared.db.owner.owner_model:PasswordHash",
    #"OwnerHash": "shared.com.identifier_model:OwnerHash",
    #"TagCode": "shared.com.identifier_model:TagCode",
    #"SessionToken": "shared.com.identifier_model:SessionToken",
    #"Timestamp": "shared.com.identifier_model:Timestamp",
    #"PublicKey": "shared.com.identifier_model:PublicKey",
}
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"
SHARED_PATH = Path(__file__).parents[2] / "runtime"
sys.path.insert(0, str(SHARED_PATH))

all_schemas = OrderedDict()
global_defs = OrderedDict()
combined_schema = {}


def dictify(obj):
    # Recursively convert OrderedDict/list to dict/list
    if isinstance(obj, OrderedDict):
        return {k: dictify(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [dictify(i) for i in obj]
    return obj


def update_refs(obj):
    """Recursively update $ref links to OpenAPI 3.x style."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                obj[k] = v.replace("#/$defs/", "#/components/schemas/")
            else:
                update_refs(v)
    elif isinstance(obj, list):
        for item in obj:
            update_refs(item)


def safe_import(modulename, classname):
    try:
        module = import_module(modulename)
        model_class = getattr(module, classname)
        return model_class
    except Exception as e:
        print(f"Error importing {modulename}:{classname} -> {e}")
        return None

for name, import_path in MODEL_SOURCES.items():
    modulename, classname = import_path.split(":")
    model_class = safe_import(modulename, classname)
    if model_class is None:
        continue

    try:
        if isinstance(model_class, type) and issubclass(model_class, BaseModel):
            schema = model_class.model_json_schema()
        else:
            schema = TypeAdapter(model_class).json_schema()
    except Exception as e:
        print(f"Error generating schema for {name}: {e}")
        continue

    if "$defs" in schema:
        for def_key, def_val in schema["$defs"].items():
            if def_key not in global_defs:
                global_defs[def_key] = def_val
            elif global_defs[def_key] != def_val:
                print(f"Warning: Conflicting definition for {def_key}")
        del schema["$defs"]

    update_refs(schema)
    global_defs[name] = schema
    print(f"Processed: {name}")

combined_schema = {
    "components": {"schemas": dictify(global_defs)},
}

try:
    with open(SCHEMA_DIR / "schemas.yaml", "w", encoding="UTF-8") as f:
        f.write("# This file is auto-generated from Pydantic models. Do not edit by hand!\n\n")
        yaml.dump(dictify(combined_schema), f, sort_keys=False)
    print(f"Generated combined schema: {SCHEMA_DIR / 'schemas.yaml'}")
except Exception as e:
    print(f"Error writing schema file: {e}")
