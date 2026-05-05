import sys
import math
import operator
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

import yaml
from kg import Kg
from fact import Fact

router = APIRouter(prefix="/apps/math/polynomial_plot")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

QUADRATIC_PATH = "math/algebra/real/singlevar/polynomial/quadratic"

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
        operands = node[op_path]
        op_fn = resolve_operation(op_path, kg, ROOTS)
        if op_fn is None:
            raise ValueError(f"Unknown operation: {op_path}")
        vals = [evaluate(o, variables, kg, ROOTS) for o in operands]
        if len(vals) == 1:
            return op_fn(vals[0])
        return op_fn(vals[0], vals[1])
    raise ValueError(f"Cannot evaluate: {node}")


OP_TO_LATEX = {
    "math/algebra/operation/add": ("+", "infix"),
    "math/algebra/operation/subtract": ("-", "infix"),
    "math/algebra/operation/multiply": (r"\cdot ", "infix"),
    "math/algebra/operation/divide": (None, "frac"),
    "math/algebra/operation/power": (None, "power"),
    "math/algebra/operation/sqrt": (None, "sqrt"),
    "math/algebra/operation/negate": (None, "negate"),
    "math/algebra/operation/equal": ("=", "infix"),
    "math/algebra/operation/less_than": ("<", "infix"),
    "math/algebra/operation/and": (r"\land ", "infix"),
}


def to_latex(node):
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float)):
        return str(node)
    if isinstance(node, dict):
        op_path = next(iter(node))
        if op_path == "math/expression/conditional":
            branches = node[op_path]
            cond = to_latex(branches["condition"])
            then = to_latex(branches["then"])
            els = to_latex(branches["else"])
            return r"\begin{cases} " + then + r" & \text{if } " + cond + r" \\ " + els + r" & \text{otherwise} \end{cases}"
        operands = node[op_path]
        info = OP_TO_LATEX.get(op_path, (op_path, "infix"))
        symbol, style = info
        parts = [to_latex(o) for o in operands]
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


ROOT_PLUS_PATH = "math/algebra/real/singlevar/polynomial/quadratic/root_plus"
ROOT_MINUS_PATH = "math/algebra/real/singlevar/polynomial/quadratic/root_minus"


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


def find_roots(a, b, c, kg, ROOTS):
    roots = []
    undefined_reason = None
    variables = {"a": a, "b": b, "c": c}
    for root_path in (ROOT_PLUS_PATH, ROOT_MINUS_PATH):
        info = load_fact_info(kg, root_path, ROOTS)
        if info is None:
            continue
        reason = check_undefined(info, variables, kg, ROOTS)
        if reason:
            undefined_reason = reason
            continue
        expr_yaml = info.get("has", {}).get("expression_yaml", {}).get("val", "")
        if not expr_yaml:
            continue
        tree = yaml.safe_load(expr_yaml)
        try:
            val = evaluate(tree, variables, kg, ROOTS)
            roots.append(val)
        except Exception:
            pass
    return roots, undefined_reason


@router.get("/")
def polynomial_plot(request: Request):
    from pysrc.web.server import kg, ROOTS

    info = load_fact_info(kg, QUADRATIC_PATH, ROOTS)

    expression_str = ""
    expression_yaml_str = ""
    expression_latex = ""
    expression_tree = None
    inputs = {}

    if info:
        has = info.get("has", {})
        expr_str_info = has.get("expression_str", {})
        expression_str = expr_str_info.get("val", "")
        expr_yaml_info = has.get("expression_yaml", {})
        expression_yaml_str = expr_yaml_info.get("val", "")
        if expression_yaml_str:
            expression_tree = yaml.safe_load(expression_yaml_str)
            expression_latex = "f(x) = " + to_latex(expression_tree)
        for attr, val in has.items():
            t = val.get("type", "")
            if t in ("math/variable", "math/constant"):
                inputs[attr] = t

    a = float(request.query_params.get("a", "1"))
    b = float(request.query_params.get("b", "0"))
    c = float(request.query_params.get("c", "-1"))

    roots, undefined_reason = find_roots(a, b, c, kg, ROOTS)
    roots = [round(r, 6) for r in sorted(roots)]

    vertex_x = -b / (2 * a) if a != 0 else 0
    if roots:
        x_center = (min(roots) + max(roots)) / 2
        spread = (max(roots) - min(roots)) * 1.5
        spread = max(spread, 2)
    else:
        x_center = vertex_x
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
            try:
                y = evaluate(expression_tree, {"x": x, "a": a, "b": b, "c": c}, kg, ROOTS)
                points.append({"x": round(x, 6), "y": round(y, 6)})
            except Exception:
                pass

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({
            "expression": expression_str,
            "a": a, "b": b, "c": c,
            "x_min": x_min, "x_max": x_max,
            "points": points,
            "roots": roots,
            "undefined_reason": undefined_reason,
        })

    return templates.TemplateResponse(request, "polynomial_plot.html", {
        "expression_str": expression_str,
        "expression_yaml_str": expression_yaml_str,
        "expression_latex": expression_latex,
        "a": a, "b": b, "c": c,
        "x_min": x_min, "x_max": x_max,
        "points": points,
        "roots": roots,
        "undefined_reason": undefined_reason,
        "inputs": inputs,
    })
