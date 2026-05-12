import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from expression import load_fact_info
from diagram import FlowLayout, to_json

router = APIRouter(prefix="/apps/computer/algorithm_viewer")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def extract_algorithm(info):
    has = info.get("has", {})
    description = ""
    desc_info = has.get("description", {})
    if desc_info:
        description = desc_info.get("val", "")

    steps = {}
    for attr, val in has.items():
        if attr.startswith("step_"):
            steps[attr] = val

    first_step = None
    for name in ["step_init", "step_start", "step_evaluate"]:
        if name in steps:
            first_step = name
            break
    if first_step is None and steps:
        first_step = next(iter(steps))

    return description, steps, first_step


@router.get("/")
def algorithm_viewer(request: Request):
    from pysrc.web.server import kg, ROOTS

    fact_path = request.query_params.get("fact", "")

    info = None
    description = ""
    steps = {}
    diagram_data = None
    error = ""

    if fact_path:
        info = load_fact_info(kg, fact_path)
        if info is None:
            error = f"Fact not found: {fact_path}"
        else:
            types = info.get("type", [])
            if "computer/algorithm" not in types:
                error = f"Not an algorithm: {fact_path}"
            else:
                description, steps, first_step = extract_algorithm(info)
                if not steps:
                    error = f"No steps found in: {fact_path}"
                elif first_step:
                    layout = FlowLayout()
                    diagram = layout.layout(steps, first_step)
                    diagram_data = to_json(diagram)

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({
            "fact": fact_path,
            "description": description,
            "diagram": diagram_data,
            "error": error,
        })

    return templates.TemplateResponse(request, "algorithm_viewer.html", {
        "fact_path": fact_path,
        "description": description,
        "steps": steps,
        "diagram_data": diagram_data,
        "error": error,
    })
