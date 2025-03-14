import re
from utils.openapi_utils import *
from utils.gptcall import GPTChatCompletion

PARAMETER_OBSERVATION = '''Given the specification of an input parameter for a REST API, your responsibility is to provide a brief observation of that parameter.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"
'''

SCHEMA_OBSERVATION = '''\
Given a schema in an OpenAPI Specification for a RESTful API service, your responsibility is to briefly explain the meaning of each attribute specified in the provided schema.

Below is the schema's specification:
- Schema name: "{schema}"
- Specification: {specification}
'''

PARAMETER_SCHEMA_MAPPING_PROMPT = '''Given an input parameter and an API response schema, your responsibility is to check whether there is a corresponding attribute in the API response schema.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"

Follow these step to find the coresponding attribute of the input parameter:
STEP 1: Let's give a brief observation about the input parameter.

{parameter_observation}

STEP 2: Identify the corresponding attribute in the API response's schema.

Some cases can help determine a corresponding attribute:
- The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
- The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.

Below is the specification of the schema "{schema}":
{schema_observation}

If there is a corresponding attribute in the response schema, let's explain the identified attribute. Follow the format of triple backticks below:
```explanation
explain...
```

Let's give your confirmation: Does the input parameter have any corresponding attribute in the response schema? Follow the format of triple backticks below:
```answer
just respond: yes/no (without any explanation)
```

Let's identify all corresponding attributes name of the provided input parameter in {attributes}. Format of triple backticks below:
```corresponding attribute
just respond corresponding attribute's name here (without any explanation)
```
'''

NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT = '''Given an input parameter and an API response schema, your responsibility is to check whether there is a corresponding attribute in the API response schema.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"

Follow these step to find the coresponding attribute of the input parameter:


Identify the corresponding attribute in the API response's schema.

Some cases can help determine a corresponding attribute:
- The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
- The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.

Below is the specification of the schema "{schema}":
{schema_specification}

If there is a corresponding attribute in the response schema, let's explain the identified attribute. Follow the format of triple backticks below:
```explanation
explain...
```

Let's give your confirmation: Does the input parameter have any corresponding attribute in the response schema? Follow the format of triple backticks below:
```answer
just respond: yes/no (without any explanation)
```

Let's identify all corresponding attributes name of the provided input parameter in {attributes}. Format of triple backticks below:
```corresponding attribute
just respond corresponding attribute's name here (without any explanation)
```
'''


MAPPING_CONFIRMATION = '''Given an input parameter of a REST API and an identified equivalent attribute in an API response schema, your responsibility is to check that the mapping is correct.

The input parameter's information:
- Operation: {method} {endpoint}
- Parameter: "{parameter_name}"
- Description: "{description}"

The corresponding attribute's information:
- Resource: {schema}
- Corresponding attribute: "{corresponding_attribute}"

STEP 1, determine the equivalence of resources based on the operation, the description of the input parameter. Explain about the resource of the input parameter, follow the format of triple backticks below:
```explanation
your explanation...
```

STEP 2, based on your explanation about the provided input parameter's resource, help to check the mapping of the input parameter as "{parameter_name}" with the equivalent attribute as "{corresponding_attribute}" specified in the {schema} resource.

Note that: The mapping is correct if their values are related to a specific attribute of a resource or their semantics are equivalent.

The last response should follow the format of triple backticks below:
```answer
just respond: correct/incorrect
```
'''


def extract_answer(response):
    if response is None:
        return ""

    if "```answer" in response:
        pattern = r'```answer\n(.*?)```'
        match = re.search(pattern, response, re.DOTALL)

        if match:
            answer = match.group(1)
            return answer.strip().lower()
        else:
            return ""
    else:
        return response.strip()


def extract_coresponding_attribute(response):
    if response is None:
        return ""

    pattern = r'```corresponding attribute\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)

    if match:
        answer = match.group(1)
        return answer.strip().replace('"', '').replace('\'', "")
    else:
        return ""


def standardize_string(string):
    return string.strip().replace('"', "")


def get_data_type(attr_simplified_spec):
    return attr_simplified_spec.split("(description:")[0].strip()


def filter_attributes_in_schema_by_data_type(schema_spec, filterring_data_type):
    specification = copy.deepcopy(schema_spec)
    if isinstance(specification, str):
        data_type = specification.split("(description:")[0].strip()
        if data_type != filterring_data_type:
            return {}
        return specification
    if not specification:
        return {}
    for attribute, value in schema_spec.items():
        # if not isinstance(value, str):
        #     del specification[attribute]
        #     continue
        if isinstance(value, dict):
            value = filter_attributes_in_schema_by_data_type(
                value, filterring_data_type)
            if not value:
                del specification[attribute]
                continue
            specification[attribute] = value
        elif isinstance(value, list):
            value = filter_attributes_in_schema_by_data_type(
                value[0], filterring_data_type)
            if not value:
                del specification[attribute]
                continue
            specification[attribute] = [value]
        if isinstance(value, str):
            data_type = value.split("(description:")[0].strip()
            if data_type != filterring_data_type:
                del specification[attribute]
    return specification

