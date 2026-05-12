# Session Notes — May 6, 2026

## Work Done

### 1. Newton's Second Law as a physics equation

Created `physics/classical/mechanics/dynamics/law/newton_second.yaml` — the first
physics law expressed as both a `physics/equation` and a `math/expression`.

**Taxonomy decision:** `physics/classical/mechanics/dynamics/law/` — separating
dynamics from statics and kinematics. Getting taxonomy right upfront prevents
chaos when multiple contributors add facts.

**Physics equation concept:** Created `physics/equation.yaml` with `lhs` and `rhs`
(both type `list`). For Newton's second law:
- `lhs: [force]` — the quantity being defined
- `rhs: [mass, acceleration]` — the defining quantities

The names (`force`, `mass`, `acceleration`) are shared between the physics
equation (`lhs`/`rhs`) and the math expression (`expression_yaml`). A checker
can verify they match.

### 2. GitHub organization

Created `fact-kg` org on GitHub (`github.com/fact-kg`). Transferred all repos:
`fact`, `fact_physics`, `fact_math`, `fact_computer`.

Created `facts` repo as top-level container with git submodules:
```
facts/
  fact/           ← submodule: app code, kg, kg2
  fact_physics/   ← submodule
  fact_math/      ← submodule
  fact_computer/  ← submodule
```

Working directory moved from `prj/fact/fact` to `prj/fact/facts/fact`.

### 3. Deployed to Render fact-kg.onrender.com

https://fact-kg.onrender.com
https://fact-kg.onrender.com/fact/physics/atom/element/chromium

Deployed the web app to Render (free tier). Files added to `facts/` repo:

- `requirements.txt` — Python dependencies
- `render.yaml` — Render service config

Start command: `cd fact && uvicorn pysrc.web.server:app --host 0.0.0.0 --port $PORT`

Submodules work correctly — Render pulls them for public repos. Paths resolve
because `fact-server.yaml` uses `../fact_physics` etc., and submodules are siblings.

**Free tier behavior:** First requests after inactivity are slow (cold start ~30s).
Once facts are cached in memory, responses are fast. Single worker can get
overwhelmed with concurrent requests during initial loading.

---

## Design Decisions

### Physics equation structure

**Decision:** `physics/equation` has `lhs` (left-hand side) and `rhs` (right-hand
side), both type `list`. The equation declares physical participants as `has`
entries typed with MKS dimensions. `lhs`/`rhs` reference these participant names.

**Rationale:** Separates physics meaning (which quantities participate, what's input
vs output) from math computation (the expression tree). The same names bridge both
layers. `lhs`/`rhs` also enables future equation rearrangement — `F = ma` can become
`a = F/m` by swapping lhs/rhs and changing the expression tree.

### Taxonomy for physics laws

**Decision:** `physics/classical/mechanics/dynamics/law/` rather than flat
`physics/law/`.

**Rationale:** Anticipates growth. An authority should create proper structure
upfront rather than letting contributors scatter files. The hierarchy reflects
how physics is actually organized: classical vs quantum, mechanics vs thermodynamics,
dynamics vs statics.

### Deployment architecture

**Decision:** `facts` repo as a container with submodules, deployed to Render.
No code changes needed for deployment — existing `fact-server.yaml` paths work
because submodules are siblings.

**Alternatives considered:** Railway (less generous free tier), Fly.io (needs
Dockerfile). Render chosen for simplicity and truly free tier.

---

## Observations

### Using open source data

Wikidata/Wikipedia data (values, properties, URLs) can be imported automatically.
But the ontology — taxonomy, expression structure, type relationships — requires
human judgment and is the competitive advantage.

### Agent-assisted KG growth

A realistic future workflow:
1. Human builds ontology skeleton (taxonomy, types, expression patterns)
2. LLM agent crawls sources, generates YAML facts matching the patterns
3. Checker verifies every generated fact
4. Human reviews and approves

The skeleton built over these sessions is already enough to demonstrate this.

---

