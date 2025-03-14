import copy
import json, yaml
import re
import os

ruler = lambda: print("-" * 100)
jprint = lambda x: print(json.dumps(x, indent=2))
success_code = lambda x: 200 <= x < 300
# Replace all '/', '{', '}', '.' characters in the path with "_"
convert_path_fn = lambda x: re.sub(r"_+", "_", re.sub(r"[\/{}.]", "_", x))

def extract_operations(spec):
    '''
    Currently work well with OAS 3.0
    '''
    operations = []
    paths = spec['paths']
    valid_methods = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']
    for path in paths:
        for method in paths[path]:
            if method.startswith('x-') or method not in valid_methods:
                continue
            operations.append(method + '-' + path)
    
    return operations

def isSuccessStatusCode(x):
    if isinstance(x, int):
        return success_code(x)
    elif isinstance(x, str):
        return x.isdigit() and success_code(int(x))
    return False

def load_openapi(path):
    '''
    Break the openapi spec into semantic parts
    ---
    Input:
        path: path to the openapi spec
    '''
    # Check if file is existed
    if not os.path.exists(path):
        print(f'File {path} is not existed')
        return None
    
    if path.endswith('.yml') or path.endswith('.yaml'):
        # Read YAML file
        with open(path, 'r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    elif path.endswith('.json'):
        # Read JSON file
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        print(f'File {path} is not supported. Must be in YAML or JSON format.')
        return None

def get_ref(spec: dict, ref: str):
    sub = ref[2:].split('/')
    schema = spec
    for e in sub:
        schema = schema.get(e, {})
    return schema

def find_object_with_key(json_obj, target_key):
    if isinstance(json_obj, dict):
        if target_key in json_obj:
            return json_obj
        for value in json_obj.values():
            result = find_object_with_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_object_with_key(item, target_key)
            if result is not None:
                return result
    return None

def get_schema_params(body, spec, visited_refs=None, get_description=False, max_depth=None, current_depth=0, ignore_attr_with_schema_ref=False):
    if visited_refs is None:
        visited_refs = set()
    
    if max_depth:
        if current_depth > max_depth:
            return None

    properties = find_object_with_key(body, "properties")
    ref = find_object_with_key(body, "$ref")
    schema = find_object_with_key(body, "schema")
    
    new_schema = {}
    if properties:
        for p, prop_details in properties["properties"].items():
            p_ref = find_object_with_key(prop_details, "$ref")
            
            if p_ref and ignore_attr_with_schema_ref:
                continue
            
            # Initialize the description string
            description_string = ""
            
            # Check the get_description flag
            if get_description:
                description_parent = find_object_with_key(prop_details, "description")
                if description_parent and not isinstance(description_parent["description"], dict):
                    description_string = " (description: " + description_parent["description"].strip(' .') + ")"
            
            if "type" in prop_details:
                if prop_details["type"] == "array":
                    if p_ref:
                        new_schema[p] = {}
                        new_schema[p][f'array of \'{p_ref["$ref"].split("/")[-1]}\' objects'] = [get_schema_params(prop_details, spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)]
                    else:
                        new_schema[p] = {}
                        new_schema[p][f'array of {prop_details["items"]["type"]} objects'] = [get_schema_params(prop_details["items"], spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)]
                else:
                    new_schema[p] = prop_details["type"] + description_string
                    
            elif p_ref:
                if p_ref["$ref"] in visited_refs:
                    new_schema[p] = {f'schema of {p_ref["$ref"].split("/")[-1]}': {}}
                    continue
                
                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_params(schema, spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)
                if child_schema is not None:
                    new_schema[p] = {}
                    new_schema[p][f'schema of {p_ref["$ref"].split("/")[-1]}'] = child_schema
                    
    elif ref:
        if ref["$ref"] in visited_refs:
            return None
        
        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_params(schema, spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)
    elif schema:
        return get_schema_params(schema['schema'], spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)
    else:
        field_value = ""
        if body is not None and "type" in body:
            field_value = body["type"]
        
        if field_value != "":
            return field_value
        else:
            return None
    
    return new_schema

def get_operation_params(spec: dict, 
                        only_get_parameter_types: bool = False, 
                        get_not_required_params: bool = True, 
                        get_test_object: bool = False, 
                        insert_test_data_file_link: bool = False, 
                        get_description: bool = False,
                        get_response_body: bool = True):
    operations = extract_operations(spec)
    operation_params_only_dict = {}

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])  # dict[str, ]

        operation_params_only_entry = {}
        
        if "tags" in obj:
            operation_params_only_entry["tags"] = obj["tags"]
        if "summary" in obj:
            operation_params_only_entry["summary"] = obj["summary"]
        if "description" in obj:
            operation_params_only_entry["description"] = obj["description"]
        
        if get_test_object:
            if "test_object" in obj and obj["test_object"] is not None:
                operation_params_only_entry["test_object"] = obj["test_object"].strip('\n')
        
        # parameters
        if "parameters" in obj and obj["parameters"]:
            if only_get_parameter_types == False:
                params = obj["parameters"]
                param_entry = {}
                
                if get_not_required_params:
                    for param in params:
                        if '$ref' in param:
                            param = get_ref(spec, param['$ref'])
                        
                        # get description string
                        description_string = ""
                        if get_description:
                            description_parent = find_object_with_key(param, "description")
                            if description_parent and not isinstance(description_parent["description"], dict):
                                description_string = " (description: " + description_parent["description"].strip(' .') + ")"
                
                        name, dtype = None, None
                        name_parent = find_object_with_key(param, "name")
                        type_parent = find_object_with_key(param, "type")
                        param_schema_parent = find_object_with_key(param, "$ref")
                        
                        if name_parent:
                            name = name_parent["name"]
                        if type_parent:
                            dtype = type_parent["type"]

                        if name is not None and param_schema_parent is not None:
                            param_schema = get_ref(spec, param_schema_parent["$ref"])
                            param_entry[name] = get_schema_params(param_schema, spec)
                        elif name is not None and dtype is not None:
                            param_entry[name] = dtype + description_string
                else:
                    for param in params:
                        if '$ref' in param:
                            param = get_ref(spec, param['$ref'])

                        # get description string
                        description_string = ""
                        if get_description:
                            description_parent = find_object_with_key(param, "description")
                            if description_parent and not isinstance(description_parent["description"], dict):
                                description_string = " (description: " + description_parent["description"].strip(' .') + ")"
                
                        name, dtype, required = None, None, None
                        name_parent = find_object_with_key(param, "name")
                        type_parent = find_object_with_key(param, "type")
                        param_schema_parent = find_object_with_key(param, "$ref")
                        
                        required_parent = find_object_with_key(param, "required")
                        if name_parent:
                            name = name_parent["name"]
                        if type_parent:
                            dtype = type_parent["type"]
                        
                        required = False
                        if required_parent:
                            required = required_parent["required"]

                        if required:
                            if name is not None and param_schema_parent is not None:
                                param_schema = get_ref(spec, param_schema_parent["$ref"])
                                param_entry[name] = get_schema_params(param_schema, spec)
                            elif name is not None and dtype is not None:
                                param_entry[name] = dtype + description_string
            else:
                # In detailed parameters mode, we will return the whole parameters object instead of just the name and type
                # Only keep 'name' and 'in' field
                param_entry = {}
                for param in obj["parameters"]:
                    if 'name' in param and 'in' in param:
                        if param['in'] == 'path':
                            param_entry[param['name']] = "PATH VARIABLE"
                        else:
                            param_entry[param['name']] = "QUERY PARAMETER"
            
            if param_entry:
                operation_params_only_entry["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            body_entry = {}
            
            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                if "$ref" in request_body_schema:
                    schema_name = request_body_schema["$ref"].split('/')[-1]
                    body_entry[f'schema of {schema_name}'] = get_schema_params(request_body_schema, spec, get_description=get_description)
                else:
                    body_entry = get_schema_params(request_body_schema, spec, get_description=get_description)

            if body_entry:
                operation_params_only_entry["requestBody"] = body_entry
        
        # responseBody (single response body)
        if get_response_body and ("responses" in obj or "response" in obj):
            response_entry = {}
            
            if method.lower() != "delete":
                if "responses" in obj:
                    responses = obj["responses"] 
                else:
                    responses = obj["response"]
                    
                success_response = None
                for rk, rv in responses.items():
                    if isSuccessStatusCode(rk):
                        success_response = rv
                        break
                
                if success_response is not None:    
                    schema_object_ref = find_object_with_key(success_response, "$ref")
                    
                    if schema_object_ref is not None:
                        schema_name = schema_object_ref["$ref"].split('/')[-1]
                        response_entry[f"schema of {schema_name}"] = get_schema_params(success_response, spec, get_description=get_description)
                    else:
                        response_entry = get_schema_params(success_response, spec, get_description=get_description)
                
                if response_entry:
                    operation_params_only_entry["responseBody"] = response_entry
                        
        if insert_test_data_file_link:
            test_data = {}
            try:
                operation_id = spec['paths'][object_name][method]["operationId"]
            except:
                operation_id = method.upper()
            unique_name = f"{convert_path_fn(object_name)}_{operation_id}"
            
            if "parameters" in obj and obj["parameters"] and operation_params_only_entry["parameters"] is not None:
                test_data["Parameter data"] = f"Data Files/{unique_name}_param"

            if "requestBody" in obj and obj["requestBody"] and operation_params_only_entry["requestBody"] is not None:
                test_data["Request body data"] = f"Data Files/{unique_name}_body"

            operation_params_only_entry["available_test_data"] = test_data
            
        operation_params_only_dict[operation] = operation_params_only_entry  # dict[str, dict[str, ]

    return operation_params_only_dict


def get_schema_required_fields(body, spec, visited_refs=None):
    if visited_refs is None:
        visited_refs = set()

    properties = find_object_with_key(body, "properties")
    ref = find_object_with_key(body, "$ref")
    schema = find_object_with_key(body, "schema")
    
    required_fields = []
    required_fields_spec = find_object_with_key(body, "required")
    if required_fields_spec is None:
        if properties is not None:
            return {}
    else:
        required_fields = required_fields_spec["required"]
    
    new_schema = {}
    if properties:
        for p, prop_details in properties["properties"].items():
            if p not in required_fields:
                continue
            
            p_ref = find_object_with_key(prop_details, "$ref")
            
            if "type" in prop_details:
                if prop_details["type"] == "array":
                    if p_ref:
                        new_schema[p] = {}
                        new_schema[p] = get_schema_required_fields(prop_details, spec, visited_refs=visited_refs)
                    else:
                        new_schema[p] = "array"
                else:
                    new_schema[p] = prop_details["type"]
                    
            elif p_ref:
                if p_ref["$ref"] in visited_refs:
                    continue
                
                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_required_fields(schema, spec, visited_refs=visited_refs)
                if child_schema is not None:
                    new_schema[p] = child_schema
                    
    elif ref:
        if ref["$ref"] in visited_refs:
            return None
        
        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_required_fields(schema, spec, visited_refs=visited_refs)
    else:
        return {}
    
    return new_schema

def get_required_fields(spec: dict):
    operations = extract_operations(spec)
    operation_params_only_dict = {}

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])  # dict[str, ]

        operation_params_only_entry = {}

        # parameters
        if "parameters" in obj and obj["parameters"]:
            params = obj["parameters"]
            param_entry = {}
            
            for param in params:
                if '$ref' in param:
                    param = get_ref(spec, param['$ref'])

                name, dtype, required = None, None, None
                name_parent = find_object_with_key(param, "name")
                type_parent = find_object_with_key(param, "type")
                param_schema_parent = find_object_with_key(param, "$ref")
                
                required_parent = find_object_with_key(param, "required")
                if name_parent:
                    name = name_parent["name"]
                if type_parent:
                    dtype = type_parent["type"]
                
                required = False
                if required_parent:
                    required = required_parent["required"]

                if required:
                    if name is not None and param_schema_parent is not None:
                        param_schema = get_ref(spec, param_schema_parent["$ref"])
                        param_entry[name] = get_schema_required_fields(param_schema, spec)
                    elif name is not None and dtype is not None:
                        param_entry[name] = dtype
                           
            operation_params_only_entry["parameters"] = param_entry
            
        # requestBody
        if "requestBody" in obj:
            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                operation_params_only_entry["requestBody"] = get_schema_required_fields(request_body_schema, spec)
            else:
                operation_params_only_entry["requestBody"] = {}
        else:
            operation_params_only_entry["requestBody"] = None
            
        operation_params_only_dict[operation] = operation_params_only_entry  # dict[str, dict[str, ]

    return operation_params_only_dict

