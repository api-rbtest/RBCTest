from utils.openapi_utils import *
from utils.gptcall import GPTChatCompletion
import subprocess
import re
import json
import os
import copy

############################################# PROMPTS #############################################
DESCRIPTION_OBSERVATION_PROMPT = '''Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"
- schema: "{param_schema}"

If the description implies any constraints, rules, or limitations for legalizing the attribute itself, let's provide a brief description of these constraints.
'''


NAIVE_CONSTRAINT_DETECTION_PROMPT = '''Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"

If the description implies any constraints, rules, or limitations for legalizing the attribute itself, return yes; otherwise, return no. follow the following format:
```answer
yes/no
```

'''


CONSTRAINT_CONFIRMATION = '''Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself. Your goal is to confirm whether there is sufficient information to generate a test script that verifies those constraints.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"
- schema: "{param_schema}"

Does the description imply any constraints, rules, or limitations?
- {description_observation}

Follow these rules to determine whether a constraint validation script can be generated:

1. **General rule**: Consider a constraint valid if the description contains specific values, value sets, format patterns, or conditional logic that can be programmatically checked.

2. **Format signals**: If the description **includes or implies formats** (either explicitly or via examples), treat them as constraints when:
   - It mentions or implies **URI, URL, or HTTP links**, especially GitHub or API links (e.g. `https://api.github.com/...`)
   - It contains timestamps or patterns resembling **ISO 8601** (`2011-01-26T19:06:43Z`)
   - It includes **email-like**, **slug**, **date**, **date-time**, or **version strings** (e.g., `"v1.0"`, `"YYYY-MM-DD"`)
   - It includes `format: uri`, `format: date-time`, even without textual explanation.

3. **Enum constraints**: If the description mentions fixed options (e.g., "must be one of 'public', 'private', 'internal'") — even inside examples — this implies an enum constraint.

4. **Min/Max/Range**: Mention of numeric/string range, length, size (e.g., "must be ≤ 255", "between 1 and 10") is a constraint.

5. **Avoid vague recommendations**: Do not treat vague phrases like "recommended", "typically", or "usually" as enforceable unless they come with clear validation rules.

6. **Examples inside description**:
   - If the description or schema includes **examples** that clearly indicate format (e.g., a URL or date), and no contradictory information is given, assume it implies a valid constraint.

Now, let's confirm: Is there sufficient information mentioned in the description to generate a script for verifying the identified constraints?
```answer
yes/no
```
'''




# CONSTRAINT_CONFIRMATION = '''Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself. Ensure that the description contains sufficient information to generate a script capable of verifying these constraints.

# Below is the attribute's specification:
# - name: "{attribute}"
# - type: {data_type}
# - description: "{description}"
# - schema: "{param_schema}"

# Does the description imply any constraints, rules, or limitations?
# - {description_observation}

# Follow these rules to identify the capability of generating a constraint validation test script:
# - If there is a constraint for the attribute itself, check if the description contains specific predefined values, ranges, formats, etc. Exception: Predefined values such as True/False for the attribute whose data type is boolean are not good constraints.
# - If there is an inter-parameter constraint, ensure that the relevant attributes have been mentioned in the description.

# Now, let's confirm: Is there sufficient information mentioned in the description to generate a script for verifying these identified constraints?
# ```answer
# yes/no
# ```
# '''

GROOVY_SCRIPT_VERIFICATION_GENERATION_PROMPT = '''Given a description implying constraints, rules, or limitations of an attribute in a REST API, your responsibility is to generate a corresponding Python script to check whether these constraints are satisfied through the API response.

Below is the attribute's description:
- "{attribute}": "{description}"

{attribute_observation}

Below is the API response's schema:
"{schema}": "{specification}"

The correspond attribute of "{attribute}" in the API response's schema is: "{corresponding_attribute}"

Below is the request information to the API: 
{request_information}

Rules: 
- Ensure that the generated Python code can verify fully these identified constraints.
- The generated Python code does not include any example of usages.
- The Python script should be generalized, without specific example values embedded in the code.
- The generated script should include segments of code to assert the satisfaction of constraints using a try-catch block.
- You'll generate a Python script using the response body variable named 'latest_response' (already defined) to verify the given constraint in the triple backticks as below: 
```python
def verify_latest_response(latest_response):
    // deploy verification flow...
    // return True if the constraint is satisfied and False otherwise.
```
- No explanation is needed.'''

