import os

import pandas as pd

CONSTRAINT_TYPE = "Response-property"
# range of values', 'format, logic', 'logic', 'range of values, logic', 'logic, format', 'inter-parameter dependency', 'format'

def evaluate_response_property_constraint_mining(approach_folder, ground_truth_folder, api_folders, csv_file, export=False, verifier=False):
    if not os.path.exists(csv_file):
        with open(csv_file, "w") as f:
            f.write("API,Constraint_Type,TP,FP,FN,Precision,Recall,F1\n")
    categories_dict = {}
    all_fns = pd.DataFrame()
    for api_folder in api_folders:
        if api_folder == ".DS_Store":
            continue
        approach_file = f'{approach_folder}/{api_folder}/response_property_constraints.xlsx'
        ground_truth_file = f'{ground_truth_folder}/{api_folder}/response_property_constraints.xlsx'
        
        
        if not os.path.exists(approach_file) or not os.path.exists(ground_truth_file):
            continue
        ground_truth_df = pd.read_excel(ground_truth_file, engine='openpyxl')

        print(f"Processing {approach_file}, on {ground_truth_file}")
        approach_df = pd.read_excel(approach_file, engine='openpyxl')
        if approach_df.empty:
            continue

        if api_folder not in categories_dict:
            categories_dict[api_folder] = {"type": CONSTRAINT_TYPE}
            

        if verifier:
            approach_df = approach_df[approach_df["verify_result"] != 0]

        approach_df["constraint_correctness"] = ""
        approach_df["category"] = ""
        for row, data in approach_df.iterrows():
            description = data["description"]

            mask = (ground_truth_df["description"] == description)
            found_mapping = ground_truth_df[mask]
            if found_mapping.empty:
                approach_df.at[row, "constraint_correctness"] = "FP"
            else:
                approach_df.at[row, "constraint_correctness"] = "TP"
                if "tp" in approach_df.columns:
                    if approach_df.at[row, "tp"] == 1:
                        approach_df.at[row, "category"] = found_mapping["category"].values[0]
                        if found_mapping["category"].values[0] not in categories_dict[api_folder]:
                            categories_dict[api_folder][found_mapping["category"].values[0]] = 0
                        categories_dict[api_folder][found_mapping["category"].values[0]] += 1
                    else:
                        category = found_mapping["category"].values[0]
                        category = category + "_FP"
                        if category not in categories_dict[api_folder]:
                            categories_dict[api_folder][category] = 0
                        categories_dict[api_folder][category] += 1

        if export:
            approach_df.to_excel(approach_file, index=False)

        approach_df = approach_df[['attribute', 'description', 'operation']].drop_duplicates()
        ground_truth_df = ground_truth_df[['attribute', 'description', 'operation']].drop_duplicates()

        ground_truth_df["concat"] = ground_truth_df["attribute"] + ground_truth_df["description"] + ground_truth_df["operation"]
        approach_df["concat"] = approach_df["attribute"] + approach_df["description"] + approach_df["operation"]

        gt_values = set(ground_truth_df["concat"].values)
        approach_values = set(approach_df["concat"].values)
        tps = gt_values.intersection(approach_values)
        fps = approach_values - gt_values
        fns = gt_values - approach_values
        

        precision = len(tps) / (len(tps) + len(fps))
        recall = len(tps) / (len(tps) + len(fns))
        f1 = 2 * (precision * recall) / (precision + recall)

        # x100 and round to 2 decimal places
        precision = round(precision * 100, 1)
        recall = round(recall * 100, 1)
        f1 = round(f1 * 100, 1)

        all_fns = pd.concat([all_fns, ground_truth_df[~ground_truth_df['concat'].isin(approach_df['concat'])]])

        with open(csv_file, "a") as f:
            f.write(f"{api_folder},{CONSTRAINT_TYPE},{len(tps)},{len(fps)},{len(fns)},{precision},{recall},{f1}\n")

    categories_df = pd.DataFrame(categories_dict)
    categories_df = categories_df.transpose()
    if os.path.exists(f"{approach_folder}/categories.xlsx"):
        tmp_df = pd.read_excel(f"{approach_folder}/categories.xlsx", engine='openpyxl')
        categories_df = pd.concat([tmp_df, categories_df])
    categories_df.to_excel(f"{approach_folder}/categories.xlsx")

    all_fns.to_excel(f"{approach_folder}/{CONSTRAINT_TYPE}_fns.xlsx", index=False)

