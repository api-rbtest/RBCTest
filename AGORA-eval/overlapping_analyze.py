import re 
import os
import pandas as pd
def find_matched_files(root_dir, pattern):
    matched_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if pattern.match(file):  # Just match the file name, not the full path
                matched_files.append(os.path.join(root, file))
    return matched_files

root_dir = r"approaches\new_method_agora_data"
pattern = re.compile(r'overlapping_analysis_.xlsx')
matched_files = find_matched_files(root_dir, pattern)
matched_files = sorted(matched_files)

# if len(matched_files) != 11:
#     print(f'Expected 11 files, but got {len(matched_files)}')
#     exit()
# matched_files = sorted(open('matched_files_.txt').read().split('\n'))

file_groups = {}
all_invariants = pd.DataFrame()

for file in matched_files:
    df = pd.read_excel(file)

    if file not in file_groups:
        file_groups[file] = {
            'static_better': len(df[df['eval'] == 's']),
            'dynamic_better': len(df[df['eval'] == 'd']),
            'equal': len(df[df['eval'] == '=']),
        }
    else:
        file_groups[file]['static_better'] += len(df[df['eval'] == 's'])
        file_groups[file]['dynamic_better'] += len(df[df['eval'] == 'd'])
        file_groups[file]['equal'] += len(df[df['eval'] == '='])

    df['file'] = file.replace(root_dir, '').replace(pattern.pattern, '')
    temp_df = df

    all_invariants = pd.concat([all_invariants, temp_df])

# open excel writer, write 2 sheets: file_groups, all_invariants
with pd.ExcelWriter('overlapping_analysis_all.xlsx') as writer:
    file_groups = pd.DataFrame(file_groups.items(), columns=['file', 'count'])
    file_groups.to_excel(writer, sheet_name='file_groups', index=False)
    all_invariants.to_excel(writer, sheet_name='all_invariants', index=False)

