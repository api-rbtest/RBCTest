import os

import pandas as pd

CONSTRAINT_TYPE = "Request-Response"



def evaluate_request_response_constraint_mining(approach_folder, ground_truth_folder, api_folders, csv_file, verifier=False, export=False):
    if not os.path.exists(csv_file):
        with open(csv_file, "w") as f:
            f.write("API,Constraint_Type,TP,FP,FN,Precision,Recall,F1\n")
    categories_dict = {}
    all_fns = pd.DataFrame()
    for api_folder in api_folders:
        if api_folder == ".DS_Store":
            continue
        approach_file = f'{approach_folder}/{api_folder}/request_response_constraints.xlsx'
        ground_truth_file = f'{ground_truth_folder}/{api_folder}/request_response_constraints.xlsx'
        print(f"Processing {approach_file}, on {ground_truth_file}")
        
        ground_truth_df = pd.read_excel(ground_truth_file, engine='openpyxl')
        
        if not os.path.exists(approach_file) or not os.path.exists(ground_truth_file):
            continue

        print(f"Processing {approach_file}, on {ground_truth_file}")
        approach_df = pd.read_excel(approach_file, engine='openpyxl')


        if approach_df.empty:
            continue

        if verifier:
            approach_df = approach_df[approach_df["verify_result"] != 0]

        if api_folder not in categories_dict:
            categories_dict[api_folder] = {"type": CONSTRAINT_TYPE}

        approach_df["constraint_correctness"] = ""
        approach_df["category"] = ""
        for row, data in approach_df.iterrows():
            attribute = data["attribute"]
            response_resource = data["response resource"]
            parameter = data["corresponding attribute"]
            parameter_description = data["corresponding attribute description"]
            attribute_inferred_from_operation = data["attribute inferred from operation"]

            mask = (ground_truth_df["attribute"] == attribute) & (ground_truth_df["response resource"] == response_resource) & (ground_truth_df["corresponding attribute"] == parameter)
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
        # approach_df.to_excel(approach_file.replace(".xlsx", "_eval.xlsx"), index=False)


        tmp_ground_truth_df = ground_truth_df.copy()
        tmp_ground_truth_df["concat"] = tmp_ground_truth_df["attribute"] + tmp_ground_truth_df["response resource"] + tmp_ground_truth_df["corresponding attribute"] + tmp_ground_truth_df["attribute inferred from operation"]

        tmp_approach_df = approach_df.copy()
        tmp_approach_df["concat"] = tmp_approach_df["attribute"] + tmp_approach_df["response resource"] + tmp_approach_df["corresponding attribute"] + tmp_approach_df["attribute inferred from operation"]

        gt_values = set(tmp_ground_truth_df["concat"].values)
        approach_values = set(tmp_approach_df["concat"].values)
        
        tps = gt_values.intersection(approach_values)
        fps = approach_values - gt_values
        fns = gt_values - approach_values

        if len(tps) == 0:
            precision = "-"
            recall = "-"
            f1 = "-"
        else:
            precision = len(tps) / (len(tps) + len(fps))
            recall = len(tps) / (len(tps) + len(fns))
            f1 = 2 * (precision * recall) / (precision + recall)

            # x100 and round to 2 decimal places
            precision = round(precision * 100, 1)
            recall = round(recall * 100, 1)
            f1 = round(f1 * 100, 1)

        all_fns = pd.concat([all_fns, tmp_ground_truth_df[~tmp_ground_truth_df['concat'].isin(tmp_approach_df['concat'])]])

        with open(csv_file, "a") as f:
            f.write(f"{api_folder},{CONSTRAINT_TYPE},{len(tps)},{len(fps)},{len(fns)},{precision},{recall},{f1}\n")

    categories_df = pd.DataFrame(categories_dict)
    categories_df = categories_df.transpose()
    if os.path.exists(f"{approach_folder}/categories.xlsx"):
        tmp_df = pd.read_excel(f"{approach_folder}/categories.xlsx", engine='openpyxl')
        categories_df = pd.concat([tmp_df, categories_df])
    categories_df.to_excel(f"{approach_folder}/categories.xlsx")

    all_fns.to_excel(f"{approach_folder}/{CONSTRAINT_TYPE}_fns.xlsx", index=False)


