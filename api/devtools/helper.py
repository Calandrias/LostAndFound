from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict
import json5
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template, meta


class Config:
    """Config wrapper for project configuration and path handling."""

    def __init__(self, config_dict: Dict[str, Any]):
        self._config = config_dict
        self.paths = config_dict.get('paths', {})
        self.lambdas = config_dict.get('lambdas', [])
        self.modelsources = config_dict.get('modelsources', {})

    @classmethod
    def load(cls, filename: str) -> 'Config':
        """Load config from JSON5 file."""
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
        """Get Path by key from paths config."""

        path_str = self.paths.get(key)
        if not path_str:
            raise KeyError(f"Path '{key}' not found in config['paths']")
        return Path(path_str)

    def get_lambda_functions(self) -> List[Dict[str, Any]]:
        """ Get List of all lambda functions from config """
        return self.lambdas.get('functions', [])

    def get_lambda_generic_config(self) -> Dict[str, Any]:
        """Get generic config for lambda functions"""
        return self.lambdas.get('generic', {})

    def get_lambda_function_by_name(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get single lambda function by tag_name"""
        all_funcs = self.get_lambda_functions() or {}
        for func in all_funcs:
            if func.get("tag_name") == tag_name:
                return func.copy()
        return None

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
        for key in list(schema.keys()):
            if key not in schema:
                continue

            value = schema[key]

            if key == "nullable" and value is True:
                schema.clear()
                schema["type"] = "object"
                schema["nullable"] = True
                continue

            if isinstance(value, (dict, list)):
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
        schema = obj.get("schema")
        if isinstance(schema, dict):
            if "$ref" in schema:
                refs.append(schema["$ref"])
            for one_of_item in schema.get("oneOf", []):
                if isinstance(one_of_item, dict) and "$ref" in one_of_item:
                    refs.append(one_of_item["$ref"])
            discriminator = schema.get("discriminator", {})
            for disc_ref in discriminator.get("mapping", {}).values():
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


def to_snake_case(value):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', value).lower()


def load_jinja_template(template_name: str, template_dir: str) -> Tuple[Template, dict]:
    """Load a Jinja2 template from the given directory and return Template + expected variables dict."""
    env = Environment(loader=FileSystemLoader(template_dir), undefined=StrictUndefined, autoescape=True)
    env.filters['snake_case'] = to_snake_case
    template: Template = env.get_template(template_name)
    expected_vars = {}
    if env.loader:
        template_source = env.loader.get_source(env, template_name)[0]
        ast = env.parse(template_source)
        variables = meta.find_undeclared_variables(ast)
        expected_vars = {var: None for var in variables}
    return template, expected_vars


def render_jinja_template(template: Template, **kwargs) -> str:
    """Render a Jinja2 template with the provided variables."""
    return template.render(**kwargs)


def patch_schema_all(schema_dict: Any) -> Any:
    """
    Call all patch functions on the schema dict to ensure OpenAPI 3.x compatibility.
    """
    patch_const_to_enum(schema_dict)
    update_refs(schema_dict)
    fix_nullable_fields_deep(schema_dict)
    patch_anyof_nullables(schema_dict)
    return dictify(schema_dict)
