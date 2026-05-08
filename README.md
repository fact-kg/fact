# Fact — YAML-based Knowledge Graph

**Live demo: [fact-kg.onrender.com](https://fact-kg.onrender.com/)**

A knowledge representation system where facts are YAML files with semantic tags.
File paths encode taxonomy and serve as fact identity. Unlike traditional knowledge
graphs, facts in this system are not just data — they **compute**. Expression trees
evaluate numerically, render as LaTeX, and bind to language-specific implementations,
all from the same YAML source.

## What makes this different

Traditional knowledge graphs (Neo4j, RDF, Wikidata) store static relationships.
They can represent "force equals mass times acceleration" as a string, but they
can't evaluate it. This system can:

```yaml
# physics/classical/mechanics/dynamics/law/newton_second.yaml
- is:
    type: physics/equation
    as:
      - physics/equation:
          lhs:
            value: [force]
          rhs:
            value: [mass, acceleration]
- is:
    type: math/expression
- has:
    force:
      type: physics/unit/mks/force
- has:
    mass:
      type: physics/unit/mks/mass
- has:
    acceleration:
      type: physics/unit/mks/acceleration
- has:
    expression_yaml:
      type: str
      value: |
        math/algebra/operation/multiply:
          - mass
          - acceleration
```

The same fact is simultaneously:
- A **physics equation** with typed participants and lhs/rhs structure
- A **math expression** with an evaluable tree
- **Human-readable** — a domain expert can edit it directly
- **LLM-consumable** — no serialization layer needed
- **Machine-verifiable** — the checker validates schema, references, and types

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

## Executable expressions

Expressions use YAML-in-YAML: a machine-readable expression tree stored as a
string that is itself valid YAML. Operations reference fact paths — the checker
verifies they exist, and the evaluator resolves them to language-specific
implementations:

```
math/algebra/operation/add  →  computer/sw/lang/python/operator/add  →  "+"
                            →  computer/sw/lang/latex/operator/add   →  "+"
```

One expression tree produces both numerical computation and LaTeX rendering.
The quadratic formula renders as proper mathematical notation and evaluates
to find roots — from the same YAML facts.

Features demonstrated in the [live demo](https://fact-kg.onrender.com/):
- **Polynomial Plot** — evaluates expression trees, plots curves, finds roots,
  renders LaTeX. Supports linear through n-degree (via indexed summation).
- **Element Table** — periodic table with Mendeleev, ADOMAH, and list views.
  ADOMAH positions computed from quantum mechanics facts (subshell data), not
  hardcoded.
- **Unit Converter** — converts between units using factors from the KG.
- **Planet Compare** — compares solar system bodies by properties.

## Knowledge roots

Facts are organized across multiple root directories by domain:

| Root | Domain |
|------|--------|
| `kg/` | General knowledge (astronomy) |
| `kg2/` | Application self-description |
| [fact_physics](https://github.com/fact-kg/fact_physics) | Physics (elements, units, constants, subshells, laws) |
| [fact_math](https://github.com/fact-kg/fact_math) | Mathematics (operations, expressions, polynomials) |
| [fact_computer](https://github.com/fact-kg/fact_computer) | Computer science (languages, operators, LaTeX) |

All roots merge into one unified namespace. A fact in `fact_physics` can
reference a fact in `fact_computer` by logical path — root names never
appear in references.

## Tools

**Checker** — validates schema, referential integrity, and fact construction:

```bash
python pysrc/check.py --roots kg,kg2,../fact_physics,../fact_math,../fact_computer --all
```

**Web server** — browse facts, view relationship graphs, and run apps:

```bash
uvicorn pysrc.web.server:app --reload
```

**Source verifier** — checks Python source code against fact descriptions:

```bash
python pysrc/pyprogverify/verify.py --roots=kg,kg2 --src-root=. pysrc/check.py
```

## Design principles

- **Knowledge that computes** — expression trees are both data and computation,
  evaluable in any language via fact-driven bindings
- **Symbolic precision where possible, LLM inference fills gaps** — strong
  tags are ground truth, everything else is softer territory
- **Human editability is a first-class constraint** — domain experts can
  maintain facts directly without specialized tools
- **File path is ontology** — directory structure encodes taxonomy without
  a formal ontology language
- **Roots are physical storage, not logical** — facts can move between roots
  without breaking references
- **Store fundamental facts, not view-specific data** — the ADOMAH periodic
  table layout is derived from actual electron configurations, not hardcoded
