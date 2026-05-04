# Fact — YAML-based Knowledge Graph

A knowledge representation system where facts are stored as YAML files with
semantic tags. File paths encode taxonomy and serve as fact identity. Designed
to be human-readable, LLM-consumable, and machine-verifiable.

## How it works

Each fact is a YAML file containing an array of tags:

```yaml
# physics/atom/element/hydrogen.yaml
- is:
    type: physics/atom/element
    as:
      - physics/atom/element:
          atomic_number:
            value: 1
          symbol:
            value: H
          atomic_mass:
            value: 1.008
- has:
    valence_subshell:
      type: physics/atom/subshell/1s
- has:
    wikipedia_url:
      type: computer/sw/url
      value: "https://en.wikipedia.org/wiki/Hydrogen"
```

Three tags express all relationships:

| Tag | Meaning | Strength |
|-----|---------|----------|
| `is` | Identity / type declaration | Strong (symbolic ground truth) |
| `has` | Property / attribute | Strong (symbolic ground truth) |
| `part` | Loose affiliation to container | Weak |

The file path **is** the fact's identity: `physics/atom/element/hydrogen`
references the file above. Directory structure encodes taxonomy — `hydrogen`
is under `element`, under `atom`, under `physics`.

## Knowledge roots

Facts are organized across multiple root directories by domain:

| Root | Domain |
|------|--------|
| `kg/` | General knowledge (astronomy) |
| `kg2/` | Application self-description |
| `fact_physics/` | Physics (elements, units, constants, subshells) |
| `fact_math/` | Mathematics (operations, expressions, polynomials) |
| `fact_computer/` | Computer science (languages, operators) |

All roots merge into one unified namespace. A fact in `fact_physics` can
reference a fact in `fact_computer` by logical path — root names never
appear in references.

## Mathematical expressions

Expressions use YAML-in-YAML: a machine-readable expression tree stored
as a string that is itself valid YAML:

```yaml
# math/algebra/real/singlevar/polynomial/quadratic.yaml
- is:
    type: math/expression
- has:
    expression_str:
      type: str
      value: "f(x) = a*x^2 + b*x + c"
- has:
    x:
      type: math/variable
- has:
    a:
      type: math/constant
- has:
    expression_yaml:
      type: str
      value: |
        math/algebra/operation/add:
          - math/algebra/operation/add:
              - math/algebra/operation/multiply:
                  - a
                  - math/algebra/operation/power:
                      - x
                      - 2
              - math/algebra/operation/multiply:
                  - b
                  - x
          - c
```

Operation names are fact paths — verifiable by the checker. Variable names
match declared `has` attributes. The tree is evaluable by walking it and
resolving operations to their language-specific implementations
(e.g. `math/algebra/operation/add` → `computer/sw/lang/python/operator/add` → `+`).

## Tools

**Checker** — validates schema, referential integrity, and fact construction:

```bash
python pysrc/check.py --roots kg,kg2,../fact_physics,../fact_math --all
```

**Web server** — browse facts, view relationship graphs, and run apps:

```bash
uvicorn pysrc.web.server:app --reload
```

**Web apps:**

- **Planet Compare** — compare solar system planets by properties
- **Element Table** — periodic table with Mendeleev, ADOMAH, and list views
- **Unit Converter** — convert between units using factors from the KG
- **Polynomial Plot** — plot functions by evaluating expression trees from facts

**Source verifier** — checks Python source code against fact descriptions:

```bash
python pysrc/pyprogverify/verify.py --roots=kg,kg2 --src-root=. pysrc/check.py
```

## Design principles

- **Symbolic precision where possible, LLM inference fills gaps** — strong
  tags are ground truth, everything else is softer territory
- **Human editability is a first-class constraint** — domain experts can
  maintain facts directly
- **File path is ontology** — directory structure encodes taxonomy without
  a formal ontology language
- **Roots are physical storage, not logical** — facts can move between roots
  without breaking references
- **Store fundamental facts, not view-specific data** — the ADOMAH periodic
  table layout is derived from actual electron configurations, not hardcoded
