# Building the Infrastructure for AI That Reasons

## The neurosymbolic gap

There are two ways to represent knowledge for AI.

**Symbolic systems** (knowledge graphs, ontologies, formal logic) are precise
and verifiable but brittle. They can tell you hydrogen's atomic number is 1,
but can't handle "the sun is roughly a million times heavier than Earth."

**Neural systems** (LLMs, embeddings) are flexible and can reason in natural
language, but hallucinate and can't verify their own outputs.

Every serious AI system needs both. The question is how to combine them
without losing the strengths of either.

I've been building a YAML-based knowledge graph that holds **both symbolic
and natural language knowledge in the same fact**, with a deliberate boundary
between what's precise and what's fuzzy. Strong tags (`is`, `has`) are
symbolic ground truth. Natural language descriptions, constraints, and
rationale live alongside them. An LLM reads the whole fact — the precise
parts ground its reasoning, the natural language parts give it context.

The result: a knowledge system where an algorithm fact has five simultaneous
layers — executable steps, natural language descriptions, formal constraints,
computational expressions, and design rationale — all in one YAML file that
a human can edit and an LLM can reason about.

## What this looks like in practice

Here's Newton's second law as a fact:

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
    expression_algebraic:
      type: math/expression
      as:
        - math/expression:
            expression_str:
              value: "F = m * a"
            expression_yaml:
              value: |
                math/algebra/operation/multiply:
                  - mass
                  - acceleration
    expression_differential:
      type: math/expression
      as:
        - math/expression:
            expression_str:
              value: "F(t) = m * d²x/dt²"
```

This single fact is simultaneously:
- A **physics equation** with typed participants (force, mass, acceleration)
  and lhs/rhs structure
- A **math expression** with an evaluable tree that resolves operations
  through `python_impl` (→ `*`) and `latex_impl` (→ `\cdot`)
- **Two representations** of the same law — algebraic and differential
- **LLM-readable** — a language model understands the structure, types, and
  natural language descriptions without any translation layer
- **Machine-verifiable** — the checker validates that referenced types exist,
  that the expression tree uses valid operations, that MKS units are
  consistent

The expression tree `math/algebra/operation/multiply: [mass, acceleration]`
is not a string — it's structured knowledge. The operation `multiply` is
itself a fact that links to Python's `*` operator, LaTeX's `\cdot` symbol,
and declares arity 2. One tree evaluates numerically, renders as LaTeX, and
generates code.

## Expressions that compute

The quadratic formula `f(x) = ax² + bx + c` lives as a YAML expression tree.
From this single fact:

- The **polynomial plotter** evaluates the tree at 200 points and draws the
  curve on an HTML canvas
- **KaTeX** renders the formula as proper mathematical notation in the browser
- The **root finder** evaluates separate expression facts for the quadratic
  formula, with domain restrictions (discriminant < 0 → no real roots) and
  conditional branching (linear case when a=0) — all expressed as YAML
  expression trees
- The **expression diagram** app visualizes the tree structure with D3.js
- An **indexed summation** `Σ(i=0..n) coefficients[i] × x^i` handles
  arbitrary-degree polynomials — one compact tree for any degree

Mathematical constants have dual identity. Euler's number `e` is both
`math/constant` (value 2.718281828459045) and `math/expression` (the limit
definition `lim(n→∞) (1+1/n)^n`). Pi is both a numeric value and the ratio
of circumference to diameter — with typed references to circle geometry
facts.

`sin(x)` has five expression representations: geometric (opposite/hypotenuse),
Taylor series, Euler's formula, unit circle, and differential equation. Each
is simultaneously true. The knowledge graph holds all of them.

## Algorithms as knowledge

This is where the symbolic and natural language layers come together most
powerfully.

A sorting algorithm in Fact KG isn't a description of bubble sort — it IS
bubble sort. Every step is a typed fact. Every variable is declared with a
description. Every constraint is explicit.

Here's what a single algorithm fact contains:

**Layer 1 — Procedural (symbolic).** Steps with typed operations and explicit
control flow. `assign`, `for_each`, `if`, `assign_indexed`, `return`. Each
step has a `next` link. Nested loops reference body steps.

**Layer 2 — Declarative (natural language).** Every step has a description:
"check if adjacent elements are out of order," "save element before swap."
Every variable has a description: "the maximum element found so far."

**Layer 3 — Constraints (symbolic + natural language).** Preconditions:
"len(array) > 0." Postconditions: "for all i: array[i] <= array[i+1]."
Loop invariants: "result is the maximum of elements seen so far."

**Layer 4 — Computational (symbolic).** Inline expression evaluation for
computed values: `inner_bound = len(array) - i - 2`, `j_next = j + 1`.
Operations resolved through the math ontology.

**Layer 5 — Epistemic (natural language).** Design rationale:

```yaml
understanding:
  problem: "sort elements in ascending order"
  constraints: ["can compare two elements", "can swap adjacent elements"]
