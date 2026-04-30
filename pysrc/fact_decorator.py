def fact(fact_path, field_name=None):
    """Marker connecting a code element to its fact description."""
    def decorator(obj):
        obj._fact_path = fact_path
        obj._fact_field = field_name
        return obj
    return decorator

def fact_link(fact_path, field_name=None):
    """Metadata marker for Annotated type hints."""
    return ("fact_link", fact_path, field_name)