IDL_TRANSFORMATION_PROMPT = '''You will be provided with a description specifying the constraint/rule/limitation of an attribute in natural language and a Python script to verify whether the attribute satisfies that constraint or not. Your responsibility is to specify that constraint using IDL. Follow these steps below to complete your task:

STEP 1: You will be guided to understand IDL keywords.

Below is the catalog of Inter/Inner-Parameter Dependency Language (IDL for short):

1. Conditional Dependency: This type of dependency is expressed as "IF <predicate> THEN <predicate>;", where the first predicate is the condition and the second is the consequence.
Syntax: IF <predicate> THEN <predicate>;
Example: IF custom.label THEN custom.amount; //This specification implies that if a value is provided for 'custom.label' then a value must also be provided for 'custom.amount' (or if custom.label is True, custom.amount must also be True).

2. Or: This type of dependency is expressed using the keyword "Or" followed by a list of two or more predicates placed inside parentheses: "Or(predicate, predicate [, ...]);". The dependency is satisfied if at least one of the predicates evaluates to true.
Syntax/Predicate: Or(<predicate>, <predicate>, ...);
Example: Or(header, upload_type); //This specification implies that the constraint will be satisfied if a value is provided for at least one of 'header' or 'upload_type' (or if at least one of them is True).

3. OnlyOne: These dependencies are specified using the keyword "OnlyOne" followed by a list of two or more predicates placed inside parentheses: "OnlyOne(predicate, predicate [, ...]);". The dependency is satisfied if one, and only one of the predicates evaluates to true.
Syntax/Predicate: OnlyOne(<predicate>, <predicate>, ...);
Example: OnlyOne(amount_off, percent_off); //This specification implies that the constraint will be satisfied if a value is provided for only one of 'header' or 'upload_type' (or if only one of them is set to True)

4. AllOrNone: This type of dependency is specified using the keyword "AllOrNone" followed by a list of two or more predicates placed inside parentheses: "AllOrNone(predicate, predicate [, ...]);". The dependency is satisfied if either all the predicates evaluate to true, or all of them evaluate to false.
Syntax/Predicate: AllOrNone(<predicate>, <predicate>, ...)
Example: AllOrNone(rights, filter=='track'|'album'); //This specification implies that the constraint will be satisfied under two conditions: 1. If a value is provided for 'rights,' then the value of 'filter' must also be provided, and it can only be 'track' or 'album'. 2. Alternatively, the constraint is satisfied if no value is provided for 'rights' and 'filter' (or if the value of 'filter' is not 'track' or 'album').

5. ZeroOrOne: These dependencies are specified using the keyword "ZeroOrOne" followed by a list of two or more predicates placed inside parentheses: "ZeroOrOne(predicate, predicate [, ...]);". The dependency is satisfied if none or at most one of the predicates evaluates to true.
Syntax/Predicate: ZeroOrOne(<predicate>, <predicate>, ...)
Example: ZeroOrOne(type, affiliation); // This specification implies that the constraint will be satisfied under two conditions: 1. If no value is provided for 'type' and 'affiliation' (or both are False). 2. If only one of 'type' and 'affiliation' is provided a value (or if only one of them is set to True).

6. Arithmetic/Relational: Relational dependencies are specified as pairs of parameters joined by any of the following relational operators: ==, !=, <=, <, >= or >. Arithmetic dependencies relate two or more parameters using the operators +, - , *, / followed by a final comparison using a relational operator.
Syntax: ==, !=, <=, <, >=, >, +, - , *, /
Example: created_at_min <= created_at_max; // the created_at_min is less than or equal to created_at_max

7. Boolean operators: 'AND', 'OR', 'NOT'

STEP 2: You will be provided with the attribute's description specifying a constraint in natural language and the corresponding generated Python script to verify the attribute's satisfaction for that constraint.

Below is the attribute's description:
- "{attribute}": "{description}"

Below is the specification for the {part}, where the attribute is specified:
{specification}

Below is the generated Python script to verify that constraint:
{generated_python_script}

Now, help to specify the constraint/limitation of the attribute using IDL by considering both the constraint in natural language and its verification script in Python, follow these rules below: 
- If the provided constraint description does not mention any types mentioned above, you do not need to respond with any IDL specification.
- You do not need to generate any data samples in the IDL specification sentence; instead, mention the related variables and data in the constraint description only.
- Only respond the IDL sentence and only use IDL keywords (already defined above).
- Only respond coresponding your IDL specification. 
- Respond IDL specification in the format below:
```IDL
IDL specification...
```
- No explanation is needed.'''
####################################################################################################

