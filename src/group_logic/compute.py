import glob
import pandas as pd
import os
# ALL = "all_contrains.csv"
# TP = "contrains.csv"
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
# apis = ["Canada Holidays API", "GitLab Branch API",
#         "GitLab Commit API", "GitLab Groups API", "GitLab Issues API", "GitLab Project API", "GitLab Repository API", "StripeClone API"]

for api in apis:
    data = pd.read_csv(f"agora_data/our_mining/{api}/mapping_verify_status.csv")
    # filter 
    data = data[data["tp"] >= 1]
    data = data[data["check_verify"] == "yes"]
    count_by_status = data.groupby("status").size().reset_index(name='count')
    #pandas

    print(api)
    print(count_by_status)
#     data_tp =  data[data["tp"] == 1]
# #     invariant_all = pd.read_csv(f"resultAgora/{api}/invariants_all_groups.csv")
# #     invariant_tp = pd.read_csv(f"resultAgora/{api}/invariants_all_tp_groups.csv")

#     print(api,"-", len(data), "-",len(data_tp))

# ALL = "all_contrains.csv"
# TP = "contrains.csv"
# apis = ["Canada Holidays API", "GitLab Branch API",
#         "GitLab Commit API", "GitLab Groups API", "GitLab Issues API", "GitLab Project API", "GitLab Repository API", "StripeClone API"]
# # apis = ["Canada Holidays API"]

# for api in apis:
#     data = pd.read_csv(f"our_data_mining/{api}/{ALL}")
#     data_tp =  data[data["tp"] == 1]

#     invariant = pd.read_csv(f"agora_data_mining/{api}/invariants.csv")

#     invariant_all = pd.read_csv(f"agora_data_mining/{api}/invariants_all_groups.csv")
#     invariant_tp = invariant_all[invariant_all["tp"] >= 1]
#     # pd.read_csv(f"agora_data_mining/{api}/invariants_all_tp_groups.csv")

#     # print(api,"-", len(data), "-",len(data_tp))
#     print(api," AGORA -", len(invariant),"-",  len(invariant_all), "-",len(invariant_tp))