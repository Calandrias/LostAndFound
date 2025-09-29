"""
Generate OpenAPI schemas out of decorated Pydantic models for the Lost & Found platform.

This script scans model sources, validates models, generates OpenAPI-compatible schemas, and writes them to disk.
All main functions and helpers are documented for maintainability.
"""
import sys
from pathlib import Path
from importlib import import_module
import importlib.util
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from pydantic import TypeAdapter, BaseModel
import yaml
from helper import Config, patch_schema_all, write_output_file
from validation_utils import (print_section, print_error_list, print_validation_summary, import_model_class, check_schema_generation, check_response_discriminator,
                              check_request_discriminator, print_model_validation_summary, generate_schema_for_model, collect_defs, pretty_print_model_table)

from shared import minimal_registry as registry

# --------- UTILS AND HELPERS ---------


def scan_directory_for_models(directory: str, recursive: bool = True) -> List[Path]:
    """Scan a directory for Python model files for debugging or test importing."""
    base_path = Path(directory)
    pattern = "**/*.py" if recursive else "*.py"
    original_path = sys.path.copy()
    if str(base_path) not in sys.path:
        sys.path.insert(0, str(base_path))
    if str(base_path.parent) not in sys.path:
        sys.path.insert(0, str(base_path.parent))
    imported_modules = []
    try:
        for py_file in base_path.glob(pattern):
            if any(part.startswith('.') or part == '__pycache__' for part in py_file.parts):
                continue
            if py_file.name.startswith('test_') or py_file.name.endswith('_test.py'):
                continue
            try:
                spec = importlib.util.spec_from_file_location("temp_module", py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    imported_modules.append(py_file.relative_to(base_path))
            except (ImportError, FileNotFoundError, AttributeError, SyntaxError) as e:
                print(f"Warning: Could not import {py_file.name}: {type(e).__name__}: {e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"Unexpected error while importing {py_file.name}: {type(e).__name__}: {e}")
    finally:
        sys.path = original_path
    return imported_modules


def safe_import(modulename: str, classname: str) -> Optional[Any]:
    """Safely import a class from a module."""
    try:
        module = import_module(modulename)
        model_class = getattr(module, classname)
        return model_class
    except (ImportError, AttributeError, ModuleNotFoundError) as e:
        print(f"Error importing {modulename}:{classname} -> {type(e).__name__}: {e}")
        return None


def get_models_from_registry() -> Dict[str, Any]:
    """Get decorated models from model registry """
    try:
        return registry.get_registered_models()
    except ImportError:
        print("Warning: No registry found, scanning will not discover decorated models")
        return {}


def validate_models(validation_models: Dict[str, Any]) -> bool:
    """Validate Pydantic models and discriminators for response/request models."""
    validation_issues = []
    valid_models = []
    response_models = []
    request_models = []
    try:
        response_registry = getattr(registry, 'get_response_models', lambda: {})()
    except (AttributeError, TypeError):
        response_registry = {}
    try:
        request_registry = getattr(registry, 'get_request_models', lambda: {})()
    except (AttributeError, TypeError):
        request_registry = {}
    for model_name, import_path in validation_models.items():
        model_class = import_model_class(model_name, import_path)
        if model_class is None:
            validation_issues.append(f"Could not import {model_name}")
            continue
        if not check_schema_generation(model_class, model_name, valid_models, validation_issues):
            continue
        check_response_discriminator(model_name, model_class, response_registry, validation_issues, response_models)
        check_request_discriminator(model_name, model_class, request_registry, validation_issues, request_models)
    print_model_validation_summary(validation_issues, valid_models, response_models, request_models)
    return len(validation_issues) == 0


def process_model_sources(model_sources: Dict[str, Any], global_defs: OrderedDict):
    """Process models for schema extraction, collect all $defs and merge conflicts."""
    processed_models = []
    for model_name, import_path in model_sources.items():
        model_class = import_model_class(model_name, import_path)
        if model_class is None:
            continue
        try:
            schema = generate_schema_for_model(model_class)
        except Exception as e:
            print(f"Error generating schema for {model_name}: {e}")
            continue
        collect_defs(schema, global_defs)
        global_defs[model_name] = schema
        processed_models.append(model_name)
    pretty_print_model_table(processed_models)


# --------- MAIN SCRIPT ---------


def load_and_combine_modelsources(config_obj) -> dict:
    """Lädt und kombiniert Modelsourcen aus Registry und Config."""
    registry_models = get_models_from_registry()
    model_sources_dict = {src["name"]: src["import"] for src in config_obj.get_all_modelsources() if "name" in src and "import" in src}
    if registry_models:
        print(f"📦 Found {len(registry_models)} models from registry")
        combined_sources = dict(registry_models)
        for name, path in model_sources_dict.items():
            if name not in combined_sources:
                combined_sources[name] = path
    else:
        print(f"📦 Found {len(model_sources_dict)} models from config")
        combined_sources = model_sources_dict
    return combined_sources


def validate_and_report(model_sources_dict: dict) -> bool:
    """Validiert Modelle und gibt Ergebnis aus."""
    print_section("Validating models")
    validation_result = validate_models(model_sources_dict)
    if not validation_result:
        print_error_list(["Validation completed with issues – see warnings above"])
    else:
        print_validation_summary(True, context="Models")
    return validation_result


def generate_and_write_schema(model_sources_dict: dict, config_obj) -> int:
    """Generiert und schreibt das Schema, gibt die Anzahl der generierten Schemas zurück."""
    print_section("Generating schemas")
    global_defs = OrderedDict()
    process_model_sources(model_sources_dict, global_defs)
    print_section("Patching schema for OpenAPI 3.x and dictify")
    combined_schema = patch_schema_all({"components": {"schemas": global_defs}})
    schema_file_local = config_obj.get_path("schema_file")
    print_section("Writing output")
    write_output_file(schema_file_local, "# This file is auto-generated from Pydantic models. Do not edit by hand!\n\n" + yaml.dump(combined_schema, sort_keys=False))
    print(f"✅ Generated schema: {schema_file_local}")
    print(f"📊 Total schemas: {len(global_defs)}")
    return len(global_defs)


def print_summary(imported_files_list, model_sources_dict, num_schemas_int, validation_passed_bool):
    """Gibt eine Zusammenfassung der Ergebnisse aus."""
    print_section("Summary")
    print(f" • Files imported: {len(imported_files_list)}")
    print(f" • Models processed: {len(model_sources_dict)}")
    print(f" • Schemas generated: {num_schemas_int}")
    print_validation_summary(validation_passed_bool, context="Models")
    if not validation_passed_bool:
        print_error_list(["Please review warnings and fix models if needed!"])
    print("\nDone.")


if __name__ == "__main__":
    print("🚀 Schema Generator for Lost & Found Platform")
    print("=" * 60)
    config_obj = Config.load("config.json5")
    schema_file = config_obj.get_path("schema_file")
    input_dir = config_obj.get_path("input_dir")
    print(f"📁 Scanning directory: {input_dir}")
    imported_files_list = scan_directory_for_models(str(input_dir), recursive=True)
    print(f"✅ Imported {len(imported_files_list)} Python files")
    model_sources_dict = load_and_combine_modelsources(config_obj)
    if not model_sources_dict:
        print("❌ No models found – aborting")
        sys.exit(1)
    VALIDATION_PASSED = validate_and_report(model_sources_dict)
    num_schemas_int = generate_and_write_schema(model_sources_dict, config_obj)
    print_summary(imported_files_list, model_sources_dict, num_schemas_int, VALIDATION_PASSED)
