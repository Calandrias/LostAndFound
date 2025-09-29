"""
Generate Lambda handler code from OpenAPI spec for the Lost & Found platform.

This script merges generic and per-function config, loads OpenAPI tags, and renders handler templates for each tag.
All main functions and helpers are documented for maintainability.
"""

import json
from pathlib import Path
from typing import Dict, Any
from s2_generate_api import load_openapi_by_tag
from helper import Config, load_jinja_template, render_jinja_template, extract_user_code_blocks, inject_user_code, write_output_file
from validation_utils import print_section, print_error_list

# Config und OpenAPI laden
config = Config.load("config.json5")
openapi_file = config.get_path("temp_api_file")
output_dir = Path("generated_lambdas")
output_dir.mkdir(exist_ok=True)

generic_config = config.get_lambda_generic_config()
lambda_functions = config.get_lambda_functions()


def check_missing_parameters(expected, provided):
    """
    Print and return missing parameters between expected and provided dicts.

    Args:
        expected (dict): Expected parameters (from template).
        provided (dict): Provided parameters (from config/tag).
    Returns:
        set: Set of missing parameter names.
    """
    print(f"Expected parameters: {json.dumps(expected, indent=2)}")
    print(f"Provided parameters: {json.dumps(provided, indent=2)}")
    missing = set(expected) - set(provided)
    if missing:
        print(f"Missing parameters: {json.dumps(list(missing), indent=2)}")
    return missing


def process_template(template_name: str, template_dir: str, template_variables: Dict[str, Any], output_path: Path) -> bool:
    """
    Render a Jinja2 template with variables, merge user code blocks, and write to output file.

    Args:
        template_name (str): Name of the template file.
        template_dir (str): Directory containing the template.
        template_variables (dict): Variables for template rendering.
        output_path (Path): Output file path.
    Returns:
        bool: True if successful, False if missing parameters.
    """
    template, expected_parameters = load_jinja_template(template_name, template_dir)
    if check_missing_parameters(expected_parameters, template_variables):
        print_error_list([f"Missing parameter: {k}" for k in set(expected_parameters) - set(template_variables)])
        return False
    user_blocks = {}
    if output_path.exists():
        user_blocks = extract_user_code_blocks(output_path)
        if user_blocks:
            print(f"Merging user code blocks for {output_path.name}")
    code = render_jinja_template(template=template, **template_variables)
    if user_blocks:
        code = inject_user_code(code, user_blocks)
    write_output_file(output_path, code)
    return True


# Merging generic config into each lambda function config
merged_lambda_functions = []
for func in lambda_functions:
    merged_func = {**generic_config, **(func or {})}
    merged_lambda_functions.append(merged_func)

tags = load_openapi_by_tag(str(openapi_file))

for tag, endpoints in tags.items():

    print(f"processing tag {tag}")
    #lambda runtime generation by tag

    config_for_tag = next((func for func in merged_lambda_functions if func.get("tag_name") == tag), None)

    if not config_for_tag:
        print("no config found for tag, skipping")
        continue

    parameters = {
        "endpoints": endpoints,
        **config_for_tag,
    }

    # Abc-Handler
    process_template(
        template_name="handler_ABC.py.j2",
        template_dir="api/devtools/templates/runtime",
        template_variables=parameters,
        output_path=Path(config_for_tag.get("runtime_path")) / f"{tag}_ABC.py",
    )

    # Lambda-Handler
    process_template(
        template_name="lambda_handler.py.j2",
        template_dir="api/devtools/templates/runtime",
        template_variables=parameters,
        output_path=Path(config_for_tag.get("runtime_path")) / f"{tag}_lambda_handler.py",
    )

    # Handler-Implementation prototype
    process_template(
        template_name="handler_impl.py.j2",
        template_dir="api/devtools/templates/runtime",
        template_variables=parameters,
        output_path=Path(config_for_tag.get("runtime_path")) / f"{tag}_handler_impl.py",
    )

print_section("All Lambda handlers and implementations have been generated.")
