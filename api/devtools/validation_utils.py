"""
Common validation and error reporting utilities for Lost & Found devtools.
"""
from typing import List
from importlib import import_module
from pydantic import BaseModel, TypeAdapter


def print_error_list(errors: List[str], max_items: int = 5):
    """Prints a list of errors, limiting output to max_items."""
    for err in errors[:max_items]:
        print(f" • {err}")
    if len(errors) > max_items:
        print(f" ... and {len(errors)-max_items} more")


def print_section(title: str):
    """Prints a formatted section title."""
    print(f"\n=== {title} ===")


def print_validation_summary(valid: bool, context: str = "Validation"):
    """Prints a standardized validation summary line."""
    print(f" • Status: {'✅ PASS' if valid else '❌ FAIL'} [{context}]")


def import_model_class(import_path):
    """Imports a model class based on the import path."""
    if isinstance(import_path, dict):
        return import_path.get('class')
    try:
        modulename, classname = import_path.split(":")
        module = import_module(modulename)
        return getattr(module, classname)
    except (ImportError, AttributeError, ValueError):
        # handle known import errors
        return None
    except Exception:  # pylint: disable=broad-exception-caught
        # unexpected error
        return None


def check_schema_generation(model_class, model_name, valid_models, validation_issues):
    """Checks if the model generates a valid Pydantic schema definition."""

    try:
        if isinstance(model_class, type) and issubclass(model_class, BaseModel):
            model_class.model_json_schema()
        else:
            TypeAdapter(model_class).json_schema()
        valid_models.append(model_name)
        return True
    except (TypeError, AttributeError, ValueError) as e:
        validation_issues.append(f"Schema generation failed for {model_name}: {type(e).__name__}: {e}")
        return False


def check_response_discriminator(model_name, model_class, response_registry, validation_issues, response_models):
    """Checks if the response model contains the 'kind' field for the discriminator."""
    if model_name in response_registry:
        response_models.append(model_name)
        fields = getattr(model_class, 'model_fields', {})
        if 'kind' not in fields:
            validation_issues.append(f"Response model {model_name} missing 'kind' field for discriminator")


def check_request_discriminator(model_name, model_class, request_registry, validation_issues, request_models):
    """Checks if the request model and its submodels contain the 'kind' field for the discriminator."""
    if model_name in request_registry:
        request_models.append(model_name)
        fields = getattr(model_class, 'model_fields', {})
        if 'data' in fields:
            sub_ann = fields['data'].annotation
            if hasattr(sub_ann, '__args__'):
                for submodel in sub_ann.__args__:
                    if hasattr(submodel, 'model_fields') and 'kind' not in submodel.model_fields:
                        validation_issues.append(f"Request submodel {getattr(submodel, '__name__', str(submodel))} in {model_name} missing 'kind' field for discriminator")


def print_model_validation_summary(validation_issues, valid_models, response_models, request_models):
    """Prints a summary of model validation results."""
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


def generate_schema_for_model(model_class):
    """create json schema for a model, Pydantic v2 compatible."""
    if isinstance(model_class, type) and issubclass(model_class, BaseModel):
        return model_class.model_json_schema()
    return TypeAdapter(model_class).json_schema()


def collect_defs(schema, global_defs):
    """Adds $defs from the model schema into the global defs dict, checking for conflicts."""
    if "$defs" in schema:
        for def_key, def_val in schema["$defs"].items():
            if def_key not in global_defs:
                global_defs[def_key] = def_val
            elif global_defs[def_key] != def_val:
                print(f"Warning: Conflicting definition for {def_key}")
        del schema["$defs"]


def pretty_print_model_table(processed_models, columns=4):
    """Prints the model names in a tabular format."""
    for i in range(0, len(processed_models), columns):
        row = processed_models[i:i + columns]
        while len(row) < columns:
            row.append("")
        print('\t'.join(f"{name:<{40}}" for name in row))
