from response_body_verification.data_model_buiding import *
from response_body_verification.constraint_inference import *
from response_body_verification.parameter_responsebody_mapping import *

import openai
from eval.request_approach_evaluate import evaluate_request_response_constraint_mining
from utils.convert_json_to_excel_annotation_file import convert_json_to_excel_request_response_constraints
import os, dotenv
dotenv.load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')

def main():        
    # rest_services = ["GitLab Project", "GitLab Repository", "GitLab Commit", "GitLab Groups", "GitLab Issues", "Canada Holidays"]
    experiment_folder = "experiment_our"
    ground_truth_folder = "approaches/ground_truth"
    rest_services = ["GitLab Branch", "GitLab Project", "GitLab Repository", "GitLab Commit", "GitLab Groups", "GitLab Issues", "Canada Holidays", "StripeClone"]
    selected_operations = open("stripe_selected/selected_operations", "r").readlines()
    selected_operations = [operation.strip() for operation in selected_operations]

    selected_schemas = open("src/selected_schemas.txt", "r").readlines()
    selected_schemas = [schema.strip() for schema in selected_schemas]


    for rest_service in rest_services:
        print("\n"+"*"*20)
        print(rest_service)
        print("*"*20)

        openapi_path = f"RBCTest_dataset/{rest_service}/openapi.json"
        
        openapi_spec = load_openapi(openapi_path)
        service_name = openapi_spec["info"]["title"] 
        os.makedirs(f"{experiment_folder}/{service_name}", exist_ok=True)   
        
        # Find parameter constraints
        if rest_service == "StripeClone":
            constraint_extractor = ConstraintExtractor(openapi_path, save_and_load=False, list_of_operations=selected_operations)
        else:
            constraint_extractor = ConstraintExtractor(openapi_path, save_and_load=False)

        outfile = f"{experiment_folder}/{service_name}/response_property_constraints.json"
        constraint_extractor.get_input_parameter_constraints(outfile=outfile)
        with open(f"{experiment_folder}/{service_name}/response_property_constraints.json", "w") as f:
            json.dump(constraint_extractor.input_parameter_constraints, f, indent=2)
        
        list_of_schemas = json.load(open("response-verification/stripe_schemas.json","r"))
        outfile = f"{experiment_folder}/{service_name}/request_response_constraints.json"
        parameterResponseMapper = ParameterResponseMapper(openapi_path, save_and_load=False, outfile=outfile)
        with open(f"{experiment_folder}/{service_name}/request_response_constraints.json", "w") as f:
            json.dump(parameterResponseMapper.response_body_input_parameter_mappings, f, indent=2)    

        convert_json_to_excel_request_response_constraints(outfile, openapi_path, outfile.replace(".json", ".xlsx"))
        evaluate_request_response_constraint_mining(experiment_folder, ground_truth_folder, [service_name], f"{experiment_folder}/evaluation.csv", export=True)




if __name__ == "__main__":
    main()