def extract_variables(statement):
    variable_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    matches = re.findall(variable_pattern, statement)
    
    keywords = {'IF', 'THEN', 'Or', 'OnlyOne', 'AllOrNone', 'ZeroOrOne', 'AND', 'OR', 'NOT', '==', '!=', '<=', '<', '>=', '>', '+', '-' , '*', '/', 'True', 'False', 'true', 'false'}
    
    variables = []
    for match in matches:
        if match not in keywords:
            preceding_text = statement[:statement.find(match)]
            if not (preceding_text.count('"') % 2 != 0 or preceding_text.count("'") % 2 != 0):
                variables.append(match)
    
    return list(set(variables))

def extract_values(statement):
    pattern = r"\'(.*?)\'|\"(.*?)\"|(\d+\.?\d*)"
    matches = re.findall(pattern, statement)
    
    values = [match[0] or match[1] or match[2] for match in matches]
    return values

# This is used to extract attributes specified in OpenAPI spec (except OpenAPI keywords)
def extract_dict_attributes(input_dict, keys_list=None):
    if keys_list is None:
        keys_list = []
    
    for key, value in input_dict.items():
        if not key.startswith("array of") and not key.startswith("schema of"):
            keys_list.append(key)
        if isinstance(value, dict):
            extract_dict_attributes(value, keys_list)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    extract_dict_attributes(item, keys_list)
    return keys_list

def extract_python_code(response):
    if response is None:
        return None
    
    pattern = r'```python\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)

    if match:
        python_code = match.group(1)
        return python_code
    else:
        return None
    
def extract_answer(response):
    if response is None:
        return None
    
    if "```answer" in response:
        pattern = r'```answer\n(.*?)```'
        match = re.search(pattern, response, re.DOTALL)

        if match:
            answer = match.group(1)
            return answer.strip()
        else:
            return None  
    else:
        return response.lower()
    
def extract_summary_constraint(response):
    if response is None:
        return None
    
    pattern = r'```constraint\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)

    if match:
        constraint = match.group(1)
        return constraint.strip()
    else:
        return None  
    
def extract_idl(response):
    if response is None:
        return None
    
    pattern = r'```IDL\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)

    if match:
        constraint = match.group(1)
        return constraint.strip()
    else:
        return None 

def is_construct_json_object(text):
    try:
        json.loads(text)
        return True
    except:
        return False
    
def standardize_returned_idl(idl_sentence):
    if idl_sentence is None:
        return None
    
    idl_lines = idl_sentence.split("\n")
    for i, line in enumerate(idl_lines):
        if ":" in line:
            idl_lines[i] = line.split(":", 1)[1].lstrip()
            
    result = "\n".join(idl_lines).strip('`"\'')
    
    return result

