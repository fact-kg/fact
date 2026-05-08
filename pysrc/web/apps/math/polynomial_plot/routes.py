import sys
import math
import operator
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

import yaml
import numpy as np
from kg import Kg
from fact import Fact

router = APIRouter(prefix="/apps/math/polynomial_plot")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

POLYNOMIALS = {
    "linear": {
        "path": "math/algebra/real/singlevar/polynomial/linear",
        "coeffs": ["a", "b"],
        "defaults": {"a": "2", "b": "-1"},
        "root_paths": ["math/algebra/real/singlevar/polynomial/linear/root"],
    },
    "quadratic": {
        "path": "math/algebra/real/singlevar/polynomial/quadratic",
        "coeffs": ["a", "b", "c"],
        "defaults": {"a": "1", "b": "0", "c": "-1"},
        "root_paths": [
            "math/algebra/real/singlevar/polynomial/quadratic/root_plus",
            "math/algebra/real/singlevar/polynomial/quadratic/root_minus",
        ],
    },
    "cubic": {
        "path": "math/algebra/real/singlevar/polynomial/cubic",
        "coeffs": ["a", "b", "c", "d"],
        "defaults": {"a": "1", "b": "0", "c": "-3", "d": "0"},
        "root_paths": None,
    },
    "n-degree": {
        "path": "math/algebra/real/singlevar/polynomial/n_degree",
        "coeffs_list": True,
        "defaults_list": "1, 0, -3, 0, 1",
        "root_paths": None,
    },
}

SYMBOL_TO_FN = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "**": operator.pow,
    "==": operator.eq,
    "<": operator.lt,
    "&": operator.and_,
    "neg": operator.neg,
    "math.sqrt": math.sqrt,
}

_op_cache = {}


def resolve_operation(op_path, kg, ROOTS):
    if op_path in _op_cache:
        return _op_cache[op_path]
    info = load_fact_info(kg, op_path, ROOTS)
    if info is None:
        return None
    impl_type = info.get("has", {}).get("python_impl", {}).get("type", "")
    if not impl_type:
        return None
    impl_info = load_fact_info(kg, impl_type, ROOTS)
    if impl_info is None:
        return None
    val_as = impl_info.get("val_as", {})
    symbol = val_as.get("computer/sw/lang/python/operator", {}).get("symbol", "")
    if not symbol:
        symbol = val_as.get("computer/sw/lang/python/function", {}).get("name", "")
    fn = SYMBOL_TO_FN.get(symbol)
    _op_cache[op_path] = fn
    return fn


def load_fact_info(kg, path, ROOTS):
    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)
    if not has_fact or kg.load(path) != 0:
        return None
    fact = Fact(kg, path)
    if fact.construct() != 0:
        return None
    return kg.get_fact(path).get("info", {})


def evaluate(node, variables, kg, ROOTS):
    if isinstance(node, str):
        if node in variables:
            return variables[node]
        return float(node)
    if isinstance(node, (int, float)):
        return float(node)
    if isinstance(node, dict):
        op_path = next(iter(node))
        if op_path == "math/expression/conditional":
            branches = node[op_path]
            cond = evaluate(branches["condition"], variables, kg, ROOTS)
            if cond:
                return evaluate(branches["then"], variables, kg, ROOTS)
            else:
                return evaluate(branches["else"], variables, kg, ROOTS)
        if op_path == "math/algebra/expression/indexed/sum":
            node_data = node[op_path]
            index_name = node_data["index"]
            from_val = int(node_data["from"])
            to_length_key = node_data.get("to_length")
            if to_length_key:
                to_val = len(variables[to_length_key]) - 1
            else:
                to_val = int(node_data["to"])
            body = node_data["body"]
            result = 0
            for i in range(from_val, to_val + 1):
                variables[index_name] = i
                result = result + evaluate(body, variables, kg, ROOTS)
            del variables[index_name]
            return result
        if op_path == "math/expression/indexed/element_at":
            node_data = node[op_path]
            collection = variables[node_data["collection"]]
            idx = int(variables[node_data["at"]])
            return collection[idx]
        operands = node[op_path]
        op_fn = resolve_operation(op_path, kg, ROOTS)
        if op_fn is None:
            raise ValueError(f"Unknown operation: {op_path}")
        vals = [evaluate(o, variables, kg, ROOTS) for o in operands]
        if len(vals) == 1:
            return op_fn(vals[0])
        return op_fn(vals[0], vals[1])
    raise ValueError(f"Cannot evaluate: {node}")


