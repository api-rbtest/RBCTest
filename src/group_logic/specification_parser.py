import json

import os
from pathlib import Path
from prance import ResolvingParser
import json
from typing import List, Dict, Optional, Union, Iterable


from typing import List, Dict, Optional, Union, Iterable
from dataclasses import dataclass, field, asdict


def isEmpty(value):
    return value == '-' or value is None or value == [] or value == ['-'] or value == ''


def isSuccessful(code) -> bool:
    if isinstance(code, str):
        return code[0] == '2'
    return code >= 200 and code < 300


def isInformational(code: int):
    return code >= 100 and code < 200


def isRedirection(code: int):
    return code >= 300 and code < 400


def isClientError(code: int):
    return code >= 400 and code < 500


def isServerError(code: int):
    return code >= 500 and code < 600



def flatten_json_schema(schema, parent_key='', sep='.'):
    flat_schema = {}
    if 'properties' in schema:
        for key, value in schema['properties'].items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if not value:
                continue
            if value.get('type') == 'object' and 'properties' in value:
                # Recursively flatten nested object
                flat_schema.update(
                    flatten_json_schema(value, new_key, sep=sep))

            elif value.get('type') == 'array':
                items = value.get('items', {})
                array_key = f"{new_key}[]"

                if items.get('type') == 'object' and 'properties' in items:
                    # Flatten object inside array
                    flat_schema.update(flatten_json_schema(
                        items, array_key, sep=sep))
                else:
                    # Array of primitives
                    flat_schema[array_key] = items
            else:
                # Primitive field
                flat_schema[new_key] = value

    return flat_schema


def to_dict_helper(item):
    """
    Helper method for parsing in to a dictionary. Handles the case where the item is a dictionary, list, or object with
    a to_dict method.
    """
    if hasattr(item, 'to_dict'):
        return item.to_dict()
    elif isinstance(item, dict):
        return {k: to_dict_helper(v) for k, v in item.items()}
    elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        return [to_dict_helper(i) for i in item]
    else:
        return item

def remove_nulls(item):
    if hasattr(item, 'to_dict'):
        return item.to_dict()
    elif isinstance(item, dict):
        return {k: remove_nulls(v) for k, v in item.items() if not isEmpty(v) and remove_nulls(v)}
    elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        return [remove_nulls(i) for i in item if remove_nulls(i) is not None]
    else:
        return item
#  HTTP Status Code


@dataclass
class ItemProperties:
    """
    Class to store the properties of either the schema values, in the case of parameters, or the request body object values
    """
    type: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None
    items: 'ItemProperties' = None
    properties: Dict[str, 'ItemProperties'] = None
    required: List[str] = field(default_factory=list)
    default: Optional[Union[str, int, float, bool, List, Dict]] = None
    enum: Optional[List[str]] = field(default_factory=list)
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    max_items: Optional[int] = None
    min_items: Optional[int] = None
    unique_items: Optional[bool] = None
    additional_properties: Union[bool, 'ItemProperties', None] = None
    nullable: Optional[bool] = None
    read_only: Optional[bool] = None
    write_only: Optional[bool] = None
    example: Optional[Union[str, int, float, bool, List, Dict]] = None
    examples: List[Optional[Union[str, int, float, bool, List, Dict]]] = field(
        default_factory=list)
    xrefs: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        it = cls(**data)
        if data.get("items"):
            it.items = ItemProperties.from_dict(data.get("items"))
        return it

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result


@dataclass
class ParameterProperties:
    """
    Class to store the properties of a parameter. Parameters have nested schemas, whereas request bodies do not.
    """
    name: str = ''
    in_value: Optional[str] = None
    description: Optional[str] = None
    required: Optional[bool] = None
    deprecated: Optional[bool] = None
    allow_empty_value: Optional[bool] = None
    style: Optional[str] = None
    explode: Optional[bool] = None
    allow_reserved: Optional[bool] = None
    schema: ItemProperties = None
    example: Optional[Union[str, int, float, bool, List, Dict]] = None
    examples: List[Optional[Union[str, int, float, bool, List, Dict]]] = field(
        default_factory=list)

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    @classmethod
    def from_dict(cls, data: dict):
        it = cls(**data)
        if data.get("schema"):
            it.schema = ItemProperties.from_dict(data.get("schema"))
        return it


