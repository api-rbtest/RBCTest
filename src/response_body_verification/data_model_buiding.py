import json
from utils.openapi_utils import *
from utils.gptcall import GPTChatCompletion

FIND_SCHEMA_KEYS = '''Given a schema in an OpenAPI specification file, your responsibility is to identify one or some attributes in the schema that play the role of identifying the specific object (primary keys):

Below is the schema specification:
{schema_specification}

If the given schema does not reflect an object, you only need to respond with "None"; otherwise, respond with the primary keys you identified, separated by commas. No explanation is needed.'''

DATA_MODEL_PROMPT = r'''Given two schemas specified in an OpenAPI Specification file, your responsibility is to find all pairs of two fields that have the same meaning.

Below are the two schemas needed to find pairs:
Schema 1: {schema_1}
Schema 2: {schema_2}

Rules:
1. The two fields in a pair must be of the same data type.
2. The two fields in a pair must share the same meaning; their values should represent the id of the same object or maintain an attribute value of the same object,...
3. A field in one schema only pairs with at most one field in another schema, and vice versa.

Please follow these rules in your response:
1. If there exist pairs of two fields that share the same meaning:
Follow the format below to indicate them:
<field at Schema 1> -> <field at Schema 2>
...
2. If there are no pairs of two fields with the same meaning found between the two schemas, you only need to respond with "None".'''

def extract_data_model_information(gpt_response):
    pattern = r'(\w+) -> (\w+)'
    matches = re.findall(pattern, gpt_response)

    key_pairs = [(match[0], match[1]) for match in matches if match[0] != 'None' and match[1] != 'None']

    return key_pairs

class DataModelBuilder:
    def __init__(self, openapi_path, ks_project_path):
        self.openapi_path = openapi_path
        self.ks_project_path = ks_project_path
        self.openapi_spec = load_openapi(openapi_path)
        self.simplified_openapi = get_operation_params(self.openapi_spec, get_description=True, get_response_body=False)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)
        self.initialize()
        self.filter_attributes()
        self.building_data_model()
    
    def initialize(self):
        self.service_name = self.openapi_spec['info']['title']
        self.odg_output_dir = f"{self.ks_project_path}/KAT Plugin/{self.service_name}/operation_sequences.json"
        self.operation_sequences = json.load(open(self.odg_output_dir, "r"))
        
    def filter_attributes(self):
        for schema in self.simplified_schemas:
            filter_out_attrs = []
            for attr, value in self.simplified_schemas[schema].items():
                if not any(data_type in value for data_type in ["integer", "string"]):
                    filter_out_attrs.append(attr)
            for _attr in filter_out_attrs:
                self.simplified_schemas[schema].pop(_attr)
    
    def building_data_model(self):
        self.data_model = {"schema_keys": {}, "schema_model": [[],[]]} 
        schemas = []
        for operation in self.simplified_openapi:
            _, relevant_response_schemas = get_relevant_schemas_of_operation(operation, self.openapi_spec)
            schemas.extend(relevant_response_schemas)
            
            sequences = self.operation_sequences.get(operation, [])
            for sequence in sequences:
                for child_operation in sequence:
                    _, child_operation_relevant_response_schemas = get_relevant_schemas_of_operation(child_operation, self.openapi_spec)
                    relevant_response_schemas.extend(child_operation_relevant_response_schemas)
            
            relevant_response_schemas = list(set(relevant_response_schemas))
            
            for i in range(len(relevant_response_schemas)):
                for j in range(i+1, len(relevant_response_schemas)):
                    if not self.simplified_schemas[relevant_response_schemas[i]] or not self.simplified_schemas[relevant_response_schemas[j]]:
                        continue
                    if (relevant_response_schemas[i], relevant_response_schemas[j]) not in self.data_model['schema_model'][0] and (relevant_response_schemas[j], relevant_response_schemas[i]) not in self.data_model['schema_model'][0]:
                        self.data_model['schema_model'][0].append((relevant_response_schemas[i], relevant_response_schemas[j]))
                        self.data_model['schema_model'][1].append([])
                        
                        schema_1 = f"{relevant_response_schemas[i]}\n{self.simplified_schemas[relevant_response_schemas[i]]}"
                        schema_2 = f"{relevant_response_schemas[j]}\n{self.simplified_schemas[relevant_response_schemas[j]]}"
                        data_model_prompt = DATA_MODEL_PROMPT.format(schema_1=schema_1, schema_2=schema_2)
                        
                        data_model_response = GPTChatCompletion(data_model_prompt, system="", temperature=0.0)
                        if data_model_response:
                            key_pairs = extract_data_model_information(data_model_response)
                            self.data_model['schema_model'][1][-1].extend(key_pairs)
        
        schemas = list(set(schemas))
        
        for schema in schemas:
            prompt = FIND_SCHEMA_KEYS.format(schema_specification = json.dumps(self.simplified_schemas[schema]))
            response = GPTChatCompletion(prompt, system="")
            
            # print(f"Prompt:\n{prompt}")
            # print("_"*20)
            # print(f"Response:\n{response}")
            # print("_"*20)
            
            if response:
                keys = [key.strip() for key in response.split(',')]
                keys = [key for key in keys if key in self.simplified_schemas[schema]]
                self.data_model["schema_keys"][schema] = keys
                        
def main():
    dataModelBuilder = DataModelBuilder("response-verification/openapi/Petstore.json")
    with open(f"experiment/{dataModelBuilder.service_name}_data_model.json", "w") as file:
        json.dump(dataModelBuilder.data_model, file, indent=2)
    
if __name__ == "__main__":
    main()