"""
Helper utilities and configuration loader for devtools and code generation scripts.

Provides the Config class for project configuration, path handling, and helpers for schema and template patching.
All functions are documented for clarity and maintainability.
"""

from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict
import json5
from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template, meta


class Config:
    """
    Config wrapper for project configuration and path handling.

    Provides methods to load config from JSON5, resolve paths, and access lambda/model sources.
    """

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize Config with a config dictionary.

        Args:
            config_dict (Dict[str, Any]): The configuration dictionary loaded from file.
        """
        self._config = config_dict
        self.paths = config_dict.get('paths', {})
        self.lambdas = config_dict.get('lambdas', [])
        self.modelsources = config_dict.get('modelsources', {})

    @classmethod
    def load(cls, filename: str) -> 'Config':
        """
        Load config from a JSON5 file.

        Args:
            filename (str): The filename of the config file (relative to this script).
        Returns:
            Config: Loaded Config instance.
        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be parsed.
        """
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
        """
        Get a Path object by key from the config's paths section.

        Args:
            key (str): The key in the paths config.
        Returns:
            Path: The resolved path.
        Raises:
            KeyError: If the key is not found in config['paths'].
        """

        path_str = self.paths.get(key)
        if not path_str:
            raise KeyError(f"Path '{key}' not found in config['paths']")
        return Path(path_str)

    def get_lambda_functions(self) -> List[Dict[str, Any]]:
        """
        Get a list of all lambda functions from config.

        Returns:
            List[Dict[str, Any]]: List of lambda function configs.
        """
        return self.lambdas.get('functions', [])

    def get_lambda_generic_config(self) -> Dict[str, Any]:
        """
        Get the generic config for lambda functions.

        Returns:
            Dict[str, Any]: Generic lambda config.
        """
        return self.lambdas.get('generic', {})

    def get_lambda_function_by_name(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a single lambda function config by tag_name.

        Args:
            tag_name (str): The tag name of the lambda function.
        Returns:
            Optional[Dict[str, Any]]: The lambda function config, or None if not found.
        """
        all_funcs = self.get_lambda_functions() or {}
        for func in all_funcs:
            if func.get("tag_name") == tag_name:
                return func.copy()
        return None

    def get_modelsource(self, source_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a model source config by name.

        Args:
            source_name (str): The name of the model source.
        Returns:
            Optional[Dict[str, Any]]: The model source config, or None if not found.
        """
        return self.modelsources.get(source_name)

    def get_all_modelsources(self) -> List[Dict[str, Any]]:
        """
        Get all model source configs as a list.

        Returns:
            List[Dict[str, Any]]: All model source configs.
        """
        return list(self.modelsources.values())


def update_refs(obj: Any) -> None:
    """
    Recursively update $ref links in a schema object to OpenAPI 3.x style.

    Args:
        obj (Any): The schema object (dict or list) to update in-place.
    """
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
    """
    Recursively replace 'const' nodes with equivalent 'enum' nodes for OpenAPI 3.0 compatibility.

    Args:
        schema (Any): The schema object to patch.
    """
    if isinstance(schema, dict):
        if "const" in schema:
            schema["enum"] = [schema.pop("const")]
        for val in schema.values():
            patch_const_to_enum(val)
    elif isinstance(schema, list):
        for item in schema:
            patch_const_to_enum(item)


def fix_nullable_fields_deep(schema: Any):
    """
    Recursively patch nullable fields to conform to OpenAPI.

    Args:
        schema (Any): The schema object to patch.
    """
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

    Args:
        schema (Any): The schema object to patch.
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
    """
    Recursively convert OrderedDict/list to dict/list.

    Args:
        obj (Any): The object to convert.
    Returns:
        Any: The converted object.
    """
    if isinstance(obj, OrderedDict):
        return {k: dictify(v) for k, v in sorted(obj.items())}
    if isinstance(obj, dict):
        return {k: dictify(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [dictify(i) for i in obj]
    return obj


def extract_schema_refs(obj: Any, context: str = "") -> List[str]:
    """
    Extract all $ref references from request/response objects recursively.

    Args:
        obj (Any): The object to search for $ref.
        context (str): Optional context for debugging.
    Returns:
        List[str]: List of all $ref strings found.
    """
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
    """
    Enhanced error printer for Prance ValidationError.

    Args:
        ve (Any): The ValidationError to print.
    """
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


def to_snake_case(value: str) -> str:
    """
    Convert a string to snake_case.

    Args:
        value (str): The string to convert.
    Returns:
        str: The snake_case version of the string.
    """
    return re.sub(r'(?<!^)(?=[A-Z])', '_', value).lower()


def load_jinja_template(template_name: str, template_dir: str) -> Tuple[Template, dict]:
    """
    Load a Jinja2 template from the given directory and return Template + expected variables dict.

    Args:
        template_name (str): The template filename.
        template_dir (str): The directory containing the template.
    Returns:
        Tuple[Template, dict]: The loaded template and a dict of expected variables.
    """
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
    """
    Render a Jinja2 template with the provided variables.

    Args:
        template (Template): The Jinja2 template to render.
        **kwargs: Variables to pass to the template.
    Returns:
        str: The rendered template as a string.
    """
    return template.render(**kwargs)


def patch_schema_all(schema_dict: Any) -> Any:
    """
    Call all patch functions on the schema dict to ensure OpenAPI 3.x compatibility.

    Args:
        schema_dict (Any): The schema dictionary to patch.
    Returns:
        Any: The patched and dictified schema.
    """
    patch_const_to_enum(schema_dict)
    update_refs(schema_dict)
    fix_nullable_fields_deep(schema_dict)
    patch_anyof_nullables(schema_dict)
    return dictify(schema_dict)


def extract_user_code_blocks(filepath: Path) -> Dict[str, str]:
    """
    Extract user code blocks from an existing handler_impl file.
    Returns a dict: {method_name: (indent, user_code_str)}
    """
    user_blocks = {}
    if not filepath.exists():
        return user_blocks
    current_method = None
    current_lines = []
    current_indent = ''
    inside_block = False
    for line in filepath.read_text(encoding="utf-8").splitlines(keepends=True):
        begin_match = re.match(r"^(\s*)# -- BEGIN USER CODE: (\w+) --", line)
        end_match = re.match(r"^(\s*)# -- END USER CODE: (\w+) --", line)
        if begin_match:
            inside_block = True
            current_method = begin_match.group(2)
            current_indent = begin_match.group(1)
            current_lines = []
            continue
        if end_match and inside_block and current_method == end_match.group(2):
            user_blocks[current_method] = (current_indent, ''.join(current_lines))
            inside_block = False
            current_method = None
            current_lines = []
            current_indent = ''
            continue
        if inside_block:
            current_lines.append(line)
    return user_blocks


def inject_user_code(rendered: str, user_blocks: Dict[str, tuple]) -> str:
    """
    Replace the default user code blocks in the rendered template with the user's code.
    If the block in the template still contains the '# DEFAULT USER CODE:' marker, always replace it (even if formatting was changed by yapf etc).
    Any user code blocks that are not matched to a method in the template will be appended at the end of the file.
    """
    used_blocks = set()

    def replacer(match):
        indent = match.group(1)
        method = match.group(2)
        block_content = match.group(0)
        if method in user_blocks:
            _, user_code = user_blocks[method]
            # Einheitliche Prüfung für alle Blöcke
            if '# DEFAULT USER CODE:' in block_content:
                used_blocks.add(method)
                # Re-indent user code to match current block
                user_code_lines = user_code.splitlines(keepends=True)
                reindented = ''.join([indent + line.lstrip() if line.strip() else line for line in user_code_lines])
                return f"{indent}# -- BEGIN USER CODE: {method} --\n" + reindented + f"{indent}# -- END USER CODE: {method} --"
            used_blocks.add(method)
            return block_content
        return block_content

    pattern = re.compile(r"^(\s*)# -- BEGIN USER CODE: (\w+) --.*?^\1# -- END USER CODE: \2 --", re.DOTALL | re.MULTILINE)
    result = pattern.sub(replacer, rendered)
    # Füge nicht verwendete User-Blocks am Ende an
    unused_blocks = [m for m in user_blocks if m not in used_blocks]
    if unused_blocks:
        result += "\n\n# --- Unmatched user code blocks from previous version ---\n"
        for m in unused_blocks:
            indent, user_code = user_blocks[m]
            user_code_lines = user_code.splitlines(keepends=True)
            reindented = ''.join([indent + line.lstrip() if line.strip() else line for line in user_code_lines])
            result += f"{indent}# -- BEGIN USER CODE: {m} --\n" + reindented + f"{indent}# -- END USER CODE: {m} --\n"
    return result


def write_output_file(path: Path, content: str):
    """Write content to a file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
