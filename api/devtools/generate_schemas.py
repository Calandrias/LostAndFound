from importlib import import_module
import importlib.util
from collections import OrderedDict
from pydantic import TypeAdapter, BaseModel
import yaml
import json
import sys
from pathlib import Path
from helper import load_config, build_path


def scan_directory_for_models(directory, recursive=True):

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
        # Restore original path
        sys.path = original_path

    return imported_modules


def get_models_from_registry():
    try:
        from shared.api import minimal_registry as registry
        return registry.get_registered_models()
    except ImportError:
        print("Warning: No registry found, scanning will not discover decorated models")
        return {}


def validate_models(model_sources):
    """Compact validation: Pydantic models + Response discriminators"""
    validation_issues = []
    valid_models = []
    response_models = []

    # Get response models from registry if available
    try:
        from shared.api import minimal_registry as registry
        response_registry = getattr(registry, 'get_response_models', lambda: {})()
    except:
        response_registry = {}

    for model_name, import_path in model_sources.items():
        # Extract model class
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
            except:
                validation_issues.append(f"Invalid import path for {model_name}")
                continue

        # Validation 1: Test schema generation
        try:
            if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                schema = model_class.model_json_schema()
            else:
                schema = TypeAdapter(model_class).json_schema()
            valid_models.append(model_name)
        except Exception as e:
            validation_issues.append(f"Schema generation failed for {model_name}: {e}")
            continue

        # Validation 2: Response model discriminator check
        if model_name in response_registry:
            response_models.append(model_name)

            # Check for 'kind' field
            if hasattr(model_class, 'model_fields'):
                fields = model_class.model_fields
            else:
                fields = {}

            if 'kind' not in fields:
                validation_issues.append(f"Response model {model_name} missing 'kind' field for discriminator")

    # Print validation summary
    if validation_issues:
        print("⚠️ Validation Issues:")
        for issue in validation_issues[:5]:  # Show first 5
            print(f"  • {issue}")
        if len(validation_issues) > 5:
            print(f"  ... and {len(validation_issues) - 5} more")

    print(f"✅ Validated {len(valid_models)} models")
    if response_models:
        print(f"🏷️  Found {len(response_models)} response models")

    return len(validation_issues) == 0


# Load config
config = load_config("config.json5")

# Get paths from config
schema_dir = build_path(config["schema_file"])
input_dir = build_path(config["input_dir"])
schema_file = build_path(config["schema_file"])

# Add input_dir to sys.path
sys.path.insert(0, str(input_dir))

all_schemas = OrderedDict()
global_defs = OrderedDict()


def dictify(obj):
    # Recursively convert OrderedDict/list to dict/list
    if isinstance(obj, OrderedDict):
        return {k: dictify(v) for k, v in sorted(obj.items())}
    if isinstance(obj, dict):
        return {k: dictify(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [dictify(i) for i in obj]
    return obj


def update_refs(obj):
    """Recursively update $ref links to OpenAPI 3.x style."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            # $ref key
            if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                obj[k] = v.replace("#/$defs/", "#/components/schemas/")
            # Discriminator mapping or other string values
            elif isinstance(v, str) and v.startswith("#/$defs/"):
                obj[k] = v.replace("#/$defs/", "#/components/schemas/")
            else:
                update_refs(v)
    elif isinstance(obj, list):
        for item in obj:
            update_refs(item)


def fix_nullable_fields_deep(schema):
    if isinstance(schema, dict):
        # Patch ANY dict mit anyOf/$ref/null
        if "anyOf" in schema:
            items = schema["anyOf"]
            non_null = [i for i in items if i.get("type") != "null"]
            has_null = any(i.get("type") == "null" for i in items)

            if has_null and non_null:
                del schema["anyOf"]
                if non_null[0].get("$ref"):
                    schema["$ref"] = non_null[0]["$ref"]
                elif non_null[0].get("type"):
                    schema["type"] = non_null[0]["type"]
                schema["nullable"] = True

        # Rekursiv für alle Dict- und List-Elemente
        for k, v in list(schema.items()):
            fix_nullable_fields_deep(v)
    elif isinstance(schema, list):
        for item in schema:
            fix_nullable_fields_deep(item)


def safe_import(modulename, classname):
    try:
        module = import_module(modulename)
        model_class = getattr(module, classname)
        return model_class
    except Exception as e:
        print(f"Error importing {modulename}:{classname} -> {e}")
        return None


def process_model_sources(model_sources):
    """Process models from manual config or registry"""
    processed_models = []
    for model_name, import_path in model_sources.items():
        if isinstance(import_path, dict):
            # Registry format: {'class': ModelClass, 'module': '...', ...}
            model_class = import_path.get('class')
            if model_class is None:
                continue
        else:
            # Traditional format: "module:classname"
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

        if "$defs" in schema:
            for def_key, def_val in schema["$defs"].items():
                if def_key not in global_defs:
                    global_defs[def_key] = def_val
                elif global_defs[def_key] != def_val:
                    print(f"Warning: Conflicting definition for {def_key}")
            del schema["$defs"]

        global_defs[model_name] = schema
        processed_models.append(model_name)

    columns = 4
    for i in range(0, len(processed_models), columns):
        row = processed_models[i:i + columns]
        # Fülle leere Spalten auf falls nötig
        while len(row) < columns:
            row.append("")
        print('\t'.join(f"{name:<{40}}" for name in row))


# Main execution
if __name__ == "__main__":

    print(f"Scanning directory: {input_dir}")
    imported_files = scan_directory_for_models(input_dir, recursive=True)
    print(f"Imported {len(imported_files)} files")

    # 2. Try to get models from registry
    registry_models = get_models_from_registry()

    # 3. Combine with manual config models (if any)
    model_sources = config.get("modelsources", {})

    # Prefer registry models over manual config
    if registry_models:
        print(f"Using {len(registry_models)} models from registry")
        combined_sources = dict(registry_models)
        # Add any manual models that aren't in registry
        for name, path in model_sources.items():
            if name not in combined_sources:
                combined_sources[name] = path
    else:
        print(f"Using {len(model_sources)} models from config")
        combined_sources = model_sources

    if not combined_sources:
        print("No models found to process")
        sys.exit(1)

    print("\n📋 Validating models...")
    validation_passed = validate_models(combined_sources)
    if not validation_passed:
        print("⚠️  Continuing with issues - review warnings above")

    # 4. Process all models
    process_model_sources(combined_sources)

    # 5. Update refs and fix nullable fields
    update_refs(global_defs)

    combined_schema = {"components": {"schemas": dictify(global_defs)}}

    fix_nullable_fields_deep(combined_schema)

    # 6. Write output
    try:
        schema_file.parent.mkdir(parents=True, exist_ok=True)
        with open(schema_file, "w", encoding="UTF-8") as f:
            f.write("# This file is auto-generated from Pydantic models. Do not edit by hand!\n\n")
            yaml.dump(dictify(combined_schema), f, sort_keys=False)

        print(f"Generated combined schema: {schema_file}")
        print(f"Total schemas: {len(global_defs)}")
    except Exception as e:
        print(f"Error writing schema file: {e}")
        sys.exit(1)
