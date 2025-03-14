import os
from eval.request_approach_evaluate import evaluate_request_response_constraint_mining, evaluate_request_response_test_gen
from eval.response_approach_evaluate import evaluate_response_property_constraint_mining, evaluate_response_property_test_gen


def main():
    approach_folder = "approaches/baseline"
    ground_truth_folder = "approaches/ground_truth"
    csv_file = f"{approach_folder}/approach_evaluation.csv"

    if os.path.exists(csv_file):
        os.remove(csv_file)

    api_folders = os.listdir(ground_truth_folder)
    api_folders = [f for f in api_folders if not f.startswith(".") and os.path.isdir(os.path.join(ground_truth_folder, f))]
    api_folders.sort()

    evaluate_request_response_constraint_mining(approach_folder, ground_truth_folder, api_folders, csv_file, verifier=False)
    evaluate_response_property_constraint_mining(approach_folder, ground_truth_folder, api_folders, csv_file, verifier=False)

    csv_file = f"{approach_folder}/approach_evaluation_test_gen__.csv"
    if os.path.exists(csv_file):
        os.remove(csv_file)

    api_folders = os.listdir(approach_folder)
    api_folders = [f for f in api_folders if not f.startswith(".") and os.path.isdir(os.path.join(approach_folder, f))]
    api_folders.sort()

    evaluate_request_response_test_gen(approach_folder, api_folders, csv_file, ground_truth_folder)
    evaluate_response_property_test_gen(approach_folder, api_folders, csv_file, ground_truth_folder)



if __name__ == "__main__":
    main()
    