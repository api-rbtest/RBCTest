

import pandas as pd
import re

from api_testing.dataset.specification_parser import SpecificationParser

spec_path = "datasets/GitLabBranch.json"
contrains_path = "Eval/our_data_mining/GitLab Branch API/request_response_constraints.xlsx"


def isSuccessful(code) -> bool:
    if isinstance(code, str):
        return code[0] == '2'
    return code >= 200 and code < 300


spec = SpecificationParser(spec_path)
operations = spec.parse_specification()

data = pd.read_excel(contrains_path)
# group by endpoint

# grouped = data.groupby(["operation"])


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


newEndpoints = {}
for key, endpoint in operations.items():
    response = get_reponse_body(endpoint)
    try:
        if "xrefs" in response:
            newRef = response.get("xrefs", "")
        else:
            newRef = ""
        flatten = flatten_json_schema(response, ref=newRef)
        newEndpoints[key] = flatten
    except Exception as e:
        print(str(e))
print("=" * 30)

print(newEndpoints)
array = []
empty_result = []
for index, row in data.iterrows():
    # get all key matching\
    endpoint = row.iloc[4]
    # get flatten by endpoint
    endpointData = newEndpoints[endpoint]
    results = []
    for key, value in endpointData.items():
        sepKey = key.split(".")
        # if (row.iloc[2] == 'optional'):
        #     print(sepKey[-1])
        # else:
        #     print(value.get('xrefs','').lower() , "=>", row.iloc[1].lower())
        if sepKey[-1] == row.iloc[2] and row.iloc[1].lower() == value.get('xrefs', '').lower():
            results.append(key)
    for result in results:
        array.append({
            "attribute inferred from operation": row.iloc[4],
            "response resource": row.iloc[1],
            "attribute": row.iloc[2],
            "group": result
        })
    print("-=-------------------------------")
    print(row.iloc[4], "_", row.iloc[2], "=>", results)
    if len(results) <= 0:
        empty_result.append({
            "kio": row.iloc[0],
            "response resource": row.iloc[1],
            "attribute": row.iloc[2],
            "description": row.iloc[3],
            "attribute inferred from operation": row.iloc[4],
            "x": row.iloc[5],
            "part": row.iloc[6],

        })
    # get by key
df = pd.DataFrame(array)
merged = pd.merge(
    df, data, on=['attribute inferred from operation', 'response resource', 'attribute'], how='left')

# data.at[index, "groups"] = ','.join(results)
merged.to_csv(contrains_path.replace(".xlsx", "_groups.csv"), index=False)
empty = pd.DataFrame(empty_result)

empty.to_csv(contrains_path.replace(".xlsx", "_empty.csv"), index=False)

# # flat to key
# for endpoint in operations.values():
#     path = endpoint.http_method + "+" + \
#         endpoint.endpoint_path.strip("/").replace("/", "_")
#     newEndpoints[path] = endpoint.to_dict()

# for key, groupdf in grouped:
#     #
#     # platten json body
#     operationId = key[0]
#     response = get_reponse_body(operations.get(operationId))
#     flatten = flatten_json_schema(response)
# foreach platten

# resource_group = groupdf.groupby(["response resource"])
# print(resource_group)
# group by re
# print())
# print(key)
# print(groupdf)

# panas
# newEndpoints = {}
# for endpoint in operations.values():
#     path = endpoint.http_method + "+" + \
#         endpoint.endpoint_path.strip("/").replace("/", "_")
#     newEndpoints[path] = endpoint.to_dict()

# print(newEndpoints)
