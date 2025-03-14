from openapi_utils import *
import pandas as pd

def convert_json_to_excel_request_response_constraints(json_file, openapi_spec_file, output_file):
    if not os.path.exists(json_file) or not os.path.exists(openapi_spec_file):
        print(f"File {json_file} does not exist")
        return
    openapi_spec = json.load(open(openapi_spec_file, "r", encoding="utf-8"))
    simplified_openapi = simplify_openapi(openapi_spec)
    simplified_schemas = get_simplified_schema(openapi_spec)

    selected_operations = open("src/stripe_selected/selected_operations.txt", "r").readlines()
    selected_operations = [operation.strip() for operation in selected_operations]

    service_name = openapi_spec["info"]["title"]
    response_body_input_parameter_mappings_with_constraint = json.load(open(json_file, "r"))

    data = []
    operations_with_constraint = set()

    for operation in simplified_openapi:
        relevant_schemas = get_main_response_schemas_of_operation(openapi_spec, operation)
        for schema in relevant_schemas:
            mappings_with_constraint = response_body_input_parameter_mappings_with_constraint.get(schema, {})
            # if mappings_with_constraint != {}:
            for attr in mappings_with_constraint:
                mappings = mappings_with_constraint[attr]
                mappings = list(map(tuple, set(map(tuple, mappings))))
                
                attribute_description = simplified_schemas[schema].get(attr, "")
                if "(description:" not in attribute_description:
                    attribute_description = None
                else:
                    attribute_description = attribute_description.split("(description:")[-1][:-1].strip()
                    
                for mapping in mappings:
                    corresponding_operation = mapping[0]
                    corresponding_part = mapping[1]
                    corresponding_attribute = mapping[2]
                    
                    corresponding_attribute_description = simplified_openapi[corresponding_operation].get(corresponding_part, {}).get(corresponding_attribute, "")
                    if "(description:" not in corresponding_attribute_description:
                        corresponding_attribute_description = None
                    else:
                        corresponding_attribute_description = corresponding_attribute_description.split("(description:")[-1][:-1].strip()
                    new_instance = {
                        # "operation": operation,
                        "response resource": schema,
                        "attribute": attr,
                        "description": attribute_description,
                        "attribute inferred from operation": corresponding_operation,
                        "part": corresponding_part,
                        "corresponding attribute": corresponding_attribute,
                        "corresponding attribute description": corresponding_attribute_description,
                    }
                    if new_instance not in data:
                        data.append(new_instance)
                    
                    operations_with_constraint.add(operation)

    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)

    print(f"No. of operations having constraints inferred from input parameters: {len(operations_with_constraint)}")
    

def convert_json_to_excel_response_property_constraints(json_file, openapi_spec_file, output_file):
    if not os.path.exists(json_file) or not os.path.exists(openapi_spec_file):
        print(f"File {json_file} does not exist")
        return

    openapi_spec = json.load(open(openapi_spec_file, "r", encoding="utf-8-sig"))
    simplified_openapi = simplify_openapi(openapi_spec)
    simplified_schemas = get_simplified_schema(openapi_spec)

    service_name = openapi_spec["info"]["title"]

    selected_operations = open("src/stripe_selected/selected_operations.txt", "r").readlines()
    selected_operations = [operation.strip() for operation in selected_operations]

    selected_schemas = open("src/stripe_selected/selected_schemas.txt", "r").readlines()
    selected_schemas = [schema.strip() for schema in selected_schemas]
    
    inside_response_body_constraints = json.load(open(json_file, "r"))
    print(inside_response_body_constraints)


    data = []

    no_of_constraints = 0
    operations_with_constraint = set()

    for operation in simplified_openapi:
        if service_name == "StripeClone API" and operation not in selected_operations:
            continue
        _, relevant_schemas = get_relevent_response_schemas_of_operation(openapi_spec, operation)
        
        for schema in relevant_schemas:
            if service_name == "StripeClone API" and schema not in selected_schemas:
                continue
            attributes_with_constraint = inside_response_body_constraints.get(schema, {})
            
            for attribute in attributes_with_constraint:
                data.append({
                    "operation": operation,
                    "response resource": schema,
                    "attribute": attribute,
                    "description": attributes_with_constraint[attribute],
                })
                no_of_constraints += 1
                operations_with_constraint.add(operation)
    # remove duplicates and keep the first occurrence
    data = [dict(t) for t in {tuple(d.items()) for d in data}]
    if not data:
        data = [{"operation": "", "response resource": "", "attribute": "", "description": ""}]
    df = pd.DataFrame(data)
    df.to_excel(f"{output_file}", index=False)
    print(f"Converted to {output_file}")
    print(f"No. of constraints in response bodies: {no_of_constraints}")
    print(f"No. of operation having constraints inside response body: {len(operations_with_constraint)}")


def main():
    service_names = ["Spotify getArtistAlbums"]
    output_folder = "experiment_our"
    dataset_folder = "RBCTest_dataset"
    approach = ""
    for service_name in service_names:
        json_file = f"{output_folder}/{service_name} API/request_response_constraints.json"
        openapi_spec_file = f"{dataset_folder}/{service_name}/openapi.json"
        output_file = f"{output_folder}/{service_name} API/request_response_constraints.xlsx"
        convert_json_to_excel_request_response_constraints(json_file, openapi_spec_file, output_file)

        # json_file = f"{output_folder}/{service_name} API/response_property_constraints.json"
        # output_file = f"{output_folder}/{service_name} API/response_property_constraints.xlsx"
        # convert_json_to_excel_response_property_constraints(json_file, openapi_spec_file, output_file)


if __name__ == "__main__":
    main()