def evaluate_request_response_test_gen(approach_folder, api_folders, csv_file, ground_truth_folder):
    if not os.path.exists(csv_file):
        with open(csv_file, "w") as f:
            f.write("API,Constraint_Type,total,total_correct,accuracy,fn,recall,f1,filter,filter_correct,filter_accuracy,filter_fn,filter_recall,filter_f1\n")

    for api_folder in api_folders:
        if api_folder == ".DS_Store":
            continue
        approach_file = f'{approach_folder}/{api_folder}/request_response_constraints.xlsx'
        ground_truth_file = f'{ground_truth_folder}/{api_folder}/request_response_constraints.xlsx'
        
        if not os.path.exists(approach_file) or not os.path.exists(ground_truth_file):
            continue

        print(f"Evaluating test generation for {approach_file}")
        approach_df = pd.read_excel(approach_file, engine='openpyxl')
        ground_truth_df = pd.read_excel(ground_truth_file, engine='openpyxl')


        if approach_df.empty:
            continue

        for i, row in approach_df.iterrows():
            constraint_correctness = row["constraint_correctness"]
            tp = row["tp"]
            if constraint_correctness == "FP" and tp == 1:
                print(f"Line {i}: Error: FP but tp == 1")
                input()
        
        total = len(approach_df)
        tp = approach_df[(approach_df["tp"] == 1 ) & (approach_df["constraint_correctness"] == 'TP')]
        fp = approach_df[(approach_df["tp"] == 0 ) | (approach_df["constraint_correctness"] == 'FP')]

        temp_tp = tp.copy()
        temp_tp['concat'] = temp_tp['attribute'] + temp_tp['response resource'] + temp_tp['corresponding attribute'] + temp_tp['attribute inferred from operation']

        temp_gt = ground_truth_df.copy()
        temp_gt['concat'] = temp_gt['attribute'] + temp_gt['response resource'] + temp_gt['corresponding attribute'] + temp_gt['attribute inferred from operation']

        fn = temp_gt[~temp_gt['concat'].isin(temp_tp['concat'])]


        # after verify
        verified_df = approach_df[approach_df["verify_result"] != 0]
        filter_total = len(verified_df)

        filter_tp = verified_df[(verified_df["tp"] == 1 ) & (verified_df["constraint_correctness"] == 'TP')]
        filter_fp = verified_df[(verified_df["tp"] == 0 ) | (verified_df["constraint_correctness"] == 'FP')]
        
        temp_filter_tp = filter_tp.copy()
        temp_filter_tp['concat'] = temp_filter_tp['attribute'] + temp_filter_tp['response resource'] + temp_filter_tp['corresponding attribute'] + temp_filter_tp['attribute inferred from operation']

        filter_fn = temp_gt[~temp_gt['concat'].isin(temp_filter_tp['concat'])]

        print(f"Total: {total}, TP: {len(tp)}, FP: {len(fp)}, FN: {len(fn)}, Filter: {filter_total}, TP: {len(filter_tp)}, FP: {len(filter_fp)}, FN: {len(filter_fn)}")
        
        total_correct = len(tp)
        accuracy = total_correct / total

        filter_correct = len(filter_tp)
        filter_accuracy = filter_correct / filter_total

        accuracy = round(accuracy * 100, 1)
        filter_accuracy = round(filter_accuracy * 100, 1)

        if len(fn) == 0:
            recall = "-"
            f1 = "-"
        else:
            recall = total_correct / (total_correct + len(fn))
            recall = round(recall * 100, 1)
            f1 = 2 * (accuracy * recall) / (accuracy + recall)
            f1 = round(f1, 1)

        if len(filter_fn) == 0:
            filter_recall = "-"
            filter_f1 = "-"
        else:
            filter_recall = filter_correct / (filter_correct + len(filter_fn))
            filter_recall = round(filter_recall * 100, 1)
            filter_f1 = 2 * (filter_accuracy * filter_recall) / (filter_accuracy + filter_recall)
            filter_f1 = round(filter_f1, 1)

        with open(csv_file, "a") as f:
            f.write(f"{api_folder},{CONSTRAINT_TYPE},{total},{total_correct},{accuracy},{len(fn)},{recall},{f1},{filter_total},{filter_correct},{filter_accuracy},{len(filter_fn)},{filter_recall},{filter_f1}\n")
