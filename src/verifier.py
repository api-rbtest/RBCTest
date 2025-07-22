root_folder = r"approaches\rbctest_our_data"
# root_folder = r"experiment_our"
api_spec_folder = r"RBCTest_dataset"
import json
import os
import random
import re
import pandas as pd
import uuid
from verifier.find_example_utils import find_example_value, load_openapi_spec 
from execute_code_in_excel import get_api_responses
EXECUTABLE = "python"

import subprocess

def find_replace_and_keep_recursively(search_data, field, new_value):
    """
    Takes a dict or a list of dicts with nested lists and dicts,
    searches all dicts for a key of the field provided,
    replaces its value with new_value,
    and retains only the path to the found field and its value.
    """
    if isinstance(search_data, dict):
        for key, value in search_data.items():
            if key == field:
                return {key: new_value}
            elif isinstance(value, dict):
                result = find_replace_and_keep_recursively(value, field, new_value)
                if result:
                    return {key: result}
            elif isinstance(value, list):
                results = []
                for item in value:
                    if isinstance(item, dict):
                        result = find_replace_and_keep_recursively(item, field, new_value)
                        if result:
                            results.append(result)
                if results:
                    return {key: results}
    
    elif isinstance(search_data, list):
        results = []
        for item in search_data:
            if isinstance(item, dict):
                result = find_replace_and_keep_recursively(item, field, new_value)
                if result:
                    results.append(result)
        return results if results else None
    
    return None

def execute_command(command):
    try:
        # Execute the command and capture the output
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Return the output if the command was successful
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Return None or handle the error if the command fails
        return None

def execute_python(file_path):
    result = execute_command([EXECUTABLE, file_path])
    return result

def response_property_constraint_verify(python_code, field_name, example_value, api_response):
    if "28" in api_response and field_name == "enabled_events":
        print("Error")
        
    api_response = json.loads(api_response)
    original_api_response = api_response.copy()
    api_response = find_replace_and_keep_recursively(api_response, field_name, example_value)
    if api_response is None:
        api_response = {} if isinstance(original_api_response, dict) else []
    api_response = json.dumps(api_response)

    uuid_str = str(uuid.uuid4())
    file_name = f"code/api_response_{uuid_str}.json"
    with open(file_name, "w") as f:
        f.write(api_response)

    verify_code = f"""
{python_code}
import json
latest_response = json.loads(open("{file_name}").read())
status = verify_latest_response(latest_response)
print(status)
    """

    with open("verify.py", "w") as f:
        f.write(verify_code)

    result = execute_python("verify.py")
    if result == '-1':
        with open("verify.py", "w") as f:
            f.write(verify_code)
        input(f"python_code: {python_code}\nfield_name: {field_name}\nexample_value: {example_value}\napi_response: {api_response}")
    return result


def request_response_constraint_verify(python_code, request_information, request_param, field_name, example_value, api_response):
    try:
        api_response = json.loads(api_response)
        original_api_response = api_response.copy()
        api_response = find_replace_and_keep_recursively(api_response, field_name, example_value)
        if api_response is None:
            api_response = {} if isinstance(original_api_response, dict) else []

        api_response = json.dumps(api_response)

        request_information = json.loads(request_information)
        if request_param == field_name:
            request_information[request_param] = example_value
        else:
            if request_param in request_information:
                del request_information[request_param]
        request_information = json.dumps(request_information)

    except Exception as e:
        print("Error")
        input(f"{e}\npython_code: {python_code}\nrequest_information: {request_information}\nrequest_param: {request_param}\nfield_name: {field_name}\nexample_value: {example_value}\napi_response: {api_response}")
        return "UNKNOWN"

    uuid_str = str(uuid.uuid4())
    file_name = f"code/api_response_{uuid_str}.json"

    with open(file_name, "w") as f:
        f.write(api_response)

    request_info_file = f"code/request_info_{uuid_str}.json"
    with open(request_info_file, "w") as f:
        f.write(request_information)

    verify_code = f"""
{python_code}
import json
latest_response = json.loads(open("{file_name}").read())
request_info = json.loads(open("{request_info_file}").read())
status = verify_latest_response(latest_response, request_info)
print(status)
    """

    with open("verify.py", "w") as f:
        f.write(verify_code)

    result = execute_python("verify.py")
    if result == '-1':
        with open("verify.py", "w") as f:
            f.write(verify_code)
        input(f"python_code: {python_code}\nfield_name: {field_name}\nexample_value: {example_value}\napi_response: {api_response}")

    return result


