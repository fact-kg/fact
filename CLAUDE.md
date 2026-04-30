# Fact — YAML-based Knowledge Graph

## What is this project

A knowledge representation system where facts are stored as YAML files with
semantic tags (`is`, `has`, `part`). File paths encode taxonomy and serve as
fact identity. Designed to be human-readable and LLM-consumable.

## On conversation start

Read the self-description facts to understand the system:
- `kg2/app/org/igorlesik/fact.yaml` — the application
- `kg2/app/org/igorlesik/fact/kg.yaml` — the knowledge graph concept
- `kg2/app/org/igorlesik/fact/kg/yaml.yaml` — the fact format
- `kg2/app/org/igorlesik/fact/kg/yaml/tag.yaml` — tag concept
- `kg2/app/org/igorlesik/fact/pysrc.yaml` — Python implementation

## Project structure

- `kg/` — general knowledge facts (astronomy, math, computer science)
- `kg2/` — application-specific facts (this project describes itself)
- `pysrc/` — Python implementation (checker, kg loader, fact constructor)
- `src/` — Rust implementation (dormant, do not modify)
- `schema.yaml` — JSON Schema defining valid fact structure
- `docs/` — conversation logs and design decisions

## Fact format

Each fact is a YAML file containing an array of tags:

```yaml
- is: thing name            # or: { type: path/to/other/fact }
- has:
    property_name:
      type: str              # str, num, list, or path/to/fact
      value: "some value"
- part: path/to/container
```

Rules:
- Each `- has:` entry must contain exactly one attribute
- `is` and `has` are strong tags (symbolic ground truth)
- `part` is a weak tag (loose affiliation)
- Fact path = file path relative to root, without `.yaml` extension
- A fact referenced by type must exist as a file

## How to check facts

```bash
# Check single fact
python.exe pysrc/check.py math/function

# Check all facts in default root (kg)
python.exe pysrc/check.py --all

# Check across multiple roots
python.exe pysrc/check.py --roots kg,kg2 --all
```

Exit codes: 0 = success, 1 = file/load error, 2 = schema error, 3 = construction error.

## Before making changes

- Read `docs/2026_04_25_kg_conversation.md` for design philosophy and theory
- Read `docs/2026_04_26_conversation.md` for recent decisions
- Read facts in `kg2/app/org/igorlesik/fact/` to understand the system's self-description
- Run `python.exe pysrc/check.py --roots kg,kg2 --all` after modifying any YAML facts
- Run `python.exe pysrc/pyprogverify/verify.py --roots=kg,kg2 --src-root=. pysrc/check.py pysrc/kg.py pysrc/fact.py` after modifying Python code
- Use LF line endings, not CRLF
- Do not modify files under `src/` (Rust, dormant)

## Tag reference

| Tag | Meaning | Strength |
|-----|---------|----------|
| `is` | Identity / type declaration | Strong |
| `has` | Property / attribute | Strong |
| `part` | Loose affiliation to container | Weak |

## Design principles

- Roots are physical storage; the logical graph is one unified namespace
- Fact paths must be unique across all roots
- Root names never appear in references — facts can move between roots
- Symbolic precision where possible, LLM inference fills gaps
- Human editability is a first-class constraint