def extract_ref_values(json_obj):
    refs = []

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key == "$ref":
                refs.append(value)
            else:
                refs.extend(extract_ref_values(value))  # Recursively search nested values
    elif isinstance(json_obj, list):
        for item in json_obj:
            refs.extend(extract_ref_values(item))  # Recursively search items in a list

    return list(set(refs))

def get_schema_recursive(body, spec, visited_refs=None):
    if visited_refs is None:
        visited_refs = set()

    schema_dict = {}
    schema_name_list = []
    schema_refs = extract_ref_values(body)

    for ref in schema_refs:        
        schema_name = ref.split("/")[-1]
        
        if ref not in visited_refs:  # Check if schema_name is already processed
            visited_refs.add(ref)
            
            schema_body = get_ref(spec, ref)  # Assuming get_ref is a function that retrieves the schema
            
            new_schema = get_schema_params(schema_body, spec, get_description=True, max_depth=0, ignore_attr_with_schema_ref=False)  # Assuming get_schema_params is a function that processes the schema
            if isinstance(new_schema, dict):
                schema_dict[schema_name] = new_schema
                schema_name_list.append(schema_name)  # Add schema_name only if it's new
            
            nested_schemas_body, nested_schemas_name = get_schema_recursive(schema_body, spec, visited_refs=visited_refs)
            schema_dict.update(nested_schemas_body)
            schema_name_list.extend(nested_schemas_name)
        
    return schema_dict, schema_name_list

