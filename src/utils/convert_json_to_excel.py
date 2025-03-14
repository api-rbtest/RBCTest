import pandas as pd

def convert_json_to_excel(json_file, excel_file):
    # Read the JSON file
    data = pd.read_json(json_file)
    
    # Convert the JSON data to a DataFrame
    df = pd.DataFrame(data)
    
    # Write the DataFrame to an Excel file
    df.to_excel(excel_file, index=False)

# Example usage
json_file = "{experiment_folder}/Stripe API/parameter_constraints.json"
excel_file = "{experiment_folder}/Stripe API/parameter_constraints.xlsx"
convert_json_to_excel(json_file, excel_file)