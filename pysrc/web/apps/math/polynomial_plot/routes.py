import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

import yaml
import numpy as np
from expression import ExpressionEvaluator, ExpressionLatex, load_fact_info, extract_expression

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


def check_undefined(info, variables, evaluator):
    has = info.get("has", {})
    for attr, val in has.items():
        if val.get("type") == "math/function/domain/undefined":
            constraint_yaml = val.get("val", "")
            if constraint_yaml:
                tree = yaml.safe_load(constraint_yaml)
                try:
                    result = evaluator.evaluate(tree, variables)
                    if result:
                        return attr
                except Exception:
                    pass
    return None


def find_roots_from_facts(root_paths, variables, kg, evaluator):
    roots = []
    undefined_reason = None
    for root_path in root_paths:
        info = load_fact_info(kg, root_path)
        if info is None:
            continue
        reason = check_undefined(info, variables, evaluator)
        if reason:
            undefined_reason = reason
            continue
        expr = extract_expression(info)
        if expr is None or expr["tree"] is None:
            continue
        try:
            val = evaluator.evaluate(expr["tree"], variables)
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

    evaluator = ExpressionEvaluator(kg)
    latex_renderer = ExpressionLatex(kg)

    degree = request.query_params.get("degree", "quadratic")
    if degree not in POLYNOMIALS:
        degree = "quadratic"
    poly = POLYNOMIALS[degree]

    info = load_fact_info(kg, poly["path"])

    expression_str = ""
    expression_yaml_str = ""
    expression_latex = ""
    expression_tree = None
    inputs = {}

    if info:
        expr = extract_expression(info)
        if expr:
            expression_str = expr["str"]
            expression_yaml_str = expr["yaml"]
            expression_tree = expr["tree"]
            if expression_tree:
                expression_latex = "f(x) = " + latex_renderer.to_latex(expression_tree)
        has = info.get("has", {})
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
        roots, undefined_reason = find_roots_from_facts(poly["root_paths"], coeffs, kg, evaluator)
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
                y = evaluator.evaluate(expression_tree, variables)
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
