# Session Notes — May 3, 2026

## Design Decisions

### Mathematical expressions

**Decision:** Expressions are represented with two complementary forms:
- `expression_str` (type `str`) — human/LLM-readable formula, e.g. `"f(x) = a*x^2 + b*x + c"`
- `expression_yaml` (type `str`) — machine-readable YAML-in-YAML string representing the expression tree

The `expression_yaml` string is valid YAML that can be parsed into a tree structure.
Operations in the tree use full fact paths (e.g. `math/algebra/operation/add`), making
them verifiable — the checker can confirm each operation exists as a fact.

```yaml
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

**Rationale:** YAML-in-YAML keeps the expression in a single file (no directory explosion
for the tree), is parseable by programs (`yaml.safe_load`), readable by LLMs, and opaque
enough to the base checker that no schema changes are needed. A dedicated expression
checker can validate the inner structure separately.

### Separation of math and physics

**Decision:** Mathematical expressions live in `math/`, physical laws that use them
live in `physics/`. The expression `f(x) = x * y` is pure math. `F = m * a` is physics
applying that math with physical units.

**Rationale:** The same mathematical structure (e.g. multiplication of two inputs) can
be used by many different physical laws. Keeping math generic avoids duplication.

### Function inputs

**Decision:** Function inputs are declared as `has` entries directly typed with their
mathematical kind:

```yaml
- has:
    x:
      type: math/variable
- has:
    a:
      type: math/constant
```

Not wrapped in a `math/function/input` container type.

**Rationale:** The input's name becomes the `has` attribute name, and its nature
(variable vs constant vs function) is expressed by the type. This is direct and avoids
an extra indirection layer. Variable names in `expression_yaml` must match `has`
attribute names — this is verifiable.

Rejected alternative: `math/function/input` with a `kind` property set via `as`.
Adds indirection without benefit — the type already carries the information.

### Operations

**Decision:** Operations are the base type `math/operation` with `arity` (always an
integer, typically 2). Operations are namespaced by their branch of mathematics:

```
math/algebra/operation/add.yaml
math/algebra/operation/multiply.yaml
math/linalg/operation/dot_product.yaml
```

Not `math/operation/algebra/add.yaml` — the branch is the primary organizer, operations
live inside it.

**Rationale:** This allows branches to contain other concepts besides operations
(e.g. properties, theorems). Addition in linear algebra is a different operation from
scalar addition — same name, different semantics and potentially different arity.

### Binary operations only

**Decision:** All arithmetic operations have arity 2. Variadic forms (e.g. `add(a, b, c)`)
are expressed as nested binary operations: `add(add(a, b), c)`.

**Rationale:** Binary is how computation actually works — in hardware and in formal
algebra. Variadic notation is syntactic sugar that saves space on paper but obscures
structure. The expression tree should reflect the actual computation.

### Polynomial taxonomy

**Decision:** Polynomials are organized as:

```
math/algebra/real/singlevar/polynomial/quadratic.yaml
math/algebra/real/singlevar/polynomial/cubic.yaml
math/algebra/real/singlevar/polynomial/linear.yaml
```

Each level is meaningful and extensible:
- `math/algebra/real/` vs `math/algebra/complex/`
- `real/singlevar/` vs `real/multivar/`
- `polynomial/quadratic`, `polynomial/cubic`, etc.

### Expression type is universal

**Decision:** `math/expression.yaml` is not branch-specific. It declares only
`expression_str` and `expression_yaml` — the branch-specific parts are the operations
used inside the tree and the types of the inputs, which live on concrete expression facts.

**Rationale:** A calculus expression, a linear algebra expression, a logic expression —
they all have a human-readable string and a machine-readable tree. The base type captures
that universality.

---

## Work Done

### 1. Unit converter web app

Created `/apps/physics/unit_converter/` — select dimension, pick source/target units,
live conversion in JS using factor/exponent from facts. No hardcoded conversion tables.

### 2. Math knowledge facts

Created in `fact_math`:
- `math/variable.yaml`, `math/constant.yaml` — input types
- `math/operation.yaml` — base type with arity
- `math/expression.yaml` — base type with expression_str and expression_yaml
- `math/algebra/operation/add.yaml`, `multiply.yaml`, `power.yaml` — arity 2
- `math/algebra/real/singlevar/polynomial/quadratic.yaml` — first expression fact

### 3. Polynomial plot web app

Created `/apps/math/polynomial_plot/` — loads quadratic expression from KG, evaluates
the `expression_yaml` tree at 200 sample points, plots on HTML canvas with axes and grid,
computes and marks roots. User controls `a`, `b`, `c` parameters and x range.

Auto-range: centers on roots when they exist, falls back to vertex with spread 10.

Root finding is currently hardcoded (quadratic formula in Python) — to be replaced with
a roots formula expressed as facts in the future.

### 4. Added `../fact_math` to `fact-server.yaml`

### 5. Formatted base.html Apps dropdown for readability

### 6. Deep memory measurement in check.py

Replaced shallow `sys.getsizeof` with recursive `deep_sizeof` that walks nested
dicts/lists/sets. 249 facts use ~1.2 MB of KG memory.
