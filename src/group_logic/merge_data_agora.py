import glob
import pandas as pd
import os
RP = "response_property_constraints_all_groups.csv"
RR = "request_response_constraints_all_groups.csv"
apis = [
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
# apis = ["Canada Holidays API"]

for api in apis:
    #
    data = []
    if os.path.exists(f"resultAgora/{api}/{RR}"):
        df = pd.read_csv(f"resultAgora/{api}/{RR}")
        df["description"] = "Attribute " + df["attribute"] + " is responded to by parameter " + \
            df["corresponding attribute"] + " with a description: " + \
            df["corresponding attribute description"]

        df = df[["attribute inferred from operation",
                 "group", "response resource", "attribute", "description","tp"]]
        # rename
        df.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description','tp']
        df["endpoint"] = df["endpoint"].apply(
            lambda x: x.replace("-/", "+").replace("/", "_"))
        data.append(df)
    if os.path.exists(f"resultAgora/{api}/{RP}"):
        df = pd.read_csv(f"resultAgora/{api}/{RP}")
        df = df[["operation",
                 "group", "response resource", "attribute", "description", "tp"]]
        # rename
        df.columns = ['endpoint', 'group',
                      'response resource', 'attribute', 'description', 'tp']
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
    # invariant["tp"] = invariant["tp"].apply(lambda x: 1 if x >=1 else 0)
    invariant.to_csv(
        f'resultAgora/{api}/all_contrains.csv', index=False)
    
    invariant[invariant["tp"] >= 1].to_csv(f"resultAgora/{api}/tp_contrains.csv", index=False)\

    merged.to_csv(f"resultAgora/{api}/rp_rr_merged_all.csv", index=False)\

# operation	response resource	attribute	description