_latex_cache = {}


def resolve_latex(op_path, kg, ROOTS):
    if op_path in _latex_cache:
        return _latex_cache[op_path]
    info = load_fact_info(kg, op_path, ROOTS)
    if info is None:
        return None, "infix"
    impl_type = info.get("has", {}).get("latex_impl", {}).get("type", "")
    if not impl_type:
        return None, "infix"
    impl_info = load_fact_info(kg, impl_type, ROOTS)
    if impl_info is None:
        return None, "infix"
    val_as = impl_info.get("val_as", {}).get("computer/sw/lang/latex/operator", {})
    symbol = val_as.get("symbol", "")
    style = val_as.get("style", "infix")
    _latex_cache[op_path] = (symbol, style)
    return symbol, style


def to_latex(node, kg, ROOTS):
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float)):
        return str(node)
    if isinstance(node, dict):
        op_path = next(iter(node))
        if op_path == "math/expression/conditional":
            branches = node[op_path]
            cond = to_latex(branches["condition"], kg, ROOTS)
            then = to_latex(branches["then"], kg, ROOTS)
            els = to_latex(branches["else"], kg, ROOTS)
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
            body = to_latex(node_data["body"], kg, ROOTS)
            return r"\sum_{" + idx + "=" + from_val + "}^{" + to_str + "} " + body
        if op_path == "math/expression/indexed/element_at":
            node_data = node[op_path]
            return node_data["collection"] + "_{" + node_data["at"] + "}"
        operands = node[op_path]
        symbol, style = resolve_latex(op_path, kg, ROOTS)
        parts = [to_latex(o, kg, ROOTS) for o in operands]
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


def check_undefined(info, variables, kg, ROOTS):
    has = info.get("has", {})
    for attr, val in has.items():
        if val.get("type") == "math/function/domain/undefined":
            constraint_yaml = val.get("val", "")
            if constraint_yaml:
                tree = yaml.safe_load(constraint_yaml)
                try:
                    result = evaluate(tree, variables, kg, ROOTS)
                    if result:
                        return attr
                except Exception:
                    pass
    return None


def find_roots_from_facts(root_paths, variables, kg, ROOTS):
    roots = []
    undefined_reason = None
    for root_path in root_paths:
        info = load_fact_info(kg, root_path, ROOTS)
        if info is None:
            continue
        reason = check_undefined(info, variables, kg, ROOTS)
        if reason:
            undefined_reason = reason
            continue
        expr_yaml = ""
        for attr, val in info.get("has", {}).items():
            if val.get("type") == "math/expression":
                expr_yaml = val.get("val_as", {}).get("math/expression", {}).get("expression_yaml", "")
                break
        if not expr_yaml:
            continue
        tree = yaml.safe_load(expr_yaml)
        try:
            val = evaluate(tree, variables, kg, ROOTS)
            roots.append(val)
        except Exception:
            pass
    return roots, undefined_reason


def find_roots_numpy(coefficients):
    if all(c == 0 for c in coefficients):
        return [], "undefined_zero_polynomial"
    while len(coefficients) > 1 and coefficients[0] == 0:
        coefficients = coefficients[1:]
    if len(coefficients) <= 1:
        return [], None
    all_roots = np.roots(coefficients)
    real_roots = [float(r.real) for r in all_roots if abs(r.imag) < 1e-10]
    return real_roots, None


