"""Match rule conditions against the knowledge graph.

A binding is a dict mapping variable names to values:
  {"?X": "luna", "?Y": "earth"}

Matching produces a list of all valid bindings that satisfy
the conditions. Each condition filters and extends bindings
from the previous condition (AND semantics).
"""

from expression import load_fact_info

MAX_BINDING_VARS = 20


def _resolve(token, binding):
    """Resolve a token — return bound value if variable, else literal."""
    if token.startswith("?") and token in binding:
        return binding[token]
    return None if token.startswith("?") else token


def _bind(token, value, binding):
    """Try to bind a variable to a value.

    Returns new binding dict or None on conflict.
    """
    if not token.startswith("?"):
        return binding if token == value else None
    if token in binding:
        return binding if binding[token] == value else None
    assert len(binding) < MAX_BINDING_VARS, \
        f"Binding exceeded {MAX_BINDING_VARS} variables — possible runaway match"
    new = dict(binding)
    new[token] = value
    return new


def _all_fact_paths(kg):
    """Get all loaded fact paths from the KG."""
    return list(kg.get_dict().keys())


# --- condition matchers ---

def _match_part(condition, kg, binding):
    subject = condition["subject"]
    obj = condition["object"]
    results = []
    resolved_subject = _resolve(subject, binding)

    if resolved_subject:
        info = load_fact_info(kg, resolved_subject)
        if info is None:
            return []
        for part_val in info.get("part", []):
            new_binding = _bind(subject, resolved_subject, binding)
            if new_binding is None:
                continue
            new_binding = _bind(obj, part_val, new_binding)
            if new_binding is not None:
                results.append(new_binding)
    else:
        for fp in _all_fact_paths(kg):
            info = kg.get_fact(fp).get("info")
            if info is None:
                continue
            for part_val in info.get("part", []):
                new_binding = _bind(subject, fp, binding)
                if new_binding is None:
                    continue
                new_binding = _bind(obj, part_val, new_binding)
                if new_binding is not None:
                    results.append(new_binding)

    return results


def _match_is(condition, kg, binding):
    subject = condition["subject"]
    obj = condition["object"]
    results = []
    resolved_subject = _resolve(subject, binding)

    if resolved_subject:
        info = load_fact_info(kg, resolved_subject)
        if info is None:
            return []
        for type_val in info.get("type", []):
            new_binding = _bind(subject, resolved_subject, binding)
            if new_binding is None:
                continue
            new_binding = _bind(obj, type_val, new_binding)
            if new_binding is not None:
                results.append(new_binding)
    else:
        for fp in _all_fact_paths(kg):
            info = kg.get_fact(fp).get("info")
            if info is None:
                continue
            for type_val in info.get("type", []):
                new_binding = _bind(subject, fp, binding)
                if new_binding is None:
                    continue
                new_binding = _bind(obj, type_val, new_binding)
                if new_binding is not None:
                    results.append(new_binding)

    return results


def _match_has_exists(condition, kg, binding):
    subject = condition["subject"]
    prop = condition["property"]
    results = []
    resolved_subject = _resolve(subject, binding)
    resolved_prop = _resolve(prop, binding)

    if resolved_subject:
        info = load_fact_info(kg, resolved_subject)
        if info is None:
            return []
        has = info.get("has", {})
        if resolved_prop:
            if resolved_prop in has:
                results.append(dict(binding))
        else:
            for attr in has:
                new_binding = _bind(prop, attr, binding)
                if new_binding is not None:
                    new_binding = _bind(subject, resolved_subject, new_binding)
                    if new_binding is not None:
                        results.append(new_binding)
    return results


def _match_has_value(condition, kg, binding):
    subject = condition["subject"]
    prop = condition["property"]
    val = condition["value"]
    results = []
    resolved_subject = _resolve(subject, binding)
    resolved_prop = _resolve(prop, binding)

    if resolved_subject:
        info = load_fact_info(kg, resolved_subject)
        if info is None:
            return []
        has = info.get("has", {})
        if resolved_prop:
            if resolved_prop in has:
                actual = has[resolved_prop].get("val", "")
                new_binding = _bind(val, str(actual), binding)
                if new_binding is not None:
                    results.append(new_binding)
        else:
            for attr, attr_val in has.items():
                new_binding = _bind(prop, attr, binding)
                if new_binding is None:
                    continue
                actual = attr_val.get("val", "")
                new_binding = _bind(val, str(actual), new_binding)
                if new_binding is not None:
                    new_binding = _bind(subject, resolved_subject, new_binding)
                    if new_binding is not None:
                        results.append(new_binding)
    return results


# --- condition dispatch ---

CONDITION_MATCHERS = {
    "part": _match_part,
    "is": _match_is,
    "has_exists": _match_has_exists,
    "has_value": _match_has_value,
}


def match_condition(condition, kg, binding):
    """Match a single condition against the KG."""
    matcher = CONDITION_MATCHERS.get(condition["type"])
    if matcher is None:
        return []
    return matcher(condition, kg, binding)


def match_conditions(conditions, kg, initial_binding=None):
    """Match AND-joined conditions. Returns all satisfying bindings."""
    bindings = [initial_binding or {}]

    for condition in conditions:
        new_bindings = []
        for binding in bindings:
            new_bindings.extend(match_condition(condition, kg, binding))
        bindings = new_bindings
        if not bindings:
            break

    return bindings
