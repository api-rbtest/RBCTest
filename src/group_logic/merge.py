import glob
import pandas as pd
import os
RP = "response_property_constraints_groups_new.xlsx"
RR = "request_response_constraints_groups.xlsx"
# apis = ["Canada Holidays API", "GitLab Issues API", "StripeClone API"]
# apis = ["Canada Holidays API"]
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
apis = ["Canada Holidays API", "GitLab Branch API",
        "GitLab Commit API", "GitLab Groups API", "GitLab Issues API", "GitLab Project API", "GitLab Repository API", "StripeClone API"]

for api in apis:
    #
    data = []
    api = api.replace(" API", "")
    if os.path.exists(f"group_mining_evaluate/{api}/{RR}"):
        df = pd.read_excel(f"group_mining_evaluate/{api}/{RR}")
        # print(df.columns.tolist())
        df = df.drop_duplicates()
        df["description"] = "Attribute " + df["attribute"] + " is responded to by parameter " + \
            df["corresponding attribute"] + " with a description: " + \
            df["corresponding attribute description"]

        df = df[["attribute inferred from operation",
                 "group", "response resource", "attribute", "description","tp","status"]]
        # rename
        df["_check_verification_script"] = "yes"
        df.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description',"tp","status","_check_verification_script"]
        df["endpoint"] = df["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(df)
    if os.path.exists(f"group_mining_evaluate/{api}/{RP}"):
        df = pd.read_excel(f"group_mining_evaluate/{api}/{RP}")
        df = df.drop_duplicates()
        df = df[["operation",
                 "group", "response resource", "attribute", "description","tp","status","_check_verification_script"]]
        # rename
        df.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description',"tp","status","_check_verification_script"]
        df["endpoint"] = df["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(df)

    merged = pd.concat(data)
    merged['description'] = merged['description'].astype(str)

    grouped = merged.groupby(["endpoint", "group"], as_index=False)
    invariant = grouped.agg(
        description=('description', lambda x: '\n'.join(x)),
        tp=('tp', 'mean'),
        status=('status', lambda x: '\n'.join(x)),
        _check_verification_script=('_check_verification_script', lambda x: ','.join(x)),
    )
    invariant["check_verify"] = invariant["_check_verification_script"].apply( lambda x: 'no' if 'no' in x else 'yes') 
    invariant.to_csv(
        f'group_mining_evaluate/{api}/status.csv', index=False)
    # merges
    # mygroups
    our_data = pd.read_csv(f'our_data/our_mining/{api} API/all_contrains.csv')
    # our_data["key"] = our_data["endpoint"].apply(lambda x: x.replace("{", "").replace("}", "").lower()) + "_" + our_data["group"].apply(lambda x: x.replace(".", "_"))
    # invariant["key"] = invariant["endpoint"].apply(lambda x: x.replace("{", "").replace("}", "").lower()) + "_" + invariant["group"].apply(lambda x: x.replace(".", "_"))
    # our_data['key'] = our_data['key'].astype(str)
    # invariant['key'] = invariant['key'].astype(str)
    # print(our_data['key'])
    # print(invariant['key'])
    our_data["endpoint"] = our_data["endpoint"].apply(
        lambda x: x.lower())
    invariant["endpoint"] = invariant["endpoint"].apply(
        lambda x: x.lower())
    our_data = pd.merge(our_data, invariant, how='left', on=['endpoint', 'group'], indicator=True)
    our_data.to_csv(
        f'our_data/our_mining/{api} API/mapping_verify_status.csv', index=False)
     
# operation	response resource	attribute	description
