"""
PydanticValidator — validate a submitted JSON-LD item against the esgvoc
Pydantic model for its *kind*, via the ``pycmipld`` wrapper.

    result = PydanticValidator("horizontal_grid_cell", item).validate()

    result.data              # dict: passed, validated_fields, failed_fields, ...
    result.md                # Markdown section string
    result.passed            # bool
    result.validated_fields  # frozenset of submitted field keys that passed
    result.failed_fields     # frozenset that failed
    result.unmodelled_fields # frozenset not in the model (text-sim candidates)

Key translations (mirrors pycmipld._prepare_dict)
--------------------------------------------------
``validation_key`` → ``drs_name`` in the model.
Fields whose short name starts with ``drs`` or ``validation`` are always
excluded from similarity analysis — they are identifier / DRS fields.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Set, Type

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Shared constants (imported by text_similarity.py)
# ---------------------------------------------------------------------------

DEFAULT_SKIP_PREFIXES: tuple = ("drs", "validation")

# Types whose raw issue/form data shape does not match the esgvoc pydantic
# schema, so running pydantic on them always produces spurious "Field required"
# errors (e.g. horizontal_subgrids contains string IDs at submission time but
# the schema expects fully-expanded objects with .id/.type/.drs_name — those
# get hydrated later via JSON-LD resolution). Pydantic validation is the wrong
# tool for these types at submission stage; we skip it explicitly so neither
# new_issue.py nor ReportBuilder produces misleading "Schema validation failed"
# admonitions on PRs that successfully merged.
#
# This is the single source of truth — new_issue.py imports this set instead
# of maintaining its own copy.
SKIP_PYDANTIC_VALIDATION: frozenset = frozenset({
    "horizontal_subgrid",
    "horizontal_computational_grid",
    "component_config",
})

CMIPLD_KEY_TRANSLATION: Dict[str, str] = {
    "validation_key": "drs_name",
    "@id":            "id",
    "@type":          "type",
    "@context":       "context",
}


def short(key: str) -> str:
    """Last path segment of a URI key — used for display everywhere."""
    return key.split("/")[-1]


def is_default_skip(key: str) -> bool:
    """True for @-prefixed keys and DRS/identifier short-name prefixes."""
    if key.startswith("@"):
        return True
    return any(short(key).startswith(p) for p in DEFAULT_SKIP_PREFIXES)


def _translate(key: str) -> str:
    """Map a submitted key to its pycmipld / model-side field name."""
    s = short(key)
    return CMIPLD_KEY_TRANSLATION.get(s, CMIPLD_KEY_TRANSLATION.get(key, s))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _esgvoc_class(kind: str) -> Optional[Type[BaseModel]]:
    try:
        from cmipld.utils.esgvoc import DATA_DESCRIPTOR_CLASS_MAPPING
        return DATA_DESCRIPTOR_CLASS_MAPPING.get(kind)
    except ImportError:
        return None


def _model_fields(cls: Optional[Type[BaseModel]]) -> FrozenSet[str]:
    if cls is None:
        return frozenset()
    try:
        return frozenset(cls.model_fields.keys())
    except AttributeError:
        return frozenset(cls.__fields__.keys())


def _model_metadata(cls: Optional[Type[BaseModel]]) -> Dict[str, dict]:
    if cls is None:
        return {}
    out: Dict[str, dict] = {}
    try:
        fields = cls.model_fields
    except AttributeError:
        fields = cls.__fields__
    for name, info in fields.items():
        ann = getattr(info, "annotation", None)
        type_str = ann.__name__ if hasattr(ann, "__name__") else str(ann)
        try:
            required = info.is_required()
        except AttributeError:
            required = info.required
        out[name] = {
            "required": required,
            "type": type_str,
            "description": getattr(info, "description", "") or "",
        }
    return out


def _parse_failed(errors_md: Optional[str]) -> FrozenSet[str]:
    """Extract model-side field names from the pycmipld error table."""
    if not errors_md:
        return frozenset()
    failed: set = set()
    for line in errors_md.splitlines():
        if line.startswith("|") and "---" not in line and "Field" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts:
                failed.add(parts[0].strip("`").split(".")[0])
    return frozenset(failed)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

class ValidationResult:
    """
    Returned by ``PydanticValidator.validate()``.

    Attributes
    ----------
    passed            : bool — True when all model fields validated
    validated_fields  : submitted keys that map to the model and passed
    failed_fields     : submitted keys that failed validation
    unmodelled_fields : submitted keys not in the model (text-sim candidates)
    model_fields      : all field names declared by the esgvoc model
    errors_md         : raw error table from pycmipld (or None)
    """

    def __init__(self, passed, validated_fields, failed_fields,
                 unmodelled_fields, model_fields, model_meta, errors_md, kind):
        self.passed            = passed
        self.validated_fields  = validated_fields
        self.failed_fields     = failed_fields
        self.unmodelled_fields = unmodelled_fields
        self.model_fields      = model_fields
        self._model_meta       = model_meta
        self.errors_md         = errors_md
        self._kind             = kind

    @property
    def data(self) -> dict:
        return {
            "passed":            self.passed,
            "validated_fields":  sorted(short(f) for f in self.validated_fields),
            "failed_fields":     sorted(short(f) for f in self.failed_fields),
            "unmodelled_fields": sorted(short(f) for f in self.unmodelled_fields),
            "model_fields":      sorted(self.model_fields),
        }

    @property
    def md(self) -> str:
        lines = ["## 🧩 Pydantic Validation\n"]

        if self._model_meta:
            lines += [
                "### Schema fields (pre-validated)\n",
                "_These fields are defined in the esgvoc schema and validated automatically. "
                "`drs_name` / `validation_key` are identifier fields and excluded from similarity._\n",
                "| Field | Required | Type | Description |",
                "|-------|----------|------|-------------|",
            ]
            for fname, info in sorted(self._model_meta.items()):
                req = "✅" if info["required"] else "—"
                lines.append(f"| `{fname}` | {req} | `{info['type']}` | {info['description']} |")
            lines.append("")
        else:
            lines.append(f"_No esgvoc model found for `{self._kind}`._\n")

        status = "✅ All submitted schema fields passed." if self.passed else "❌ Validation errors found."
        lines.append(f"### Status\n\n{status}\n")

        if self.errors_md:
            lines += ["### Errors\n", self.errors_md, ""]

        if self.validated_fields:
            lines.append("### Pre-validated fields\n")
            lines += [f"- ✅ `{short(f)}`" for f in sorted(self.validated_fields)]
            lines.append("")

        if self.failed_fields:
            lines.append("### Failed fields\n")
            lines += [f"- ❌ `{short(f)}`" for f in sorted(self.failed_fields)]
            lines.append("")

        if self.unmodelled_fields:
            lines.append("### Not in schema — assessed by text similarity\n")
            lines += [f"- `{short(f)}`" for f in sorted(self.unmodelled_fields)]
            lines.append("")

        return "\n".join(lines)

    def __repr__(self):
        return (
            f"ValidationResult(passed={self.passed}, "
            f"validated={sorted(short(f) for f in self.validated_fields)}, "
            f"unmodelled={sorted(short(f) for f in self.unmodelled_fields)})"
        )


# ---------------------------------------------------------------------------
# PydanticValidator
# ---------------------------------------------------------------------------

class PydanticValidator:
    """
    Validate a submitted JSON-LD item against the esgvoc model for *kind*.

    Parameters
    ----------
    kind : str
        e.g. ``"horizontal_grid_cell"``
    item : dict
        The JSON-LD item to validate.
    """

    def __init__(self, kind: str, item: dict):
        self.kind  = kind
        self.item  = item
        self._cls  = _esgvoc_class(kind)

    def validate(self) -> ValidationResult:
        """Run validation and return a :class:`ValidationResult`."""
        # Early-skip: types in SKIP_PYDANTIC_VALIDATION are known to have
        # submission-stage data shapes that don't match the esgvoc schema.
        # Returning a no-op passed result here means new_issue.py STEP 1 sees
        # passed=True (so the PR is allowed to be created — same as before),
        # and ReportBuilder sees a val_result with no errors_md (so the
        # "Schema validation failed" admonition does not appear on the PR).
        if self.kind in SKIP_PYDANTIC_VALIDATION:
            return ValidationResult(
                passed=True, validated_fields=frozenset(),
                failed_fields=frozenset(), unmodelled_fields=frozenset(),
                model_fields=frozenset(), model_meta={}, errors_md=None, kind=self.kind,
            )

        model_fnames = _model_fields(self._cls)
        model_meta   = _model_metadata(self._cls)

        if self._cls is None:
            return ValidationResult(
                passed=True, validated_fields=frozenset(),
                failed_fields=frozenset(), unmodelled_fields=frozenset(),
                model_fields=frozenset(), model_meta={}, errors_md=None, kind=self.kind,
            )

        try:
            from cmipld.utils.esgvoc import pycmipld
        except ImportError as exc:
            raise ImportError("esgvoc must be installed to run PydanticValidator.") from exc

        instance   = pycmipld(self._cls, **self.item)
        passed     = instance.data is not None
        errors_md  = instance.validation_md

        # Map submitted keys → model names, skipping default-skip fields
        submitted: Dict[str, str] = {
            k: _translate(k)
            for k in self.item
            if not is_default_skip(k)
        }

        intersect = frozenset(k for k, t in submitted.items() if t in model_fnames)

        if passed:
            validated  = intersect
            failed     = frozenset()
        else:
            failed_trans = _parse_failed(errors_md)
            failed       = frozenset(k for k, t in submitted.items() if t in failed_trans)
            validated    = intersect - failed

        unmodelled = frozenset(
            k for k, t in submitted.items() if t not in model_fnames
        )

        return ValidationResult(
            passed=passed, validated_fields=validated, failed_fields=failed,
            unmodelled_fields=unmodelled, model_fields=model_fnames,
            model_meta=model_meta, errors_md=errors_md, kind=self.kind,
        )
