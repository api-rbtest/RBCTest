import json

def find_key(obj, key, ancestor_key, within_ancestor=False):
    if within_ancestor:
        # Now we are within the ancestor_key, check if key exists
        if key in obj:
            return obj[key]
        
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == ancestor_key:
                # Once the ancestor_key is found, search only within its scope
                if isinstance(v, dict):
                    return find_key(v, key, ancestor_key, True)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            result = find_key(item, key, ancestor_key, True)
                            if result is not None:
                                return result
            
            # Continue to search recursively in nested dictionaries and lists
            if isinstance(v, dict):
                result = find_key(v, key, ancestor_key, within_ancestor)
                if result is not None:
                    return result
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        result = find_key(item, key, ancestor_key, within_ancestor)
                        if result is not None:
                            return result
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                result = find_key(item, key, ancestor_key, within_ancestor)
                if result is not None:
                    return result
    
    return None

def find_keys(obj, key, ancestor_key, within_ancestor=False):
    results = []

    if within_ancestor:
        # Now we are within the ancestor_key, check if key exists
        if key in obj:
            results.append(obj[key])

    for k, v in obj.items():
        if k == ancestor_key:
            # Once the ancestor_key is found, search only within its scope
            if isinstance(v, dict):
                results.extend(find_keys(v, key, ancestor_key, True))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        results.extend(find_keys(item, key, ancestor_key, True))
        
        # Continue to search recursively in nested dictionaries and lists
        if isinstance(v, dict):
            results.extend(find_keys(v, key, ancestor_key, within_ancestor))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    results.extend(find_keys(item, key, ancestor_key, within_ancestor))
    
    return results


def find_example_value_brute_force(openapi_spec, object_name, field_name):
    # walk through the whole spec to find any key with the name of field_name, check if value is a string or number or boolean or a list of them
    example_object = find_key(openapi_spec, "example", object_name)
    example_value = None
    if example_object is not None:
        example_value = find_key(example_object, field_name, "", True)
    if example_value is None:        
        example_value = find_key(openapi_spec, field_name, "example")

    if example_value is not None:
        if isinstance(example_value, (str, int, float, bool)):
            return example_value
        elif isinstance(example_value, list):
            for item in example_value:
                if not isinstance(item, (str, int, float, bool)):
                    return None
            return example_value
    return None

def find_example_value_in_definitions(openapi_spec, object_name, field_name):
    # Check in components.schemas (OpenAPI 3.0)

    definitions = openapi_spec.get("definitions", {})
    target_object = definitions.get(object_name, {})

    example = target_object.get("example", {})
    if isinstance(example, list) and len(example) > 0:
        for example_value in example:
            if example_value.get(field_name, None) is not None:
                return example_value.get(field_name, None)
        example_value = None
    else:
        example_value = example.get(field_name, None)


    if example_value is None:
        properties = target_object.get("properties", {})
        field = properties.get(field_name, {})
        example_value = field.get("example", None)

    # Return the example value if available
    return example_value

def find_example_value_in_components(openapi_spec, object_name, field_name):
    # Check in components.schemas (OpenAPI 3.0)

    components = openapi_spec.get("components", {})
    schemas = components.get("schemas", {})
    target_object = schemas.get(object_name, {})

    field = target_object.get("properties", {}).get(field_name, {})
    example_value = field.get("example", None)

    if example_value is None:
        example = target_object.get("example", {})
        if isinstance(example, list) and len(example) > 0:
            example_value = example[0].get(field_name, None)
        else:
            example_value = example.get(field_name, None)
    
    if example_value is None:
        if 'enum' in field and len(field['enum']) > 0:
            example_value = field['enum'][0]
            
    # Return the example value if available
    return example_value

def find_example_value(openapi_spec, object_name, field_name):
    # Check in components.schemas (OpenAPI 3.0)
    example_value = find_example_value_in_components(openapi_spec, object_name, field_name)

    # Check in definitions (OpenAPI 2.0)
    if example_value is None:
        example_value = find_example_value_in_definitions(openapi_spec, object_name, field_name)

    if example_value is None:
        example_value = find_example_value_brute_force(openapi_spec, object_name, field_name)

    # if example_value is None:
        # print(f"Example value not found for '{field_name}' in '{object_name}' for API spec {openapi_spec.get('info', {}).get('title', '')}")
    # input(f"Example value for '{field_name}' in '{object_name}': {example_value}")
    return example_value

def load_openapi_spec(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        openapi_spec = json.load(file)
    return openapi_spec

# Usage example:
# Assuming you have a JSON file for OpenAPI spec called "openapi.json"
# and you want to find the example value for "fieldName" in the "ObjectName"
if __name__ == "__main__":
    # filepath = r"RBCTest_dataset\GitLab Branch\openapi.json"
    filepath = r"RBCTest_dataset\Canada Holidays\openapi.json"
    openapi_spec = load_openapi_spec(filepath)
    fieldName = "id"
    ObjectName = "BasicProjectDetails"
    example_value = find_example_value_in_definitions(openapi_spec, ObjectName, fieldName)

    print(f"Example value for '{fieldName}' in '{ObjectName}': {example_value}")