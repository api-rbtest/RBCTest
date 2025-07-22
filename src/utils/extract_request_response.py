# RBCTest_dataset\Hotel Search\AmadeusHotel_50.csv
# read the csv file as pd df, get the col queryParameters, responseBody
# for each row, write responseBodies to a json file in the subfolder name responseBodies
# for each row, write queryParameters to a json file in the subfolder name queryParameters

import pandas as pd
import os
import json

from urllib.parse import parse_qs

def query_to_dict(query_string):
    # Parse the query string into a dictionary
    if not isinstance(query_string, str):
        return {}
    query_string = query_string.replace(";", "&")
    parsed_query = parse_qs(query_string)

    # Convert lists to single values
    parsed_query = {k: v[0] if len(v) == 1 else v for k, v in parsed_query.items()}

    # Convert the dictionary to a JSON string

    return parsed_query

def write_json_file(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main():
    csv_file_path = r'RBCTest_dataset/StripeClone/requests.csv'
    df = pd.read_csv(csv_file_path, encoding="utf-8")
    for index, row in df.iterrows():
        query_parameters = row["queryParameters"]
        response_bodies = row["responseBody"]
        body_parameters = row["bodyParameter"]
        path_parameters = row["pathParameters"]

        # if last char of query_parameters is ;, append path_parameters to query_parameters
        # if isinstance(path_parameters, str) and isinstance(query_parameters, str):
        #     if len(query_parameters) > 0 and query_parameters[-1] == ";":
        #         query_parameters += path_parameters
        #     else:
        #         query_parameters += ";" + path_parameters

        response_bodies_path = f"responseBody/{index}.json"
        query_parameters_path = f"queryParameters/{index}.json"
        body_parameters_path = f"bodyParameters/{index}.json"

        root_folder = os.path.dirname(csv_file_path)
        response_bodies_path = os.path.join(root_folder, response_bodies_path)
        query_parameters_path = os.path.join(root_folder, query_parameters_path)
        body_parameters_path = os.path.join(root_folder, body_parameters_path)

        os.makedirs(os.path.dirname(response_bodies_path), exist_ok=True)
        os.makedirs(os.path.dirname(query_parameters_path), exist_ok=True)
        os.makedirs(os.path.dirname(body_parameters_path), exist_ok=True)

        # query_parameters = query_to_dict(query_parameters)
        query_parameters = json.loads(query_parameters) if isinstance(query_parameters, str) else {}
        response_bodies = json.loads(response_bodies) if isinstance(response_bodies, str) else {}
        body_parameters = json.loads(body_parameters) if isinstance(body_parameters, str) else {}
        write_json_file(response_bodies, response_bodies_path)
        write_json_file(query_parameters, query_parameters_path)
        write_json_file(body_parameters, body_parameters_path)

if __name__ == "__main__":
    main()