# Ideas to Think About

## EARS (Easy Approach to Requirements Syntax)

Structured natural language templates for requirements: ubiquitous, event-driven,
state-driven, unwanted behavior, optional. Each template has trigger/condition +
subject + action.

Current assessment: not directly useful yet. Our facts are already more precise
than EARS templates. But the condition/trigger concept is missing from our tags —
we describe what things *are* and *have*, not *when* or *under what conditions*.

The `function` concept (inputs → outputs) may be a more natural way to express
behavior than borrowing EARS patterns. A condition is just another input.

Revisit when we start expressing behavioral requirements as facts.

Reference: https://alistairmavin.com/ears/

## JSON output for check and verify tools

Add `--output-json` flag to `check.py` and `verify.py` so that LLM agents and
scripts can consume structured output instead of parsing human-readable text.

Current assessment: not needed yet. Claude handles the text output fine.
Revisit when we build automation that chains tool outputs or when the output
gets complex enough that text parsing becomes unreliable.

## Rust verifier — multi-language fact-driven development

Rust has proc macros and custom attributes that mirror Python's `@fact` decorator:

```rust
#[fact("app/org/igorlesik/fact/pysrc/kg_module")]
struct Kg { ... }
```

The `syn` crate can parse Rust AST to find `#[fact(...)]`, struct fields,
method signatures, and trait implementations. Same verification logic,
different language frontend.

Key difference from Python: Rust uses traits (interfaces) not inheritance,
so we'd need `implements_trait` instead of `parent_class` — reinforcing
that fact vocabulary should be language-specific (`computer/sw/lang/rust/`).

This is potentially the real value of the project: write facts once as
language-agnostic specifications, verify against any language with AST tooling.

Revisit after the Python verifier is mature and the `src/` Rust code is revived.

## YAML block scalars as embedded structured data

YAML `|` block scalars can contain YAML-formatted content as plain text:

```yaml
- has:
    config_template: |
      - host: localhost
        port: 8080
        options:
          timeout: 30
          retries: 3
```

The content is a string to the fact system but parseable on demand. This creates
a middle tier in the epistemology:

1. **Strong tags** (`is`, `has`) — fully structured, verified by checker
2. **`|` block with structured content** — carried but opaque to the checker,
   parseable by programs or LLM agents when needed
3. **LLM-inferred** — not in the fact at all

This avoids extending the type system beyond `str`, `num`, `list` while
allowing arbitrarily complex data structures inside facts. Could be used for
examples, templates, complex configurations, or data that doesn't fit the
current tag model.

## Web UI design decisions

Stack: FastAPI + Jinja2 + HTMX + vis.js + classless CSS (Pico or Simple.css).

- **HTMX** for navigation and dynamic content — server renders HTML, minimal JS
- **vis.js** for interactive graph visualization — self-contained, no framework needed
- **Classless CSS** for styling — write semantic HTML, looks professional automatically
- **No build tools** — no npm, no webpack, just `<script>` tags
- **Zero lock-in** — each piece is replaceable independently

Design principles: minimal, professionally elegant, fast. Good typography and
spacing matter more than animations or effects. The graph visualization is the
key interactive element.

Dual output: HTML for humans, JSON for bots/agents. Same endpoints, content
negotiation via Accept header.
