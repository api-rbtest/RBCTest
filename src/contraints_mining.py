from response_body_verification.data_model_buiding import *
from response_body_verification.constraint_inference import *
from response_body_verification.parameter_responsebody_mapping import *

from utils.convert_json_to_excel_annotation_file import (
    convert_json_to_excel_response_property_constraints,
    convert_json_to_excel_request_response_constraints
)

import os
import json
import openai
import dotenv

dotenv.load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')


def main():
    experiment_folder = "experiment_our"

#     service_names = [
#   "Github CreateOrganizationRepository",
#   "Github GetOrganizationRepositories",
#   "Hotel Search",
#   "Marvel getComicById",
#   "OMDB byIdOrTitle",
#   "OMDB bySearch",
#   "Spotify createPlaylist",
#   "Spotify getAlbumTracks",
#   "Spotify getArtistAlbums",
#   "Yelp getBusinesses",
#   "Youtube GetVideos"
# ]
    service_names = [
  "Canada Holidays",
  "GitLab Branch",
  "GitLab Commit",
  "GitLab Groups",
  "GitLab Issues",
  "GitLab Project",
  "GitLab Repository",
  "StripeClone"
];
    for service_name in service_names:
        print("=" * 50)
        print(f"🔍 Processing: {service_name}")
        print("=" * 50)

        openapi_path = f"RBCTest_dataset/{service_name}/openapi.json"
        output_dir = f"{experiment_folder}/{service_name}"
        os.makedirs(output_dir, exist_ok=True)

        # ========== 1. Extract RESPONSE PROPERTY CONSTRAINTS ==========
        print("→ Extracting response property constraints...")
        constraint_extractor = ConstraintExtractor(
            openapi_path=openapi_path,
            save_and_load=True,
            experiment_folder=experiment_folder
        )

        response_json_path = f"{output_dir}/response_property_constraints.json"
        constraint_extractor.get_inside_response_body_constraints(outfile=response_json_path)

        with open(response_json_path, "w", encoding="utf-8") as f:
            json.dump(constraint_extractor.inside_response_body_constraints, f, indent=2)

        convert_json_to_excel_response_property_constraints(
            response_json_path,
            openapi_path,
            response_json_path.replace(".json", ".xlsx")
        )

        # ========== 2. Extract REQUEST-RESPONSE CONSTRAINTS ==========
        print("→ Extracting request-response constraints...")
        input_json_path = f"{output_dir}/input_parameter.json"
        input_parameter_constraints = constraint_extractor.get_input_parameter_constraints(outfile=input_json_path)
        
        # Lưu input_parameter_constraints vào file
        with open(input_json_path, "w", encoding="utf-8") as f:
            json.dump(input_parameter_constraints, f, indent=2)

        reqresp_json_path = f"{output_dir}/request_response_constraints.json"
        parameter_mapper = ParameterResponseMapper(
            openapi_path=openapi_path,
            service_name=service_name,
            experiment_folder=experiment_folder,
            outfile=reqresp_json_path
        )

        convert_json_to_excel_request_response_constraints(
            json_file=reqresp_json_path,
            openapi_spec_file=openapi_path,
            output_file=reqresp_json_path.replace(".json", ".xlsx")
        )


if __name__ == "__main__":
    main()