@router.get("/")
def polynomial_plot(request: Request):
    from pysrc.web.server import kg, ROOTS

    degree = request.query_params.get("degree", "quadratic")
    if degree not in POLYNOMIALS:
        degree = "quadratic"
    poly = POLYNOMIALS[degree]

    info = load_fact_info(kg, poly["path"], ROOTS)

    expression_str = ""
    expression_yaml_str = ""
    expression_latex = ""
    expression_tree = None
    inputs = {}

    if info:
        has = info.get("has", {})
        for attr, val in has.items():
            t = val.get("type", "")
            if t == "math/expression":
                expr_as = val.get("val_as", {}).get("math/expression", {})
                expression_str = expr_as.get("expression_str", "")
                expression_yaml_str = expr_as.get("expression_yaml", "")
                if expression_yaml_str:
                    expression_tree = yaml.safe_load(expression_yaml_str)
                    expression_latex = "f(x) = " + to_latex(expression_tree, kg, ROOTS)
                break
        for attr, val in has.items():
            t = val.get("type", "")
            if t in ("math/variable", "math/constant"):
                inputs[attr] = t

    coeffs = {}
    coeffs_list_str = ""
    if poly.get("coeffs_list"):
        coeffs_list_str = request.query_params.get("coefficients", poly["defaults_list"])
        coeff_list = [float(c.strip()) for c in coeffs_list_str.split(",")]
        coeffs = {"coefficients": coeff_list}
    else:
        for name in poly["coeffs"]:
            coeffs[name] = float(request.query_params.get(name, poly["defaults"][name]))
        coeff_list = [coeffs[name] for name in poly["coeffs"]]

    if poly["root_paths"]:
        roots, undefined_reason = find_roots_from_facts(poly["root_paths"], coeffs, kg, ROOTS)
    else:
        if poly.get("coeffs_list"):
            numpy_coeffs = list(reversed(coeff_list))
        else:
            numpy_coeffs = coeff_list
        roots, undefined_reason = find_roots_numpy(numpy_coeffs)

    roots = [round(r, 6) for r in sorted(roots)]

    if degree == "quadratic" and coeff_list[0] != 0:
        center = -coeff_list[1] / (2 * coeff_list[0])
    else:
        center = 0
    if roots:
        x_center = (min(roots) + max(roots)) / 2
        spread = (max(roots) - min(roots)) * 1.5
        spread = max(spread, 2)
    else:
        x_center = center
        spread = 10
    default_xmin = x_center - spread
    default_xmax = x_center + spread

    x_min = float(request.query_params.get("xmin", str(default_xmin)))
    x_max = float(request.query_params.get("xmax", str(default_xmax)))

    n_points = 200
    step = (x_max - x_min) / n_points
    points = []
    if expression_tree:
        for i in range(n_points + 1):
            x = x_min + i * step
            variables = {"x": x}
            variables.update(coeffs)
            try:
                y = evaluate(expression_tree, variables, kg, ROOTS)
                #np_y = np.polyval(list(reversed(coeff_list)), x)
                #print(f"  x={x:.2f} tree_y={y:.6f} np_y={np_y:.6f}")
                points.append({"x": round(x, 6), "y": round(y, 6)})
            except Exception:
                pass

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({
            "expression": expression_str,
            "coeffs": coeffs,
            "x_min": x_min, "x_max": x_max,
            "points": points,
            "roots": roots,
            "undefined_reason": undefined_reason,
        })

    return templates.TemplateResponse(request, "polynomial_plot.html", {
        "expression_str": expression_str,
        "expression_yaml_str": expression_yaml_str,
        "expression_latex": expression_latex,
        "degree": degree,
        "degrees": list(POLYNOMIALS.keys()),
        "coeffs": coeffs,
        "coeffs_list": poly.get("coeffs_list", False),
        "coeffs_list_str": coeffs_list_str,
        "x_min": x_min, "x_max": x_max,
        "points": points,
        "roots": roots,
        "undefined_reason": undefined_reason,
        "inputs": inputs,
    })