def get_simplified_schema(spec: dict, ):
    simplified_schema_dict = {}
    
    operations = extract_operations(spec)

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])  # dict[str, ]
        
        # responseBody (single response body)
        if "responses" in obj:
            responses = obj["responses"] 
            success_response = None
            for rk, rv in responses.items():
                if isSuccessStatusCode(rk):
                    success_response = rv
                
                    schema_ref = find_object_with_key(success_response, "$ref")
                    if schema_ref is None:
                        continue
                    
                    simplified_schema, _ = get_schema_recursive(success_response, spec)
                    simplified_schema_dict.update(simplified_schema)
                    
    return simplified_schema_dict
    
def contains_required_parameters(operation, origin_spec):
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    obj = origin_spec["paths"][path][method]
    parameters_obj = find_object_with_key(obj, "parameters")
    if parameters_obj is None:
        return False
    parameters_obj = str(parameters_obj["parameters"])
    return "'required': True" in parameters_obj

def get_relevant_schemas_of_operation(operation, openapi_spec):
    main_response_schemas = []
    relevant_schemas = []
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    
    operation_spec = openapi_spec["paths"][path][method]
    
    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                _, new_relevant_schemas = get_schema_recursive(operation_spec["responses"][response_code], openapi_spec)
                if new_relevant_schemas:
                    main_response_schemas.append(new_relevant_schemas[0])
                relevant_schemas.extend(new_relevant_schemas)
    return list(set(main_response_schemas)), list(set(relevant_schemas))

