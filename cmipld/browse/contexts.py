import typing
from urllib.parse import urljoin
import requests
import logging



logger = logging.getLogger(__name__)


def generate_context(base='https://wcrp-cmip.github.io',vocab=None,type=None,id=None, expand={},expand_ctx={}):
    
    
    from ..locations import mapping
    from ..utils import sorted_ctx
    
    context = mapping.copy()


    if base:
        context['@base'] = base
    if vocab:
        context['@vocab'] = vocab
        
    context.update(expand_ctx)    
        
    context = {"@context":context}
    
    if type:
        context['@type'] = type
    if id:
        context['@id'] = id
        
    context.update(expand)
    
    
    return sorted_ctx(context)    



class ContextResolutionError(Exception):
    """Custom exception for context resolution errors."""
    pass



def resolve_contexts(
    contexts: typing.Union[str, list, dict], 
    base_uri: str = '.'
) -> typing.List[dict]:
    """Recursively resolve and expand @context URIs or inline contexts."""
    try:
        if isinstance(contexts, str):
            resolved_uri = urljoin(base_uri, contexts)
            logger.info(f'Resolving context from URI: {resolved_uri}')
            return fetch_resolved_context(resolved_uri)
        
        if isinstance(contexts, list):
            return [
                ctx_item 
                for ctx in contexts 
                for ctx_item in resolve_contexts(ctx, base_uri)
            ]

        if isinstance(contexts, dict):
            return [contexts]
        
        raise ContextResolutionError(f"Unsupported @context format: {type(contexts)}")
    
    except Exception as e:
        logger.error(f"Context resolution error: {e}")
        raise ContextResolutionError(f"Resolution failed: {e}")


def combine_contexts(
    context: typing.Union[list, dict]
) -> dict:
    """Combine multiple context dictionaries into a single dictionary."""
    if isinstance(context, list):
        # context.reverse()
        return {k: v for ctx in context if isinstance(ctx, dict) for k, v in ctx.items()}
        # print(context)
        # ctx = {}
        # (ctx.update(c) for c in context)
        # return ctx
    
    if isinstance(context, dict):
        return context
    
    raise ContextResolutionError(f"Invalid context type: {type(context)}")

def fetch_resolved_context(
    jsonld_uri: str, 
    timeout: int = 10
) -> typing.List[dict]:
    """Fetch and resolve a JSON-LD document's @context."""
    try:
        response = requests.get(jsonld_uri, timeout=timeout)
        response.raise_for_status()
        context = response.json().get('@context')
        return resolve_contexts(context, jsonld_uri) if context else []

    except requests.RequestException as e:
        logger.error(f"Context fetch failed: {e}")
        raise ContextResolutionError(f"Fetch error: {e}")

def get_context(jsonld_uri: str) -> dict:
    """Retrieve and combine a JSON-LD document's resolved contexts."""
    return combine_contexts(fetch_resolved_context(jsonld_uri))