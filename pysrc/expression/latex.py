from expression.helpers import load_fact_info


class ExpressionLatex:
    def __init__(self, kg):
        self.kg = kg
        self._cache = {}

    def resolve_latex(self, op_path):
        if op_path in self._cache:
            return self._cache[op_path]
        info = load_fact_info(self.kg, op_path)
        if info is None:
            return None, "infix"
        impl_type = info.get("has", {}).get("latex_impl", {}).get("type", "")
        if not impl_type:
            return None, "infix"
        impl_info = load_fact_info(self.kg, impl_type)
        if impl_info is None:
            return None, "infix"
        val_as = impl_info.get("val_as", {}).get("computer/sw/lang/latex/operator", {})
        symbol = val_as.get("symbol", "")
        style = val_as.get("style", "infix")
        self._cache[op_path] = (symbol, style)
        return symbol, style

    def to_latex(self, node):
        if isinstance(node, str):
            return node
        if isinstance(node, (int, float)):
            return str(node)
        if isinstance(node, dict):
            op_path = next(iter(node))
            if op_path == "math/expression/conditional":
                branches = node[op_path]
                cond = self.to_latex(branches["condition"])
                then = self.to_latex(branches["then"])
                els = self.to_latex(branches["else"])
                return r"\begin{cases} " + then + r" & \text{if } " + cond + r" \\ " + els + r" & \text{otherwise} \end{cases}"
            if op_path == "math/algebra/expression/indexed/sum":
                node_data = node[op_path]
                idx = node_data["index"]
                from_val = str(node_data["from"])
                to_key = node_data.get("to_length")
                if to_key:
                    to_str = r"\text{len}(" + to_key + ") - 1"
                else:
                    to_str = str(node_data["to"])
                body = self.to_latex(node_data["body"])
                return r"\sum_{" + idx + "=" + from_val + "}^{" + to_str + "} " + body
            if op_path == "math/expression/indexed/element_at":
                node_data = node[op_path]
                return node_data["collection"] + "_{" + node_data["at"] + "}"
            operands = node[op_path]
            symbol, style = self.resolve_latex(op_path)
            parts = [self.to_latex(o) for o in operands]
            if style == "frac":
                return r"\frac{" + parts[0] + "}{" + parts[1] + "}"
            if style == "power":
                return "{" + parts[0] + "}^{" + parts[1] + "}"
            if style == "sqrt":
                return r"\sqrt{" + parts[0] + "}"
            if style == "negate":
                return "-" + parts[0]
            return parts[0] + " " + symbol + " " + parts[1]
        return str(node)
