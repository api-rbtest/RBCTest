

import pandas as pd
import re
import os
from specification_parser import SpecificationParser
import json

apis = ["Canada Holidays API", "GitLab Branch API",
        "GitLab Commit API", "GitLab Groups API", "GitLab Issues API", "GitLab Project API", "GitLab Repository API", "StripeClone API"]
# apis = [
#     "Github CreateOrganizationRepository",
#     "Github GetOrganizationRepositories",
#     "Hotel Search",
#     "Marvel getComicById",
#     "OMDB byIdOrTitle",
#     "OMDB bySearch",
#     "Spotify createPlaylist",
#     "Spotify getAlbumTracks",
#     "Spotify getArtistAlbums",
#     "Yelp getBusinesses",
#     "Youtube GetVideos"
# ]
def isSuccessful(code) -> bool:
    if isinstance(code, str):
        return code[0] == '2'
    return code >= 200 and code < 300

def get_reponse_body(operation):
        for httpStatus, httpContent in operation.responses.items():
            if isSuccessful(httpStatus):
                for contentType, contentTypeValue in httpContent.content.items():
                    return contentTypeValue.to_dict()
                
def flatten_json_schema(schema, parent_key='', sep='.', ref=""):
        flat_schema = {}
        if schema is None:
            return
        newRef = ref
        if 'properties' in schema:
            # root
            for key, value in schema['properties'].items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                if value is None:
                    continue

                if value.get('type') == 'object' and 'properties' in value:
                    # Recursively flatten nested object
                    if "xrefs" in value:
                        newRef = value.get("xrefs", "")
                    flat_schema.update(
                        flatten_json_schema(value, new_key, sep=sep, ref=newRef))

                elif value.get('type') == 'array':
                    items = value.get('items', {})
                    array_key = f"{new_key}"
                    # if "xrefs" in value.get("items",[]):
                    #     ref = value.get("xrefs")
                    if items.get('type') == 'object' and 'properties' in items:
                        # Flatten object inside array
                        if "xrefs" in value.get("items", {}):
                            newRef = value.get("items", {}).get("xrefs", "")
                        flat_schema.update(flatten_json_schema(
                            items, array_key, sep=sep, ref=newRef))
                    else:
                        if ref != "":
                            items["xrefs"] = ref
                        # Array of primitives
                        flat_schema[array_key] = items
                else:
                    # Primitive field
                    if ref != "":
                        value["xrefs"] = ref
                    flat_schema[new_key] = value
        elif schema.get('type') == 'array':
            # nested
            items = schema.get('items', {})
            newRef = ref
            if "xrefs" in items:
                newRef = items.get("xrefs", "")
            flat_schema.update(
                flatten_json_schema(items, parent_key, sep=sep, ref=newRef))
        return flat_schema

def process_rr(rr_contrains_path, newEndpoints):
    if not os.path.exists(rr_contrains_path):
        print(f"File {rr_contrains_path} does not exist.")
        return None
    data = pd.read_excel(rr_contrains_path)
    data = data.drop_duplicates() # drop duplicates
    print("===> Processing RR constraints for ", rr_contrains_path)
    array = []
    empty_result = []
    data['response resource'] = data['response resource'].astype(str)
    data = data.rename(columns={'attribute inferred from operation': 'operation'})

    records = json.loads(data.to_json(orient='records'))
    if len(records) <= 0:
        print(f"No records found in {rr_contrains_path}. Skipping processing.")
        return None
    for row in records:
        endpoint = row['operation']
        endpoint = endpoint.replace(" ", "-") # Ensure endpoint is formatted correctly
        endpointData = newEndpoints[endpoint.lower()]
        results = []
        for key, value in endpointData.items():
            sepKey = key.split(".")
            if sepKey[-1] == row["attribute"] and row["response resource"].lower() == value.get('xrefs', 'nan').lower():
                results.append(key)

        for result in results:
            array.append({
                "operation": row['operation'],
                "response resource": '' if row["response resource"] == 'nan' else row["response resource"],
                "attribute": row["attribute"],
                "group": result
            })
        if len(results) <= 0:
            empty_result.append(row)

    df = pd.DataFrame(array)
    merged =  None
    if not df.empty:
        merged = pd.merge(
            df, data, on=['operation', 'response resource', 'attribute'], how='left')
        merged["operation"] = merged["operation"].apply(
            lambda x: x.replace(" ", "-").lower())
        merged.to_csv(rr_contrains_path.replace(".xlsx", "_all_groups.csv"), index=False)

    empty = pd.DataFrame(empty_result)
    if len(empty) > 0:
        print(f"Found {len(empty)} empty results for {api}. Saving to CSV.")
        empty.to_csv(rr_contrains_path.replace(
            ".xlsx", "_all_empty.csv"), index=False)
    return merged

