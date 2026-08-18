"""
Canonical Realm String (CRS) — build, parse, validate.

A CRS is a compact deterministic fingerprint for ESM coupling topology, e.g.:

    A[AcAe](L,O)L(O)O[ObSi]Ae^Li^

Notation
--------
  parent[child1child2]   — child realms embedded inside parent (sorted)
  parent[child[gchild]]  — embeddings nest to arbitrary depth; a child may itself
                           contain an embedding block, e.g. 'A[Ac[Ae]L]' means
                           aerosol inside chemistry inside atmosphere, alongside
                           land-surface also inside atmosphere.
  parent(c1,c2)          — forward-only couplings from parent to others (sorted)
  code^                  — the realm is PRESCRIBED (present but imposed from an
                           external dataset, not interactively coupled). The '^'
                           binds to the code it follows, e.g. 'Ae^', 'Li^'.
                           Prescribed realms appear as bare roots (never embedded
                           or coupled) after all dynamic realms in canonical order.

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
* Embeddings form a forest and may nest to any depth (no cycles).
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


# ── Embedding forest helpers ───────────────────────────────────────────────────

# With 8 realms, an embedding chain longer than this is necessarily cyclic.
MAX_EMBED_DEPTH: int = len(CANONICAL_ORDER)


class CRSSyntaxError(ValueError):
    """Raised when a CRS string cannot be parsed."""


def _embedding_maps(embedded) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Turn a list of [child, parent] pairs into (parent_of, children_of).

    Duplicate identical pairs are collapsed; a child claimed by two *different*
    parents raises, since that cannot be rendered as a tree.
    """
    parent_of: Dict[str, str] = {}
    children_of: Dict[str, List[str]] = {}
    for pair in embedded:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        child, parent = to_code(pair[0]), to_code(pair[1])
        if child in parent_of:
            if parent_of[child] != parent:
                raise ValueError(
                    f"'{to_name(child)}' ({child}) is embedded in more than one "
                    f"parent: '{to_name(parent_of[child])}' and '{to_name(parent)}'"
                )
            continue
        parent_of[child] = parent
        kids = children_of.setdefault(parent, [])
        if child not in kids:
            kids.append(child)
    return parent_of, children_of


def _assert_acyclic(parent_of: Dict[str, str]) -> None:
    """Raise if the embedding map contains a cycle (including self-embedding)."""
    for start in parent_of:
        seen: Set[str] = set()
        cur = start
        while cur in parent_of:
            if cur in seen:
                raise ValueError(
                    f"Embedding cycle detected involving "
                    f"'{to_name(start)}' ({start})"
                )
            seen.add(cur)
            cur = parent_of[cur]


# ── Build ──────────────────────────────────────────────────────────────────────

def build(
    dynamic: List[str],
    embedded: List[List[str]],
    coupling_groups: List[List[str]],
    prescribed: List[str] | None = None,
) -> str:
    """
    Construct the canonical CRS string.

    Parameters
    ----------
    dynamic : list of full realm names that are dynamic (prognostic, interactive)
    embedded : list of [child, parent] pairs (full names or codes)
    coupling_groups : list of groups; realms within a group are all mutually coupled
    prescribed : list of full realm names that are prescribed (imposed from an
        external dataset, not interactively coupled). Rendered as bare roots with
        a trailing '^', after all dynamic realms in canonical order.

    Backwards compatibility: if `prescribed` is None, any realm that appears in
    `dynamic` but in no embedding or coupling is still rendered plain (no '^'),
    matching the previous dynamic+prescribed-merged behaviour.
    """
    # Normalise everything to codes
    dyn_codes: Set[str] = {to_code(r) for r in dynamic}
    pre_codes: Set[str] = {to_code(r) for r in (prescribed or [])}
    # A realm is only prescribed if it isn't also dynamic.
    pre_codes -= dyn_codes

    # parent_of[child] = parent ; children_of[parent] = [child, ...]
    parent_of, children_of = _embedding_maps(embedded)
    _assert_acyclic(parent_of)

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

    # Render a realm and, recursively, everything embedded inside it. Nesting is
    # unbounded in principle; MAX_EMBED_DEPTH is a belt-and-braces guard on top
    # of the cycle check above.
    rendered: Set[str] = set()

    def render(code: str, depth: int = 0) -> str:
        if depth > MAX_EMBED_DEPTH:
            raise ValueError(
                f"Embedding nested deeper than {MAX_EMBED_DEPTH} at "
                f"'{to_name(code)}' ({code})"
            )
        rendered.add(code)
        token = code
        # Embedded children — each may carry its own embedding block.
        kids = _sort(children_of.get(code, []))
        if kids:
            token += "[" + "".join(render(k, depth + 1) for k in kids) + "]"
        # Forward couplings (embedded realms never have any, by the CRS rules)
        coupled = _sort(forward.get(code, []))
        if coupled:
            token += "(" + ",".join(coupled) + ")"
        return token

    # Dynamic root realms — active, not embedded in anything else
    roots = _sort([c for c in dyn_codes if c not in embedded_codes])
    parts: List[str] = [render(realm) for realm in roots]

    # Prescribed realms — bare roots with a '^' marker, after the dynamic ones.
    for realm in _sort([c for c in pre_codes if c not in embedded_codes]):
        rendered.add(realm)
        parts.append(realm + "^")

    # Nothing may be silently dropped: a realm whose parent chain does not reach
    # a rendered root would otherwise vanish from the string.
    missing = (dyn_codes | pre_codes) - rendered
    if missing:
        raise ValueError(
            "CRS would omit realm(s) — check the parents named in "
            "embedded_components: "
            + ", ".join(f"'{to_name(c)}' ({c})" for c in _sort(missing))
        )

    return "".join(parts)