apis = [f for f in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, f))]
count_example_found = 0
count_all_constraints = 0

print("Start verifying constraints", apis)
for api in apis:
    if "Can" not in api:
        continue
    api_folder = os.path.join(root_folder, api)

    api_responses = get_api_responses(os.path.join(api_spec_folder, api.replace(" API", "")))    
    api_responses = random.sample(api_responses, min(10, len(api_responses)))

    request_params = [os.path.join(api_spec_folder, api.replace(" API", ""), "queryParameters", 
                                         os.path.basename(f)) for f in api_responses]
    
    request_bodies = [os.path.join(api_spec_folder, api.replace(" API", ""), "bodyParameters",
                                      os.path.basename(f)) for f in api_responses]
    
    response_constraints_file = os.path.join(api_folder, "response_property_constraints.xlsx")
    request_response_constraints_file = os.path.join(api_folder, "request_response_constraints.xlsx")
    if os.path.exists(response_constraints_file):
        df = pd.read_excel(response_constraints_file)
        # if not have col "Example_value" then add col "Example_value" to df
        if 'Example_value' not in df.columns:
            df['Example_value'] = None

        if 'verify_result' not in df.columns:
            df['verify_result'] = None

        openapi_spec_file = os.path.join(api_spec_folder, api.replace(" API", ""), "openapi.json")
        openapi_spec = load_openapi_spec(openapi_spec_file)
        for index, row in df.iterrows():
            object_name = row['response resource']
            field_name = row['attribute']
            example_value = find_example_value(openapi_spec, object_name, field_name)
            df.at[index, 'Example_value'] = str(example_value)
            count_all_constraints += 1
            if example_value is not None:
                count_example_found += 1

                python_code = row['verification script']
                df.at[index, 'verify_result'] = 1
                if python_code is not None:
                    for api_response in api_responses:
                        api_response = open(api_response, "r", encoding="utf-8").read()
                        result = response_property_constraint_verify(python_code, field_name, example_value, api_response)
                        if result == '-1':
                            df.at[index, 'verify_result'] = 0
                            break

                
            

    if os.path.exists(response_constraints_file):
        df.to_excel(response_constraints_file)


    if os.path.exists(request_response_constraints_file):
        df = pd.read_excel(request_response_constraints_file)
        # if not have col "Example_value" then add col "Example_value" to df
        if 'Example_value' not in df.columns:
            df['Example_value'] = None

        if 'verify_result' not in df.columns:
            df['verify_result'] = None

        openapi_spec_file = os.path.join(api_spec_folder, api.replace(" API", ""), "openapi.json")
        openapi_spec = load_openapi_spec(openapi_spec_file)
        for index, row in df.iterrows():
            object_name = row['response resource']
            field_name = row['attribute']
            example_value = find_example_value(openapi_spec, object_name, field_name)
            df.at[index, 'Example_value'] = str(example_value)
            request_info_part = row['part']
            if request_info_part == 'requestBody':
                request_informations = request_bodies
            else:
                request_informations = request_params

            count_all_constraints += 1
            if example_value is not None:
                count_example_found += 1

                python_code = row['verification script']
                request_param = row['corresponding attribute']
                
                if python_code is not None:
                    df.at[index, 'verify_result'] = 1
                    for api_response, request_information in zip(api_responses, request_informations):
                        api_response = open(api_response, "r", encoding="utf-8").read()
                        request_information = open(request_information, "r", encoding="utf-8").read()

                        result = request_response_constraint_verify(python_code, request_information, request_param, field_name, example_value, api_response)
                        if result == '-1':
                            df.at[index, 'verify_result'] = 0
                            break



    if os.path.exists(request_response_constraints_file):
        df.to_excel(request_response_constraints_file.replace(".xlsx", ".xlsx"))

print(f"Found example value for {count_example_found}/{count_all_constraints} constraints")