# Method of test_data.TestDataGenerator class
class ConstraintExtractor:
    def __init__(self, openapi_path, save_and_load=False, list_of_operations=None, experiment_folder="experiment") -> None:
        self.openapi_path = openapi_path
        self.save_and_load = save_and_load
        self.list_of_operations = list_of_operations
        self.experiment_folder = experiment_folder
        self.initialize()
        self.filter_params_w_descr()

    
    def initialize(self):
        self.openapi_spec = load_openapi(self.openapi_path)
        self.service_name = self.openapi_spec["info"]["title"]
        
        self.simplified_openapi = simplify_openapi(self.openapi_spec)
        
        self.mappings_checked = []
        self.input_parameters_checked = []
        if self.save_and_load:
            self.mappings_checked_save_path = f"{self.experiment_folder}/{self.service_name}/mappings_checked.txt"
            if os.path.exists(self.mappings_checked_save_path):
                self.mappings_checked = json.load(open(self.mappings_checked_save_path, "r"))
            
            self.input_parameters_checked_save_path = f"{self.experiment_folder}/{self.service_name}/input_parameters_checked.txt"
            if os.path.exists(self.input_parameters_checked_save_path):
                self.input_parameters_checked = json.load(open(self.input_parameters_checked_save_path, "r"))
            
        if self.list_of_operations is None:
            self.list_of_operations = list(self.simplified_openapi.keys())
        
    def filter_params_w_descr(self):
        """
        Create a new dict from `self.openapi_spec`, which contains only operations that have parameters/request body fields with description.
        Save the new dict to `self.operations_containing_param_w_description`

        Returns:
            dict: the value of `self.operations_containing_param_w_description`
        """
        self.operations_containing_param_w_description = {}
        # Get simplified openapi Spec with params, that each param has a description
        self.operation_param_w_descr = simplify_openapi(self.openapi_spec)
        
        self.total_inference = json.dumps(self.operation_param_w_descr).count("(description:")
        
        for operation in self.operation_param_w_descr:
            self.operations_containing_param_w_description[operation] = {}
            if "summary" in self.operation_param_w_descr[operation]:
                self.operations_containing_param_w_description[operation]["summary"] = self.operation_param_w_descr[operation]["summary"]
                
            parts = ["parameters", "requestBody"]
            for part in parts:
                if self.operation_param_w_descr.get(operation, {}).get(part, None) is not None:
                    self.operations_containing_param_w_description[operation][part] = {}
                    if isinstance(self.operation_param_w_descr[operation][part], dict):
                        for param, value in self.operation_param_w_descr[operation][part].items():
                            if "description" in value:
                                self.operations_containing_param_w_description[operation][part][param] = value
    
    def checkedMapping(self, mapping):
        for check_mapping in self.mappings_checked:
            if check_mapping[0] == mapping:
                return check_mapping
        return None
        
    def get_response_body_input_parameter_mappings_with_constraint(self):
        print("Filterring response body constraints through input parameters...")
        self.input_parameter_responsebody_mapping = json.load(open(f"{self.experiment_folder}/{self.service_name}/request_response_mappings.json", "r"))
        self.response_body_input_parameter_mappings_with_constraint = copy.deepcopy(self.input_parameter_responsebody_mapping)

        for schema in self.input_parameter_responsebody_mapping:
            for attribute in self.input_parameter_responsebody_mapping[schema]:
                for mapping in self.input_parameter_responsebody_mapping[schema][attribute]:
                    operation, part, corresponding_attribute = mapping

                    # If the attribute does not have a description, just skip it
                    if "(description:" not in self.operations_containing_param_w_description[operation][part][corresponding_attribute]:
                        self.response_body_input_parameter_mappings_with_constraint[schema][attribute].remove(mapping)
                        continue
                    
                    data_type = self.operations_containing_param_w_description[operation][part][corresponding_attribute].split("(description: ")[0].strip()
                    description = self.operations_containing_param_w_description[operation][part][corresponding_attribute].split("(description: ")[-1][:-1].strip()
                    
                    check_mapping = self.checkedMapping(mapping)
                    if check_mapping:
                        confirmation_status = check_mapping[1]
                        if confirmation_status != 'yes':
                            if mapping in self.response_body_input_parameter_mappings_with_constraint[schema][attribute]:
                                self.response_body_input_parameter_mappings_with_constraint[schema][attribute].remove(mapping)
                        continue
                    
                    # generate an observation for the current description
                    description_observation_prompt = DESCRIPTION_OBSERVATION_PROMPT.format(
                        attribute = corresponding_attribute,
                        data_type = data_type,
                        description = description
                    )
                    description_observation_response = GPTChatCompletion(description_observation_prompt, model="gpt-4-turbo")
                    
                    # assert that the description implies constraints
                    constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                        attribute = corresponding_attribute,
                        data_type = data_type,
                        description = description,
                        description_observation = description_observation_response
                    )
                    constraint_confirmation_response = GPTChatCompletion(constraint_confirmation_prompt, model="gpt-4-turbo")
                    confirmation = extract_answer(constraint_confirmation_response) # 'yes' or 'no'
                    
                    if confirmation != 'yes':
                        if mapping in self.response_body_input_parameter_mappings_with_constraint[schema][attribute]:
                            self.response_body_input_parameter_mappings_with_constraint[schema][attribute].remove(mapping)
                            
                    self.mappings_checked.append([mapping, confirmation]) # 'yes' if this is a valid constraint, otherwise 'no'
                    
                    # update checked mappings to file
                    if self.save_and_load:
                        with open(self.mappings_checked_save_path, "w") as file:
                            json.dump(self.mappings_checked, file)

                            
                    
    def foundConstraintResponseBody(self, checking_attribute):
        for checked_attribute in self.found_responsebody_constraints:
            if checking_attribute == checked_attribute[0]:
                return checked_attribute
        return None
    
    def foundConstraintInputParameter(self, checking_parameter):
        for checked_parameter in self.input_parameters_checked:
            if checking_parameter == checked_parameter[0]:
                return checked_parameter
        return None
    
    def get_input_parameter_constraints(self, outfile=None):
        print("Inferring constaints inside input parameters...")
        self.input_parameter_constraints = {}
        
        progress_size = len(self.list_of_operations)*2
        completed = 0


        for operation in self.list_of_operations:
            self.input_parameter_constraints[operation] = {"parameters": {}, "requestBody": {}}
            parts = ['parameters', 'requestBody']
            for part in parts:
                print(f"[{self.service_name}] progess: {round(completed/progress_size*100, 2)}")
                completed += 1
                
                specification = self.simplified_openapi.get(operation, {}).get(part, {})
                operation_path = operation.split("-")[1]
                operation_name = operation.split("-")[0]
                full_specifications = self.openapi_spec.get("paths", {}).get(operation_path, {}).get(operation_name, {}).get(part, {})
                if not specification:
                    continue
                for parameter in specification:
                    parameter_name = parameter
                    
                    if "(description:" not in specification[parameter]:
                        continue
                    
                    data_type = specification[parameter_name].split("(description: ")[0].strip()
                    
                    description = ""
                    if "(description:" in specification[parameter]:
                        description = specification[parameter].split("(description: ")[-1].split(")")[0].strip()
                    
                    param_spec = {}
                    for spec in full_specifications:
                        if isinstance(spec, str):
                            continue
                        if spec.get("name", "") == parameter_name:
                            param_spec = spec
                            break

                    param_schema = param_spec.get("schema", {})
                    if param_schema:
                        param_schema = json.dumps(param_schema)
                    

                    checking_parameter = [parameter_name, specification[parameter_name]]
                    
                    checked_parameter = self.foundConstraintInputParameter(checking_parameter)
                    if checked_parameter:
                        confirmation_status = checked_parameter[1]
                        if confirmation_status == 'yes':
                            if parameter_name not in self.input_parameter_constraints[operation][part]:
                                self.input_parameter_constraints[operation][part][parameter] = specification[parameter_name]
                        continue
                    
                    description_observation_prompt = DESCRIPTION_OBSERVATION_PROMPT.format(
                        
                        attribute = parameter_name,
                        data_type = data_type,
                        description = description,
                        param_schema = param_schema
                    )
                    print(description_observation_prompt)
                    print(f"Observing operation: {operation} - part: {part} - parameter: {parameter_name}")
                    description_observation_response = GPTChatCompletion(description_observation_prompt,model = "gpt-4-turbo")
                    print(description_observation_response)
                    constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                        attribute = parameter_name,
                        data_type = data_type,
                        description_observation = description_observation_response,
                        description = description,
                        param_schema = param_schema
                    )

                    constraint_confirmation_response = GPTChatCompletion(constraint_confirmation_prompt, model = "gpt-4-turbo")
                    print("---\n", constraint_confirmation_prompt)
                    confirmation = extract_answer(constraint_confirmation_response) # 'yes' or 'no'
                    print (f"Operation: {operation} - part: {part} - parameter: {parameter_name} - Confirmation: {confirmation}")

                    if confirmation == 'yes':             
                        if parameter_name not in self.input_parameter_constraints[operation][part]:
                            self.input_parameter_constraints[operation][part][parameter_name] = specification[parameter_name]
                    
                    self.input_parameters_checked.append([checking_parameter, confirmation])
                
                    # update checked mappings to file
                    if self.save_and_load:
                        os.makedirs(os.path.dirname(self.input_parameters_checked_save_path), exist_ok=True)
                        with open(self.input_parameters_checked_save_path, "w") as file:
                            json.dump(self.input_parameters_checked, file)                    

                    if outfile is not None:
                        with open(outfile, "w") as file:
                            json.dump(self.input_parameter_constraints, file, indent=2)



    def get_inside_response_body_constraints_naive(self, selected_schemas=None, outfile=None):
        print("Inferring constraints inside response body...")
        self.inside_response_body_constraints = {}
        
        # simplified all schemas (including attribute name and its description)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)
        
        # this is use for extracting all schemas specified in response body
        response_body_specified_schemas = []
        operations = extract_operations(self.openapi_spec)
        for operation in operations:
            _,relevant_schemas_in_response = get_relevent_response_schemas_of_operation(self.openapi_spec, operation)
            response_body_specified_schemas.extend(relevant_schemas_in_response)
        response_body_specified_schemas = list(set(response_body_specified_schemas))   
        
        self.found_responsebody_constraints = []
        print(f"Schemas: {response_body_specified_schemas}") 
        if selected_schemas is not None:
            response_body_specified_schemas = selected_schemas
        for schema in response_body_specified_schemas:
            self.inside_response_body_constraints[schema] = {}
            
            attributes = self.simplified_schemas.get(schema, {})
            if not attributes:
                continue
            
            for parameter_name in attributes:
                if "(description:" not in self.simplified_schemas[schema][parameter_name] and "(schema:" not in self.simplified_schemas[schema][parameter_name]:
                    continue
                
                data_type = self.simplified_schemas[schema][parameter_name].split("(")[0].strip()
                
                description = ""
                if "(description:" in self.simplified_schemas[schema][parameter_name]:
                    description = self.simplified_schemas[schema][parameter_name].split("(description: ")[-1].split(")")[0].strip()
                
                if "(schema:" in self.simplified_schemas[schema][parameter_name]:
                    schema_info = self.simplified_schemas[schema][parameter_name].split("(schema: ")[-1].split(")")[0].strip()
                    if description:
                        description += ", " + schema_info
                    else:
                        description = schema_info
                
                if not description:
                    continue
                
                checking_attribute = [parameter_name, self.simplified_schemas[schema][parameter_name]]
                
                checked_attribute = self.foundConstraintResponseBody(checking_attribute)
                if checked_attribute:
                    confirmation_status = checked_attribute[1]
                    if confirmation_status == 'yes':
                        if parameter_name not in self.inside_response_body_constraints[schema]:
                            self.inside_response_body_constraints[schema][parameter_name] = description
                    continue
                
                constraint_confirmation_prompt = NAIVE_CONSTRAINT_DETECTION_PROMPT.format(
                    attribute = parameter_name,
                    data_type = data_type,
                    description = description
                )

                constraint_confirmation_response = GPTChatCompletion(constraint_confirmation_prompt, model = "gpt-4-turbo")
                confirmation = extract_answer(constraint_confirmation_response) # 'yes' or 'no'

                if confirmation == 'yes':
                    if parameter_name not in self.inside_response_body_constraints[schema]:
                        self.inside_response_body_constraints[schema][parameter_name] = description
                print(f"Schema: {schema} - attribute: {parameter_name} - Confirmation: {confirmation}")
                self.found_responsebody_constraints.append([checking_attribute, confirmation])
                
                if outfile is not None:
                    with open(outfile, "w") as file:
                        json.dump(self.inside_response_body_constraints, file, indent=2)


    def get_inside_response_body_constraints(self, selected_schemas=None, outfile=None):
        print("Inferring constraints inside response body...")
        self.inside_response_body_constraints = {}
        
        # simplified all schemas (including attribute name and its description)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)

 
        
        # this is use for extracting all schemas specified in response body
        response_body_specified_schemas = []
        operations = extract_operations(self.openapi_spec)
        for operation in operations:
            _,relevant_schemas_in_response = get_relevent_response_schemas_of_operation(self.openapi_spec, operation)
            response_body_specified_schemas.extend(relevant_schemas_in_response)
        response_body_specified_schemas = list(set(response_body_specified_schemas))   
        
        self.found_responsebody_constraints = []
        print(f"Schemas: {response_body_specified_schemas}") 
        if selected_schemas is not None:
            response_body_specified_schemas = selected_schemas
        for schema in response_body_specified_schemas:
            self.inside_response_body_constraints[schema] = {}
            
            attributes = self.simplified_schemas.get(schema, {})
            print(">>>>>> [code]3", "-----",self.simplified_schemas) 
            if not attributes:
                continue
            
            for parameter_name in attributes:
                print(">>>>>> [code]2",parameter_name,  "-----",self.simplified_schemas[schema]) 
                try:
                    log_filename = f"schema-logs-{self.service_name.lower().replace(' ', '-')}.txt"
                    with open(log_filename, "a", encoding='utf-8') as f:
                        f.write(f"\n{'='*50}\n")
                        f.write(f"Schema Name: {schema}\n")
                        f.write(f"Parameter Name: {parameter_name}\n")
                        f.write(f"Full Schema Content:\n{json.dumps(self.simplified_schemas[schema], indent=2)}\n")
                        f.write(f"{'='*50}\n")
                except Exception as e:
                    print(f"Error writing to log file: {e}")
                
                if "(description:" not in self.simplified_schemas[schema][parameter_name] and "(schema:" not in self.simplified_schemas[schema][parameter_name]:
                    continue
                
                data_type = self.simplified_schemas[schema][parameter_name].split("(")[0].strip()
                
                description = ""
                if "(description:" in self.simplified_schemas[schema][parameter_name]:
                    description = self.simplified_schemas[schema][parameter_name].split("(description: ")[-1].split(")")[0].strip()
                
                if "(schema:" in self.simplified_schemas[schema][parameter_name]:
                    schema_info = self.simplified_schemas[schema][parameter_name].split("(schema: ")[-1].split(")")[0].strip()
                    if description:
                        description += ", " + schema_info
                    else:
                        description = schema_info
                
                if not description:
                    continue
                
                checking_attribute = [parameter_name, self.simplified_schemas[schema][parameter_name]]
                
                checked_attribute = self.foundConstraintResponseBody(checking_attribute)
                if checked_attribute:
                    confirmation_status = checked_attribute[1]
                    if confirmation_status == 'yes':
                        if parameter_name not in self.inside_response_body_constraints[schema]:
                            self.inside_response_body_constraints[schema][parameter_name] = description
                    continue
                
                description_observation_prompt = DESCRIPTION_OBSERVATION_PROMPT.format(
                    attribute = parameter_name,
                    data_type = data_type,
                    description = description,
                    param_schema = ""
                )
                print(f"Observing schema: {schema} - attribute: {parameter_name}")
                description_observation_response = GPTChatCompletion(description_observation_prompt,model = "gpt-4-turbo")
                with open("prompt.txt", "w") as file:
                    file.write(f"PROMPT: {description_observation_prompt}\n")
                    file.write(f"---\n")
                    file.write(f"RESPONSE: {description_observation_response}\n")
            
                constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                    attribute = parameter_name,
                    data_type = data_type,
                    description_observation = description_observation_response,
                    description = description,
                    param_schema = ""
                )

                print(f"Confirming schema: {schema} - attribute: {parameter_name}")
                constraint_confirmation_response = GPTChatCompletion(constraint_confirmation_prompt, model = "gpt-4-turbo")
                confirmation = extract_answer(constraint_confirmation_response) # 'yes' or 'no'
                with open("prompt.txt", "a") as file:
                    file.write(f"PROMPT: {constraint_confirmation_prompt}\n")
                    file.write(f"---\n")
                    file.write(f"RESPONSE: {constraint_confirmation_response}\n")

                if confirmation == 'yes':
                    if parameter_name not in self.inside_response_body_constraints[schema]:
                        self.inside_response_body_constraints[schema][parameter_name] = description
                print(f"Schema: {schema} - attribute: {parameter_name} - Confirmation: {confirmation}")
                self.found_responsebody_constraints.append([checking_attribute, confirmation])
                
                if outfile is not None:
                    with open(outfile, "w") as file:
                        json.dump(self.inside_response_body_constraints, file, indent=2)