# ── Parse ──────────────────────────────────────────────────────────────────────

def parse(crs: str, strict: bool = True) -> Dict[str, list]:
    """
    Parse a CRS string back into embeddings and coupling pairs.

    Recursive descent, so embedding blocks nest to any depth and a coupling
    block binds to the realm it lexically follows rather than to a guessed
    owner.

    Parameters
    ----------
    crs : the CRS string
    strict : raise CRSSyntaxError on malformed input (unbalanced brackets,
        unknown realm codes, stray characters). Set False for the older
        permissive behaviour, which skips anything it cannot interpret.

    Returns
    -------
    dict with keys:
      'embeddings'      : [[parent_code, child_code], ...]  (all depths, flat)
      'coupling_pairs'  : [[code_a, code_b], ...]  (canonical order, no duplicates)
      'roots'           : [code, ...]  (non-embedded realms in canonical order)
      'prescribed'      : [code, ...]  (realms marked with '^', canonical order)
      'tree'            : nested [{'code': str, 'children': [...]}, ...] in
                          document order — the embedding forest as written
    """
    s = crs.strip()
    n = len(s)
    i = 0

    embeddings: List[List[str]] = []
    coupling_pairs: List[List[str]] = []
    prescribed: List[str] = []
    roots: List[str] = []
    tree: List[dict] = []

    def fail(msg: str) -> None:
        if strict:
            raise CRSSyntaxError(f"{msg} at position {i} in {crs!r}")

    def read_code(pos: int) -> Tuple[str, int]:
        """Read a 1-or-2-char realm code starting at pos."""
        if pos >= n or not s[pos].isupper():
            return "", pos
        code = s[pos]
        pos += 1
        if pos < n and s[pos].islower():
            code += s[pos]
            pos += 1
        return code, pos

    def parse_realm(parent: str | None, depth: int) -> dict | None:
        nonlocal i
        code, i = read_code(i)
        if not code:
            fail("expected a realm code")
            i += 1
            return None
        if code not in CODE_TO_REALM:
            fail(f"unknown realm code '{code}'")
        node = {"code": code, "children": []}

        # A trailing '^' marks the realm as prescribed.
        if i < n and s[i] == "^":
            prescribed.append(code)
            i += 1

        if parent is None:
            roots.append(code)
        else:
            embeddings.append([parent, code])

        # Embedding block — recurse.
        if i < n and s[i] == "[":
            if depth + 1 > MAX_EMBED_DEPTH:
                fail(f"embedding nested deeper than {MAX_EMBED_DEPTH}")
            i += 1  # consume '['
            while i < n and s[i] != "]":
                before = i
                child = parse_realm(code, depth + 1)
                if child:
                    node["children"].append(child)
                if i == before:      # no progress — bail out rather than spin
                    fail("malformed embedding block")
                    i += 1
            if i >= n:
                fail("unclosed '['")
            else:
                i += 1  # consume ']'

        # Coupling block — owned by this realm, whatever the depth.
        if i < n and s[i] == "(":
            i += 1  # consume '('
            while i < n and s[i] != ")":
                if s[i] == ",":
                    i += 1
                    continue
                coupled, i = read_code(i)
                if not coupled:
                    fail("malformed coupling list")
                    i += 1
                    continue
                if coupled not in CODE_TO_REALM:
                    fail(f"unknown realm code '{coupled}' in coupling list")
                pair = _sort([code, coupled])
                if pair not in coupling_pairs:
                    coupling_pairs.append(pair)
            if i >= n:
                fail("unclosed '('")
            else:
                i += 1  # consume ')'

        return node

    while i < n:
        if s[i].isupper():
            node = parse_realm(None, 0)
            if node:
                tree.append(node)
        else:
            fail(f"unexpected character '{s[i]}'")
            i += 1

    return {
        "embeddings":     embeddings,
        "coupling_pairs": coupling_pairs,
        "roots":          _sort(roots),
        "prescribed":     _sort(prescribed),
        "tree":           tree,
    }


