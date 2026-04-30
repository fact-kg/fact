def fact(fact_path, field_name=None):
    """Marker connecting a code element to its fact description."""
    def decorator(obj):
        obj._fact_path = fact_path
        obj._fact_field = field_name
        return obj
    return decorator
