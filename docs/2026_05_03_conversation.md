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

---

# Session Notes — May 3-4, 2026 (continued)

## Work Done

### 7. Unit converter web app

Created `/apps/physics/unit_converter/` with dimension selector, from/to unit
dropdowns, live JS conversion using factor/exponent from facts.

### 8. Memory optimization — delete `def` after construction

`fact.py` now deletes `self.data["def"]` after successful construction. Memory
dropped from 1.2 MB to 0.5 MB. Added `"def" not in self.data` guard in
`construct()` to skip re-construction when `def` is already freed.
`force_reload` still works — it repopulates `def` from disk before constructing.

### 9. CSafeLoader with fallback

`kg.py` now uses `yaml.CSafeLoader` (C extension, 10-50x faster) with fallback
to `yaml.SafeLoader` if not available.

### 10. `--new-only` flag for check.py

Skips schema validation for files unchanged since last successful run. Uses
`.last_check` file timestamp. `check.bat` passes `%*` to forward arguments.

### 11. Python operator facts and fact-driven evaluation

Replaced hardcoded `OPERATIONS` dict in polynomial plot with fact-driven
resolution: `math/algebra/operation/add` → follows `python_impl` reference →
`computer/sw/lang/python/operator/add` → reads `symbol: "+"` → maps to
`operator.add`. The `SYMBOL_TO_FN` dict is the irreducible code layer.

### 12. New math operations

Created: `subtract`, `divide`, `negate` (arity 1), `sqrt` (arity 1),
`equal`, `less_than`, `and`. Plus corresponding Python operator/function facts.

### 13. Domain restrictions — `math/function/domain/undefined`

Facts can declare conditions where they're undefined:

```yaml
- has:
    undefined_no_real_roots:
      type: math/function/domain/undefined
      value: |
        math/algebra/operation/less_than:
          - discriminant expression...
          - 0
```