def evaluate_response_property_test_gen(approach_folder, api_folders, csv_file, ground_truth_folder):
    if not os.path.exists(csv_file):
        with open(csv_file, "w") as f:
            f.write("API,Constraint_Type,total,total_correct,accuracy,fn,recall,f1,filter,filter_correct,filter_accuracy,filter_fn,filter_recall,filter_f1\n")

    for api_folder in api_folders:
        if api_folder == ".DS_Store":
            continue
        approach_file = f'{approach_folder}/{api_folder}/response_property_constraints.xlsx'
        ground_truth_file = f'{ground_truth_folder}/{api_folder}/response_property_constraints.xlsx'
        if not os.path.exists(approach_file) or not os.path.exists(ground_truth_file):
            continue

        print(f"Evaluating test generation for {approach_file}")
        approach_df = pd.read_excel(approach_file, engine='openpyxl')
        ground_truth_df = pd.read_excel(ground_truth_file, engine='openpyxl')

        if approach_df.empty:
            continue

        # Thêm các cột cần thiết nếu chưa tồn tại
        if 'tp' not in approach_df.columns:
            approach_df['tp'] = 0
            approach_df['constraint_correctness'] = 'FP'
        
        if 'verify_result' not in approach_df.columns:
            approach_df['verify_result'] = 1  # Mặc định là 1 (verified)
        
        for i, row in approach_df.iterrows():
            constraint_correctness = row["constraint_correctness"]
            tp = row["tp"]
            print(constraint_correctness, tp)
            if constraint_correctness == "FP" and tp == 1:
                print(f"Line {i}: Error: FP but tp == 1")
                input()
        
        total = len(approach_df)
        total_tp = approach_df[approach_df["tp"] == 1]
        total_correct = len(approach_df[approach_df["tp"] == 1])
        accuracy = total_correct / total if total > 0 else 0

        filter_df = approach_df[approach_df["verify_result"] != 0]
        filter_total = len(filter_df)
        filter_tp = filter_df[filter_df["tp"] == 1]
        filter_correct = len(filter_df[filter_df["tp"] == 1])
        filter_accuracy = filter_correct / filter_total if filter_total > 0 else 0

        accuracy = round(accuracy * 100, 1)
        filter_accuracy = round(filter_accuracy * 100, 1)

        tmp_ground_truth_df = ground_truth_df.copy()
        tmp_ground_truth_df["concat"] = tmp_ground_truth_df["attribute"] + tmp_ground_truth_df["description"] + tmp_ground_truth_df["operation"]
        
        tmp_approach_df = total_tp.copy()
        tmp_approach_df["concat"] = tmp_approach_df["attribute"] + tmp_approach_df["description"] + tmp_approach_df["operation"]
                                                                                   
        gt_values = set(tmp_ground_truth_df["concat"].values)
        approach_values = set(tmp_approach_df["concat"].values)

        fns = gt_values - approach_values

        tmp_approach_df = filter_tp.copy()
        tmp_approach_df["concat"] = tmp_approach_df["attribute"] + tmp_approach_df["description"] + tmp_approach_df["operation"]

        gt_values = set(tmp_ground_truth_df["concat"].values)
        approach_values = set(tmp_approach_df["concat"].values)

        fns_filter = gt_values - approach_values

        if len(fns) == 0 or total_correct == 0:
            recall = "-"
            f1 = "-"
        else:
            recall = total_correct / (total_correct + len(fns))
            recall = round(recall * 100, 1)
            if accuracy + recall > 0:
                f1 = 2 * (accuracy * recall) / (accuracy + recall)
                f1 = round(f1, 1)
            else:
                f1 = "-"

        if len(fns_filter) == 0 or filter_correct == 0:
            filter_recall = "-"
            filter_f1 = "-"
        else:
            filter_recall = filter_correct / (filter_correct + len(fns_filter))
            filter_recall = round(filter_recall * 100, 1)
            if filter_accuracy + filter_recall > 0:
                filter_f1 = 2 * (filter_accuracy * filter_recall) / (filter_accuracy + filter_recall)
                filter_f1 = round(filter_f1, 1)
            else:
                filter_f1 = "-"

        with open(csv_file, "a") as f:
            f.write(f"{api_folder},{CONSTRAINT_TYPE},{total},{total_correct},{accuracy},{len(fns)},{recall},{f1},{filter_total},{filter_correct},{filter_accuracy},{len(fns_filter)},{filter_recall},{filter_f1}\n")




    