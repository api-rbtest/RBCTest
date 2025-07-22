import glob
import pandas as pd
import os
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

# Write to multiple sheets
with pd.ExcelWriter('report.xlsx', engine='xlsxwriter') as writer:
    total = {
            "inner": 0,
            "left": 0,
            "right": 0
        }
    for api in apis:
        print(f"Processing {api}===============================")
        # dynamic
        d = pd.read_csv(f"our_data/agora_mining/{api}/invariants_all_tp_groups.csv")
        # d = d[['group', 'invariant']]
        s = pd.read_csv(f"our_data/our_mining/{api}/all_contrains.csv")
        #
        s = s[s['tp'] >= 1]
        # print(d.head(1))
        
        d["endpoint"] = d["endpoint"].apply(lambda x: x.lower())
        s["endpoint"] = s["endpoint"].apply(lambda x: x.lower())
        for how in ["inner", "left", "right"]:
            intersection = pd.merge(d, s, how=how, on=['endpoint', 'group'])
            # print(f" {how} interset {api} - {len(intersection)}")
            total[how] += len(intersection)
            # intersection.to_excel(writer, sheet_name=f"{api}_{how}", index=False)
        # all_contrains.csv
        intersection = pd.merge(d, s, how='inner', on=['endpoint','group'])
        intersection.to_csv(f"our_data/our_mining/{api}/interset_contrains.csv")
        intersection.to_excel(
            writer, sheet_name=api, index=False)
    print(total)
        