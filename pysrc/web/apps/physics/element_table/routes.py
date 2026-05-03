import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from kg import Kg
from fact import Fact

router = APIRouter(prefix="/apps/physics/element_table")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

ELEMENT_DIR = "physics/atom/element"
ELEMENT_TYPE = "physics/atom/element"


def load_fact_info(kg, path, ROOTS):
    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)
    if not has_fact or kg.load(path) != 0:
        return None
    fact = Fact(kg, path)
    if fact.construct() != 0:
        return None
    return kg.get_fact(path).get("info", {})


def collect_values(info):
    values = {}
    for type_name, attrs in info.get("val_as", {}).items():
        for attr, val in attrs.items():
            values[attr] = val
    return values


def load_elements():
    from pysrc.web.server import kg, ROOTS

    elements = []
    for root in ROOTS:
        elem_dir = root / ELEMENT_DIR
        if not elem_dir.is_dir():
            continue
        for f in elem_dir.iterdir():
            if f.suffix != ".yaml":
                continue
            fact_path = ELEMENT_DIR + "/" + f.stem
            info = load_fact_info(kg, fact_path, ROOTS)
            if info is None:
                continue
            if ELEMENT_TYPE not in info.get("type", []):
                continue
            values = collect_values(info)
            if values:
                elements.append({
                    "name": f.stem,
                    "path": fact_path,
                    "props": values,
                })
    elements.sort(key=lambda e: e["props"].get("atomic_number", 0))
    return elements


@router.get("/")
def element_table(request: Request):
    view = request.query_params.get("view", "mendeleev")
    elements = load_elements()

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"view": view, "elements": [
            {"name": e["name"], "path": e["path"], "values": e["props"]}
            for e in elements
        ]})

    return templates.TemplateResponse(request, "element_table.html", {
        "view": view,
        "elements": elements,
    })
