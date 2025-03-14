import os
import pandas as pd
import openpyxl

def categorize_constraint(excel_file, knowledge_base_file):
    print(f"Categoryzing {excel_file}")
    df = pd.read_excel(excel_file, engine='openpyxl')
    kb_df = pd.read_excel(knowledge_base_file, engine='openpyxl')
    if df.empty or kb_df.empty:
        return
    for row, data in df.iterrows():
        description = data["description"]
        if "corresponding attribute description" in df.columns:
            description = data["corresponding attribute description"]

        # find the description in the knowledge base
        mask = kb_df["description"] == description
        found_mapping = kb_df[mask]
        if found_mapping.empty:
            print(f"Cannot find {description}")
            continue
        category = found_mapping["category of constraint"].values[0]
        df.at[row, "category of constraint"] = category

    df.to_excel(excel_file, index=False)

        

def summarize_test_gen_response(excel_file, summary_dict, api_name):
    global all_description
    print(f"Excel file: {excel_file}")
    # read excel file and make sure it is read as string
    df = pd.read_excel(excel_file, engine='openpyxl', dtype=str)
    if df.empty:
        return summary_dict, pd.DataFrame()
    # filter TP constraints
    if "constraint_correctness" not in df.columns or "correctness_of_script" not in df.columns:
        print(f"Excel file {excel_file} does not have column constraint_correctness")
        return summary_dict, pd.DataFrame()
    tp_df = df[df["constraint_correctness"] == "TP"]
    # correct test
    print(tp_df["correctness_of_script"])
    first_row = tp_df.at[tp_df.index[0], "correctness_of_script"]
    if first_row == "correct" or first_row == "incorrect":
        correct_df = tp_df[tp_df["correctness_of_script"] == "correct"]
    else:
        correct_df = tp_df[tp_df["correctness_of_script"] == "True"]
    # correctness_of_script is correct and status is satisfied
    truely_satisfied_df = correct_df[(correct_df["status"] == "satisfied")]
    truely_mismatched_df = correct_df[(correct_df["status"] == "mismatched")]
    truely_unknown_df = correct_df[correct_df["status"] == "unknown"]

    summary_dict[api_name] = {
        "All": len(df),
        "No test gen": len(tp_df),
        "correct": len(correct_df),
        "TP_satisfied": len(truely_satisfied_df),
        "TP_mismatched": len(truely_mismatched_df),
        "unknown": len(truely_unknown_df)
    }

    api_path = os.path.dirname(excel_file)
    base_name = os.path.basename(excel_file)
    output_path = os.path.join(api_path, f"annalyze_{base_name}")

    truely_mismatched_df["API"] = api_name


    return summary_dict, truely_mismatched_df
    




if __name__ == "__main__":
    root_exp = "approaches/rbctest_our_data"

    summarize_test_gen_for_response = {}
    summarize_test_gen_for_request = {}
    api_names = []
    all_true_mismatched = pd.DataFrame()

    apis = [api for api in os.listdir(root_exp) if os.path.isdir(
        os.path.join(root_exp, api)) and not api.startswith(".")]
    apis.sort()
    

    for api in apis:
        # if "Canada" in api:
        #     continue
        api_name = api.replace(" API", "")
        api_names.append(api_name)
        api_path = os.path.join(root_exp, api)
        excel_files = [f for f in os.listdir(api_path) if f.endswith(
            ".xlsx") and not f.startswith("~$") and not f.startswith(".")]
        print(f"API: {api}")

        response_excel = None
        request_excel = None 


        response_excel = os.path.join(api_path, "response_property_constraints.xlsx")
        request_excel = os.path.join(api_path, "request_response_constraints.xlsx")

        print(f"Found files: {response_excel}, {request_excel}")

        if os.path.exists(response_excel):
            summarize_test_gen_for_response, true_mismatched = summarize_test_gen_response(response_excel, summarize_test_gen_for_response, api_name)
            all_true_mismatched = pd.concat([all_true_mismatched, true_mismatched])

        if os.path.exists(request_excel):
            summarize_test_gen_for_request, true_mismatched = summarize_test_gen_response(request_excel, summarize_test_gen_for_request, api_name)
            all_true_mismatched = pd.concat([all_true_mismatched, true_mismatched])

        

    # add a row for total and average precision
    total_request = {
        "All": 0,
        "No test gen": 0,
        "correct": 0,
        "TP_satisfied": 0,
        "FP_satisfied": 0,
        "TP_mismatched": 0,
        "FP_mismatched": 0,
        "unknown": 0
    }
    total_response = {
        "All": 0,
        "No test gen": 0,
        "correct": 0,
        "TP_satisfied": 0,
        "FP_satisfied": 0,
        "TP_mismatched": 0,
        "FP_mismatched": 0,
        "unknown": 0
    }
    for api in api_names:
        if api not in summarize_test_gen_for_response:
            summarize_test_gen_for_response[api] = {
                "All": 0,
                "No test gen": 0,
                "correct": 0,
                "TP_satisfied": 0,
                "FP_satisfied": 0,
                "TP_mismatched": 0,
                "FP_mismatched": 0,
                "unknown": 0
            }
        else:
            for key in summarize_test_gen_for_response[api]:
                total_response[key] += summarize_test_gen_for_response[api][key]

        if api not in summarize_test_gen_for_request:
            summarize_test_gen_for_request[api] = {
                "All": 0,
                "No test gen": 0,
                "correct": 0,
                "TP_satisfied": 0,
                "FP_satisfied": 0,
                "TP_mismatched": 0,
                "FP_mismatched": 0,
                "unknown": 0
            }
        else:
            for key in summarize_test_gen_for_request[api]:
                total_request[key] += summarize_test_gen_for_request[api][key]
    summarize_test_gen_for_response["Total"] = total_response
    summarize_test_gen_for_request["Total"] = total_request

    

    with pd.ExcelWriter(f"{root_exp}/test_gen_summary.xlsx") as writer:
        df = pd.DataFrame.from_dict(summarize_test_gen_for_response, orient='index')
        df.sort_index(inplace=True)
        # remove col FP_satisfied and FP_mismatched
        df.drop(columns=["FP_satisfied", "FP_mismatched"], inplace=True)

        df.to_excel(writer, sheet_name='response')

        df = pd.DataFrame.from_dict(summarize_test_gen_for_request, orient='index')
        df.sort_index(inplace=True)
        # remove col FP_satisfied and FP_mismatched
        df.drop(columns=["FP_satisfied", "FP_mismatched"], inplace=True)

        df.to_excel(writer, sheet_name='request')

        all_true_mismatched.to_excel(writer, sheet_name='all_true_mismatched')




            
    print("Done!")