The evaluator checks all undefined constraints before computing. Returns the
specific constraint name that triggered ("undefined no equation", "undefined
no real roots").

### 14. Quadratic root formulas as facts

`root_plus.yaml` and `root_minus.yaml` — full quadratic formula with domain
restrictions and conditional for the linear case (`a==0`).

### 15. Conditional expressions — `math/expression/conditional`

Ternary expression node with `condition`, `then`, `else` branches. Evaluator
short-circuits (only evaluates the taken branch). Handles `a==0` linear case
inside the expression tree.

### 16. LaTeX rendering from expression trees

Added `to_latex()` tree walker that converts expression trees to LaTeX strings.
KaTeX (CDN) renders them in the browser. Same tree produces both numerical
computation and mathematical notation — proving expressions are facts, not code.

---

## Design Decisions

### Boolean operations return {0, 1}

**Decision:** Comparison and logical operations return integers 0 and 1, not
booleans. Bitwise `&` used for logical AND since `operator.and_` works on
0/1 integers.

**Rationale:** Keeps everything in one evaluation pipeline. No special boolean
type needed. Comparisons can participate in arithmetic.

### Conditional is ternary, always returns a value

**Decision:** `math/expression/conditional` requires `condition`, `then`, and
`else` — all mandatory. It's an expression (returns a value), not a statement.

**Rationale:** Expression trees must be composable. An if-without-else doesn't
produce a value and can't be a subtree. Domain restrictions handle the "no
answer" case separately.

**Parked:** May need `let`/`where` constructs later for temporary variables
inside branches.

### Domain restrictions vs conditional

**Decision:** Two separate mechanisms:
- `math/function/domain/undefined` — function has no answer (pre-check, skips
  evaluation entirely)
- `math/expression/conditional` — function has different formulas for different
  cases (inside the expression tree)

### LaTeX rendering from facts

Operation-to-LaTeX mapping is in Python code (`OP_TO_LATEX` dict). Could be
moved to facts (like `python_impl` → `latex_impl`) but parked for now.

### N-degree polynomials — implemented

Indexed sum concept implemented. See below.

---

# Session Notes — May 5, 2026

## Work Done

### 1. LaTeX rendering from facts (`latex_impl`)

Moved LaTeX rendering from hardcoded `OP_TO_LATEX` dict to fact-driven resolution.
Each math operation now has `latex_impl` referencing a `computer/sw/lang/latex/operator/`
fact with `symbol` and `style` properties.

Created `computer/sw/lang/latex/operator.yaml` base type and 11 operator facts
(add, subtract, multiply, divide, power, sqrt, negate, equal, less_than, and).

Styles: `infix` (a + b), `frac` (\frac{a}{b}), `power` (a^{b}), `sqrt` (\sqrt{a}),
`negate` (-a).

### 2. Linear and cubic polynomial facts

Created `math/algebra/real/singlevar/polynomial/linear.yaml` with expression tree
and `linear/root.yaml` with domain restriction (`a == 0` → undefined).

Created `math/algebra/real/singlevar/polynomial/cubic.yaml` with expression tree.
Roots use `numpy.roots` (no closed-form fact yet).

### 3. Polynomial degree selector in app

App now has tabs: Linear, Quadratic, Cubic, N-degree. Each loads its expression
from the KG. Linear and quadratic use fact-based root formulas, cubic and n-degree
use `numpy.roots`.

### 4. Indexed expressions — `math/expression/indexed`

New concept for iterating with an index variable over a range. Base hierarchy:

```
math/expression/indexed.yaml          — base concept
math/expression/indexed/index.yaml    — iteration variable (name, from, to)
math/expression/indexed/sum.yaml      — indexed sum (has accumulator, body)
math/expression/indexed/element_at.yaml — access list element by position
math/algebra/expression/indexed/sum.yaml — algebra sum (accumulator = add)
```

In `expression_yaml`, the indexed sum uses named keys (like `conditional`):

```yaml
math/algebra/expression/indexed/sum:
  index: i
  from: 0
  to_length: coefficients
  body:
    math/algebra/operation/multiply:
      - math/expression/indexed/element_at:
          collection: coefficients
          at: i
      - math/algebra/operation/power:
          - x
          - i
```

### 5. N-degree polynomial

`math/algebra/real/singlevar/polynomial/n_degree.yaml` — uses indexed sum to express
`f(x) = Σ(i=0..n) coefficients[i] * x^i`. One compact tree works for any degree.

Coefficients provided as comma-separated list. Order: `a₀, a₁, a₂, ...` (constant
term first). Reversed for `numpy.roots` which expects highest degree first.

LaTeX renders as `\sum_{i=0}^{...} coefficients_i \cdot x^i`.

Verified against `numpy.polyval` — expression tree evaluation matches exactly.

---

## Design Decisions

### Two kinds of expression nodes

**Decision:** Expression trees have two node types:
1. **Operations** — positional operands as list (`[a, b]`). Examples: add, multiply, power.
2. **Structural nodes** — named keys as dict (`{index:, from:, body:}`). Examples:
   conditional, indexed/sum, indexed/element_at.

**Rationale:** Operations are pure computation — order of operands matters but they're
uniform. Structural nodes control flow — they need named parts because the parts have
different roles (condition vs body, index vs range).

### Indexed sum accumulator from facts

**Decision:** `math/expression/indexed/sum` has `accumulator: type: math/operation`.
The algebra-specific `math/algebra/expression/indexed/sum` sets it to
`math/algebra/operation/add`. Future `math/linalg/expression/indexed/sum` could use
a different add operation.

**Current limitation:** The evaluator hardcodes `result = 0` and `+` instead of
loading the accumulator operation from the fact. To be made fully fact-driven later
(needs identity element concept — 0 for add, 1 for multiply).

### List as input type

**Decision:** `coefficients: type: list` declares a list input. The checker doesn't
validate list contents. The evaluator receives the list through `variables` dict.

**Current state:** Informational — tells humans/LLMs this input is a list, but not
enforced by the system.

---

## Fact KG vs Traditional Knowledge Graphs

### Where traditional KGs (Neo4j, RDF/SPARQL, Wikidata) fail

Based on research (Hogan et al. 2021, Noy et al. 2019, Suchanek & Weikum 2023):

1. **No computation semantics** — KGs store `F = m * a` as a string, can't evaluate it
2. **Triple rigidity** — binary relations only, n-ary requires awkward reification
3. **Variable-length structures** — lists, matrices need nested rdf:first/rdf:rest chains
4. **Procedural knowledge** — algorithms, workflows, conditionals don't fit
5. **Static snapshots** — describe "what is", not "how" or "when"

### What our system already handles

| KG limitation | Our answer |
|---|---|
| Can't execute formulas | `expression_yaml` trees evaluate numerically |
| No computation binding | `python_impl`, `latex_impl` — facts produce code and notation |
| Variable-length structures | Indexed sum, native YAML lists |
| No control flow | `conditional`, domain restrictions in expression trees |
| Binary relations only | `has` with nested `as` — n-ary naturally |
| Static data only | Expression trees describe process, not just state |

### Potential application areas

1. **Scientific formulas database** — evaluable, renderable, verifiable expression
   trees with unit types. Not just storing formulas (MathML) but computing with them.
   Currently working on this.

2. **Algorithms as facts** — sorting, searching, graph algorithms expressed as
   indexed operations with conditionals. No KG can represent executable algorithms.
   Next planned area after physics formulas.

3. **Cross-domain reasoning** — polynomial roots connect math operations → Python
   operators → LaTeX rendering → physics units. Four domains in one evaluation chain.
   KGs separate computation from data; our system unifies them.

4. **Fact verification from papers** — load a scientific paper, extract claims, match
   against the KG. The "unknown" category drives KG growth. Needs LLM API access.

### Core positioning

Traditional KGs are passive data stores. Our system is active — the knowledge
executes. The tagline: **"Knowledge graphs that compute."**

---

## What Emerges From a Large Executable Knowledge Graph?

Open question for further thinking. If the KG grows to millions of verified,
structured, executable facts:

1. **Implicit knowledge** — derivable facts nobody explicitly wrote. `F = ma` and
   `a = v/t` together imply `F = mv/t`. Expression tree substitution could discover
   these automatically. The implicit knowledge surface grows combinatorially.

2. **Contradictions become visible** — at large scale, two different derivation paths
   producing different values for the same quantity reveals gaps in understanding.
   Not bugs — signals.

3. **Domain boundaries dissolve** — math → computer science → physics → chemistry
   all connected through shared operations, units, and expression trees. Knowledge
   becomes a unified executable web rather than isolated silos.

4. **Better substrate for teaching** — structural relationships without pedagogical
   bias. Any reasoner (LLM, human) can generate explanations at any level from
   the same verified facts.

5. **Not intelligence, but a substrate for thinking** — the KG doesn't "know"
   anything. But it contains verified relationships that make reasoning more reliable,
   whether the reasoner is human or machine. A sufficiently large executable KG
   is a shared foundation that any intelligence can build on.

Comparison with LLMs: an LLM develops something resembling reasoning from
statistical patterns in text. An executable KG develops something resembling
understanding from verified structural relationships. The two are complementary —
the KG grounds the LLM, the LLM fills gaps in the KG.
