import pandas as pd
import re
# api = 'Github CreateOrganizationRepository'

# data = pd.read_csv(api + "/invariants.csv")
api = 'StripeClone API'
data = pd.read_excel('AGORA Our Dataset.xlsx', sheet_name=api)

for index, row in data.iterrows():
    print(f"Row {index}: {row.iloc[0]} - {row.iloc[1]} - {row.iloc[3]} ")
    # remove parentheses
    variables = row.iloc[3][1:-1]
    variables = [s.strip() for s in variables.split(',')
                 ]    # split by comma and trim
    passed = False
    for item in variables:
        # first_item
        if 'return' in item:
            variable = item.replace("[..]", "").replace(
                "size(", "").replace(")", "")
            matches = re.search(r'&(\d{3})&', row.iloc[0])
            if matches:
                # get index of ()
                indexEnd = row.iloc[0].find("()")
                pptReturnPrefix = row.iloc[0][matches.start()+5:indexEnd]
                pptReturnPrefix = pptReturnPrefix.replace("&", ".")
                outputVariablesPath = pptReturnPrefix
                variable = variable.replace("return", outputVariablesPath)
            else:
                variable = variable.replace("return.", "")
            data.at[index, "group"] = variable
            # passed = True
            break
    # if not passed:
    #     data.at[index, "tp"] = ""
    #     data.at[index, "fp"] = ""
    #     data.at[index, "enter"] = 1
data.to_csv(f'agora_data_mining/{api}/invariants_normalize.csv', index=False)
tp_data = data[data["tp"] == 1]
tp_data.to_csv(f'agora_data_mining/{api}/invariants_tp.csv', index=False)
# groups
grouped = tp_data.groupby(["endpoint", "group"], as_index=False)

invariant = grouped.agg(
    invariant=('invariant', lambda x: '\n'.join(x)),
    invariantType=('invariantType', lambda x: '\n'.join(x)),
    variables=('variables', lambda x: '\n'.join(x)),
    postmanAssertion=('postmanAssertion', lambda x: '\n'.join(x)),
    pptname=('pptname', lambda x: '\n'.join(x))
)

invariant.to_csv(f'agora_data_mining/{api}/invariants_groups.csv', index=False)

# groups
