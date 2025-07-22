import glob
import pandas as pd
import os
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
# Write to multiple sheets
with pd.ExcelWriter('report.xlsx', engine='xlsxwriter') as writer:

    for api in apis:
        # # dynamic
        d = pd.read_csv(f"our_data/our_ground_truth/{api}/all_contrains.csv")
        s = pd.read_csv(f"our_data/our_mining/{api}/all_contrains.csv")
        
        d["endpoint"] = d["endpoint"].apply(lambda x: x.lower())
        s["endpoint"] = s["endpoint"].apply(lambda x: x.lower())
        d['tp'] = 1
        # s_tp = s_tp[['group', 'description']]

        # #
        # # 
        # hows = ["inner", "left", "right"]
        # with pd.ExcelWriter(f"our_data_mining/{api}/interset_contrains.xlsx", engine='xlsxwriter') as writer2:
        #     for how in hows:
        #         intersection = pd.merge(d, s, how=how, on=['endpoint', 'group'])
        #         intersection.to_excel(writer2, sheet_name=how, index=False)

        intersection = pd.merge(d, s, how='right', on=['endpoint','group'])
        print(f"interset {api} - {len(intersection[intersection["tp"] != 1])}")
        # intersection.to_excel(writer, sheet_name=api.replace("Github","GH"), index=False)