planning:
  observation: "comparing adjacent elements and swapping is simplest"
  insight: "one pass bubbles the largest element to the end"
  question: "does one pass suffice?"
  conclusion: "no, each pass fixes one element, repeat n times"
alternatives:
  - name: "merge sort"
    tradeoff: "O(n log n) but needs O(n) extra memory"
```

No existing framework combines all five layers in a machine-readable format.
Research on design rationale (DRL, QOC, Polya's "How to Solve It") captures
fragments, but none in structured data alongside executable code.

## Code generation

The algorithm viewer generates working code from the same YAML fact. The
code generator walks steps, resolves operation symbols through facts, and
emits language-specific syntax.

**Generated Python:**
```python
def find_max(input_array: list):
    """Find maximum element in an array"""
    result = input_array[0]
    for i in range(1, len(input_array)):
        if input_array[i] > result:
            result = input_array[i]
    return result
```

**Generated C++:**
```cpp
template<typename T>
auto find_max(std::vector<T>& input_array) {
    auto result = input_array[0];
    for (int i = 1; i < input_array.size(); i++) {
        if (input_array[i] > result) {
            result = input_array[i];
        }
    }
    return result;
}
```

Both are clean, idiomatic code. A human would write exactly this. The
generated Python passes the same test facts that verify the YAML algorithm
directly.

Adding a new target language means writing ~100 lines of step generators
and a dispatch table. The algorithm fact stays unchanged.

## The scale question

340 facts across five knowledge domains. Small. But the architecture scales:

**Across domains.** The polynomial roots fact chain crosses four domains in
one evaluation: math operations → Python operators → LaTeX rendering →
physics units. A single expression tree connects algebra, computer science,
typography, and physics. Each domain is its own git repository. References
use logical paths — facts can move between repositories without breaking.

**Across representations.** One algorithm fact produces a flowchart diagram,
structured text with constraints, Python code, C++ code, and the YAML source.
One expression produces numerical computation, LaTeX notation, and a tree
diagram. Adding a representation (Rust code, JavaScript, SVG diagram) doesn't
change the fact — it adds a renderer.

**Across consumers.** The same fact is:
- **Human-readable** — YAML in any text editor
- **Machine-executable** — expression evaluator, algorithm executor
- **LLM-comprehensible** — structured with natural language at every level
- **Machine-verifiable** — schema validation, referential integrity, tests

**Across time.** Facts are versioned in git. Algorithm variants are new facts,
not code branches. The design rationale captures why decisions were made.
Knowledge evolves without losing history.

## Why this matters for LLMs

An LLM reading a Fact KG algorithm sees structure at every level. The
symbolic parts (steps, operations, types) give it precise execution
semantics. The natural language parts (descriptions, constraints, rationale)
give it context for reasoning.

With constraints, the LLM can verify correctness: "Does the postcondition
follow from the invariant when the loop terminates?" With rationale, it can
reason by analogy: "The key insight from find_max (track best-so-far) also
applies to this problem." With multiple representations, it can choose the
most useful view.

This isn't RAG — it's not just retrieving relevant text. It's giving the
LLM a verified, structured, executable knowledge base that it can reason
over, compute with, and extend.

## Current state

The project is open source. The system includes:

- A fact checker with schema validation, referential integrity, and
  construction verification
- An expression evaluator that resolves operations through fact-driven
  language bindings
- An algorithm executor that walks typed steps
- A test framework where test cases are themselves facts
- Code generators for Python and C++
- A web application with six interactive apps
- A diagram library with tree and flowchart layouts

Live demo: https://fact-kg.onrender.com
GitHub: https://github.com/fact-kg
