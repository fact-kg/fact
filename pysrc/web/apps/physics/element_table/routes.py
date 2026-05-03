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


BLOCK_OFFSET = {'f': 0, 'd': 14, 'p': 24, 's': 30}


def load_elements():
    from pysrc.web.server import kg, ROOTS

    subshell_cache = {}

    def get_subshell_info(subshell_path):
        if subshell_path in subshell_cache:
            return subshell_cache[subshell_path]
        info = load_fact_info(kg, subshell_path, ROOTS)
        if info is None:
            return None
        vals = collect_values(info)
        subshell_cache[subshell_path] = vals
        return vals

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
            if not values:
                continue
            elem = {
                "name": f.stem,
                "path": fact_path,
                "props": values,
            }
            has = info.get("has", {})
            vs = has.get("valence_subshell", {})
            vs_type = vs.get("type", "")
            if vs_type and vs_type not in ("str", "num", "list"):
                ss = get_subshell_info(vs_type)
                if ss:
                    elem["subshell_n"] = ss.get("principal_quantum_number", 0)
                    elem["subshell_block"] = ss.get("block", "")
            elements.append(elem)

    elements.sort(key=lambda e: e["props"].get("atomic_number", 0))

    by_subshell = {}
    for e in elements:
        key = (e.get("subshell_n", 0), e.get("subshell_block", ""))
        by_subshell.setdefault(key, []).append(e)

    for e in elements:
        n = e.get("subshell_n", 0)
        block = e.get("subshell_block", "")
        if not block or n == 0:
            continue
        group = by_subshell.get((n, block), [])
        pos_in_subshell = group.index(e)
        row = BLOCK_OFFSET.get(block, 0) + pos_in_subshell + 1
        col = n
        e["adomah_row"] = row
        e["adomah_col"] = col

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
