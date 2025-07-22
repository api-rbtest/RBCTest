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
    def __init__(self, openapi_path, service_name, except_attributes_found_constraints_inside_response_body=False,
                 save_and_load=False, list_of_available_schemas=None,
                 outfile=None, experiment_folder="experiment_our", is_naive=False):
        self.openapi_spec = load_openapi(openapi_path)
        self.service_name = service_name
        self.except_attributes_found_constraints = except_attributes_found_constraints_inside_response_body
        self.save_and_load = save_and_load
        self.list_of_available_schemas = list_of_available_schemas
        self.outfile = outfile
        self.experiment_folder = experiment_folder
        self.response_body_input_parameter_mappings = {}
        print("TT")

        self.initialize()
        print("TT")
        self.filter_params_w_descr()
        if is_naive:
            self.mapping_response_bodies_to_input_parameters_naive()
        else:
            self.mapping_response_bodies_to_input_parameters()

    def initialize(self):
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)
        self.simplified_openapi = simplify_openapi(self.openapi_spec)

        self.input_parameter_constraints = json.load(open(
            f"{self.experiment_folder}/{self.service_name}/input_parameter.json", "r"))

        if self.except_attributes_found_constraints:
            self.inside_response_body_constraints = json.load(open(
                f"{self.experiment_folder}/{self.service_name}/response_property_constraints.json", "r"))

        self.found_mappings = []
        if self.save_and_load:
            self.save_path = f"{self.experiment_folder}/{self.service_name}/found_maping.txt"
            if os.path.exists(self.save_path):
                self.found_mappings = json.load(open(self.save_path, "r"))

        self.list_of_schemas = list(self.simplified_schemas.keys())
        if self.list_of_available_schemas:
            self.list_of_schemas = self.list_of_available_schemas

    def filter_params_w_descr(self):
        self.operations_containing_param_w_description = {}
        self.operation_param_w_descr = simplify_openapi(self.openapi_spec)

        for operation in self.operation_param_w_descr:
            self.operations_containing_param_w_description[operation] = {}
            if "summary" in self.operation_param_w_descr[operation]:
                self.operations_containing_param_w_description[operation][
                    "summary"] = self.operation_param_w_descr[operation]["summary"]

            for part in ["parameters", "requestBody"]:
                if self.operation_param_w_descr.get(operation, {}).get(part):
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
        return {
            key: value for key, value in self.simplified_schemas[schema].items()
            if key not in self.inside_response_body_constraints.get(schema, {})
        }

    def mapping_response_bodies_to_input_parameters(self):
        print("Mapping response bodies to input parameters...")
        print(self.operation_param_w_descr)

        for operation in self.operation_param_w_descr:
            for part in ["parameters", "requestBody"]:
                print("WTF")
                if part not in self.operation_param_w_descr[operation]:
                    continue
                for parameter_name, value in self.operation_param_w_descr[operation][part].items():
                    if "(description:" not in value:
                        continue
                    data_type = value.split("(description: ")[0].strip()
                    description = value.split(
                        "(description: ")[-1][:-1].strip()

                    # Tìm schema tương ứng với operation
                    _, relevant_schemas = get_relevent_response_schemas_of_operation(
                        self.openapi_spec, operation)
                    print(relevant_schemas)
                    for schema in relevant_schemas:
                        if schema not in self.response_body_input_parameter_mappings:
                            self.response_body_input_parameter_mappings[schema] = {
                            }

                        # Tạo mapping giữa parameter và schema
                        mapping = [operation, part, parameter_name]
                        if parameter_name not in self.response_body_input_parameter_mappings[schema]:
                            self.response_body_input_parameter_mappings[schema][parameter_name] = [
                            ]
                        if mapping not in self.response_body_input_parameter_mappings[schema][parameter_name]:
                            self.response_body_input_parameter_mappings[schema][parameter_name].append(
                                mapping)

        # Lưu kết quả vào file
        if self.outfile:
            with open(self.outfile, "w") as f:
                json.dump(
                    self.response_body_input_parameter_mappings, f, indent=2)

    # Các phương thức mapping_response_bodies_to_input_parameters và naive sẽ được thêm theo yêu cầu
