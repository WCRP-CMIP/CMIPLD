
from .__init__ import * 
import glob, yaml, json, os
from pprint import pprint
# from collections import OrderedDict
from tqdm import tqdm

from jsonschema import RefResolver

def list_to_md(lst):
    return '| ' + ' | '.join(lst) + ' |'

def resolve_ref(schema, resolver):
    
    """Recursively resolve $ref in the schema"""
    try:
        # overrride = schema.get('form',False)
        if "$ref" in schema:
            ref_url = schema["$ref"]
            # schema0 = schema.copy()
            # Resolve the reference using the resolver and get the actual definition
            schema.update(resolver.resolve(ref_url)[1])
            
            # print(schema, schema0)# The second element is the resolved schema
        if isinstance(schema, dict):
            for key, value in schema.items():
                schema[key] = resolve_ref(value, resolver)
        elif isinstance(schema, list):
            for idx, item in enumerate(schema):
                schema[idx] = resolve_ref(item, resolver)
    finally: 
        # if overrride and overrride!= None:
        #     schema['form'] = overrride
        return schema


def expand_schema(schema):
    """Expand the schema by resolving all $ref references using a self-contained URI"""
    resolver = RefResolver.from_schema(schema)
    return resolve_ref(schema, resolver)



def convert_schema_to_github_form(schema_path):
    
    # with open(schema_path, 'r') as f:
    #     schema = json.load(f)

    schema = schema_path
    
    schema['contains'] = list_to_md(schema['contains']['enum'])
    
    

    if '@context' in schema:
        del schema['@context']
    
    form = {
        "name": f'Add/Modify: {schema.get("id").capitalize()}',
        "description": schema.get('description',f"Type: {schema.get('id')}"),
        "title":f"Add/Modify: {schema.get('id').capitalize()}: <enter item name>",
        "labels": ['delta',schema.get('id')],
        "body": []
    }


    info = {
            "type": "markdown",
            "attributes": {
                "value": schema.get("markdown_content","").format(**schema) or 'Please fill in the form below.'  # Using the string with \n for line breaks
            }
        }
    # Add the markdown content description
    form['body'].append( info )



    for field, details in schema.get("properties", {}).items():
        
        if field in ['id','type']: continue
        
        # print(field, details), print()
        
        
        # if 'enum' in details:
        #     details = details['enum']
        
        form_field = {
            "id": field,
            "attributes": {
                "label": details.get("title", field.replace("_", " ").title()),
                "description": details.get("description", f"Enter the {field.replace('_', ' ')}"),
                # "placeholder": details.get("default", "")
                

            },
    "validations":{"required": field in schema.get("required", [])}
        }

        print('OVERRRIDE',field,details.get('form'))
        if details.get('form'):
            details['type'] = 'override'
            print('OVERRRIDE',field,details.get('form'))
            
        if details.get('form')=="dropdown" or details["type"] == "string" and "enum" in details:
            form_field["type"] = "dropdown"
            form_field["attributes"]["options"] = list(details["enum"])
                
            
        elif details.get('form')=="checkboxes" or details["type"] == "array" and "items" in details and "enum" in details["items"]:
            
            form_field["type"] = "checkboxes"
            
            if 'items' in details:
                form_field["attributes"]["options"] = [{"label": opt.lower()} for opt in details["items"]["enum"]]
            elif 'enum' in details:
                form_field["attributes"]["options"] = [{"label": opt.lower()} for opt in details["enum"]]
            
            else:
                print('CHECKBOX FAIL',details)
                # assert False, "No enum or items found for checkboxes"
            
                
                
            # form_field['multiple'] = details.get("multiple", False)
            
        elif details.get('form')=="bool" or details["type"] == "boolean":
            form_field["type"] = "dropdown"
            form_field["attributes"]["options"] = ["Yes", "No"]
            # form_field['multiple'] = details.get("multiple", False)
            
        elif details.get('form')=="textarea":
            form_field["type"] = "textarea"
            # form_field["attributes"]["placeholder"] = details.get("default",f"Enter your {field.replace('_', ' ')}")
        else:
            form_field["type"] = "input"
            # form_field["attributes"]["placeholder"] = details.get("default",f"Enter your {field.replace('_', ' ')}")

        if details.get('other',False):
                form["body"].append(form_field)
                
                form_field = {
                    "id": field+'_other',
                    "attributes": {
                        
                        "label":"^",
                        "description":  details['other']+ " For new values only, please register them in the relevant area.",
                        },
                "type" : "input",
                "validations":{"required":False}
                }


        form["body"].append(form_field)



# checkbox options can be required much like the field. 





    return form

    # with open(output_path, 'w') as f:
    #     yaml.dump(form, f, sort_keys=False)
    # return yaml.dump(form)



def main():
    
    os.system(f'mkdir -p .github/ISSUE_TEMPLATE')
    os.system('rm .github/ISSUE_TEMPLATE/cmipld_*.yml')
        
    print('Generating issue templates for all data descriptors')
    
    for dir in tqdm(glob.glob("./src-data/*/")):
        
        if not os.path.exists(dir+'_schema_') and not os.path.exists(dir+'_context'):
            # skip all directories without a schema and context
            continue
        
        schema = json.load(open(dir+'_schema_'))
        schema = expand_schema(schema)
        
        # pprint(schema)

        form = convert_schema_to_github_form(schema)
        
        # print(yaml.dump(form,indent=4,sort_keys=False))
        
        with open(f'.github/ISSUE_TEMPLATE/cmipld_'+dir.split('/')[-2]+'.yml','w') as f:
            yaml.dump(form,f,indent=4,sort_keys=False)
        
        
        # yaml.dump(form, open(dir+'_form.yaml','w'), sort_keys=False)
        
        
if __name__ == '__main__':
    main()  