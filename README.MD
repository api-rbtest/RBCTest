# Repository for "RBCTest: Leveraging LLMs to Mine and Verify Oracles ofAPI Response Bodies for RESTful API Testing"

This repository contains the resources and code related to the paper "RBCTest: Leveraging LLMs to Mine and Verify Oracles ofAPI Response Bodies for RESTful API Testing."

## Folder Structure

- [`RBCTest_dataset`](RBCTest_dataset): Our self-collected dataset, contains of 8 services, including an OpenAPI specification for each service.
- [`agora_dataset`](AGORA_dataset): AGORA's dataset.
- [`approaches`](approaches): Includes our ground-truth constraints, detected constraints from RBCTest, RBCTest-.
- [`src`](src): Source code.
- Benchmark for API Constraints Mining in [`approaches/agora_data/our_ground_truth`](approaches/agora_data/our_ground_truth) and [`approaches/our_data/our_ground_truth`](approaches/our_data/our_ground_truth).

## Usage

### Environment Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file under the [`src`](src) directory with the following content:
   ```
   OPENAI_API_KEY=<your_openai_api_key>
   ```
   Please ensure that your key supports the required models.

### Constraint Mining

1. **Request-Response Constraints:**
   - For our approach:
     ```bash
     python src/request_response_constraint_mining.py
     ```
   - For the ablation approach:
     ```bash
     python src/response_property_constraint_mining_ablation.py
     ```

2. **Response Property Constraints:**
   - For our approach:
     ```bash
     python src/request_response_constraint_mining.py
     ```
   - For the ablation approach:
     ```bash
     python src/request_response_constraint_mining_ablation.py
     ```

### Constraint Test Generation

- Run the script:
  ```bash
  python src/constraints_test_generation.py
  ```

## Evaluation

- To re-evaluate constraints mining, run:
  ```bash
  python src/evaluate_constraints_mining.py
  ```

- To re-evaluate test generation, run:
  ```bash
  python src/evaluate_test_gen.py
  ```
 
## Experimental Results

### RQ1 Results on AGORA and RBCTest Dataset
#### AGORA Dataset
- All Dynamic (AGORA) detected invariants: [`AGORA-eval/agora_all.xlsx`](AGORA-eval/agora_all.xlsx)
- All Static (LLM-based) detected constraints: see sub-folders in [`approaches/agora_data/our_mining`](approaches/agora_data/our_mining)
- Overlapping analysis: [`AGORA-eval/overlapping_analysis_all.xlsx`](AGORA-eval/overlapping_analysis_all.xlsx)
#### RBCTest Dataset
- All Dynamic (AGORA) detected invariants: see file invariants.csv in each sub-folders [`approaches/our_data/agora_mining/`](approaches/our_data/agora_mining) 
- All Static (LLM-based) detected constraints: see sub-folders in [`approaches/our_data/our_mining/`](approaches/our_data/our_mining/)
- Overlapping analysis: [`approaches/agora_data/Overlapping.xlsx`](approaches/agora_data/Overlapping.xlsx) and [`approaches/our_data/Overlapping.xlsx`](approaches/our_data/Overlapping.xlsx)

**Annotation:** in column "Better"
- `1`: Static constraint is better
- `-1`: Dynamic invariant is better
- `0`: Equivalent constraint

### RQ2, RQ3, RQ4 Results on RBCTest Dataset and AGORA Dataset
- Results Analysis: [`approaches/agora_data/Overlapping.xlsx`](approaches/agora_data/Overlapping.xlsx) and [`approaches/our_data/Overlapping.xlsx`](approaches/our_data/Overlapping.xlsx) in sheet 'AnalyzeRQ2'
- Details: see [`approaches/agora_data`](approaches/agora_data) (each subfolder is an API-under-test) of AGORA Dataset and [`approaches/our_mining`](approaches/our_mining) (each subfolder is an API-under-test) of RBCTest Dataset
### RQ5 Ablation
- Ablation study: see [`approaches/ablation`](approaches/ablation)

