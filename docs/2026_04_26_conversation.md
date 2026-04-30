# Session Notes — April 26, 2026

## Work Done

### 1. Converted old-format YAML files to current schema

19 files under `kg/computer/com/ualink/` were in the old format (plain dict, no array wrapper,
missing `is` tags, using unsupported `alias` tag). Converted all to the current array-of-tags format.

- `alias` tag removed, replaced with `is` referencing the target type.
- All files now use `- is: ...`, `- has: ...`, `- part: ...` array entries.

### 2. Schema update — one key per `has`

Design decision: each `- has:` entry must contain exactly one attribute.
Multiple attributes are expressed as separate `- has:` entries.

```yaml
# Correct:
- has:
    host:
      type: computer/com/ualink/host
- has:
    acc:
      type: computer/ai/accelerator

# Wrong (old style):
- has:
    host:
      type: computer/com/ualink/host
    acc:
      type: computer/ai/accelerator
```

Updated `schema.yaml` to enforce `minProperties: 1` and `maxProperties: 1` on `has`.

### 3. Added `has` type validation

The checker now validates type references inside `has` tags:
- Primitive types (`str`, `num`, `list`) — accepted as-is.
- Fact path references (e.g., `computer/cpu`) — resolved via `kg.load()`,
  file must exist.

### 4. Created stub facts for missing type references

- `computer/cpu.yaml` — central processing unit
- `computer/ai/accelerator.yaml` — AI accelerator
- `computer/os/operating_system.yaml` — operating system

### 5. Fixed exit codes in `check.py`

- `main()` return value now passed to `sys.exit()`.
- Failed `fact.construct()` returns exit code 3 instead of falling through to 0.

### 6. Added `--all` flag to `check.py`

`python.exe pysrc/check.py --all` checks all YAML files in the kg directory
and prints a summary with pass/fail counts.

### 7. Minor fixes

- Fixed arg help text: "The name of the user." → "Fact path, e.g. math/function"
- Clarified FIXME comment in `fact.py`
- Added comment in `kg.py` about the `def` wrapper convention

---

## Design Decisions

### Multiple roots for knowledge bases

**Decision:** Support multiple root directories (e.g., `kg`, `kg2`) that merge into
one unified logical graph.

**Rules:**

1. **Search path order must not matter.** All roots are peers, loading order is irrelevant.
2. **Cross-references across roots are allowed and expected.** Knowledge is one big graph;
   a fact in `kg2` can reference a fact in `kg` and vice versa.
3. **Root names are not part of references.** A fact is always referenced by its domain path
   (e.g., `computer/cpu`), never by its root (e.g., ~~`kg:computer/cpu`~~).
   This means facts can be moved between roots without breaking references.
4. **Fact paths must be unique across all roots.** If `computer/cpu.yaml` exists in both
   `kg` and `kg2`, that's an error.
5. **Roots are specified via command line**, not hardcoded.
   Planned: `python.exe pysrc/check.py --roots kg,kg2 --all`

**Rationale:** Roots are physical storage organization, not logical. The separation
allows general knowledge (`kg`) to be distinct from project-specific knowledge (`kg2`)
while maintaining a single unified namespace.

### Self-description: describing this program as facts

**Decision:** Create a second root `kg2` and describe this program (fact checker)
in terms of facts, under the path `app/org/igorlesik/fact/`.

**Benefits:**
- Dogfooding — stress-tests whether the system can represent software artifacts
  (one of the three core use cases).
- LLM agents can read the facts to understand the program faster than reading source.
- Will surface representation gaps in the current tag vocabulary.

### Tag vocabulary (confirmed current state)

| Tag | Meaning | Status |
|---|---|---|
| `is` | Taxonomic identity / type declaration | Active, strong (symbolic) |
| `has` | Compositional — declares properties | Active, strong (symbolic) |
| `part` | Loose affiliation (renamed from `belongs`) | Active, weak |
| `alias` | Was used for abbreviations | **Removed**, replaced by `is` |

---

# Session Notes — April 27-28, 2026

## Work Done

### 1. Multi-root support implemented

- `kg.py`: `Kg` now accepts `List[Path]` of roots instead of single path.
- New `find_fact_file()` searches across all roots, detects duplicates.
- `check.py`: added `--roots` flag (default: `kg`), validates root dirs exist.

### 2. Self-description facts created (kg2)

Created `kg2/app/org/igorlesik/fact/` with 11 fact files describing the
application, KG concept, YAML format, tags, and Python modules:

- `fact.yaml` — the application
- `fact/kg.yaml` — knowledge graph concept
- `fact/kg/yaml.yaml` — YAML fact format
- `fact/kg/yaml/tag.yaml` — base tag concept
- `fact/kg/yaml/tag/is.yaml`, `has.yaml`, `part.yaml` — individual tags
- `fact/pysrc.yaml` — Python implementation
- `fact/pysrc/checker.yaml` — check.py
- `fact/pysrc/kg_module.yaml` — kg.py (Kg class)
- `fact/pysrc/fact_module.yaml` — fact.py (Fact class)

### 3. `has` tag now supports `as` (symmetric with `is`)

Property overrides via `as` now work in `has` entries, same syntax as `is`.
Updated schema.yaml and fact.py. Example:

```yaml
- has:
    method_load:
      type: computer/sw/lang/python/class_method
      as:
        - computer/sw/lang/python/class_method:
            name:
              value: load
```

### 4. Python source verification tool (pyprogverify)

Created `pysrc/pyprogverify/verify.py` — verifies Python source code against
facts using AST (no runtime import of target code).

