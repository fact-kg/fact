"""Rule engine — loads rules from the KG, evaluates them on demand.

Rules are facts with type knowledge/rule. They have 'when' (conditions)
and 'then' (conclusion) properties set via as.

The engine loads all rules at initialization, then answers queries
by matching conditions against the KG and applying conclusions.
"""

from expression import load_fact_info
from rule.pattern import parse_rule
from rule.matcher import match_conditions


class RuleEngine:
    """Loads rules from the KG and evaluates queries."""

    def __init__(self, kg, roots):
        self.kg = kg
        self.roots = roots
        self.rules = []
        self._load_rules()

    def _load_rules(self):
        """Discover and load all knowledge/rule facts across all roots."""
        from fact import Fact
        for root in self.roots:
            for yf in root.rglob("*.yaml"):
                fp = str(yf.relative_to(root).with_suffix('')).replace('\\', '/')
                if self.kg.load(fp) != 0:
                    continue
                f = Fact(self.kg, fp)
                if f.construct() != 0:
                    continue
                info = self.kg.get_fact(fp).get("info", {})
                if "knowledge/rule" not in info.get("type", []):
                    continue
                val_as = info.get("val_as", {}).get("knowledge/rule", {})
                when = val_as.get("when", "")
                then = val_as.get("then", "")
                if when and then:
                    conditions, conclusion = parse_rule(when, then)
                    self.rules.append({
                        "path": fp,
                        "when": when,
                        "then": then,
                        "conditions": conditions,
                        "conclusion": conclusion,
                    })

    def query(self, pattern_text, initial_binding=None):
        """Find all bindings that satisfy a pattern.

        First matches against direct facts, then applies rules
        to derive additional bindings.
        """
        from rule.pattern import parse_pattern
        conditions = parse_pattern(pattern_text)
        direct = match_conditions(conditions, self.kg, initial_binding)

        # apply rules to derive additional bindings
        derived = list(direct)
        for rule in self.rules:
            rule_bindings = match_conditions(
                rule["conditions"], self.kg, initial_binding)
            for rb in rule_bindings:
                conclusion = rule["conclusion"]
                # check if the derived conclusion matches the query
                derived_bindings = self._apply_conclusion(
                    conclusion, rb, conditions)
                derived.extend(derived_bindings)

        # deduplicate
        seen = set()
        unique = []
        for b in derived:
            key = tuple(sorted(b.items()))
            if key not in seen:
                seen.add(key)
                unique.append(b)

        return unique

    def _apply_conclusion(self, conclusion, rule_binding, query_conditions):
        """Check if a rule conclusion satisfies the query conditions.

        Given a rule conclusion with bound variables, check if it
        matches the pattern being queried.
        """
        results = []

        # substitute variables in conclusion with bound values
        resolved = {}
        for key, val in conclusion.items():
            if key == "type":
                resolved[key] = val
                continue
            if isinstance(val, str) and val.startswith("?"):
                resolved[key] = rule_binding.get(val, val)
            else:
                resolved[key] = val

        # check if the resolved conclusion matches query conditions
        for qc in query_conditions:
            if qc["type"] != resolved.get("type"):
                continue
            binding = {}
            match = True
            for field in ("subject", "object", "property", "value"):
                if field not in qc:
                    continue
                q_val = qc[field]
                r_val = resolved.get(field, "")
                if q_val.startswith("?"):
                    binding[q_val] = r_val
                elif q_val != r_val:
                    match = False
                    break
            if match:
                results.append(binding)

        return results

    def find_transitive(self, fact_path, relation="part"):
        """Find all transitive relationships for a fact.

        Follows chains: if X part Y and Y part Z, returns [Y, Z, ...].
        """
        visited = set()
        result = []
        self._follow_chain(fact_path, relation, visited, result)
        return result

    PRIMITIVES = {"str", "num", "list"}

    def _follow_chain(self, fact_path, relation, visited, result):
        if fact_path in visited:
            return
        visited.add(fact_path)

        if fact_path in self.PRIMITIVES:
            return

        info = load_fact_info(self.kg, fact_path)
        if info is None:
            return

        INFO_KEYS = {"is": "type", "part": "part"}
        info_key = INFO_KEYS.get(relation, relation)
        targets = info.get(info_key, [])
        for target in targets:
            if target not in result:
                result.append(target)
            self._follow_chain(target, relation, visited, result)