def process_rp(rp_contrains_path, newEndpoints):
    if not os.path.exists(rp_contrains_path):
        print(f"File {rp_contrains_path} does not exist.")
        return None
    
    data = pd.read_excel(rp_contrains_path)
    data = data.drop_duplicates() # drop duplicates
    data = data.drop('kio', axis=1, errors='ignore')
    print("===> Processing RP constraints for ", rr_contrains_path)

    array = []
    empty_result = []
    data['response resource'] = data['response resource'].astype(str)
  
    # data = data.rename(columns={'attribute inferred from operation': 'operation'})
    records = json.loads(data.to_json(orient='records'))
    for row in records:
        
        try :
            endpoint = row['operation']
            endpoint = endpoint.replace(" ", "-") # Ensure endpoint is formatted correctly
        except:
            print(row)
        
        endpointData = newEndpoints[endpoint.lower()]
        results = []
        for key, value in endpointData.items():
            sepKey = key.split(".")
            if sepKey[-1] == row["attribute"] and row["response resource"].lower() == value.get('xrefs', 'nan').lower():
                results.append(key)

        for result in results:
            array.append({
                "operation": row['operation'],
                "response resource": '' if row["response resource"] == 'nan' else row["response resource"],
                "attribute": row["attribute"],
                "group": result
            })
        if len(results) <= 0:
            empty_result.append(row)

    df = pd.DataFrame(array)
    merged = None
    if not df.empty:
        merged = pd.merge(
            df, data, on=['operation', 'response resource', 'attribute'], how='left')
        merged["operation"] = merged["operation"].apply(
            lambda x: x.replace(" ", "-").lower())

        merged.to_csv(rp_contrains_path.replace(".xlsx", "_all_groups.csv"), index=False)

    empty = pd.DataFrame(empty_result)
    if len(empty) > 0:
        print(f"Found {len(empty)} empty results for {api}. Saving to CSV.")
        empty.to_csv(rp_contrains_path.replace(
            ".xlsx", "_all_empty.csv"), index=False)
    return merged

for api in apis:
    spec_path = f"our_data/our_mining/{api}/openapi.json"
    rp_contrains_path = f"our_data/our_mining/{api}/response_property_constraints.xlsx"
    rr_contrains_path = f"our_data/our_mining/{api}/request_response_constraints.xlsx"
    path = f"our_data/our_mining/{api}"
    # 
    # spec_path = f"Eval/resultAgora/{api}/openapi.json"
    # contrains_path = f"Eval/ground_truth_data/{api}/response_property_constraints.csv"
    print("PROCESS ", api)

    # READ Specification
    spec = SpecificationParser(spec_path)
    operations = spec.parse_specification()
    # compute
    newEndpoints = {}
    for key, endpoint in operations.items():
        response = get_reponse_body(endpoint)
        try:
            if "xrefs" in response:
                newRef = response.get("xrefs", "")
            else:
                newRef = ""
            flatten = flatten_json_schema(response, ref=newRef)
            newEndpoints[key.lower()] = flatten
        except Exception as e:
            pass

    # 
    print("PARSED ", len(newEndpoints), " endpoints",  newEndpoints.keys())

    rp = process_rp(rp_contrains_path, newEndpoints)    
    rr = process_rr(rr_contrains_path, newEndpoints)
    # merge
    data = []
    if rr is not None:
        rr = rr.drop_duplicates()
        rr["description"] = "Attribute " + rr["attribute"] + " is responded to by parameter " + \
            rr["corresponding attribute"] + " with a description: " + \
            rr["corresponding attribute description"]
        rr = rr[["operation", "group", "response resource", "attribute", "description",'tp']]
        # rename
        rr.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description','tp']
        rr["endpoint"] = rr["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(rr)
	

    if rp is not None: 
        rp = rp.drop_duplicates()
        rp['description'] = rp['description'].fillna('').astype(str)
        if "detail schema" in rp.columns:
             print("Found 'detail schema' in rr columns")
             rp["description"] = rp["description"] + " " + rp["detail schema"]   
        # rr["description"] = (rr["description"] + " " + rr["detail schema"]) if "detail schema" in rr.columns else rr["description"]
        rp = rp[["operation",
                 "group", "response resource", "attribute", "description", 'TP']]
        # rename
        rp.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description','tp']
        rp["endpoint"] = rp["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(rp)

    merged = pd.concat(data)
    merged['description'] = merged['description'].astype(str)
    merged.to_csv(path + "/rp_rr_merged.csv", index=False)

    grouped = merged.groupby(["endpoint", "group"], as_index=False)
    invariant = grouped.agg(
        description=('description', lambda x: '\n'.join(x)),
        tp=('tp','mean')
    )
    invariant.to_csv(path + "/all_contrains.csv", index=False)
    # invariant[invariant["tp"] >= 1].to_csv(
    #     f'ground_truth_data/{api}/tp_contrains.csv', index=False)


    # merge
    
    