
from jsonschema import validate, exceptions
from jsonschema import RefResolver

import json
import yaml

# validate(data, schema)


def expand_schema(schema):
    """Expand the schema by resolving all $ref references using a self-contained URI"""
    resolver = RefResolver.from_schema(schema)
    return resolve_ref(schema, resolver)

# expand_schema(schema)


# def convert_schema_to_github_form(schema_path, output_path):

#     # with open(schema_path, 'r') as f:
#     #     schema = json.load(f)

#     schema = schema_path
#     form = {
#         "name": schema.get("title", "Form"),
#         "description": "Auto-generated form from JSON Schema.",
#         "title":"{{ name }} - Submission",
#         "body": []
#     }

#     for field, details in schema.get("properties", {}).items():
#         form_field = {
#             "id": field,
#             "attributes": {
#                 "label": details.get("title", field.replace("_", " ").title()),
#                 "description": details.get("description", ""),
#                 "placeholder": details.get("default", "")

#             },
#     "validations":{"required": field in schema.get("required", [])}
#         }

#         if details["type"] == "string" and "enum" in details:
#             form_field["type"] = "dropdown"
#             form_field["attributes"]["options"] = details["enum"]
#         elif details["type"] == "array" and "items" in details and "enum" in details["items"]:
#             form_field["type"] = "checkboxes"
#             form_field["attributes"]["options"] = [{"label": opt.lower()} for opt in details["items"]["enum"]]
#             form_field['multiple'] = details.get("multiple", False)
#         elif details["type"] == "boolean":
#             form_field["type"] = "dropdown"
#             form_field["attributes"]["options"] = ["Yes", "No"]
#             form_field['miultiple'] = details.get("multiple", False)
#         else:
#             form_field["type"] = "input"
#             form_field["attributes"]["placeholder"] = details.get("default",f"Enter your {field.replace('_', ' ')}")

#         form["body"].append(form_field)

# # checkbox options can be required much like the field.


#     # with open(output_path, 'w') as f:
#     #     yaml.dump(form, f, sort_keys=False)
#     return yaml.dump(form)

# Example Usage
