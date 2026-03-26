"""
ESGVOC Pydantic Model Wrapper for CMIP JSON-LD Translation

Provides a generic wrapper class to translate CMIP JSON-LD format to 
ESGVOC-compatible pydantic models with built-in validation and error reporting.
"""

from typing import TypeVar, Generic, Type
from pydantic import BaseModel, ValidationError, ConfigDict

# esgvoc is a declared dependency — import directly
try:
    from esgvoc.api.data_descriptors import *
except ImportError as e:
    raise ImportError(
        "esgvoc is not installed. Run: pip install esgvoc"
    ) from e

T = TypeVar("T", bound=BaseModel)


class pycmipld(BaseModel, Generic[T]):
    '''
    A wrapper class to translate CMIP JSONLD format to the ESGVOC compatible pydantic models. 
    
    Usage:
        model = pycmipld(HorizontalGridCells, **data_dictionary)
        
        # Check if validation passed
        if model.data:
            print("✅ Validation passed!")
        else:
            print("❌ Validation failed")
        
        # Print validation errors as formatted table
        model.print_validation()
        
        # Or get the Markdown string
        if model.validation_md:
            print(model.validation_md)
    '''
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
  
    data: T | None = None
    model_class: Type[T] | None = None
    validation_md: str | None = None  # Stores validation warnings/errors as Markdown
    
    def __init__(self, model: Type[T], **cmip_ld_data):
        translated = self._prepare_dict(cmip_ld_data)
        # Attempt validation
        try:
            validated_data = model.model_validate(translated)
            super().__init__(data=validated_data, model_class=model)
        except ValidationError as e:
            # Capture errors as Markdown instead of raising
            super().__init__(data=None, model_class=model, validation_md=self._errors_to_md(e))
  
    def _prepare_dict(self, values: dict) -> dict:
        """Translate JSON-LD to model dict; convert empty strings to None."""
        # Always a list for @type
        raw_type = values.get("@type", [])
        type_value = next((t.replace('esgvoc:', '') for t in raw_type if 'esgvoc:' in t), None)
        # Build translated dict
        translated = {
            k: (v if v != '' else None)  # convert empty strings to None
            for k, v in {
                "id": values.get("@id"),
                "type": type_value,
                "context": values.get("@context"),
                "drs_name": values.get("validation_key"),
                **{k: v for k, v in values.items() if not k.startswith("@")}
            }.items()
        }
        return translated
    
    def _errors_to_md(self, err: ValidationError) -> str:
        """Convert ValidationError into a pretty Markdown table."""
        headers = ["Field", "Error Type", "Input Value", "Input Type", "Message"]
        rows = []
        for e in err.errors():
            loc = ".".join(str(x) for x in e.get("loc", ["unknown"]))
            err_type = e.get("type", "")
            input_value = e.get("ctx", {}).get("given", e.get("input_value", None))
            input_type = type(input_value).__name__ if input_value is not None else "None"
            msg = e.get("msg", "").replace("\n", "<br>")
            rows.append([loc, err_type, f"`{input_value}`", input_type, msg])
        md = "| " + " | ".join(f"**{h}**" for h in headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        for row in rows:
            md += "| " + " | ".join(str(c) for c in row) + " |\n"
        return md
    
    def print_validation(self) -> None:
        """Print validation errors as a formatted Markdown table to console."""
        if self.validation_md:
            print("\n❌ Validation Errors:\n")
            print(self.validation_md)
        else:
            print("\n✅ No validation errors")
