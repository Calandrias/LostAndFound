import os
import sys
import json
import yaml
from copy import deepcopy
from typing import Any, Dict, List, DefaultDict
from collections import defaultdict
from prance import BaseParser, ValidationError
from helper import load_config, build_path


def combine_openapi(openapi_path: str, schemas_path: str, out_path: str = "openapi_combined.yaml") -> Dict:
    """
    Combines OpenAPI YAML with external schemas into a self-contained file.
    Returns the combined spec for validation.
    """
    with open(openapi_path, 'r', encoding='utf-8') as f:
        openapi = yaml.safe_load(f)

    with open(schemas_path, 'r', encoding='utf-8') as f:
        schemas = yaml.safe_load(f)

    combined = deepcopy(openapi)
    combined.setdefault('components', {})['schemas'] = schemas['components']['schemas']

    def fix_refs(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == '$ref' and isinstance(v, str) and '#' in v:
                    after_hash = v.split('#', 1)[-1]
                    obj[k] = '#' + after_hash
                else:
                    fix_refs(v)
        elif isinstance(obj, list):
            for v in obj:
                fix_refs(v)

    fix_refs(combined)

    with open(out_path, 'w', encoding='utf-8') as f:
        yaml.dump(combined, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f'Combined OpenAPI written to: {out_path}')
    return combined


def validate_schema_references(combined_spec: Dict) -> Dict:
    """
    Pre-Prance validation: Check if all $ref references can be resolved.
    Returns detailed validation report.
    """
    validation_report = {'valid': True, 'missing_refs': [], 'invalid_paths': [], 'schema_issues': [], 'total_refs_checked': 0}

    # Get all available schemas
    available_schemas = set()
    if 'components' in combined_spec and 'schemas' in combined_spec['components']:
        available_schemas = set(combined_spec['components']['schemas'].keys())
        print(f"📋 Available schemas ({len(available_schemas)}):")
        # Print in 4 columns
        schema_list = list(available_schemas)
        for i in range(0, len(schema_list), 4):
            row = schema_list[i:i + 4]
            print('\t'.join(f"{name:<40}" for name in row))

    def check_refs_recursive(obj, path=""):
        """Recursively check all $ref references"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                if key == '$ref' and isinstance(value, str):
                    validation_report['total_refs_checked'] += 1

                    # Check if it's a schema reference
                    if value.startswith('#/components/schemas/'):
                        schema_name = value.replace('#/components/schemas/', '')
                        if schema_name not in available_schemas:
                            validation_report['missing_refs'].append({'path': current_path, 'reference': value, 'schema_name': schema_name})
                            validation_report['valid'] = False

                else:
                    check_refs_recursive(value, current_path)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                check_refs_recursive(item, current_path)

    # Check all paths
    if 'paths' in combined_spec:
        for path_name, path_item in combined_spec['paths'].items():
            if not isinstance(path_item, dict):
                validation_report['invalid_paths'].append(path_name)
                validation_report['valid'] = False
                continue

            check_refs_recursive(path_item, f"paths.{path_name}")

    # Check components
    if 'components' in combined_spec:
        check_refs_recursive(combined_spec['components'], "components")

    return validation_report


def validate_request_response_schemas(combined_spec: Dict) -> Dict:
    """
    Validate that requestBody and response schemas reference valid schemas.
    Focus on Lost & Found platform specific validation.
    """
    validation_report = {'valid': True, 'issues': [], 'request_body_count': 0, 'response_count': 0, 'discriminator_issues': []}

    def extract_schema_refs(obj, context=""):
        """Extract all schema references from request/response"""
        refs = []
        if isinstance(obj, dict):
            if '$ref' in obj:
                refs.append(obj['$ref'])
            elif 'schema' in obj:
                if isinstance(obj['schema'], dict) and '$ref' in obj['schema']:
                    refs.append(obj['schema']['$ref'])
                elif isinstance(obj['schema'], dict) and 'oneOf' in obj['schema']:
                    # Check discriminated unions (important for Lost & Found)
                    for one_of_item in obj['schema']['oneOf']:
                        if isinstance(one_of_item, dict) and '$ref' in one_of_item:
                            refs.append(one_of_item['$ref'])

                    # Check discriminator mapping
                    if 'discriminator' in obj['schema']:
                        discriminator = obj['schema']['discriminator']
                        if 'mapping' in discriminator:
                            for disc_key, disc_ref in discriminator['mapping'].items():
                                refs.append(disc_ref)
                        else:
                            validation_report['discriminator_issues'].append({'context': context, 'issue': 'Discriminator without mapping found'})

            for key, value in obj.items():
                refs.extend(extract_schema_refs(value, f"{context}.{key}"))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                refs.extend(extract_schema_refs(item, f"{context}[{i}]"))

        return refs

    # Get available schemas
    available_schemas = set()
    if 'components' in combined_spec and 'schemas' in combined_spec['components']:
        available_schemas = set(f"#/components/schemas/{name}" for name in combined_spec['components']['schemas'].keys())

    # Check paths
    if 'paths' in combined_spec:
        for path_name, path_item in combined_spec['paths'].items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue

                operation_context = f"{method.upper()} {path_name}"

                # Check requestBody
                if 'requestBody' in operation:
                    validation_report['request_body_count'] += 1
                    request_refs = extract_schema_refs(operation['requestBody'], f"{operation_context}.requestBody")

                    for ref in request_refs:
                        if ref not in available_schemas:
                            validation_report['issues'].append({'type': 'missing_request_schema', 'operation': operation_context, 'reference': ref})
                            validation_report['valid'] = False

                # Check responses
                if 'responses' in operation:
                    for status_code, response in operation['responses'].items():
                        validation_report['response_count'] += 1
                        response_refs = extract_schema_refs(response, f"{operation_context}.responses.{status_code}")

                        for ref in response_refs:
                            if ref not in available_schemas:
                                validation_report['issues'].append({'type': 'missing_response_schema', 'operation': operation_context, 'response': status_code, 'reference': ref})
                                validation_report['valid'] = False

    return validation_report


def detailed_validation_report(combined_spec: Dict) -> bool:
    """
    Comprehensive validation before sending to Prance.
    Returns True if validation passes, False otherwise.
    """
    print("\n🔍 Pre-Prance Validation:")
    print("=" * 50)

    # 1. Schema Reference Validation
    print("📋 Checking schema references...")
    ref_validation = validate_schema_references(combined_spec)

    if ref_validation['missing_refs']:
        print(f"❌ Found {len(ref_validation['missing_refs'])} missing schema references:")
        for missing in ref_validation['missing_refs'][:5]:  # Show first 5
            print(f"  • {missing['path']}: {missing['reference']}")
            print(f"    Schema '{missing['schema_name']}' not found in components/schemas")
        if len(ref_validation['missing_refs']) > 5:
            print(f"  ... and {len(ref_validation['missing_refs']) - 5} more")
    else:
        print(f"✅ All {ref_validation['total_refs_checked']} schema references valid")

    # 2. Request/Response Schema Validation
    print("\n🔧 Checking request/response schemas...")
    req_res_validation = validate_request_response_schemas(combined_spec)

    if req_res_validation['issues']:
        print(f"❌ Found {len(req_res_validation['issues'])} request/response issues:")
        for issue in req_res_validation['issues'][:5]:
            if issue['type'] == 'missing_request_schema':
                print(f"  • {issue['operation']}: Missing requestBody schema {issue['reference']}")
            elif issue['type'] == 'missing_response_schema':
                print(f"  • {issue['operation']} [{issue['response']}]: Missing response schema {issue['reference']}")
        if len(req_res_validation['issues']) > 5:
            print(f"  ... and {len(req_res_validation['issues']) - 5} more")
    else:
        print(f"✅ Validated {req_res_validation['request_body_count']} request bodies and {req_res_validation['response_count']} responses")

    # 3. Lost & Found specific validation
    if req_res_validation['discriminator_issues']:
        print("\n🏷️  Discriminator Issues (Lost & Found specific):")
        for issue in req_res_validation['discriminator_issues']:
            print(f"  ⚠️  {issue['context']}: {issue['issue']}")

    # Summary
    overall_valid = ref_validation['valid'] and req_res_validation['valid']
    print(f"\n📊 Validation Summary:")
    print(f"  • Schema references: {'✅ PASS' if ref_validation['valid'] else '❌ FAIL'}")
    print(f"  • Request/Response schemas: {'✅ PASS' if req_res_validation['valid'] else '❌ FAIL'}")
    print(f"  • Overall: {'✅ READY FOR PRANCE' if overall_valid else '❌ NEEDS FIXING'}")

    return overall_valid


def validation_error_printer(ve: ValidationError):
    """Enhanced error printer for Prance ValidationError"""
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


def load_openapi_by_tag(filename: str) -> DefaultDict[str, List[Dict[str, Any]]]:
    """
    Loads an OpenAPI YAML/JSON file, parses it, and returns all endpoints grouped by tag.
    """
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"File not found: {filename}")

    if not filename.lower().endswith((".yaml", ".yml", ".json")):
        raise ValueError("Expected an OpenAPI file with extension .yaml, .yml, or .json")

    try:
        parser = BaseParser(filename)
        spec: Any = parser.specification
    except ValidationError as ve:
        print("\n❌ Prance Validation Failed:")
        validation_error_printer(ve)
        raise ValueError(f"OpenAPI validation error: {ve}") from ve
    except Exception as e:
        raise RuntimeError(f"Error parsing file: {e}") from e

    if not isinstance(spec, dict) or "paths" not in spec:
        raise ValueError("'paths' section missing or invalid OpenAPI document")

    paths = dict(spec.get("paths", {}))
    tagged_endpoints: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method, details in path_item.items():
            if not isinstance(details, dict):
                continue

            if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}:
                continue

            path_tags = details.get("tags", ["untagged"])
            for path_tag in path_tags:
                tagged_endpoints[path_tag].append({
                    "path": path,
                    "method": method.upper(),
                    "operationId": details.get("operationId"),
                    "summary": details.get("summary"),
                    "parameters": details.get("parameters", []),
                    "requestBody": details.get("requestBody", None),
                    "responses": details.get("responses", {}),
                })

    return tagged_endpoints


if __name__ == "__main__":
    cfg = load_config("config.json5")
    openapi_file = build_path(cfg["openapi_file"])
    schemas_file = build_path(cfg["schema_file"])
    temp_file = build_path(cfg["temp_api_file"])
    output_dir = build_path(cfg["output_dir"])

    print("🚀 Enhanced OpenAPI Parser for Lost & Found Platform")
    print("=" * 60)

    # Step 1: Combine files
    print(f"📁 Combining {openapi_file} + {schemas_file}")
    combined_spec = combine_openapi(openapi_path=str(openapi_file), schemas_path=str(schemas_file), out_path=str(temp_file))

    # Step 2: Pre-validation (NEW!)
    validation_passed = detailed_validation_report(combined_spec)

    if not validation_passed:
        print("\n⚠️  Pre-validation failed, but continuing with Prance...")
        print("Review the issues above before deploying.")
    else:
        print("\n✅ Pre-validation passed - OpenAPI spec looks good!")

    # Step 3: Prance validation and parsing
    print("\n🔧 Running Prance validation and parsing...")
    try:
        tags = load_openapi_by_tag(str(temp_file))

        print(f"\n✅ Prance validation passed!")
        print(f"📊 Found {sum(len(endpoints) for endpoints in tags.values())} endpoints in {len(tags)} tags")

        for tag, endpoints in tags.items():
            print(f"\n🏷️  Tag: {tag} ({len(endpoints)} endpoints)")
            for ep in endpoints:
                print(f"   {ep['method']} {ep['path']} - {ep['operationId']} ({ep['summary']})")

    except Exception as e:
        print(f"\n❌ Prance validation/parsing failed: {e}")
        sys.exit(1)
