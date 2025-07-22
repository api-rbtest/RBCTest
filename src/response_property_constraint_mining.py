from response_body_verification.data_model_buiding import *
from response_body_verification.constraint_inference import *
from response_body_verification.parameter_responsebody_mapping import *

import openai
from utils.convert_json_to_excel_annotation_file import convert_json_to_excel_response_property_constraints
from eval.response_approach_evaluate import evaluate_response_property_constraint_mining
import os, dotenv
dotenv.load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')

def main():        
    experiment_folder = "experiment_our"
    ground_truth_folder = "approaches/ground_truth"

    rest_services = ["Spotify getArtistAlbums"]


    selected_schemas = open("src/stripe_selected/selected_schemas.txt").readlines()
    selected_schemas = [schema.strip() for schema in selected_schemas]

    selected_operations = open("src/stripe_selected/selected_operations.txt").readlines()
    selected_operations = [operation.strip() for operation in selected_operations]

    for rest_service in rest_services:
        print("*"*20)
        print(rest_service)
        print("*"*20)
        # openapi_path = r"RBCTest_dataset\Github CreateOrganizationRepository\swagger_createAnOrganizationRepository.json"
        openapi_path = f"RBCTest_dataset/{rest_service}/openapi.json"
        
        openapi_spec = load_openapi(openapi_path)
        print(openapi_spec)
        service_name = openapi_spec["info"]["title"] 
        os.makedirs(f"{experiment_folder}/{service_name}", exist_ok=True)   

        outfile = f"{experiment_folder}/{service_name}/response_property_constraints.json"

        if rest_service == "StripeClone":
            constraint_extractor = ConstraintExtractor(openapi_path, save_and_load=False, list_of_operations=selected_operations)
            constraint_extractor.get_inside_response_body_constraints(outfile=outfile, selected_schemas=selected_schemas)
        else:
            constraint_extractor = ConstraintExtractor(openapi_path, save_and_load=False)
            constraint_extractor.get_inside_response_body_constraints(outfile=outfile)

        with open(outfile, "w") as f:
            json.dump(constraint_extractor.inside_response_body_constraints, f, indent=2)

        convert_json_to_excel_response_property_constraints(outfile, openapi_path, outfile.replace(".json", ".xlsx"))
        evaluate_response_property_constraint_mining(experiment_folder, ground_truth_folder, [service_name], f"{experiment_folder}/evaluation.csv", export=True)
            
                      
if __name__ == "__main__":
    main()