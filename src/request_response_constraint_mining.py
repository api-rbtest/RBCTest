# Thông qua input parameter
from response_body_verification.data_model_buiding import *
from response_body_verification.constraint_inference import *
from response_body_verification.parameter_responsebody_mapping import *
from utils.convert_json_to_excel_annotation_file import convert_json_to_excel_response_property_constraints
import openai

import os
import dotenv
dotenv.load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')


def main():
    experiment_folder = "experiment_our"

    rest_services = ["Spotify getArtistAlbums"]

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
            pass
            # constraint_extractor = ConstraintExtractor(
            #     openapi_path, save_and_load=False, list_of_operations=selected_operations)
        else:
            constraint_extractor = ConstraintExtractor(
                openapi_path, save_and_load=False)

        outfile = f"{experiment_folder}/{service_name}/input_parameter.json"
        constraint_extractor.get_input_parameter_constraints(outfile=outfile)
        with open(f"{experiment_folder}/{service_name}/input_parameter.json", "w") as f:
            json.dump(
                constraint_extractor.input_parameter_constraints, f, indent=2)
        outfile = f"{
            experiment_folder}/{service_name}/request_response_constraints.json"
        parameterResponseMapper = ParameterResponseMapper(
            openapi_path, save_and_load=False, outfile=outfile)
        with open(f"{experiment_folder}/{service_name}/request_response_constraints.json", "w") as f:
            json.dump(
                parameterResponseMapper.response_body_input_parameter_mappings, f, indent=2)
            
        convert_json_to_excel_response_property_constraints(
            outfile, openapi_path, outfile.replace(".json", ".xlsx"))


if __name__ == "__main__":
    main()