def get_operations_belong_to_schemas(openapi):
    operations_belong_to_schemas = {}
    
    operations = extract_operations(openapi)
    for operation in operations:
        _,relevant_schemas = get_relevant_schemas_of_operation(operation, openapi)
        for schema in relevant_schemas:
            if schema not in operations_belong_to_schemas:
                operations_belong_to_schemas[schema] = [operation]
            elif operation not in operations_belong_to_schemas[schema]:
                operations_belong_to_schemas[schema].append(operation)
    return operations_belong_to_schemas


def add_test_object_to_openapi(openapi, object_repo_name="API"):
    """
    Add test object path to each of the operation's method in openapi Spec.

    Args:
        openapi (dict): openapi data
    """
    # Find the paths and method and add the new key-value pair of test_object
    for path in openapi['paths']:
        for method in openapi['paths'][path]:
            if method.lower() not in ['get', 'post', 'put', 'patch', 'delete']:
                continue
            
            if object_repo_name == "API":
                try:
                    object_repo_name = openapi["info"]["title"]
                except:
                    pass

            try:
                operation_id = openapi['paths'][path][method]["operationId"]
            except:
                operation_id = method.upper()

            openapi['paths'][path][method]['test_object'] = get_test_object_path(object_repo_name, operation_id, path)       
    return openapi

