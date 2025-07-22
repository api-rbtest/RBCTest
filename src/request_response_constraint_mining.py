# Thông qua input parameter
from response_body_verification.data_model_buiding import *
from response_body_verification.constraint_inference import *
from response_body_verification.parameter_responsebody_mapping import *
from utils.convert_json_to_excel_annotation_file import convert_json_to_excel_request_response_constraints
import openai

import os
import dotenv
dotenv.load_dotenv()
openai.api_key = os.getenv('OPENAI_KEY')


def main():
#     service_names =[
#   "Canada Holidays",
#   "GitLab Branch",
#   "GitLab Commit",
#   "GitLab Groups",
#   "GitLab Issues",
#   "GitLab Project",
#   "GitLab Repository",
#   "LanguageTool",
#   "magento",
#   "omdb",
#   "spotifyweb",
#   "StripeClone",
#   "telegrambot",
#   "travinq-provesio",
#   "twitter"
# ]
    service_names = [
    "Github CreateOrganizationRepository",
    "Github GetOrganizationRepositories",
    "Hotel Search",
    "Marvel getComicById",
    "OMDB byIdOrTitle",
    "OMDB bySearch",
    "Spotify createPlaylist",
    "Spotify getAlbumTracks",
    "Spotify getArtistAlbums",
    "Yelp getBusinesses",
    "Youtube GetVideos"
    ]


    
    for service_name in service_names:
        print(f"Processing {service_name}...")
        
        # Đường dẫn đến file openapi.json
        openapi_path = f"RBCTest_dataset/{service_name}/openapi.json"
        
        # Đường dẫn đến thư mục output
        output_dir = f"experiment_our/{service_name}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Khởi tạo ConstraintExtractor
        constraint_extractor = ConstraintExtractor(
            openapi_path=openapi_path,
            save_and_load=True,
            experiment_folder="experiment_our"
        )
        
        # Lấy constraints từ input parameters
        outfile = f"{output_dir}/input_parameter.json"
        input_parameter_constraints = constraint_extractor.get_input_parameter_constraints(outfile=outfile)
        
        # Khởi tạo ParameterResponseMapper
        outfile = f"{output_dir}/request_response_constraints.json"
        parameterResponseMapper = ParameterResponseMapper(
            openapi_path=openapi_path,
            service_name=service_name,
            experiment_folder="experiment_our",
            outfile=outfile
        )
        
        # Chuyển đổi JSON sang Excel
        outfile = f"{output_dir}/request_response_constraints.xlsx"
        convert_json_to_excel_request_response_constraints(
            json_file=f"{output_dir}/request_response_constraints.json",
            openapi_spec_file=openapi_path,
            output_file=outfile
        )
        
        # Lấy constraints từ response body
        outfile = f"{output_dir}/response_property_constraints.json"
        constraint_extractor.get_inside_response_body_constraints(outfile=outfile)


if __name__ == "__main__":
    main()
