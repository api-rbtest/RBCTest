import pandas as pd
import tkinter as tk
from tkinter import messagebox, scrolledtext

# CSV file path
csv_file = r"experiment_our\Hotel Search API\invariants_description.csv"
df = pd.read_csv(csv_file, encoding='utf-8', sep='\t')
print(df.head())
# Add 'eval' column if it does not exist
if 'eval' not in df.columns:
    df['eval'] = ''

# Initialize row index
current_index = 0

# Create the main application window
root = tk.Tk()
root.title("CSV Evaluator")
max_width = root.winfo_screenwidth()
max_height = root.winfo_screenheight()
root.geometry(f"{max_width}x{max_height}")

# Define UI elements
label_frame = tk.Frame(root)
label_frame.pack(pady=20)

# Label to show the index of the current row
index_label = tk.Label(label_frame, text=f"Row {current_index + 1} of {len(df)}", font=('Arial', 30, 'bold'), fg='red')
index_label.pack()

upper_frame = tk.Frame(root)
upper_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

lower_frame = tk.Frame(root)
lower_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Upper section for displaying "Invariant Details"
upper_label = tk.Label(upper_frame, text="Invariant Details", font=('Arial', 20, 'bold'), fg='blue')
upper_label.pack()

upper_textbox = scrolledtext.ScrolledText(upper_frame, wrap=tk.WORD, height=10, font=('Arial', 16, 'normal'))
upper_textbox.pack(fill=tk.BOTH, expand=True)

# Lower section for displaying "Postman Assertion and Description"
lower_label = tk.Label(lower_frame, text="Postman Assertion and Description", font=('Arial', 20, 'bold'), fg='blue')
lower_label.pack()

lower_textbox = scrolledtext.ScrolledText(lower_frame, wrap=tk.WORD, height=10, font=('Arial', 16, 'normal'))
lower_textbox.pack(fill=tk.BOTH, expand=True)

# Input field for evaluation
input_text = tk.StringVar()
entry = tk.Entry(root, textvariable=input_text, font=('Arial', 20), width=50)
entry.pack(pady=20)
entry.bind("<Return>", lambda event: navigate(1))

button_frame = tk.Frame(root)
button_frame.pack(pady=20)

prev_button = tk.Button(button_frame, text="Previous", command=lambda: navigate(-1))
prev_button.pack(side=tk.LEFT, padx=5)

next_button = tk.Button(button_frame, text="Next", command=lambda: navigate(1))
next_button.pack(side=tk.RIGHT, padx=5)

save_button = tk.Button(root, text="Save", command=lambda: save_input())
save_button.pack(pady=10)

def update_ui():
    global current_index
    row_data = df.iloc[current_index].drop('eval').to_dict()
    
    upper_text = f"{row_data['pptname']}\n\n{row_data['invariant']}\n - Type: {row_data['invariantType']}\n - Variables: {row_data['variables']}"
    lower_text = f"{row_data['postmanAssertion']}\n\n{row_data['description']}"

    upper_textbox.delete('1.0', tk.END)
    upper_textbox.insert(tk.INSERT, upper_text)

    lower_textbox.delete('1.0', tk.END)
    lower_textbox.insert(tk.INSERT, lower_text)
    
    input_text.set(df.at[current_index, 'eval'])
    index_label.config(text=f"Row {current_index + 1} of {len(df)}")

def navigate(direction):
    global current_index
    save_input()
    new_index = current_index + direction
    if 0 <= new_index < len(df):
        current_index = new_index
        update_ui()
    else:
        messagebox.showwarning("Navigation Error", "No more rows in that direction.")
    df.to_csv(csv_file, sep='\t', encoding='utf-16', index=False)

def save_input():
    global current_index
    eval_value = input_text.get().strip().lower()
    if eval_value in ['t', 'f']:
        df.at[current_index, 'eval'] = eval_value
    else:
        messagebox.showerror("Input Error", "Please enter 't' or 'f' for evaluation.")

update_ui()
root.mainloop()
df.to_csv(csv_file, sep='\t', encoding='utf-16', index=False)