def get_test_object_path(api_title, operation_id, path):
    return f"Object Repository/{convert_path_fn(api_title)}/{convert_path_fn(path)}/{operation_id}"

def filter_params_has_description(operation_param_description):
    '''
    Filter out the parameters that do not have description
    This is for the purpose of detecting the inter-parameter dependencies. If a parameter does not have description, it is likely that it does not have any dependency.
    '''
    filtered_operation_param_description = {}
    for operation in operation_param_description:
        filtered_operation_param_description[operation] = {}
        if "parameters" in operation_param_description[operation] and operation_param_description[operation]["parameters"] is not None:
            filtered_operation_param_description[operation]["parameters"] = {}
            for param, value in operation_param_description[operation]["parameters"].items():
                if "description" in value:
                    filtered_operation_param_description[operation]["parameters"][param] = value
        if "requestBody" in operation_param_description[operation] and operation_param_description[operation]["requestBody"] is not None:
            filtered_operation_param_description[operation]["requestBody"] = {}
            for param, value in operation_param_description[operation]["requestBody"].items():
                if "description" in value:
                    filtered_operation_param_description[operation]["requestBody"][param] = value
    return filtered_operation_param_description

def get_operation_id(openapi_spec, operation):
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    
    operation_spec = openapi_spec["paths"][path][method]
    
    try:
        operation_id = operation_spec["operationId"]
    except:
        operation_id = method.upper()
    
    unique_name = f"{convert_path_fn(path)}_{operation_id}"
    return unique_name