def get_simplified_schema(spec: dict):
    simplified_schema_dict = {}
    
    # Xử lý cho Swagger 2.0 (definitions) và OpenAPI 3.0 (components/schemas)
    schemas = {}
    if "components" in spec and "schemas" in spec["components"]:
        schemas = spec["components"]["schemas"]
    elif "definitions" in spec:
        schemas = spec["definitions"]
    
    print(">>>>>> [code]5", "-----",spec)
    print(">>>>>> [code]5", "-----",schemas)    
    
    for schema_name, schema_body in schemas.items():
        # Xử lý schema với get_description=True
        schema_params = get_schema_params(schema_body, spec, get_description=True)
        if schema_params:
            simplified_schema_dict[schema_name] = schema_params
                    
    return simplified_schema_dict

def get_schema_params(body, spec, visited_refs=None, get_description=False, max_depth=None, current_depth=0, ignore_attr_with_schema_ref=False):
    if visited_refs is None:
        visited_refs = set()
    
    if max_depth:
        if current_depth > max_depth:
            return None

    properties = find_object_with_key(body, "properties")
    ref = find_object_with_key(body, "$ref")
    schema = find_object_with_key(body, "schema")

    print(">>>>>> [code]4", "-----",properties,"-----",ref,"-----",schema) 
    
    new_schema = {}
    if properties:
        for p, prop_details in properties["properties"].items():
            p_ref = find_object_with_key(prop_details, "$ref")
            
            if p_ref and ignore_attr_with_schema_ref:
                continue
            
            # Initialize the description string
            description_string = ""
            
            # Check the get_description flag
            if get_description:
                # Lấy description nếu có
                description = ""
                description_parent = find_object_with_key(prop_details, "description")
                if description_parent and not isinstance(description_parent["description"], dict):
                    description = description_parent["description"].strip(' .')
                
                # Kiểm tra các từ khóa đặc biệt
                has_keywords = False
                schema_str = ""

                # Kiểm tra example
                if "example" in prop_details:
                    has_keywords = True
                    schema_str = json.dumps({"type": prop_details.get("type", "string"), "example": prop_details["example"]})
                # Kiểm tra format
                if "format" in prop_details:
                    has_keywords = True
                    schema_str = json.dumps({"type": prop_details.get("type", "string"), "format": prop_details["format"]})
                
                # Kiểm tra enum
                elif "enum" in prop_details:
                    has_keywords = True
                    schema_str = json.dumps({"type": prop_details.get("type", "string"), "enum": prop_details["enum"]})
                
                # Kiểm tra min/max
                elif any(key in prop_details for key in ["minimum", "maximum", "minLength", "maxLength"]):
                    has_keywords = True
                    schema_str = json.dumps({k: v for k, v in prop_details.items() if k in ["type", "minimum", "maximum", "minLength", "maxLength"]})
                
                # Kiểm tra URL/URI
                elif any(key in str(prop_details).lower() for key in ["url", "uri"]):
                    has_keywords = True
                    schema_str = json.dumps({"type": prop_details.get("type", "string"), "format": "uri"})
                
                # Tạo description string
                if has_keywords:
                    if description:
                        description_string = f" (description: {description}, schema: {schema_str})"
                    else:
                        description_string = f" (schema: {schema_str})"
                elif description:
                    description_string = f" (description: {description})"
            
            if "type" in prop_details:
                if prop_details["type"] == "array":
                    if p_ref:
                        new_schema[p] = {}
                        ref_name = p_ref["$ref"]
                        if isinstance(ref_name, str):
                            ref_name = ref_name.split("/")[-1]
                        new_schema[p][f'array of \'{ref_name}\' objects'] = [get_schema_params(prop_details, spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)]
                    else:
                        new_schema[p] = "array" + description_string
                else:
                    new_schema[p] = prop_details["type"] + description_string
                    
            elif p_ref:
                if p_ref["$ref"] in visited_refs:
                    ref_name = p_ref["$ref"]
                    if isinstance(ref_name, str):
                        ref_name = ref_name.split("/")[-1]
                    new_schema[p] = {f'schema of {ref_name}': {}}
                    continue
                
                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_params(schema, spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)
                if child_schema is not None:
                    new_schema[p] = {}
                    ref_name = p_ref["$ref"]
                    if isinstance(ref_name, str):
                        ref_name = ref_name.split("/")[-1]
                    new_schema[p][f'schema of {ref_name}'] = child_schema
                    
    elif ref:
        if ref["$ref"] in visited_refs:
            return None
        
        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_params(schema, spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)
    elif schema:
        return get_schema_params(schema['schema'], spec, visited_refs=visited_refs, get_description=get_description, max_depth=max_depth, current_depth=current_depth+1)
    else:
        field_value = ""
        if body is not None and "type" in body:
            field_value = body["type"]
        
        if field_value != "":
            return field_value
        else:
            return None
    
    return new_schema

def contains_schema_keywords(schema):
    keywords = ['date', 'max', 'min', 'time', 'enum', 'url', 'uri', 'format',"example"]
    schema_str = json.dumps(schema).lower()
    print(f"\nChecking schema for keywords: {schema_str}")
    result = any(keyword in schema_str for keyword in keywords)
    print(f"Contains keywords: {result}")
    return result

def main():
    pass

if __name__ == "__main__":
    main()