@dataclass
class ResponseProperties:
    """
    Class to store the properties of a response
    """
    status_code: int = -1
    description: Optional[str] = None
    # MIME type as first key, then schema content as result
    content: Dict[str, 'ItemProperties'] = field(default_factory=dict)

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    @classmethod
    def from_dict(cls, data: dict):
        it = cls(**data)
        if data.get("content"):
            for contentType in data.get("content").keys():
                it.content[contentType] = ItemProperties.from_dict(
                    data.get("content").get(contentType))
        return it


@dataclass
class OperationProperties:
    """
    Class to store the properties of an operation, considering both its parameters and potential request body.
    """
    uuid: str = '',
    operation_id: str = ''
    endpoint_path: str = ''
    http_method: str = ''
    parameters: Dict[str, ParameterProperties] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    description: Optional[str] = None
    external_docs: Optional[str] = None
    # MIME type as first key, then each parameter with its properties as second dict
    request_body: Dict[str, ItemProperties] = None
    # status code as first key, then each response with its properties as second dict
    responses: Dict[str, ResponseProperties] = None
    # available contentType for operation
    # contentType: List[str] = ["application/json"]

    @classmethod
    def from_dict(cls, data: dict):
        ints = cls(**data)
        if data.get("parameters"):
            for params in data.get("parameters").keys():
                ints.parameters[params] = ParameterProperties.from_dict(
                    data.get("parameters", {}).get(params))
        if data.get("request_body"):
            for contentType in data.get("request_body").keys():
                ints.request_body[contentType] = ItemProperties.from_dict(
                    data.get("request_body", {}).get(contentType))
        if data.get("responses"):
            for statusCode in data.get("responses").keys():
                ints.responses[statusCode] = ResponseProperties.from_dict(
                    data.get("responses", {}).get(statusCode))
        return ints

    def to_dict(self):
        result = {
            k: to_dict_helper(v)
            for k, v in self.__dict__.items() if not isEmpty(v)
        }
        return result

    # def get_parameters(self, required=False):
    #     if len(self.parameters) == 0:
    #         return []
    #     if required:
    #         return remove_nulls([{
    #             "name": parameter,
    #             "type": parameter_details.schema.type,
    #             "description": parameter_details.description,
    #             "enum": parameter_details.schema.enum,
    #             "xrefs": parameter_details.schema.xrefs
    #         } for parameter, parameter_details in self.parameters.items() if parameter_details.required == True])
    #     return remove_nulls([{
    #         "name": parameter,
    #         "type": parameter_details.schema.type,
    #         "description": parameter_details.description,
    #         "enum": parameter_details.schema.enum,
    #         "xrefs": parameter_details.schema.xrefs
    #     } for parameter, parameter_details in self.parameters.items()])

    def get_parameters(self, required=False):
        if not self.parameters:
            return []
        return remove_nulls([{
            "name": name,
            "type": details.schema.type,
            "description": details.description,
            "enum": details.schema.enum,
            "xrefs": details.schema.xrefs
        } for name, details in self.parameters.items()
            if not required or details.required])

    def get_responses(self):
        if self.responses is None:
            return []
        response_list = {}
        for status_code, response_properties in self.responses.items():
            if status_code and isSuccessful(status_code) and response_properties.content:
                for response, response_details in response_properties.content.items():
                    curr_responses = flatten_json_schema(
                        to_dict_helper(response_details))
                    response_list.update(curr_responses)
        return remove_nulls([{
            "name": item,
            "type": val.get("type"),
            "description": val.get("description", ""),
            "enum": val.get("enum"),
            "xrefs": val.get("xrefs")
        } for item, val in response_list.items()])

    def get_request_body(self):
        if self.request_body is None:
            return []
        request_body_list = {}
        for content_type, item_properties in self.request_body.items():
            curr_request_body = flatten_json_schema(
                to_dict_helper(item_properties))
            request_body_list.update(curr_request_body)
        return remove_nulls([{
            "name": item,
            "type": val.get("type"),
            "description": val.get("description", ""),
            "enum": val.get("enum"),
            "xrefs": val.get("xrefs")
        } for item, val in request_body_list.items()])


