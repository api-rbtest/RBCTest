import pandas as pd
import re
excel_file = pd.ExcelFile("report.xlsx")

# Get all sheet names
sheet_names = excel_file.sheet_names
# sheet_names = [name for name in sheet_names if name not in ('count_invariantType','file_groups')]  # Exclude 'Sheet1' if it exists
print(sheet_names)
with pd.ExcelWriter('report2.xlsx', engine='xlsxwriter') as writer:

    for sheet in sheet_names:
        d = pd.read_excel("report.xlsx", sheet_name=sheet)
        old = pd.read_excel("BASE_2_Compare AGORA Data.xlsx", sheet_name=sheet)
        
        intersection = pd.merge(d, old, how='left', on=['endpoint','group'])

        intersection.to_excel(writer, sheet_name=sheet, index=False)
