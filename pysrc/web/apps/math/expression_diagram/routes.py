import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from expression import load_fact_info
from expression.helpers import extract_all_expressions
from diagram import TreeLayout, to_json

router = APIRouter(prefix="/apps/math/expression_diagram")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def tree_children(node):
    if isinstance(node, dict):
        key = next(iter(node))
        val = node[key]
        if key == "math/expression/conditional":
            return [val["condition"], val["then"], val["else"]]
        if key in ("math/algebra/expression/indexed/sum",):
            return [val["body"]]
        if key == "math/expression/indexed/element_at":
            return []
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            return [val]
    return []


def tree_label(node):
    if isinstance(node, dict):
        key = next(iter(node))
        if key == "math/expression/conditional":
            return "if-then-else"
        if key == "math/expression/indexed/element_at":
            val = node[key]
            return f"{val['collection']}[{val['at']}]"
        if "expression/indexed/sum" in key:
            val = node[key]
            idx = val.get("index", "i")
            frm = val.get("from", 0)
            to = val.get("to_length", val.get("to", "?"))
            return f"Σ {idx}={frm}..{to}"
        name = key.rsplit("/", 1)[-1]
        return name
    return str(node)


def tree_type(node):
    if isinstance(node, dict):
        key = next(iter(node))
        if "operation" in key:
            return "operation"
        if "expression" in key:
            return "expression"
        return "node"
    if isinstance(node, (int, float)):
        return "number"
    return "variable"


def build_diagram(tree):
    layout = TreeLayout(node_width=110, node_height=36, h_spacing=15, v_spacing=50)
    return layout.layout(tree, tree_children, tree_label, tree_type)


@router.get("/")
def expression_diagram(request: Request):
    from pysrc.web.server import kg, ROOTS

    fact_path = request.query_params.get("fact", "")
    selected_expr = request.query_params.get("expr", "")

    info = None
    expressions = {}
    diagram_data = None
    expression_str = ""
    error = ""

    if fact_path:
        info = load_fact_info(kg, fact_path)
        if info is None:
            error = f"Fact not found: {fact_path}"
        else:
            expressions = extract_all_expressions(info)
            if not expressions:
                error = f"No expressions found for: {fact_path}"
            else:
                if not selected_expr or selected_expr not in expressions:
                    selected_expr = next(iter(expressions))
                expr = expressions[selected_expr]
                expression_str = expr["str"]
                diagram = build_diagram(expr["tree"])
                diagram_data = to_json(diagram)

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({
            "fact": fact_path,
            "expressions": list(expressions.keys()),
            "selected": selected_expr,
            "diagram": diagram_data,
            "error": error,
        })

    return templates.TemplateResponse(request, "expression_diagram.html", {
        "fact_path": fact_path,
        "expressions": expressions,
        "selected_expr": selected_expr,
        "expression_str": expression_str,
        "diagram_data": diagram_data,
        "error": error,
    })
