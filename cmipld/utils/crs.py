"""
Canonical Realm String (CRS) — build, parse, validate.

A CRS is a compact deterministic fingerprint for ESM coupling topology, e.g.:

    A[AcAe](L,O)L(O)O[ObSi]

Notation
--------
  parent[child1child2]   — child realms embedded inside parent (sorted)
  parent(c1,c2)          — forward-only couplings from parent to others (sorted)

Realm codes (canonical order)
------------------------------
  A   atmosphere
  Ac  atmospheric-chemistry
  Ae  aerosol
  Li  land-ice
  L   land-surface
  O   ocean
  Ob  ocean-biogeochemistry
  Si  sea-ice

Rules
-----
* Each realm may be embedded in at most one parent.
* Embedded realms cannot appear in coupling groups.
* Couplings are forward-only: listed under the earlier code in canonical order.
* All output is deterministic (sorted by canonical order).
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Set

# ── Realm registry ─────────────────────────────────────────────────────────────

REALM_CODES: Dict[str, str] = {
    "atmosphere":            "A",
    "atmospheric-chemistry": "Ac",
    "aerosol":               "Ae",
    "land-ice":              "Li",
    "land-surface":          "L",
    "ocean":                 "O",
    "ocean-biogeochemistry": "Ob",
    "sea-ice":               "Si",
}

CODE_TO_REALM: Dict[str, str] = {v: k for k, v in REALM_CODES.items()}

# Defines the canonical ordering used everywhere in this module.
CANONICAL_ORDER: List[str] = ["A", "Ac", "Ae", "Li", "L", "O", "Ob", "Si"]


def _rank(code: str) -> int:
    try:
        return CANONICAL_ORDER.index(code)
    except ValueError:
        return len(CANONICAL_ORDER)


def _sort(codes) -> List[str]:
    return sorted(codes, key=_rank)


def to_code(name: str) -> str:
    """Full realm name → short code.  Returns name unchanged if not found."""
    name = name.strip().lower().replace("_", "-")
    return REALM_CODES.get(name, name)


def to_name(code: str) -> str:
    """Short code → full realm name.  Returns code unchanged if not found."""
    return CODE_TO_REALM.get(code, code)


# ── Build ──────────────────────────────────────────────────────────────────────

def build(
    dynamic: List[str],
    embedded: List[List[str]],
    coupling_groups: List[List[str]],
) -> str:
    """
    Construct the canonical CRS string.

    Parameters
    ----------
    dynamic : list of full realm names that are active (dynamic + prescribed)
    embedded : list of [parent, child] pairs (full names or codes)
    coupling_groups : list of groups; realms within a group are all mutually coupled
    """
    # Normalise everything to codes
    dyn_codes: Set[str] = {to_code(r) for r in dynamic}

    # parent_of[child] = parent
    parent_of: Dict[str, str] = {}
    # children_of[parent] = [child, ...]
    children_of: Dict[str, List[str]] = {}
    for pair in embedded:
        if len(pair) < 2:
            continue
        parent, child = to_code(pair[0]), to_code(pair[1])
        parent_of[child] = parent
        children_of.setdefault(parent, []).append(child)

    # Expand coupling groups into pairs, exclude embedded realms
    embedded_codes = set(parent_of.keys())
    coupling_pairs: Set[Tuple[str, str]] = set()
    for group in coupling_groups:
        codes = [to_code(r) for r in group if to_code(r) not in embedded_codes]
        for i, a in enumerate(codes):
            for b in codes[i + 1:]:
                lo, hi = (_sort([a, b]))
                coupling_pairs.add((lo, hi))

    # Forward-only coupling map: only listed under the canonical-earlier realm
    forward: Dict[str, List[str]] = {}
    for lo, hi in coupling_pairs:
        forward.setdefault(lo, []).append(hi)

    # Root realms — active, not embedded in anything else
    roots = _sort([c for c in dyn_codes if c not in embedded_codes])

    parts: List[str] = []
    for realm in roots:
        token = realm
        # Embedding children
        kids = _sort(children_of.get(realm, []))
        if kids:
            token += "[" + "".join(kids) + "]"
        # Forward couplings
        coupled = _sort(forward.get(realm, []))
        if coupled:
            token += "(" + ",".join(coupled) + ")"
        parts.append(token)

    return "".join(parts)


# ── Parse ──────────────────────────────────────────────────────────────────────

def parse(crs: str) -> Dict[str, list]:
    """
    Parse a CRS string back into embeddings and coupling pairs.

    Returns
    -------
    dict with keys:
      'embeddings'      : [[parent_code, child_code], ...]
      'coupling_pairs'  : [[code_a, code_b], ...]  (canonical order, no duplicates)
      'roots'           : [code, ...]  (non-embedded realms in canonical order)
    """
    embeddings: List[List[str]] = []
    coupling_pairs: List[List[str]] = []

    i = 0
    n = len(crs)

    def read_code(pos: int) -> Tuple[str, int]:
        """Read a 1-or-2-char realm code starting at pos."""
        if pos >= n:
            return "", pos
        code = crs[pos]
        pos += 1
        if pos < n and crs[pos].islower():
            code += crs[pos]
            pos += 1
        return code, pos

    # Stack holds the current parent realm while inside [...]
    parent_stack: List[str] = []
    roots: List[str] = []

    while i < n:
        ch = crs[i]

        if ch.isupper():
            code, i = read_code(i)
            current_parent = parent_stack[-1] if parent_stack else None
            if current_parent:
                embeddings.append([current_parent, code])
            else:
                roots.append(code)

            # Look ahead
            if i < n and crs[i] == "[":
                parent_stack.append(code)
                i += 1  # consume '['
            elif i < n and crs[i] == "(":
                # couplings follow — handled below
                pass

        elif ch == "]":
            if parent_stack:
                parent_stack.pop()
            i += 1

        elif ch == "(":
            # The realm that owns these couplings is the last root-level realm
            # we encountered (or top of stack if nested, but coupling can't be
            # inside embedding by the CRS rules).
            owner = roots[-1] if roots else (parent_stack[-1] if parent_stack else None)
            i += 1  # consume '('
            while i < n and crs[i] != ")":
                if crs[i] == ",":
                    i += 1
                    continue
                if crs[i].isupper():
                    coupled, i = read_code(i)
                    if owner:
                        pair = _sort([owner, coupled])
                        if pair not in coupling_pairs:
                            coupling_pairs.append(pair)
                else:
                    i += 1
            if i < n and crs[i] == ")":
                i += 1  # consume ')'

        else:
            i += 1

    return {
        "embeddings":     embeddings,
        "coupling_pairs": coupling_pairs,
        "roots":          _sort(roots),
    }


# ── Validate ───────────────────────────────────────────────────────────────────

def validate(
    dynamic: List[str],
    embedded: List[List[str]],
    coupling_groups: List[List[str]],
) -> List[str]:
    """
    Check CRS constraints. Returns a list of error strings (empty = OK).
    """
    errors: List[str] = []

    dyn_codes = {to_code(r) for r in dynamic}

    # Build parent map
    parent_of: Dict[str, str] = {}
    for pair in embedded:
        if len(pair) < 2:
            errors.append(f"Embedding pair needs [parent, child], got: {pair}")
            continue
        parent, child = to_code(pair[0]), to_code(pair[1])
        if child in parent_of:
            errors.append(
                f"'{to_name(child)}' ({child}) is embedded in more than one parent: "
                f"'{to_name(parent_of[child])}' and '{to_name(parent)}'"
            )
        else:
            parent_of[child] = parent

    # Check embedded realms are subset of dynamic
    for child, parent in parent_of.items():
        if child not in dyn_codes:
            errors.append(
                f"Embedded realm '{to_name(child)}' ({child}) is not in dynamic_components"
            )
        if parent not in dyn_codes:
            errors.append(
                f"Parent realm '{to_name(parent)}' ({parent}) is not in dynamic_components"
            )

    # Check embedded realms don't appear in coupling groups
    embedded_codes = set(parent_of.keys())
    for i, group in enumerate(coupling_groups, 1):
        codes = {to_code(r) for r in group}
        bad = embedded_codes & codes
        if bad:
            errors.append(
                f"Coupling group {i} contains embedded realm(s): "
                + ", ".join(f"'{to_name(c)}' ({c})" for c in sorted(bad, key=_rank))
            )

    # Cycle detection in embeddings (A→B→A)
    def has_cycle(start: str) -> bool:
        seen: Set[str] = set()
        cur = start
        while cur in parent_of:
            if cur in seen:
                return True
            seen.add(cur)
            cur = parent_of[cur]
        return False

    for child in parent_of:
        if has_cycle(child):
            errors.append(f"Embedding cycle detected involving '{to_name(child)}' ({child})")

    # Coupling group realms should be in dynamic
    for i, group in enumerate(coupling_groups, 1):
        for r in group:
            code = to_code(r)
            if code not in dyn_codes:
                errors.append(
                    f"Coupling group {i}: '{r}' is not in dynamic_components"
                )

    return errors


# ── Convenience round-trip helpers ─────────────────────────────────────────────

def from_model_data(data: dict) -> str:
    """
    Build a CRS string directly from a model JSON-LD dict.

    Reads: dynamic_components, embedded_components, coupling_groups
    """
    dynamic = data.get("dynamic_components", []) + data.get("prescribed_components", [])
    embedded = data.get("embedded_components", [])
    coupling_groups = data.get("coupling_groups", [])
    return build(dynamic, embedded, coupling_groups)


def to_model_fields(crs: str) -> Dict[str, list]:
    """
    Invert a CRS string into the fields used in a model JSON-LD dict.

    Returns dict with 'embedded_components' and 'coupling_groups'.
    embedded_components: [[parent_name, child_name], ...]
    coupling_groups: one group containing all coupled realm names
    """
    parsed = parse(crs)
    embedded = [[to_name(p), to_name(c)] for p, c in parsed["embeddings"]]

    # Reconstruct coupling groups: build adjacency, find connected components
    from collections import defaultdict
    adj: Dict[str, Set[str]] = defaultdict(set)
    for a, b in parsed["coupling_pairs"]:
        adj[a].add(b)
        adj[b].add(a)

    visited: Set[str] = set()
    groups: List[List[str]] = []
    all_coupled = set(adj.keys())
    for start in _sort(list(all_coupled)):
        if start in visited:
            continue
        # BFS
        group: List[str] = []
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            group.append(node)
            queue.extend(n for n in adj[node] if n not in visited)
        if group:
            groups.append([to_name(c) for c in _sort(group)])

    return {
        "embedded_components": embedded,
        "coupling_groups":     groups,
    }
