from pathlib import Path
import json5
import json
from typing import Any, Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, StrictUndefined, UndefinedError, Template


class Config:
    """Config wrapper for project configuration and path handling."""

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict
        self.paths = config_dict.get('paths', {})
        self.lambdas = config_dict.get('lambdas', [])
        self.modelsources = config_dict.get('modelsources', {})

    @classmethod
    def load(cls, filename: str) -> 'Config':
        config_file = Path(__file__).parent / filename
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = json5.load(f)
            return cls(config_dict)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {config_file}") from e
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}") from e

    def get_path(self, key: str) -> Path:
        path_str = self.paths.get(key)
        if not path_str:
            raise KeyError(f"Path '{key}' not found in config['paths']")
        return Path(path_str)

    def get_lambda_config(self, tag_name: str) -> Optional[Dict[str, Any]]:
        for entry in self.lambdas:
            if entry.get('tag') == tag_name:
                return entry
        return None

    def get_all_lambdas(self) -> List[Dict[str, Any]]:
        return self.lambdas

    def get_modelsource(self, source_name: str) -> Optional[Dict[str, Any]]:
        return self.modelsources.get(source_name)

    def get_all_modelsources(self) -> List[Dict[str, Any]]:
        return list(self.modelsources.values())


def update_refs(obj: Any) -> None:
    """Recursively update $ref links to OpenAPI 3.x style."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                if v.startswith("#/$defs/"):
                    obj[k] = v.replace("#/$defs/", "#/components/schemas/")
                elif "/#/" in v:
                    # External file with local pointer: extract after last '#/'
                    target = v.split("#/")[-1]
                    obj[k] = f"#/components/schemas/{target}"
                # Fallback (e.g. ./schemas/..., but without #/)
                elif v.startswith("./schemas/"):
                    parts = v.split("#/components/schemas/")
                    if len(parts) == 2:
                        obj[k] = f"#/components/schemas/{parts[1]}"
            elif isinstance(v, str) and v.startswith("#/$defs/"):
                obj[k] = v.replace("#/$defs/", "#/components/schemas/")
            else:
                update_refs(v)
    elif isinstance(obj, list):
        for item in obj:
            update_refs(item)


def patch_const_to_enum(schema: Any):
    """Recursively replace 'const' nodes with equivalent 'enum' nodes for OpenAPI 3.0 compatibility."""
    if isinstance(schema, dict):
        if "const" in schema:
            schema["enum"] = [schema.pop("const")]
        for val in schema.values():
            patch_const_to_enum(val)
    elif isinstance(schema, list):
        for item in schema:
            patch_const_to_enum(item)


def fix_nullable_fields_deep(schema: Any):
    """Recursively patch nullable fields to conform to OpenAPI."""
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "nullable" and value is True:
                schema.clear()
                schema["type"] = ["null"]
            elif isinstance(value, (dict, list)):
                fix_nullable_fields_deep(value)
    elif isinstance(schema, list):
        for item in schema:
            fix_nullable_fields_deep(item)


def patch_anyof_nullables(schema: Any) -> None:
    """
    Convert 'anyOf': [A, {"type": "null"}] to A + 'nullable: true' recursively (OpenAPI 3.0).
    """
    if isinstance(schema, dict):
        for key, value in list(schema.items()):
            # Patch anyOf: [foo, {"type": "null"}]
            if key == "anyOf" and isinstance(value, list) and len(value) == 2:
                if isinstance(value[0], dict) and value[1] == {"type": "null"}:
                    for k, v in value[0].items():
                        schema[k] = v
                    schema["nullable"] = True
                    del schema["anyOf"]
                elif value[0] == {"type": "null"} and isinstance(value[1], dict):
                    for k, v in value[1].items():
                        schema[k] = v
                    schema["nullable"] = True
                    del schema["anyOf"]
            else:
                patch_anyof_nullables(value)
    elif isinstance(schema, list):
        for item in schema:
            patch_anyof_nullables(item)


def dictify(obj: Any) -> Any:
    """Recursively convert OrderedDict/list to dict/list."""
    from collections import OrderedDict
    if isinstance(obj, OrderedDict):
        return {k: dictify(v) for k, v in sorted(obj.items())}
    if isinstance(obj, dict):
        return {k: dictify(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [dictify(i) for i in obj]
    return obj


def extract_schema_refs(obj: Any, context: str = "") -> List[str]:
    """Extract all $ref references from request/response objects recursively."""
    refs: List[str] = []
    if isinstance(obj, dict):
        if "$ref" in obj:
            refs.append(obj["$ref"])
        elif "schema" in obj:
            if isinstance(obj["schema"], dict) and "$ref" in obj["schema"]:
                refs.append(obj["schema"]["$ref"])
            elif isinstance(obj["schema"], dict) and "oneOf" in obj["schema"]:
                for one_of_item in obj["schema"]["oneOf"]:
                    if isinstance(one_of_item, dict) and "$ref" in one_of_item:
                        refs.append(one_of_item["$ref"])
                if "discriminator" in obj["schema"]:
                    discriminator = obj["schema"]["discriminator"]
                    if "mapping" in discriminator:
                        for disc_key, disc_ref in discriminator["mapping"].items():
                            refs.append(disc_ref)
        for key, value in obj.items():
            refs.extend(extract_schema_refs(value, f"{context}.{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            refs.extend(extract_schema_refs(item, f"{context}[{i}]"))
    return refs


def validation_error_printer(ve: Any) -> None:
    """Enhanced error printer for Prance ValidationError."""
    message = None
    if hasattr(ve, 'message') and ve.message:
        message = ve.message
    elif hasattr(ve, 'args') and ve.args:
        message = str(ve.args[0])
    else:
        message = str(ve)

    error_dict = {
        "message": json.dumps(message, indent=2),
        "validator": getattr(ve, 'validator', None),
        "validator_value": getattr(ve, 'validator_value', None),
        "absolute_path": list(getattr(ve, 'absolute_path', [])),
        "instance": str(getattr(ve, 'instance', None))[:500] + "..." if len(str(getattr(ve, 'instance', None))) > 500 else str(getattr(ve, 'instance', None))
    }

    print(json.dumps(error_dict, indent=2, ensure_ascii=False))


def load_jinja_template(template_name: str, template_dir: str) -> Template:
    """Load a Jinja2 template from the given directory."""
    env = Environment(loader=FileSystemLoader(template_dir), undefined=StrictUndefined, autoescape=True)
    return env.get_template(template_name)


def render_jinja_template(template: Template, **kwargs) -> str:
    """Render a Jinja2 template with the provided variables."""
    return template.render(**kwargs)


def list_required_variables(template: Template) -> List[str]:
    """Return a list of all required variables for a Jinja2 template by rendering with dummy values."""
    dummy_vars: Dict[str, Any] = {}
    missing_vars: List[str] = []
    while True:
        try:
            template.render(**dummy_vars)
            break  # All variables found
        except UndefinedError as e:
            msg = str(e)
            var_name = msg.split("'")[1]
            if var_name not in missing_vars:
                missing_vars.append(var_name)
            dummy_vars[var_name] = 'DUMMY'
    return missing_vars
