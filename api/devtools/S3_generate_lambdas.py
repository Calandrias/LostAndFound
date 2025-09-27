"""Generate Lambdas from OpenAPI spec"""

import json
from pathlib import Path
from typing import Dict, Any
from api.devtools.S2_generate_api import load_openapi_by_tag
from helper import Config, load_jinja_template, render_jinja_template

# Config und OpenAPI laden
config = Config.load("config.json5")
openapi_file = config.get_path("temp_api_file")
output_dir = Path("generated_lambdas")
output_dir.mkdir(exist_ok=True)

generic_config = config.get_lambda_generic_config()
lambda_functions = config.get_lambda_functions()


def check_missing_parameters(expected, provided):
    print(f"Expected parameters: {json.dumps(expected, indent=2)}")
    print(f"Provided parameters: {json.dumps(provided, indent=2)}")
    missing = set(expected) - set(provided)
    if missing:
        print(f"Missing parameters: {json.dumps(list(missing), indent=2)}")
    return missing


def process_template(template_name: str, template_dir: str, template_variables: Dict[str, Any], output_path: Path, overwrite=True) -> bool:
    template, expected_parameters = load_jinja_template(template_name, template_dir)
    if check_missing_parameters(expected_parameters, template_variables):
        return False
    if output_path.exists() and not overwrite:
        print(f"File {output_path} already exists and overwrite is False. Skipping.")
        return True
    code = render_jinja_template(template=template, **template_variables)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
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
        overwrite=True,
    )

    # Lambda-Handler
    process_template(
        template_name="lambda_handler.py.j2",
        template_dir="api/devtools/templates/runtime",
        template_variables=parameters,
        output_path=Path(config_for_tag.get("runtime_path")) / f"{tag}_lambda_handler.py",
        overwrite=True,
    )

    # Handler-Implementation prototype
    process_template(
        template_name="handler_impl.py.j2",
        template_dir="api/devtools/templates/runtime",
        template_variables=parameters,
        output_path=Path(config_for_tag.get("runtime_path")) / f"{tag}_handler_impl.py",
        overwrite=False,
    )

print("All Lambda handlers and implementations have been generated.")
