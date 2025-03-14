root_folder = r"approaches\rbctest_our_data"
api_spec_folder = r"RBCTest_dataset"
import os
import pandas as pd
from find_example_utils import find_example_value, load_openapi_spec 

apis = [f for f in os.listdir(root_folder) if os.path.isdir(os.path.join(root_folder, f))]
count_example_found = 0
count_all_constraints = 0

for api in apis:
    api_folder = os.path.join(root_folder, api)
    response_constraints_file = os.path.join(api_folder, "response_property_constraints.xlsx")
    request_response_constraints_file = os.path.join(api_folder, "request_response_constraints.xlsx")
    if os.path.exists(response_constraints_file):
        df = pd.read_excel(response_constraints_file)
        # if not have col "Example_value" then add col "Example_value" to df
        if 'Example_value' not in df.columns:
            df['Example_value'] = None

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



    if os.path.exists(request_response_constraints_file):
        df = pd.read_excel(request_response_constraints_file)
        # if not have col "Example_value" then add col "Example_value" to df
        if 'Example_value' not in df.columns:
            df['Example_value'] = None

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

    if os.path.exists(response_constraints_file):
        df.to_excel(response_constraints_file.replace(".xlsx", "_example_value.xlsx"))

    if os.path.exists(request_response_constraints_file):
        df.to_excel(request_response_constraints_file.replace(".xlsx", "_example_value.xlsx"))

print(f"Found example value for {count_example_found}/{count_all_constraints} constraints")