Currently checks:
- Class existence and name
- Parent class (inheritance) matches
- Public method names match
- `@fact` decorator bidirectional link

Usage:
```bash
python.exe pysrc/pyprogverify/verify.py --roots=kg,kg2 --src-root=. app/org/igorlesik/fact/pysrc
```

### 5. `@fact` decorator for bidirectional code-to-fact linking

Created `pysrc/fact_decorator.py` — a zero-cost-at-runtime decorator that marks
code elements with their fact path:

```python
from fact_decorator import fact

@fact("app/org/igorlesik/fact/pysrc/kg_module")
class Kg(KgIface):
```

The verifier checks both directions: fact points to code (via `source_file`,
`class_name`), code points to fact (via `@fact` decorator).

### 6. Logging replaces print noise

Replaced all diagnostic `print()` with `logging` in kg.py, fact.py, check.py.
- `print()` — program output (results, summaries)
- `logging` — diagnostics (debug, info, errors) to stderr
- Added `--verbose` and `--debug` flags to check.py and verify.py

### 7. Performance improvements

- Schema compiled once via `jsonschema.Draft202012Validator` instead of
  recompiling on every `validate()` call. **3.6x speedup** (58ms → 16ms per fact).
- Removed unnecessary `sorted()` on `rglob()` — was forcing full path collection.
- Merged two AST parse passes into one in verifier.
- Added `rich` spinner to check.py for progress indication.

### 8. Generated documentation

Created `docs/generated/` with numbered markdown files generated from facts:
`00_title.md` through `06_usage.md` plus `README.md` (merged).
Skill `.claude/commands/generate-docs.md` drives regeneration.

### 9. Bug fixes

- `parse_construct_tag_has_dict`: `"type" in string` matched as substring;
  fixed with `isinstance(info[attr_name], dict)` guard.
- `has` value was dropped when explicit `type` + `value` form used; fixed.
- `tag.keys()` → `tag` (4 occurrences) — idiomatic and marginally faster.

---

## Design Decisions

### `has` and `is` symmetry for `as`

**Decision:** The `as` mechanism for setting property values works identically
in both `is` and `has` tags. Full verbose syntax required (not shortened) to
support multiple inheritance cases.

### General knowledge vs project-specific knowledge

- `kg/computer/sw/lang/python/class_method.yaml` — general Python concept
- `kg/computer/sw/lang/python/class.yaml` — general Python concept
- `kg2/app/org/igorlesik/fact/pysrc/kg_module.yaml` — project-specific

General language concepts go in `kg`, project descriptions go in `kg2`.

### Fact-driven development direction

Explored how facts can drive code, not just describe it. Current state:
- Facts describe structure (classes, methods, inheritance) — verifiable via AST
- Behavioral facts (what code *does*) — not yet, needs `function` concept
- `@fact` decorator provides bidirectional link between facts and code
- EARS patterns evaluated, parked for later (docs/to_do_thinking.md)

### Verify tool architecture

- Takes a program fact path, follows `has` references to find modules
- Each module with `class_name` + `class_method` attributes is verifiable
- Uses AST (static analysis), never imports target code
- `--src-root` parameter for generic use with any project

---

# Session Notes — April 29, 2026

## Design Shift: Simplified `@fact` Linking

### The problem with the old approach

The verifier was 300+ lines of Python-specific introspection — it checked class
names, method lists, parent classes, function names. Each new code element type
(class, method, function, field) required new detection logic. The facts needed
Python-specific types (`computer/sw/lang/python/class_method`, etc.) and
attributes like `source_file`, `class_name` to guide the verifier.

### The new approach

`@fact` is a generic link between code and facts. The verifier only validates
that the link is valid — the referenced fact (and optionally field) exists.
No introspection of what the code element is or does.

Three linking mechanisms:

**1. `@fact("path")` — on classes and functions**
```python
@fact("app/org/igorlesik/fact/pysrc/kg_module")
class Kg(KgIface):
```

**2. `@fact("path", "field")` — linking to a specific `has` attribute**
```python
@fact("app/org/igorlesik/fact/pysrc/kg_module", "method_find_fact_file")
def find_fact_file(self, fact_name) -> Path:
```

**3. `Annotated[type, fact_link("path", "field")]` — for variables/fields**
```python
self.data: Annotated[Dict[str, Any], fact_link(
    "app/org/igorlesik/fact/pysrc/kg_module", "data_storage")] = {}
```

### What the verifier checks

1. The fact path exists as a real fact file
2. If a field name is given, the fact has that `has` attribute
3. Nothing else — no method lists, no class introspection

### Verifier invocation changed

Old: point at a fact, it finds source files.
```bash
verify.py app/org/igorlesik/fact/pysrc
```

New: point at source files, it finds `@fact` links.
```bash
verify.py pysrc/check.py pysrc/kg.py pysrc/fact.py
```

### Benefits

- Verifier is ~100 lines instead of ~300
- Language-agnostic design — same concept works for Rust, etc.
- No Python-specific fact types needed for linking
- Deeper checking (methods exist, fields match) can be done by LLM agents
  using the established links — doesn't need to be rigid tooling

### Both `@fact` styles tested for functions and methods

**Separate fact file** — code element gets its own fact:
```python
@fact("app/org/igorlesik/fact/pysrc/checker/check_one")
def check_one(kg, fact_name):
```

**Inline attribute** — code element references a field on a parent fact:
```python
@fact("app/org/igorlesik/fact/pysrc/checker", "function_main")
def main():
```

Both coexist. The comparison will reveal which style is more natural as the
project grows.
