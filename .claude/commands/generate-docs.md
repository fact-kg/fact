Generate documentation from facts into docs/generated/.

## Instructions

All documentation MUST be generated from YAML fact files only. The primary
source is `kg2/app/org/igorlesik/fact/` and its subdirectories. You may also
use general knowledge facts from `kg/` when referenced by the primary facts.

Do NOT invent information that is not in the facts. If a fact is missing or
incomplete, note it as "{TODO: missing fact}" in the output.

## Output structure

Write to `docs/generated/`. Files are numbered with `xx_` prefix to enforce
strict ordering. These files are eventually merged together into a single
document (e.g. via pandoc), so:

- Do NOT repeat the project title in files other than `00_title.md`
- Sections must flow naturally when concatenated in filename order
- Use `##` for top-level sections (the `#` title is only in `00_title.md`)
- Do not add table of contents — it will be generated later
- Use LF line endings, not CRLF

## Files to generate

Each file is generated from scratch by reading the listed facts:

- `00_title.md` — title page with generation date
- `01_overview.md` — from `app/org/igorlesik/fact.yaml`
- `02_knowledge_graph.md` — from `app/org/igorlesik/fact/kg.yaml` and `kg/yaml.yaml`
- `03_tags.md` — from `app/org/igorlesik/fact/kg/yaml/tag.yaml` and `tag/is.yaml`, `tag/has.yaml`, `tag/part.yaml`
- `04_implementation.md` — from `app/org/igorlesik/fact/pysrc.yaml` and `pysrc/checker.yaml`, `pysrc/kg_module.yaml`, `pysrc/entity.yaml`
- `05_usage.md` — from `app/org/igorlesik/fact/pysrc/checker.yaml`, include CLI arguments and examples

## Process

1. Read all fact files listed above
2. Generate each markdown file from scratch based on the corresponding facts
3. Overwrite existing files in `docs/generated/`
4. Run `python.exe pysrc/check.py --roots kg,kg2 --all` to verify facts are valid before generating
