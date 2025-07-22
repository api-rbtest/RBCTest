import os
from response_approach_evaluate import evaluate_response_property_constraint_mining, evaluate_response_property_test_gen
from request_approach_evaluate import evaluate_request_response_constraint_mining

def normalize_api_name(api_name):
    # Chuẩn hóa tên API để phù hợp với cấu trúc thư mục ground_truth
    if api_name == "Hotel Search API" or api_name == "Hotel Search":
        return "Hotel Search"
    return api_name

def main():
    # Đường dẫn đến thư mục chứa dữ liệu
    root_exp = "approaches/rbctest_our_data"
    ground_truth_folder = "approaches/ground_truth"
    
    # Lấy danh sách các API
    api_folders = [api for api in os.listdir(root_exp) if os.path.isdir(os.path.join(root_exp, api)) and not api.startswith(".")]
    api_folders.sort()
    
    # Đánh giá response property constraints
    print("Evaluating response property constraints...")
    evaluate_response_property_constraint_mining(
        approach_folder=root_exp,
        ground_truth_folder=ground_truth_folder,
        api_folders=api_folders,
        csv_file=f"{root_exp}/response_property_evaluation.csv",
        export=True
    )
    
    # Đánh giá response property test generation
    print("\nEvaluating response property test generation...")
    evaluate_response_property_test_gen(
        approach_folder=root_exp,
        api_folders=api_folders,
        csv_file=f"{root_exp}/response_property_test_gen_evaluation.csv",
        ground_truth_folder=ground_truth_folder
    )
    
    # Đánh giá request-response constraints
    print("\nEvaluating request-response constraints...")
    evaluate_request_response_constraint_mining(
        approach_folder=root_exp,
        ground_truth_folder=ground_truth_folder,
        api_folders=api_folders,
        csv_file=f"{root_exp}/request_response_evaluation.csv",
        export=True
    )
    
    print("\nEvaluation completed!")

if __name__ == "__main__":
    main() 