import glob
import pandas as pd
import os
RP = "response_property_constraints_all_groups.csv"
RR = "request_response_constraints_all_groups.csv"
apis = ["Canada Holidays API", "GitLab Branch API",
        "GitLab Commit API", "GitLab Groups API", "GitLab Issues API", "GitLab Project API", "GitLab Repository API", "StripeClone API"]
# apis = ["Canada Holidays API"]

for api in apis:
    #
    data = []
    if os.path.exists(f"ground_truth_data/{api}/{RR}"):
        df = pd.read_csv(f"ground_truth_data/{api}/{RR}")
        df = df.drop_duplicates()
        df["description"] = "Attribute " + df["attribute"] + " is responded to by parameter " + \
            df["corresponding attribute"] + " with a description: " + \
            df["corresponding attribute description"]

        df = df[["attribute inferred from operation",
                 "group", "response resource", "attribute", "description","tp"]]
        # rename
        df.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description', 'tp']
        df["endpoint"] = df["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(df)
    if os.path.exists(f"ground_truth_data/{api}/{RP}"):
        df = pd.read_csv(f"ground_truth_data/{api}/{RP}")
        df = df.drop_duplicates()
        df = df[["operation",
                 "group", "response resource", "attribute", "description",'TP']]
        # rename
        df.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description','tp']
        df["endpoint"] = df["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(df)

    merged = pd.concat(data)
    merged['description'] = merged['description'].astype(str)
    grouped = merged.groupby(["endpoint", "group"], as_index=False)
    invariant = grouped.agg(
        description=('description', lambda x: '\n'.join(x)),
        tp=('tp', 'mean')
    )
    invariant.to_csv(
        f'ground_truth_data/{api}/all_contrains.csv', index=False)
    invariant[invariant["tp"] >= 1].to_csv(
        f'ground_truth_data/{api}/tp_contrains.csv', index=False)

    merged.to_csv(f"ground_truth_data/{api}/rp_rr_merged.csv", index=False)\


# operation	response resource	attribute	description
