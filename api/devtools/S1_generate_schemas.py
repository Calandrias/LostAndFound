from importlib import import_module
import importlib.util
from collections import OrderedDict
from pydantic import TypeAdapter, BaseModel
import yaml
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from helper import Config, patch_schema_all

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
            except Exception as e:
                print(f"Warning: Could not import {py_file.name}: {e}")
    finally:
        sys.path = original_path
    return imported_modules


def safe_import(modulename: str, classname: str) -> Optional[Any]:
    """Safely import a class from a module."""
    try:
        module = import_module(modulename)
        model_class = getattr(module, classname)
        return model_class
    except Exception as e:
        print(f"Error importing {modulename}:{classname} -> {e}")
        return None


def get_models_from_registry() -> Dict[str, Any]:
    try:
        from shared.api import minimal_registry as registry  # pylint disable=import-outside-toplevel # lazy import to reduce overhead
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
    # Try to get union response/request models if registry provides them
    try:
        from shared.api import minimal_registry as registry
        response_registry = getattr(registry, 'get_response_models', lambda: {})()
        request_registry = getattr(registry, 'get_request_models', lambda: {})()
    except Exception:
        response_registry = {}
        request_registry = {}

    for model_name, import_path in validation_models.items():
        if isinstance(import_path, dict):
            model_class = import_path.get('class')
            if model_class is None:
                validation_issues.append(f"Registry model {model_name}: No class found")
                continue
        else:
            try:
                modulename, classname = import_path.split(":")
                model_class = safe_import(modulename, classname)
                if model_class is None:
                    validation_issues.append(f"Could not import {model_name}")
                    continue
            except Exception:
                validation_issues.append(f"Invalid import path for {model_name}")
                continue
        # Schema generation check
        try:
            if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                schema = model_class.model_json_schema()
            else:
                schema = TypeAdapter(model_class).json_schema()
            valid_models.append(model_name)
        except Exception as e:
            validation_issues.append(f"Schema generation failed for {model_name}: {e}")
            continue
        # Response model "kind" discriminator check
        if model_name in response_registry:
            response_models.append(model_name)
            fields = getattr(model_class, 'model_fields', {})
            if 'kind' not in fields:
                validation_issues.append(f"Response model {model_name} missing 'kind' field for discriminator")
        # Request union discriminator check
        if model_name in request_registry:
            request_models.append(model_name)
            fields = getattr(model_class, 'model_fields', {})
            if 'data' in fields:
                sub_ann = fields['data'].annotation
                if hasattr(sub_ann, '__args__'):
                    for submodel in sub_ann.__args__:
                        if hasattr(submodel, 'model_fields') and 'kind' not in submodel.model_fields:
                            validation_issues.append(f"Request submodel {getattr(submodel, '__name__', str(submodel))} in {model_name} missing 'kind' field for discriminator")
    # Summary Output
    if validation_issues:
        print("⚠️ Validation Issues:")
        for issue in validation_issues[:5]:
            print(f" • {issue}")
        if len(validation_issues) > 5:
            print(f" ... and {len(validation_issues)-5} more")
    print(f"✅ Validated {len(valid_models)} models")
    if response_models:
        print(f"🏷️ Found {len(response_models)} response models")
    if request_models:
        print(f"🏷️ Found {len(request_models)} request models with unions/discriminators")
    return len(validation_issues) == 0


def process_model_sources(model_sources: Dict[str, Any], global_defs: OrderedDict):
    """Process models for schema extraction, collect all $defs and merge conflicts."""
    processed_models = []
    for model_name, import_path in model_sources.items():
        if isinstance(import_path, dict):
            model_class = import_path.get('class')
            if model_class is None:
                continue
        else:
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
            print(f"Error generating schema for {model_name}: {e}")
            continue
        # Collect $defs
        if "$defs" in schema:
            for def_key, def_val in schema["$defs"].items():
                if def_key not in global_defs:
                    global_defs[def_key] = def_val
                elif global_defs[def_key] != def_val:
                    print(f"Warning: Conflicting definition for {def_key}")
            del schema["$defs"]
        global_defs[model_name] = schema
        processed_models.append(model_name)
    # Pretty model table
    columns = 4
    for i in range(0, len(processed_models), columns):
        row = processed_models[i:i + columns]
        while len(row) < columns:
            row.append("")
        print('\t'.join(f"{name:<{40}}" for name in row))


# --------- MAIN SCRIPT ---------

if __name__ == "__main__":
    print(f"🚀 Schema Generator for Lost & Found Platform")
    print("=" * 60)

    config = Config.load("config.json5")
    schema_file = config.get_path("schema_file")
    input_dir = config.get_path("input_dir")

    print(f"📁 Scanning directory: {input_dir}")
    imported_files = scan_directory_for_models(str(input_dir), recursive=True)
    print(f"✅ Imported {len(imported_files)} Python files")

    # Models
    registry_models = get_models_from_registry()
    model_sources = {src["name"]: src["import"] for src in config.get_all_modelsources() if "name" in src and "import" in src}

    if registry_models:
        print(f"📦 Found {len(registry_models)} models from registry")
        combined_sources = dict(registry_models)
        for name, path in model_sources.items():
            if name not in combined_sources:
                combined_sources[name] = path
    else:
        print(f"📦 Found {len(model_sources)} models from config")
        combined_sources = model_sources
    if not combined_sources:
        print("❌ No models found – aborting")
        sys.exit(1)

    print("\n🔍 Validating models...")
    validation_passed = validate_models(combined_sources)
    if not validation_passed:
        print("\n⚠️ Validation completed with issues – see warnings above")
    else:
        print("\n✅ Validation successful – all models are processable!")

    print("\n📋 Generating schemas...")
    global_defs = OrderedDict()
    process_model_sources(combined_sources, global_defs)

    print("\n🔧 Patching schema for OpenAPI 3.x and dictify....")

    combined_schema = patch_schema_all({"components": {"schemas": global_defs}})

    print("\n📝 Writing output...")
    try:
        schema_file.parent.mkdir(parents=True, exist_ok=True)
        with open(schema_file, "w", encoding="UTF-8") as f:
            f.write("# This file is auto-generated from Pydantic models. Do not edit by hand!\n\n")
            yaml.dump(combined_schema, f, sort_keys=False)
        print(f"✅ Generated schema: {schema_file}")
        print(f"📊 Total schemas: {len(global_defs)}")
    except Exception as e:
        print(f"❌ Error writing schema file: {e}")
        sys.exit(1)

    print("\n📊 Summary:")
    print(f" • Files imported: {len(imported_files)}")
    print(f" • Models processed: {len(combined_sources)}")
    print(f" • Schemas generated: {len(global_defs)}")
    print(f" • Status: {'✅ PASS' if validation_passed else '❌ FAIL'}")
    if not validation_passed:
        print(" • Please review warnings and fix models if needed!")
    print("\nDone.")