def recursion_limit_handler_none(limit, refstring, recursions):
    return {}


class SpecificationParser:
    """
    Class to parse a specification file and return a dictionary of all the operations and their properties.
    """

    def __init__(self, spec_path=None, recursion_limit=1):
        self.spec_path = spec_path
        if spec_path is not None:
            print("PARSE..")
            self.resolving_parser = ResolvingParser(
                spec_path,
                strict=False,
                recursion_limit=recursion_limit,
                recursion_limit_handler=recursion_limit_handler_none,
            )
            print("Done")
        self.operations = {}

    def get_api_url(self) -> str:
        """
        Extract the server URL from the specification file.
        """
        return self.resolving_parser.specification.get('servers', {}).get("0", {}).get('url', None)

    def get_api_title(self) -> str:
        """
        Extract the title of the API from the specification file.
        """
        return self.resolving_parser.specification.get('info', {}).get('title')

    def load_from_file(self, spec_cache):
        operation_collection = {}
        with open(spec_cache, "r") as file:
            data = json.load(file)
            for operation_id, operationProperties in data.items():
                # requestBody
                # response
                operation_properties = OperationProperties.from_dict(
                    operationProperties)
                operation_collection.setdefault(
                    operation_id, operation_properties)
        self.operations = operation_collection
        return operation_collection

    def load_or_initialize(self, cache_dir=None):
        # Check if the cache file exists
        self.cache_file = os.path.join(cache_dir, "specification.json")
        if os.path.exists(self.cache_file):
            print(f"Loading graph from cache: {self.cache_file}")
            self.load_from_file(self.cache_file)
        else:
            print("Cache file not found. Initializing Specification...")
            self.parse_specification()
            self.json_spec_output(file_name=self.cache_file)
        # # save to cache

    def process_parameter_object_properties(self, properties: Dict) -> Dict[str, ItemProperties]:
        """
        Process the properties of a parameter of type object to return a dictionary of all the properties and their
        corresponding parameter values.
        """
        if properties is None:
            return None

        object_properties = {}
        for name, values in properties.items():
            # check if this is correct, or if it should be process_parameter
            object_properties.setdefault(
                name, self.process_parameter_schema(values))
        return object_properties

    def process_parameter_schema(self, schema: Dict) -> ItemProperties:
        """
        Process the schema of a parameter to return a ValueProperties object
        """
        if not schema:
            return None

        value_properties = ItemProperties(
            type=schema.get('type'),
            format=schema.get('format'),
            description=schema.get('description'),
            items=self.process_parameter_schema(
                schema.get('items')),  # recursively process items
            properties=self.process_parameter_object_properties(
                schema.get('properties')),
            required=schema.get('required'),
            default=schema.get('default'),
            enum=schema.get('enum'),
            minimum=schema.get('minimum'),
            maximum=schema.get('maximum'),
            min_length=schema.get('minLength'),
            max_length=schema.get('maxLength'),
            pattern=schema.get('pattern'),
            max_items=schema.get('maxItems'),
            min_items=schema.get('minItems'),
            unique_items=schema.get('uniqueItems'),
            additional_properties=schema.get('additionalProperties'),
            nullable=schema.get('nullable'),
            read_only=schema.get('readOnly'),
            write_only=schema.get('writeOnly'),
            example=schema.get('example'),
            examples=schema.get('examples'),
            xrefs=schema.get('x-refs')
        )
        return value_properties

    def process_parameter(self, parameter) -> ParameterProperties:
        """
        Process an individual parameter to return a ParameterProperties object.
        """
        parameter_properties = ParameterProperties(
            name=parameter.get('name'),
            in_value=parameter.get('in'),
            description=parameter.get('description'),
            required=parameter.get('required'),
            deprecated=parameter.get('deprecated'),
            allow_empty_value=parameter.get('allowEmptyValue'),
            style=parameter.get('style'),
            explode=parameter.get('explode'),
            allow_reserved=parameter.get('allowReserved')
        )
        if parameter.get('schema'):
            parameter_properties.schema = self.process_parameter_schema(
                parameter.get('schema'))
        return parameter_properties

    def process_parameters(self, parameter_list) -> Dict[str, ParameterProperties]:
        """
        Process the parameters list to return a Dictionary with all its properties and values.
        """
        parameters = {}
        if parameter_list:
            for parameter in parameter_list:
                parameter_properties = self.process_parameter(parameter)
                parameters.setdefault(
                    parameter_properties.name, parameter_properties)
        return parameters

    def process_request_body(self, request_body) -> Dict[str, ItemProperties]:
        """
        Process the request body to return a Dictionary with mime type and its properties and values.
        """

        request_body_properties = {}
        content = request_body.get('content')
        if content:
            for mime_type, mime_details in content.items():
                # if we need to check required list, do it here
                schema = mime_details.get('schema')
                if schema:
                    request_body_properties[mime_type] = self.process_parameter_schema(
                        schema)

        return request_body_properties

    def process_responses(self, responses) -> Dict[str, ResponseProperties]:
        """
        Process the responses to return a Dictionary with status code and its properties and values.
        """
        response_properties = {}
        for status_code, response_details in responses.items():
            response_properties.setdefault(status_code, ResponseProperties(
                status_code=status_code,
                description=response_details.get('description')
            ))
            content = response_details.get('content')
            if content:
                for mime_type, mime_details in content.items():
                    # if we need to check required list, do it here
                    schema = mime_details.get('schema')
                    if schema:
                        response_properties[status_code].content[mime_type] = self.process_parameter_schema(
                            schema)
        return response_properties

    def process_operation_details(self, http_method: str, endpoint_path: str, global_parameters: List, operation_details: Dict) -> OperationProperties:
        """
        Process the parameters and request body details within a given operation to return as OperationProperties object.
        """
        operation_properties = OperationProperties(
            uuid=f'{http_method}-{endpoint_path}',
            operation_id=operation_details.get('operationId'),
            endpoint_path=endpoint_path,
            http_method=http_method,
            summary=operation_details.get('summary'),
            tags=operation_details.get('tags'),
            description=operation_details.get('description'),
            external_docs=operation_details.get('external_docs')
        )
        if operation_details.get("parameters"):
            operation_properties.parameters = self.process_parameters(
                parameter_list=global_parameters + operation_details.get('parameters'))

        if operation_details.get('requestBody'):
            operation_properties.request_body = self.process_request_body(
                request_body=operation_details.get('requestBody'))

        if operation_details.get('responses'):
            operation_properties.responses = self.process_responses(
                responses=operation_details.get('responses'))

        # maybe add security details?

        return operation_properties

    def parse_specification(self) -> Dict[str, OperationProperties]:
        """
        Parse the specification file to return a dictionary of all the operations and their properties.

        The key of the dictionary is the operationId and the value is an OperationProperties object.
        """
        supported_methods = ("get", "post", "put", "delete",
                             "head", "options", "patch")
        operation_collection = {}
        # process schema name
        spec_paths = self.resolving_parser.specification.get('paths', {})
        for endpoint_path, endpoint_details in spec_paths.items():
            global_parameters = endpoint_details.get("parameters", [])
            for http_method, operation_details in endpoint_details.items():
                if http_method in supported_methods:
                    operation_properties = self.process_operation_details(
                        http_method, endpoint_path, global_parameters, operation_details)
                    operation_collection.setdefault(
                        operation_properties.uuid, operation_properties)
        self.operations = operation_collection
        return operation_collection

    def json_spec_output(self, file_name: str):
        """
        Create a testing JSON file from the specification parsing output.
        """
        serializable_spec = to_dict_helper(self.operations)

        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(serializable_spec, file, ensure_ascii=False, indent=4)