## Session continued — May 6, 2026

### Work Done

#### Multiple expressions per fact

Refactored all expression facts to use `as` pattern on `math/expression` type.
Before: `expression_str` and `expression_yaml` as separate top-level `has` entries.
After: wrapped in a named `has` entry typed `math/expression` with `as`:

```yaml
- has:
    expression_geometric:
      type: math/expression
      as:
        - math/expression:
            expression_str:
              value: "sin(x) = opposite / hypotenuse"
            expression_yaml:
              value: |
                math/algebra/operation/divide:
                  - opposite
                  - hypotenuse
```

Updated ~10 fact files (quadratic, linear, cubic, n_degree, root_plus, root_minus,
linear/root, pi, e, newton_second) and the evaluator/LaTeX renderer in routes.py.

#### Mathematical constants — e and pi

Created `math/analysis/constant/e.yaml` — dual identity as `math/constant`
(value 2.718281828459045) and `math/expression` (limit definition). Introduced
`math/analysis/real/calculus/expression/limit.yaml` concept.

Created `math/analysis/constant/pi.yaml` — dual identity with geometric expression
(circumference / diameter). Created supporting geometry facts:
`math/geometry/euclidean/shape/circle.yaml` with `circle/circumference.yaml` and
`circle/diameter.yaml`.

#### sin(x) with five expressions

Created `math/analysis/real/function/trigonometric/sin.yaml` with `python_impl`
and five expression representations:
1. Geometric — opposite / hypotenuse (working)
2. Taylor series — FIXME: needs factorial
3. Euler's formula — FIXME: needs complex numbers, exp
4. Unit circle — FIXME: needs geometry concepts
5. Differential equation — FIXME: needs ODE concept

Each FIXME marks a gap in the expression system — a roadmap.

#### Newton's second law — two expressions

Added differential form `F(t) = m * d²x/dt²` alongside algebraic `F = ma`.
FIXME for derivative operation.

### Design Decisions

#### Multiple expressions use `as` pattern

**Decision:** Each expression is a `has` entry typed `math/expression`, with
`expression_str` and `expression_yaml` set via `as`. Multiple expressions per
fact get descriptive names (`expression_geometric`, `expression_taylor`, etc.).

**Rationale:** Reality has multiple simultaneously correct descriptions. A KG
should capture all of them, not force one canonical form. The `as` pattern
is consistent with how other typed properties work.

#### Constants are both value and expression

**Decision:** `e` and `pi` have `is: math/constant` (with numeric value via `as`)
AND `is: math/expression` (with defining formula). Dual identity.

**Rationale:** A constant's value is a fact. How it's defined is also a fact.
Both matter — the value for computation, the definition for understanding.

#### Function vs expression distinction

**Decision:** Expressions with no free variables → constants (e, pi).
Expressions with free variables → functions (sin, quadratic).
Both use `math/expression` for their expression trees.

#### Geometry taxonomy

**Decision:** `math/geometry/euclidean/shape/circle/` with properties
(circumference, diameter) nested under the shape, not abstracted as general
properties.

**Rationale:** Circumference is circle-specific. No practical value in
abstracting it away from the shape it belongs to.

---

## Session — May 11, 2026

### Work Done

#### Expression module extracted

Moved expression evaluator, LaTeX renderer, and helpers from the polynomial
plot app into a shared library at `pysrc/expression/`:
- `evaluator.py` — `ExpressionEvaluator` class with operation resolution
- `latex.py` — `ExpressionLatex` class with LaTeX rendering
- `helpers.py` — `load_fact_info`, `extract_expression`, `extract_all_expressions`

Both the polynomial plot and expression diagram apps now use the shared module.

#### Algorithm system

Created algorithm step types as facts:
- `computer/algorithm.yaml` — base type
- `computer/algorithm/step.yaml` — base step with `next`
- `computer/algorithm/assign.yaml` — set variable
- `computer/algorithm/if.yaml` — conditional branch
- `computer/algorithm/indexed/for_each.yaml` — iteration
- `computer/algorithm/return.yaml` — produce output
- `computer/algorithm/evaluate_expression.yaml` — evaluate a math expression

