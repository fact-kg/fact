def fact(fact_path):
    """Marker connecting a code element to its fact description."""
    def decorator(obj):
        obj._fact_path = fact_path
        return obj
    return decorator
