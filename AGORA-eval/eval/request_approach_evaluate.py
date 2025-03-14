import os

import pandas as pd

def evaluate_request_response_test_gen(approach_folder, api_folders, original_approach_folder, ground_truth_folder):
    all_correct_constraints_wrong_script = pd.DataFrame()
    all_false_verifier = pd.DataFrame()
    for api_folder in api_folders:
        if api_folder == ".DS_Store":
            continue
        approach_file = f'{approach_folder}/{api_folder}/request_response_constraints.xlsx'
        ground_truth_file = f'{ground_truth_folder}/{api_folder}/request_response_constraints.xlsx'
        original_approach_file = f'{original_approach_folder}/{api_folder}/request_response_constraints.xlsx'
        if not os.path.exists(approach_file) or not os.path.exists(ground_truth_file) or not os.path.exists(original_approach_file):
            continue

        print(f"Evaluating test generation for {approach_file}")
        approach_df = pd.read_excel(approach_file, engine='openpyxl')
        ground_truth_df = pd.read_excel(ground_truth_file, engine='openpyxl')
        original_approach_df = pd.read_excel(original_approach_file, engine='openpyxl')

        if approach_df.empty or ground_truth_df.empty or original_approach_df.empty:
            continue

        for i, row in approach_df.iterrows():
            constraint_correctness = row["constraint_correctness"]
            tp = row["tp"]
            if constraint_correctness == "FP" and tp == 1:
                print(f"Line {i}: Error: FP but tp == 1")
                input()

            verification_script = row["verification script"]
            original_verification_script = original_approach_df.iloc[i]["verification script"]
            # if verification_script is null or empty or nan, copy the original verification script
            if pd.isnull(verification_script) or verification_script == "":
                approach_df.at[i, "verification script"] = original_verification_script

            # do similar for the executable script
            executable_script = row["executable script"]
            original_executable_script = original_approach_df.iloc[i]["executable script"]
            # if verification_script is null or empty or nan, copy the original verification script
            if pd.isnull(executable_script) or executable_script == "":
                approach_df.at[i, "executable script"] = original_executable_script

            status = row["status"]
            original_status = original_approach_df.iloc[i]["status"]
            # if status is null or empty or nan, copy the original status
            if pd.isnull(status) or status == "":
                approach_df.at[i, "status"] = original_status

        approach_df.to_excel(approach_file, index=False)

        
        total = len(approach_df)
        correct_constraints_wrong_script = approach_df[(approach_df["tp"] == 0) & (approach_df["constraint_correctness"] == "TP")]

        correct_constraints_wrong_script["API"] = api_folder
        all_correct_constraints_wrong_script = pd.concat([all_correct_constraints_wrong_script, correct_constraints_wrong_script])

        false_verifier = approach_df[(approach_df["verify_result"] == 0)]
        false_verifier["API"] = api_folder
        all_false_verifier = pd.concat([all_false_verifier, false_verifier])

    # remove all col with 'unnamed'
    all_correct_constraints_wrong_script = all_correct_constraints_wrong_script.loc[:, ~all_correct_constraints_wrong_script.columns.str.contains('^Unnamed')]
    correct_constraints_wrong_script_file = f"{approach_folder}/correct_constraints_wrong_script.xlsx"
    all_correct_constraints_wrong_script.to_excel(correct_constraints_wrong_script_file, index=False)

    all_false_verifier = all_false_verifier.loc[:, ~all_false_verifier.columns.str.contains('^Unnamed')]
    false_verifier_file = f"{approach_folder}/false_verifier.xlsx"
    all_false_verifier.to_excel(false_verifier_file, index=False)

def evaluate_request_response_test_gen(approach_folder, api_folders, original_approach_folder, ground_truth_folder):
    all_correct_constraints_wrong_script = pd.DataFrame()
    all_false_verifier = pd.DataFrame()
    for api_folder in api_folders:
        if api_folder == ".DS_Store":
            continue
        approach_file = f'{approach_folder}/{api_folder}/request_response_constraints.xlsx'
        ground_truth_file = f'{ground_truth_folder}/{api_folder}/request_response_constraints.xlsx'
        original_approach_file = f'{original_approach_folder}/{api_folder}/request_response_constraints.xlsx'
        if not os.path.exists(approach_file) or not os.path.exists(ground_truth_file) or not os.path.exists(original_approach_file):
            continue

        print(f"Evaluating test generation for {approach_file}")
        approach_df = pd.read_excel(approach_file, engine='openpyxl')
        ground_truth_df = pd.read_excel(ground_truth_file, engine='openpyxl')
        original_approach_df = pd.read_excel(original_approach_file, engine='openpyxl')

        if approach_df.empty or ground_truth_df.empty or original_approach_df.empty:
            continue

        for i, row in approach_df.iterrows():
            constraint_correctness = row["constraint_correctness"]
            tp = row["tp"]
            if constraint_correctness == "FP" and tp == 1:
                print(f"Line {i}: Error: FP but tp == 1")
                input()

            verification_script = row["verification script"]
            original_verification_script = original_approach_df.iloc[i]["verification script"]
            # if verification_script is null or empty or nan, copy the original verification script
            if pd.isnull(verification_script) or verification_script == "":
                approach_df.at[i, "verification script"] = original_verification_script

            # do similar for the executable script
            executable_script = row["executable script"]
            original_executable_script = original_approach_df.iloc[i]["executable script"]
            # if verification_script is null or empty or nan, copy the original verification script
            if pd.isnull(executable_script) or executable_script == "":
                approach_df.at[i, "executable script"] = original_executable_script

            status = row["status"]
            original_status = original_approach_df.iloc[i]["status"]
            # if status is null or empty or nan, copy the original status
            if pd.isnull(status) or status == "":
                approach_df.at[i, "status"] = original_status

        approach_df.to_excel(approach_file, index=False)

        
        total = len(approach_df)
        correct_constraints_wrong_script = approach_df[(approach_df["tp"] == 0) & (approach_df["constraint_correctness"] == "TP")]

        correct_constraints_wrong_script["API"] = api_folder
        all_correct_constraints_wrong_script = pd.concat([all_correct_constraints_wrong_script, correct_constraints_wrong_script])

        false_verifier = approach_df[(approach_df["verify_result"] == 0)]
        false_verifier["API"] = api_folder
        all_false_verifier = pd.concat([all_false_verifier, false_verifier])

    # remove all col with 'unnamed'
    all_correct_constraints_wrong_script = all_correct_constraints_wrong_script.loc[:, ~all_correct_constraints_wrong_script.columns.str.contains('^Unnamed')]
    correct_constraints_wrong_script_file = f"{approach_folder}/correct_constraints_wrong_script.xlsx"
    all_correct_constraints_wrong_script.to_excel(correct_constraints_wrong_script_file, index=False)

    all_false_verifier = all_false_verifier.loc[:, ~all_false_verifier.columns.str.contains('^Unnamed')]
    false_verifier_file = f"{approach_folder}/false_verifier.xlsx"
    all_false_verifier.to_excel(false_verifier_file, index=False)