Created `computer/algorithm/array/find_max.yaml` — first algorithm, uses 4 step
types with reusable, parameterized steps. Variables passed by name, comparison
operation pluggable via `python_impl`.

Created `computer/algorithm/evaluate_expression_and_return.yaml` — generic
two-step algorithm that evaluates any expression fact and returns the result.

#### Algorithm executor

`pysrc/algo_executor.py` — `AlgorithmExecutor` class that reads algorithm
steps from fact `has`/`as` structure, walks the `next` chain, dispatches to
step executors by type. Uses the shared expression evaluator for
`evaluate_expression` steps and comparison operations.

#### Test framework

Created `computer/test/case.yaml` — test case type with `description`,
`subject`, `expected_result`.

Created `pysrc/test/runner.py` — discovers test facts by scanning for
`/test/` in paths, loads subject (algorithm), executes with test inputs,
compares result to expected. Supports both algorithm tests and expression
tests (via `evaluate_expression_and_return` algorithm).

Test cases created:
- `computer/algorithm/array/find_max/test/` — 4 tests (basic, single
  element, negative numbers, duplicates)
- `math/algebra/real/singlevar/polynomial/quadratic/test/` — 3 tests
  (basic, zeros, negative coefficients)

All 7 tests pass.

#### Algorithm viewer app

Created `/apps/computer/algorithm_viewer/` — search for algorithm facts,
visualize as flowchart with D3.

FlowLayout in `pysrc/diagram/flow_layout.py` — positions steps in
columns (main flow left, branches right), different shapes per step type:
- Rectangle (blue) — assign, evaluate
- Diamond (orange) — if condition
- Hexagon (purple) — for_each loop
- Rounded rectangle (green) — return

Loop-back edges rendered as dashed polylines routed around body steps.

#### Diagram library improvements

Separated `FlowLayout` into its own file `pysrc/diagram/flow_layout.py`.
Studied pyflowchart library — it does zero layout (delegates to flowchart.js).
Useful patterns: `NodesGroup` for composable subgraphs, `TransparentNode`
for edge routing. For professional layout, Sugiyama/layered algorithm is
the standard — future improvement.

### Design Decisions

#### Algorithms are the testable unit

**Decision:** Expressions are tested by wrapping them in the
`evaluate_expression_and_return` algorithm. The test runner only executes
algorithms. Every testable computation is an algorithm.

**Rationale:** An algorithm takes inputs and returns an output — naturally
testable. Evaluating an expression is just a two-step algorithm (evaluate →
return). This unified the test framework: one runner, one test case format.

#### Step types are reusable

**Decision:** Algorithm steps (`assign`, `if`, `for_each`, `return`) are
generic fact types. Each algorithm assembles them with specific parameters
via `as`. Steps receive variable names, not hardcoded values.

**Rationale:** `find_min` reuses the same steps as `find_max` with a
different comparison operation. The steps don't know what algorithm they're
in — they're pluggable components.

#### Fact-code boundary for algorithms

**Decision:** Facts describe algorithm structure (steps, connections, variable
names, operation references). Code provides step semantics (what "assign" does).
The dispatch table in `algo_executor.py` is the irreducible code layer.

**Rationale:** Same pattern as expression operations — `python_impl` resolves
to a symbol, the symbol maps to a function. Facts say "what," code says "how."

#### pyflowchart study

pyflowchart generates text for flowchart.js, does no layout computation.
For our use case (full control, D3 rendering), the useful takeaways are:
- `NodesGroup` for composable subgraphs
- `TransparentNode` for edge routing
- Sugiyama algorithm for professional layered layout

### What's Still Rough

- FlowLayout has magic numbers and simple column/row positioning
- Algorithm executor has hardcoded bracket parsing for array access
  (should use expression evaluator)
- No interactive algorithm execution app (only flowchart viewing)
