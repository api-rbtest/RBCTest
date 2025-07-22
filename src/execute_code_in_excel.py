from datetime import datetime
import json
import os
import time
import pandas as pd
# import uuid
import uuid
EXECUTION_SCRIPT = '''\
{generated_verification_script}

import json
latest_response = json.loads(open("{file_path}",).read())
status = verify_latest_response(latest_response)
print(status)
'''


INPUT_PARAM_EXECUTION_SCRIPT = '''\
{generated_verification_script}

import json

def pre_check(json, key):
    if isinstance(json, dict):
        for k, v in json.items():
            if k == key:
                return True
            if pre_check(v, key):
                return True
    elif isinstance(json, list):
        for item in json:
            if pre_check(item, key):
                return True
    return False


latest_response = json.loads(open("{api_response}", encoding="utf-8").read())
request_info = json.loads(open("{request_info}", encoding="utf-8").read())

if not pre_check(request_info, "{request_param}") or not pre_check(latest_response, "{field_name}"):
    status = 0
    
else:
    status = verify_latest_response(latest_response, request_info)
print(status)
'''

def execute_request_parameter_constraint_verification_script(python_code, api_response, request_info, request_param, field_name):
    script_string = INPUT_PARAM_EXECUTION_SCRIPT.format(
        generated_verification_script = python_code,
        api_response = api_response,
        request_info = request_info,
        request_param = request_param,
        field_name = field_name,
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"
    
    code = namespace['status']
    status = ""
    if code == -1:
        status = "mismatched"
        error_codes_folder = "error_codes"
        os.makedirs(error_codes_folder, exist_ok=True)
        file_name = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.py"
        with open(os.path.join(error_codes_folder, file_name), "w") as f:
            f.write(script_string)

    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def execute_response_constraint_verification_script(python_code, file_path):
    script_string = EXECUTION_SCRIPT.format(
        generated_verification_script = python_code,
        file_path = file_path
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"
    
    code = namespace['status']
    status = ""
    if code == -1:
        status = "mismatched"
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def fix_json(json_str):
    # if // is in the json_str and // not inside double quote, delete until the end of the line, or { or [
    lines = json_str.split("\n")
    new_lines = []
    for line in lines:
        if "//" in line:
            # if // is in the json_str and // not inside double quote, delete until the end of the line, or { or [
            new_line = ""
            inside_double_quote = False
            for i in range(len(line)):
                if line[i] == '"':
                    inside_double_quote = not inside_double_quote
                if not inside_double_quote:
                    if line[i:i+2] == "//":
                        break
                new_line += line[i]
            line = new_line
        new_lines.append(line)
    return "\n".join(new_lines)

def get_request_informations(dataset_folder):
    request_informations = []
    for file in os.listdir(os.path.join(dataset_folder, "queryParameters")):
        request_informations.append(os.path.join(dataset_folder, "queryParameters", file).replace("\\", "/"))
    return request_informations

def get_api_responses(dataset_folder):
    api_responses = []
    for file in os.listdir(os.path.join(dataset_folder, "responseBody")):
        api_responses.append(os.path.join(dataset_folder, "responseBody", file).replace("\\", "/"))
    return api_responses

def get_request_bodies(dataset_folder):
    request_bodies = []
    for file in os.listdir(os.path.join(dataset_folder, "bodyParameters")):
        request_bodies.append(os.path.join(dataset_folder, "bodyParameters", file).replace("\\", "/"))
    return request_bodies

def re_execute_code(code_excel, is_req_res=False, dataset_folder=None):
    df = pd.read_excel(code_excel)
    df = df.fillna("")
    count = 0

    for index, row in df.iterrows():
        request_informations = []
        api_responses = []
        request_bodies = []

        if "attribute inferred from operation" in df.columns:
            df_filter_operation = df[df["attribute inferred from operation"] == row["attribute inferred from operation"]]
            operation = row["attribute inferred from operation"]
        else:
            operation = row["operation"]
            df_filter_operation = df[df["operation"] == operation]

        response_bodies = df_filter_operation["API response"].tolist()
        for i, response_body in enumerate(response_bodies):
            if response_body == "" or response_body == "nan" or not isinstance(response_body, str):
                response_body = "{}"
            file_path = os.path.abspath(os.path.join(dataset_folder, operation, "responseBody", f"{i}.json")).replace("\\", "/")
            os.makedirs(os.path.abspath(os.path.join(dataset_folder, operation, "responseBody")), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(response_body)
            api_responses.append(file_path)

        if is_req_res:
            request_information = df_filter_operation["request information"].tolist()
            for i, request_info in enumerate(request_information):
                if request_info == "" or request_info == "nan" or not isinstance(request_info, str):
                    request_info = "{}"
                file_path = os.path.abspath(os.path.join(dataset_folder, operation, "queryParameters", f"{i}.json")).replace("\\", "/")
                os.makedirs(os.path.abspath(os.path.join(dataset_folder, operation, "queryParameters")), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(request_info)
                request_informations.append(file_path)

            request_body = df_filter_operation["request information"].tolist()
            for i, request in enumerate(request_body):
                if request == "" or request == "nan" or not isinstance(request, str):
                    request = "{}"
                file_path = os.path.abspath(os.path.join(dataset_folder, operation, "bodyParameters", f"{i}.json")).replace("\\", "/")
                os.makedirs(os.path.abspath(os.path.join(dataset_folder, operation, "bodyParameters")), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(request)
                request_bodies.append(file_path)
        else:
            request_informations = request_bodies = ["{}"] * len(api_responses)


        code = row["verification script"]

        execution_statuses = []
        satisfied = 0
        mismatched = 0
        unknown = 0
        code_error = 0
        mismatches_json = []
        for i, api_response, request_information, request_body in zip(range(len(api_responses)), api_responses, request_informations, request_bodies):
            if not is_req_res:
                executable_script, new_execution_status = execute_response_constraint_verification_script(code, api_response, )
            else:
                part = row["part"]
                parameter = row["corresponding attribute"]
                field_name = row["attribute"]

                if part == "parameters":
                    executable_script, new_execution_status = execute_request_parameter_constraint_verification_script(code, api_response, request_information, parameter, field_name)
                else:
                    executable_script, new_execution_status = execute_request_parameter_constraint_verification_script(code, api_response, request_body, parameter, field_name)
            execution_statuses.append(new_execution_status)
            if new_execution_status == "satisfied":
                satisfied += 1
            elif new_execution_status == "mismatched":
                mismatched += 1
                mismatches_json.append(api_response)
                mismatched_code_folder = os.path.join("code", "mismatched")
                os.makedirs(mismatched_code_folder, exist_ok=True)
                with open(os.path.join(mismatched_code_folder, f"{uuid.uuid4()}.py"), "w") as f:
                    f.write(executable_script)
            elif new_execution_status == "code error":
                code_error += 1
                code_error_folder = os.path.join("code", "code_error")
                os.makedirs(code_error_folder, exist_ok=True)
                with open(os.path.join(code_error_folder, f"{uuid.uuid4()}.py"), "w") as f:
                    f.write(executable_script)
            else:
                unknown += 1

        df.at[index, "satisfied"] = True if satisfied > 0 else False
        df.at[index, "mismatched"] = True if mismatched > 0 else False
        df.at[index, "unknown"] = False if satisfied > 0 or mismatched > 0 else True
        df.at[index, "code error"] = code_error

        with open("code/{index}.py".format(index=index), "w") as f:
            f.write(executable_script)

        count += 1

    df.to_excel(code_excel.replace(".xlsx", ".xlsx"), index=False)
    print(f"Re-executed {count} code")


if __name__ == "__main__":
    if not os.path.exists("code"):
        os.makedirs("code")
        
    approach_folder = "approaches/rbctest_our_data"
    api_names = ["GitLab Repository"]
    # , "GitLab Issues", "GitLab Project", "GitLab Repository", "GitLab Branch", "GitLab Commit"]
    # , "GitLab Groups", "GitLab Issues", "GitLab Project", "GitLab Repository", "GitLab Branch"]
    for api_name in api_names:
        dataset_folder = f"RBCTest_dataset/{api_name}"
        rr_file = f'{approach_folder}/{api_name} API/request_response_constraints.xlsx'
        rp_file = f'{approach_folder}/{api_name} API/response_property_constraints.xlsx'
        if not os.path.exists(dataset_folder):
            print(f"{dataset_folder} does not exist")
            continue
        if os.path.exists(rr_file):
            print(f"Executing codes in {rr_file}")
            re_execute_code(rr_file, is_req_res=True, dataset_folder=dataset_folder)
        else:
            print(f"{rr_file} does not exist")
            
        if os.path.exists(rp_file):
            print(f"Executing codes in {rp_file}")
            re_execute_code(rp_file, dataset_folder=dataset_folder)
        else:
            print(f"{rp_file} does not exist")