def verify_attribute_in_schema(schema_spec, attribute):
    for key, value in schema_spec.items():
        if key == attribute:
            return True
        if isinstance(value, dict):
            if verify_attribute_in_schema(value, attribute):
                return True
        if isinstance(value, list):
            if verify_attribute_in_schema(value[0], attribute):
                return True
    return False

def find_common_fields(json1, json2):
    common_fields = []
    for key in json1.keys():
        if key in json2.keys():
            common_fields.append(key)
    return common_fields


class ParameterResponseMapper:
    def __init__(self, openapi_path, except_attributes_found_constraints_inside_response_body=False, 
                 save_and_load=False, list_of_available_schemas=None, 
                 outfile=None, experiment_folder="experiment_our", is_naive=False):
        self.openapi_spec = load_openapi(openapi_path)
        self.except_attributes_found_constraints = except_attributes_found_constraints_inside_response_body
        self.save_and_load = save_and_load
        self.list_of_available_schemas = list_of_available_schemas
        self.outfile = outfile
        self.experiment_folder = experiment_folder
        self.initialize()
        self.filter_params_w_descr()
        if is_naive:
            self.mapping_response_bodies_to_input_parameters_naive()
        else:
            self.mapping_response_bodies_to_input_parameters()

    def initialize(self):
        self.service_name = self.openapi_spec['info']['title']
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)
        self.simplified_openapi = simplify_openapi(self.openapi_spec)

        self.input_parameter_constraints = json.load(open(
            f"{self.experiment_folder}/{self.service_name}/input_parameter.json", "r"))
        # input(f"Input parameter constraints: {self.input_parameter_constraints}")

        if self.except_attributes_found_constraints:
            self.inside_response_body_constraints = json.load(open(
                f"{self.experiment_folder}/{self.service_name}/response_property_constraints.json", "r"))

        self.found_mappings = []
        if self.save_and_load:
            self.save_path = f"{
                self.experiment_folder}/{self.service_name}/found_maping.txt"
            if os.path.exists(self.save_path):
                self.found_mappings = json.load(open(self.save_path, "r"))

        self.list_of_schemas = list(self.simplified_schemas.keys())
        if self.list_of_available_schemas:
            self.list_of_schemas = self.list_of_available_schemas

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

        for operation in self.operation_param_w_descr:
            self.operations_containing_param_w_description[operation] = {}
            if "summary" in self.operation_param_w_descr[operation]:
                self.operations_containing_param_w_description[operation][
                    "summary"] = self.operation_param_w_descr[operation]["summary"]

            parts = ["parameters", "requestBody"]
            for part in parts:
                if self.operation_param_w_descr.get(operation, {}).get(part, None) is not None:
                    self.operations_containing_param_w_description[operation][part] = {
                    }
                    if isinstance(self.operation_param_w_descr[operation][part], dict):
                        for param, value in self.operation_param_w_descr[operation][part].items():
                            if "(description:" in value:
                                self.operations_containing_param_w_description[operation][part][param] = value

    def foundMapping(self, input_parameter, description, schema):
        for mapping in self.found_mappings:
            if mapping[0] == input_parameter and mapping[1] == description and mapping[2] == schema:
                return mapping
        return None

    def exclude_attributes_found_constraint(self, schema):
        return {key: value for key, value in self.simplified_schemas[schema].items() if key not in self.inside_response_body_constraints.get(schema, {})}

    def mapping_response_bodies_to_input_parameters(self):
        print(f"\nMapping input parameters to response schemas...")
        self.response_body_input_parameter_mappings = {}

        progress_size = 2 * \
            len(self.input_parameter_constraints)*len(self.list_of_schemas)
        completed = 0
        # input(f"List of schemas: {self.input_parameter_constraints}")
        for operation in self.input_parameter_constraints:
            operation_method, operation_path  = operation.split('-', 1)
            full_operation_spec = self.openapi_spec.get("paths", {}).get(
                operation_path, {}).get(operation_method, {})
            # print(f"Operation path: {operation_path}, Operation method: {operation_method}")
            # input(f"{self.openapi_spec.get("paths", {}).keys()}")
            if not full_operation_spec:
                continue

            main_repsonse_schemas, _ = get_relevant_schemas_of_operation(
                operation, self.openapi_spec)
            print(f"Operation: {operation}, Main response schemas: {
                  main_repsonse_schemas}")

            for schema in main_repsonse_schemas:
                for part in ['parameters', 'requestBody']:
                    try:
                        print(f"[{self.service_name}] progress: {
                              round(completed/progress_size*100, 2)}")
                        completed += 1

                        specification = self.input_parameter_constraints.get(
                            operation, {}).get(part, {})
                        if not specification:
                            continue

                        if schema not in self.simplified_schemas:
                            continue

                        schema_spec = self.simplified_schemas[schema]

                        for param in specification:
                            print(f"Mapping {param} from {
                                  operation} to {schema}")
                            description = specification[param].split(
                                '(description:')[-1][:-1].strip()

                            found_mapping = self.foundMapping(
                                param, description, schema)

                            if found_mapping:
                                found_corresponding_attribute = found_mapping[3]
                                if found_corresponding_attribute is None:
                                    continue
                                if schema not in self.response_body_input_parameter_mappings:
                                    self.response_body_input_parameter_mappings[schema] = {
                                        found_corresponding_attribute: [[operation, part, param]]}
                                elif found_corresponding_attribute not in self.response_body_input_parameter_mappings[schema]:
                                    self.response_body_input_parameter_mappings[schema][found_corresponding_attribute] = [
                                        [operation, part, param]]
                                else:
                                    self.response_body_input_parameter_mappings[schema][found_corresponding_attribute].append([
                                                                                                                              operation, part, param])
                                continue

                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(self.found_mappings, file)

                            mapping = [param, description, schema, None]

                            filterring_data_type = get_data_type(
                                specification[param])
                            filterred_attr_schema = filter_attributes_in_schema_by_data_type(
                                schema_spec, filterring_data_type)
                            if not filterred_attr_schema:
                                self.found_mappings.append(mapping)
                                continue

                            method = operation.split('-')[0]
                            endpoint = '-'.join(operation.split('-')[1:])
                            print(f"Mapping {param} to {json.dumps(
                                filterred_attr_schema)} in {schema}")

                            parameter_observation_prompt = PARAMETER_OBSERVATION.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                attribute=param,
                                description=description
                            )

                            parameter_observation_response = GPTChatCompletion(
                                parameter_observation_prompt, model="gpt-4-turbo")

                            schema_observation_prompt = SCHEMA_OBSERVATION.format(
                                schema=schema,
                                specification=json.dumps(filterred_attr_schema)
                            )

                            schema_observation_response = GPTChatCompletion(
                                schema_observation_prompt, model="gpt-4-turbo")

                            mapping_attribute_to_schema_prompt = PARAMETER_SCHEMA_MAPPING_PROMPT.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                attribute=param,
                                description=description,
                                parameter_observation=parameter_observation_response,
                                schema=schema,
                                schema_observation=schema_observation_response,
                                attributes=[
                                    attr for attr in filterred_attr_schema]
                            )

                            mapping_attribute_to_schema_response = GPTChatCompletion(
                                mapping_attribute_to_schema_prompt, model="gpt-4-turbo")

                            print("GPT: ", mapping_attribute_to_schema_response)

                            answer = extract_answer(
                                mapping_attribute_to_schema_response)
                            if not 'yes' in answer:
                                self.found_mappings.append(mapping)
                                continue

                            corresponding_attribute = extract_coresponding_attribute(
                                mapping_attribute_to_schema_response)

                            if not verify_attribute_in_schema(filterred_attr_schema, corresponding_attribute):
                                self.found_mappings.append(mapping)
                                continue

                            mapping_confirmation_prompt = MAPPING_CONFIRMATION.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                parameter_name=param,
                                description=description,
                                schema=schema,
                                corresponding_attribute=corresponding_attribute
                            )

                            mapping_confirmation_response = GPTChatCompletion(
                                mapping_confirmation_prompt, model="gpt-4-turbo")
                            mapping_status = extract_answer(
                                mapping_confirmation_response)

                            if "incorrect" in mapping_status:
                                print(f"[INCORRECT] {method.upper()} {endpoint} {
                                      param} --- {schema} {corresponding_attribute}")
                                self.found_mappings.append(mapping)
                                continue

                            print(f"[CORRECT] {method.upper()} {endpoint} {
                                  param} --- {schema} {corresponding_attribute}")

                            if schema not in self.response_body_input_parameter_mappings:
                                self.response_body_input_parameter_mappings[schema] = {
                                    corresponding_attribute: [[operation, part, param]]}
                            elif corresponding_attribute not in self.response_body_input_parameter_mappings[schema]:
                                self.response_body_input_parameter_mappings[schema][corresponding_attribute] = [
                                    [operation, part, param]]
                            else:
                                self.response_body_input_parameter_mappings[schema][corresponding_attribute].append([
                                                                                                                    operation, part, param])

                            mapping = [param, description,
                                       schema, corresponding_attribute]
                            self.found_mappings.append(mapping)

                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(self.found_mappings, file)

                            if self.outfile:
                                with open(self.outfile, "w") as f:
                                    json.dump(self.response_body_input_parameter_mappings, f, indent=2)
                    except Exception as e:
                        print(f"Error: {e}")
                        continue

    def mapping_response_bodies_to_input_parameters_naive(self):
        print(f"\nNAIVE Mapping input parameters to response schemas...")
        self.response_body_input_parameter_mappings = {}

        progress_size = 2 * \
            len(self.input_parameter_constraints)*len(self.list_of_schemas)
        completed = 0

        for operation in self.input_parameter_constraints:
            operation_path = operation.split('-')[1]
            operation_method = operation.split('-')[0]
            full_operation_spec = self.openapi_spec.get("paths", {}).get(
                operation_path, {}).get(operation_method, {})
            if not full_operation_spec:
                continue

            main_repsonse_schemas, _ = get_relevant_schemas_of_operation(
                operation, self.openapi_spec)
            print(f"Operation: {operation}, Main response schemas: {
                  main_repsonse_schemas}")

            for schema in main_repsonse_schemas:
                for part in ['parameters', 'requestBody']:
                    try:
                        print(f"[{self.service_name}] progress: {
                              round(completed/progress_size*100, 2)}")
                        completed += 1

                        specification = self.input_parameter_constraints.get(
                            operation, {}).get(part, {})
                        if not specification:
                            continue

                        if schema not in self.simplified_schemas:
                            continue

                        schema_spec = self.simplified_schemas[schema]

                        for param in specification:
                            print(f"Mapping {param} from {
                                  operation} to {schema}")
                            description = specification[param].split(
                                '(description:')[-1][:-1].strip()

                            found_mapping = self.foundMapping(
                                param, description, schema)

                            if found_mapping:
                                found_corresponding_attribute = found_mapping[3]
                                if found_corresponding_attribute is None:
                                    continue
                                if schema not in self.response_body_input_parameter_mappings:
                                    self.response_body_input_parameter_mappings[schema] = {
                                        found_corresponding_attribute: [[operation, part, param]]}
                                elif found_corresponding_attribute not in self.response_body_input_parameter_mappings[schema]:
                                    self.response_body_input_parameter_mappings[schema][found_corresponding_attribute] = [
                                        [operation, part, param]]
                                else:
                                    self.response_body_input_parameter_mappings[schema][found_corresponding_attribute].append([
                                                                                                                              operation, part, param])
                                continue

                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(self.found_mappings, file)

                            mapping = [param, description, schema, None]

                            filterring_data_type = get_data_type(
                                specification[param])
                            filterred_attr_schema = filter_attributes_in_schema_by_data_type(
                                schema_spec, filterring_data_type)
                            if not filterred_attr_schema:
                                self.found_mappings.append(mapping)
                                continue

                            method = operation.split('-')[0]
                            endpoint = '-'.join(operation.split('-')[1:])
                            print(f"Mapping {param} to {json.dumps(
                                filterred_attr_schema)} in {schema}")

                            mapping_attribute_to_schema_prompt = NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                attribute=param,
                                description=description,
                                schema_specification=json.dumps(
                                    filterred_attr_schema),
                                schema=schema,
                                attributes=[
                                    attr for attr in filterred_attr_schema]
                            )

                            mapping_attribute_to_schema_response = GPTChatCompletion(
                                mapping_attribute_to_schema_prompt, model="gpt-4-turbo")

                            print("GPT: ", mapping_attribute_to_schema_response)

                            answer = extract_answer(
                                mapping_attribute_to_schema_response)
                            if not 'yes' in answer:
                                self.found_mappings.append(mapping)
                                continue

                            corresponding_attribute = extract_coresponding_attribute(
                                mapping_attribute_to_schema_response)

                            if schema not in self.response_body_input_parameter_mappings:
                                self.response_body_input_parameter_mappings[schema] = {
                                    corresponding_attribute: [[operation, part, param]]}
                            elif corresponding_attribute not in self.response_body_input_parameter_mappings[schema]:
                                self.response_body_input_parameter_mappings[schema][corresponding_attribute] = [
                                    [operation, part, param]]
                            else:
                                self.response_body_input_parameter_mappings[schema][corresponding_attribute].append([
                                                                                                                    operation, part, param])

                            mapping = [param, description,
                                       schema, corresponding_attribute]
                            self.found_mappings.append(mapping)

                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(self.found_mappings, file)
                    except Exception as e:
                        print(f"Error: {e}")
                        continue