# ── Validate ───────────────────────────────────────────────────────────────────

def validate(
    dynamic: List[str],
    embedded: List[List[str]],
    coupling_groups: List[List[str]],
    prescribed: List[str] | None = None,
) -> List[str]:
    """
    Check CRS constraints. Returns a list of error strings (empty = OK).
    """
    errors: List[str] = []

    dyn_codes = {to_code(r) for r in dynamic}
    pre_codes = {to_code(r) for r in (prescribed or [])} - dyn_codes

    # Build parent map
    parent_of: Dict[str, str] = {}
    for pair in embedded:
        if len(pair) < 2:
            errors.append(f"Embedding pair needs [child, parent], got: {pair}")
            continue
        child, parent = to_code(pair[0]), to_code(pair[1])
        if child in parent_of:
            # An exact duplicate pair is harmless — only conflicting parents are
            # an error (the old code reported 'X and X' for repeats).
            if parent_of[child] != parent:
                errors.append(
                    f"'{to_name(child)}' ({child}) is embedded in more than one parent: "
                    f"'{to_name(parent_of[child])}' and '{to_name(parent)}'"
                )
        else:
            parent_of[child] = parent

    # Check embedded realms are subset of dynamic (prescribed realms must not be
    # embedded — they are non-interactive by definition).
    for child, parent in parent_of.items():
        if child in pre_codes:
            errors.append(
                f"Prescribed realm '{to_name(child)}' ({child}) cannot be embedded"
            )
        elif child not in dyn_codes:
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

    # Coupling group realms should be in dynamic (prescribed realms are not
    # interactively coupled, so they must not appear in coupling groups).
    for i, group in enumerate(coupling_groups, 1):
        for r in group:
            code = to_code(r)
            if code in pre_codes:
                errors.append(
                    f"Coupling group {i}: '{r}' is prescribed and cannot be coupled"
                )
            elif code not in dyn_codes:
                errors.append(
                    f"Coupling group {i}: '{r}' is not in dynamic_components"
                )

    # Depth guard — flags a chain too deep to render (also catches cycles that
    # slipped past has_cycle on malformed input).
    def _depth(code: str) -> int:
        d, cur, seen = 0, code, set()
        while cur in parent_of and cur not in seen:
            seen.add(cur)
            cur = parent_of[cur]
            d += 1
        return d

    for child in parent_of:
        if _depth(child) > MAX_EMBED_DEPTH:
            errors.append(
                f"Embedding chain for '{to_name(child)}' ({child}) is deeper "
                f"than {MAX_EMBED_DEPTH}"
            )

    # Round-trip assertion. build() must be able to render every realm, and
    # parse() must recover exactly the embeddings it was given. This is what
    # catches silent structural loss (e.g. nested embeddings being dropped).
    if not errors:
        try:
            s = build(dynamic, embedded, coupling_groups, prescribed=prescribed)
            back = parse(s)
            want = {
                (to_code(p[1]), to_code(p[0]))
                for p in embedded
                if isinstance(p, (list, tuple)) and len(p) >= 2
            }
            got = {(p, c) for p, c in back["embeddings"]}
            if want != got:
                lost = _sort([c for _, c in want - got])
                detail = (
                    " — realm(s) lost: "
                    + ", ".join(f"'{to_name(c)}' ({c})" for c in lost)
                ) if lost else ""
                errors.append(
                    f"CRS '{s}' does not round-trip to embedded_components{detail}"
                )
        except (ValueError, CRSSyntaxError) as exc:
            errors.append(str(exc))

    return errors


# ── Convenience round-trip helpers ─────────────────────────────────────────────

def from_model_data(data: dict) -> str:
    """
    Build a CRS string directly from a model JSON-LD dict.

    Reads: dynamic_components, prescribed_components, embedded_components,
    coupled_components (or legacy coupling_groups).
    """
    dynamic = data.get("dynamic_components", [])
    prescribed = data.get("prescribed_components", [])
    embedded = data.get("embedded_components", [])
    coupling_groups = data.get("coupling_groups", []) or data.get("coupled_components", [])
    return build(dynamic, embedded, coupling_groups, prescribed=prescribed)


def to_model_fields(crs: str) -> Dict[str, list]:
    """
    Invert a CRS string into the fields used in a model JSON-LD dict.

    Returns dict with 'embedded_components' and 'coupling_groups'.
    embedded_components: [[child_name, parent_name], ...]
    coupling_groups: one group containing all coupled realm names
    """
    parsed = parse(crs)
    embedded = [[to_name(c), to_name(p)] for p, c in parsed["embeddings"]]

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
