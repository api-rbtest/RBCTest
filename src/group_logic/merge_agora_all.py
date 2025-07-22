import pandas as pd
import re

# Load the Excel file
excel_file = pd.ExcelFile("agora_all.xlsx")

# Get all sheet names
sheet_names = excel_file.sheet_names
sheet_names = [name for name in sheet_names if name not in ('count_invariantType','file_groups')]  # Exclude 'Sheet1' if it exists
print(sheet_names)
multi_data = []
for sheet_name in sheet_names:
    print(f"Processing sheet: {sheet_name}")
    data = pd.read_excel("agora_all.xlsx", sheet_name=sheet_name)
    multi_data.append(data)
# Concatenate all dataframes into one
data = pd.concat(multi_data, ignore_index=True)
# map
apis = {
    "Github CreateOrganizationRepository": "createOrganizationRepository",
    "Github GetOrganizationRepositories": "getOrganizationRepositories",
    "Hotel Search": "getMultiHotelOffers",
    "Marvel getComicById": "getComicIndividual",
    "OMDB byIdOrTitle": "searchByIdOrTitle",
    "OMDB bySearch": "bySearch",
    "Spotify createPlaylist": "createPlaylist",
    "Spotify getAlbumTracks": "getAlbumTracks",
    "Spotify getArtistAlbums": "getArtistAlbums",
    "Yelp getBusinesses": "getBusinesses",
    "Youtube GetVideos": "getVideos"
}
for key, value in apis.items():
    newData = data[data['pptname'].str.contains(value, na=False)]
    newData.to_csv(f"resultAgora/{key}/invariants.csv", index=False)


    # data.loc[data['pptname'].str.contains(key, na=False), 'pptname'] = value

# data = data.to_csv("_agora_all_.csv", index=False)
# print(len(data))
# for index, row in data.iterrows():
#     print(f"Row {index}: {row.iloc[0]} - {row.iloc[1]} - {row.iloc[3]} ")
#     # remove parentheses
#     variables = row.iloc[3][1:-1]
#     variables = [s.strip() for s in variables.split(',')
#                  ]    # split by comma and trim
#     passed = False
#     for item in variables:
#         # first_item
#         if 'return' in item:
#             variable = item.replace("[..]", "").replace(
#                 "size(", "").replace(")", "")
#             matches = re.search(r'&(\d{3})&', row.iloc[0])
#             if matches:
#                 # get index of ()
#                 indexEnd = -1
#                 match = re.search(r"\(([^()]*)\)", row.iloc[0])
#                 if match:
#                     indexEnd = match.start()
#                     # print("Start index:", match.start())

#                 pptReturnPrefix = row.iloc[0][matches.start()+5:indexEnd]
#                 pptReturnPrefix = pptReturnPrefix.replace("&", ".")
#                 outputVariablesPath = pptReturnPrefix
#                 variable = variable.replace("return", outputVariablesPath)
#             else:
#                 variable = variable.replace("return.", "")
#             data.at[index, "group"] = variable
#             # passed = True
#             break
#     # if not passed:
#     #     data.at[index, "tp"] = ""
#     #     data.at[index, "fp"] = ""
#     #     data.at[index, "enter"] = 1
# # groups
# grouped = data.groupby(["group"], as_index=False)

# invariant = grouped.agg(
#     invariant=('invariant', lambda x: '\n'.join(x)),
#     invariantType=('invariantType', lambda x: '\n'.join(x)),
#     variables=('variables', lambda x: '\n'.join(x)),
#     # postmanAssertion=('postmanAssertion', lambda x: '\n'.join(x)),
#     pptname=('pptname', lambda x: '\n'.join(x))
# )

# invariant.to_csv(api + "/testDaikon_groups.csv", index=False)

# # groups
