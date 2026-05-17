"""Parse rule patterns into structured conditions.

Pattern syntax:
  ?X part ?Y           — fact ?X has part tag with value ?Y
  ?X is ?Y             — fact ?X is type ?Y
  ?X has ?prop         — fact ?X has property ?prop (existence check)
  ?X has ?prop ?val    — fact ?X has property ?prop with value ?val

Variables start with ?. Constants are literal strings.
AND joins multiple conditions.
"""


def is_variable(token):
    """Check if a token is a variable (starts with ?)."""
    return isinstance(token, str) and token.startswith("?")


def parse_condition(text):
    """Parse a single condition string into a structured dict."""
    tokens = text.strip().split()

    if len(tokens) == 3 and tokens[1] == "part":
        return {"type": "part", "subject": tokens[0], "object": tokens[2]}

    if len(tokens) == 3 and tokens[1] == "is":
        return {"type": "is", "subject": tokens[0], "object": tokens[2]}

    if len(tokens) == 3 and tokens[1] == "has":
        return {"type": "has_exists", "subject": tokens[0], "property": tokens[2]}

    if len(tokens) == 4 and tokens[1] == "has":
        return {"type": "has_value", "subject": tokens[0],
                "property": tokens[2], "value": tokens[3]}

    return {"type": "unknown", "raw": text}


def parse_pattern(text):
    """Parse a pattern string with AND-joined conditions."""
    parts = text.split(" AND ")
    return [parse_condition(p) for p in parts]


def parse_rule(when_text, then_text):
    """Parse a complete rule into conditions and conclusion.

    Returns (conditions_list, conclusion_dict).
    """
    conditions = parse_pattern(when_text)
    conclusion = parse_condition(then_text)
    return conditions, conclusion