def simplify_openapi(openapi: dict):
    operations = extract_operations(openapi)
    simple_openapi = {}

    for operation in operations:
        method = operation.split("-")[0]
        path = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(openapi["paths"][path][method])

        simple_operation_spec = {}
        
        if "summary" in obj:
            simple_operation_spec["summary"] = obj["summary"]
        
        # parameters
        if "parameters" in obj and obj["parameters"]:
            params = obj["parameters"]
            param_entry = {}
            
            for param in params:
                if '$ref' in param:
                    param = get_ref(openapi, param['$ref'])
                
                # get description string
                description_string = ""
                description_parent = find_object_with_key(param, "description")
                if description_parent and not isinstance(description_parent["description"], dict):
                    description_string = " (description: " + description_parent["description"].strip(' .') + ")"
        
                name, dtype = None, None
                name_parent = find_object_with_key(param, "name")
                type_parent = find_object_with_key(param, "type")
                param_schema_parent = find_object_with_key(param, "$ref")
                
                if name_parent:
                    name = name_parent["name"]
                if type_parent:
                    dtype = type_parent["type"]

                if name is not None and param_schema_parent is not None:
                    param_schema = get_ref(openapi, param_schema_parent["$ref"])
                    param_entry[name] = get_schema_params(param_schema, openapi)
                elif name is not None and dtype is not None:
                    param_entry[name] = dtype + description_string
        
            if param_entry:
                simple_operation_spec["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            body_entry = {}
            
            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                body_entry = get_schema_params(request_body_schema, openapi, get_description=True)

            if body_entry:
                simple_operation_spec["requestBody"] = body_entry
        
        # responseBody (single response body)
        if "responses" in obj or "response" in obj:
            response_entry = {}
            
            if method.lower() != "delete":
                if "responses" in obj:
                    responses = obj["responses"] 
                else:
                    responses = obj["response"]
                    
                success_response = None
                
                for rk, rv in responses.items():
                    if isSuccessStatusCode(rk):
                        success_response = rv
                        break
                        
                if success_response is not None:    
                    response_entry = get_schema_params(success_response, openapi, get_description=True)

                if response_entry:
                    simple_operation_spec["responseBody"] = response_entry
                    
        simple_openapi[operation] = simple_operation_spec

    return simple_openapi

def get_response_body_name_and_type(openapi, operation):
    method = operation.split('-')[0]
    endpoint = '-'.join(operation.split('-')[1:])
    
    operation_spec = openapi["paths"][endpoint][method]
    if "responses" not in operation_spec and "response" not in operation_spec:
        return
    
    response_spec = None
    if "responses" in operation_spec:
        response_spec = operation_spec["responses"]
    else:
        response_spec = operation_spec["response"]
        
    success_response = None
    for rk, rv in response_spec.items():
        if isSuccessStatusCode(rk):
            success_response = rv
            break
            
    if success_response is None:
        return
    
    response_type = None
    main_response_schema = None
    
    schema = find_object_with_key(success_response, "schema")
    if schema:
        response_type = schema["schema"].get("type", "object")
    
    properties = find_object_with_key(success_response, "properties")
    if properties:
        return None, response_type
    
    main_schema_ref = find_object_with_key(success_response, "$ref")
    if main_schema_ref:
        schema_name = main_schema_ref["$ref"].split("/")[-1]
        return schema_name, response_type
    
    return None, response_type

def get_relevent_response_schemas_of_operation(openapi_spec, operation):
    main_response_schemas = []
    relevant_schemas = []
    
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    
    operation_spec = openapi_spec["paths"][path][method]
    
    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                main_schema_ref = find_object_with_key(operation_spec["responses"][response_code], "$ref")
                if main_schema_ref:
                    main_response_schemas.append(main_schema_ref["$ref"].split('/')[-1])
                    _, new_relevant_schemas = get_schema_recursive(operation_spec["responses"][response_code], openapi_spec)
                    relevant_schemas.extend(new_relevant_schemas)
    return main_response_schemas, list(set(relevant_schemas))

def get_main_response_schemas_of_operation(openapi_spec, operation):
    main_response_schemas = []
    
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    
    operation_spec = openapi_spec["paths"][path][method]
    
    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                main_schema_ref = find_object_with_key(operation_spec["responses"][response_code], "$ref")
                if main_schema_ref:
                    main_response_schemas.append(main_schema_ref["$ref"].split('/')[-1])
    return main_response_schemas

def list_all_param_names(spec, d, visited_refs=None):
    if visited_refs is None:
        visited_refs = set()

    if d is None:
        return []

    if '$ref' in d:
        ref = d['$ref']
        if ref in visited_refs:
            return [] 
        visited_refs.add(ref)
        return list_all_param_names(spec, get_ref(spec, ref), visited_refs)

    if d.get('type') == 'object':
        res = list(d.get('properties', {}).keys())
        for val in d.get('properties', {}).values():
            res += list_all_param_names(spec, val, visited_refs)
        return res
    elif d.get('type') == 'array':
        return list_all_param_names(spec, d.get('items', {}), visited_refs)
    elif 'name' in d:
        return [d.get('name')]
    else:
        return []
    
def get_relevant_schema_of_operation(operation, openapi_spec):
    relevant_schemas = []
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    
    operation_spec = openapi_spec["paths"][path][method]
    
    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                _, new_relevant_schemas = get_schema_recursive(operation_spec["responses"][response_code], openapi_spec)
                relevant_schemas.extend(new_relevant_schemas)
    return list(set(relevant_schemas))