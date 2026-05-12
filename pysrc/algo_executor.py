import yaml
from expression import ExpressionEvaluator, load_fact_info, extract_expression


class AlgorithmExecutor:
    def __init__(self, kg):
        self.kg = kg
        self.evaluator = ExpressionEvaluator(kg)

    def execute(self, algo_path, inputs):
        info = load_fact_info(self.kg, algo_path)
        if info is None:
            raise ValueError(f"Cannot load algorithm: {algo_path}")

        has = info.get("has", {})

        steps = {}
        for attr, val in has.items():
            if attr.startswith("step_"):
                steps[attr] = val

        first_step = None
        for name in ["step_init", "step_start"]:
            if name in steps:
                first_step = name
                break
        if first_step is None and steps:
            first_step = next(iter(steps))

        variables = dict(inputs)
        return self._execute_step(first_step, steps, variables)

    def _execute_step(self, step_name, steps, variables):
        step = steps[step_name]
        step_type = step["type"]
        step_as = step.get("val_as", {}).get(step_type, {})

        result = None
        if step_type == "computer/algorithm/assign":
            result = self._exec_assign(step_as, variables)
        elif step_type == "computer/algorithm/if":
            result = self._exec_if(step_as, variables, steps)
        elif step_type == "computer/algorithm/indexed/for_each":
            result = self._exec_for_each(step_as, variables, steps)
        elif step_type == "computer/algorithm/return":
            return self._exec_return(step_as, variables)

        next_step = step_as.get("next", "")
        if next_step and next_step in steps:
            return self._execute_step(next_step, steps, variables)
        return result

    def _resolve_value(self, expr, variables):
        if isinstance(expr, (int, float)):
            return expr
        expr = str(expr)
        if "[" in expr:
            arr_name, idx_str = expr.rstrip("]").split("[")
            idx = int(variables[idx_str]) if idx_str in variables else int(idx_str)
            return variables[arr_name][idx]
        if expr in variables:
            return variables[expr]
        try:
            return float(expr)
        except ValueError:
            return expr

    def _exec_assign(self, step_as, variables):
        var_name = step_as.get("variable", "")
        from_expr = step_as.get("from", "")
        variables[var_name] = self._resolve_value(from_expr, variables)

    def _exec_if(self, step_as, variables, steps):
        condition_path = step_as.get("condition", "")
        args = step_as.get("condition_args", [])
        op_fn = self.evaluator.resolve_operation(condition_path)
        if op_fn is None:
            raise ValueError(f"Unknown operation: {condition_path}")

        resolved = [self._resolve_value(a, variables) for a in args]
        if op_fn(resolved[0], resolved[1]):
            then_step = step_as.get("then", "")
            if then_step and then_step in steps:
                return self._execute_step(then_step, steps, variables)

    def _exec_for_each(self, step_as, variables, steps):
        index_name = step_as.get("index", "i")
        from_val = int(step_as.get("from", 0))
        to_length_key = step_as.get("to_length", "")
        to_val = len(variables[to_length_key]) - 1
        body_step = step_as.get("body", "")

        for i in range(from_val, to_val + 1):
            variables[index_name] = i
            if body_step and body_step in steps:
                self._execute_step(body_step, steps, variables)
        if index_name in variables:
            del variables[index_name]

    def _exec_return(self, step_as, variables):
        var_name = step_as.get("variable", "")
        return variables.get(var_name)
