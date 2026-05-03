import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from kg import Kg
from fact import Fact

router = APIRouter(prefix="/apps/physics/unit_converter")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

UNIT_DIRS = ["physics/unit/si", "physics/unit/imperial"]


def load_fact_info(kg, path, ROOTS):
    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)
    if not has_fact or kg.load(path) != 0:
        return None
    fact = Fact(kg, path)
    if fact.construct() != 0:
        return None
    return kg.get_fact(path).get("info", {})


def load_units():
    from pysrc.web.server import kg, ROOTS

    units = []
    for unit_dir in UNIT_DIRS:
        for root in ROOTS:
            d = root / unit_dir
            if not d.is_dir():
                continue
            for f in d.iterdir():
                if f.suffix != ".yaml":
                    continue
                fact_path = unit_dir + "/" + f.stem
                info = load_fact_info(kg, fact_path, ROOTS)
                if info is None:
                    continue
                types = info.get("type", [])
                dimension = ""
                for t in types:
                    if t.startswith("physics/unit/mks"):
                        dimension = t
                        break
                if not dimension:
                    continue
                has = info.get("has", {})
                unit = {
                    "name": f.stem.replace("_", " "),
                    "path": fact_path,
                    "dimension": dimension,
                    "dimension_name": dimension.rsplit("/", 1)[-1],
                }
                factor_info = has.get("factor", {})
                if "val" in factor_info:
                    unit["factor"] = factor_info["val"]
                exponent_info = has.get("exponent", {})
                if "val" in exponent_info:
                    unit["exponent"] = exponent_info["val"]
                units.append(unit)

    units.sort(key=lambda u: (u["dimension"], u["name"]))
    return units


@router.get("/")
def unit_converter(request: Request):
    units = load_units()

    dimensions = sorted(set(u["dimension_name"] for u in units))

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"dimensions": dimensions, "units": units})

    return templates.TemplateResponse(request, "unit_converter.html", {
        "units": units,
        "dimensions": dimensions,
    })
