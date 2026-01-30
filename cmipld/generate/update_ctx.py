import glob
import json
import os

def snake_to_pascal(name):
    return ''.join(word.capitalize() for word in name.split('_'))


def ld(linked):

    if '@context' not in linked:
        return linked
    # elif '@type' in linked and linked['@type'] == '@id' and '@container'  not in linked:
    #     linked['@container'] = '@id'
        return linked
    return {'@context': linked['@context'], '@type':'@id'}
#  lets make all linked items an array, this makes it easier to handle later
# "@container":"@id" 

def main():
    from cmipld.utils.validate_json.validator import JSONValidator
    

    global v
    v = JSONValidator('.')
    data()
    project()
    
    
def data():
    from cmipld import reverse_mapping
    # Get repo base URL§
    repo = os.popen("git remote get-url origin").read().replace('.git','').strip().split('/')[-2:]
    base = f'https://{repo[0].lower()}.github.io/{repo[1]}/'
    prefix = reverse_mapping.get(base,'no-prefix')
    base2 = f'https://{prefix}.mipcvs.dev/'


    # Process each context file
    for cx in glob.glob('*/_context'):
        folder = cx.split('/')[-2].replace('-', '_')
        esg_name = snake_to_pascal(folder)
        
        try:
            # Load context
            with open(cx) as f:
                ctx = json.load(f).get('@context', {})
                
            if isinstance(ctx, list):
                ctx = ctx[-1]  # Assume last item is the dict we want
            
            # Clean dict items without @id (fixes unhashable error)
            ctx = {k.replace('-', '_').lower(): ld(v) for k, v in ctx.items() if isinstance(v, dict) and '@id' in str(v)}

            # Set base/vocab
            ctx['@base'] = f"{base2}{folder}/"
            ctx['@vocab'] = f"{base2}docs/contents/{esg_name}/"
            ctx["@alt_base"] = f"{base}{folder}/"
            # ctx['@esg_vocab'] = f"https://esgf.github.io/esgf-vocab/api_documentation/data_descriptors.html#esgvoc.api.data_descriptors.{esg_name}"
            ctx['@esgvoc'] = esg_name
            
            
            # f"https://esgf.github.io/esgf-vocab/api_documentation/data_descriptors.html#esgvoc.api.data_descriptors.{esg_name}."
            
            # Write back
            
            print (f"Updating context file: {cx}")
            with open(cx, 'w') as f:
                json.dump({'@context': dict(sorted(ctx.items()))}, f, indent=4)
                
        except Exception as e:
            print(f"Error with {cx}: {e}")
            


            
            
def project():
    from cmipld import reverse_mapping
    global v
    # Get repo base URL
    repo = (os.popen("git remote get-url origin").read()).replace('.git','').strip().split('/')[-2:]
    base = f'https://{repo[0].lower()}.github.io/{repo[1]}/'
    prefix = reverse_mapping.get(base,'no-prefix')
    base2 = f'https://{prefix}.mipcvs.dev/'



    # Process each context file
    for cx in glob.glob('project/*.json'):
        
        folder = cx.split('/')[-1].split('.json')[0].replace('-', '_')
        esg_name = snake_to_pascal(folder)
        
        try:
            # Load context
            with open(cx,'r') as f:
                data = json.load(f)
                
                ctx = data.get('@context', {})
                
                if isinstance(ctx, list):
                    ctx = ctx[-1]  # Assume last item is the dict we want

            ctx = {k.replace('-', '_').lower(): ld(v) for k, v in ctx.items() if isinstance(v, dict) and '@id' in str(v)}

            # Set base/vocab
            # ctx['@base'] = f"{base}project/"
            # ctx['@vocab'] = f"https://esgf.github.io/esgf-vocab/api_documentation/data_descriptors.html#esgvoc.api.data_descriptors.{esg_name}"
            
            # Set base/vocab
            ctx['@base'] = f"{base2}{folder}/"
            ctx['@vocab'] = f"{base2}docs/contents/{esg_name}/"
            ctx["@alt_base"] = f"{base}{folder}/"
            
            data['@context'] = dict(sorted(ctx.items()))
            # Write back
            with open(cx, 'w') as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"Error with {cx}: {e}")
            
        # validate_and_fix_json
        v.project_type = data.get('@id')

        v.validate_and_fix_json(cx)    
    
