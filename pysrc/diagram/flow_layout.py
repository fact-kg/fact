from diagram.model import Diagram, Node, Edge
from diagram.layout import Layout

STEP_SHAPES = {
    "computer/algorithm/assign": "rect",
    "computer/algorithm/assign_indexed": "rect",
    "computer/algorithm/if": "diamond",
    "computer/algorithm/indexed/for_each": "hexagon",
    "computer/algorithm/evaluate_expression": "rect",
    "computer/algorithm/evaluate_expression_fact": "rect",
    "computer/algorithm/return": "rounded",
}


class FlowLayout(Layout):
    def __init__(self, node_width=160, node_height=50,
                 h_spacing=60, v_spacing=40, diagram_padding=20):
        self.node_width = node_width
        self.node_height = node_height
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.diagram_padding = diagram_padding

    def layout(self, steps, first_step) -> Diagram:
        diagram = Diagram()
        visited = set()
        self._place_chain(first_step, steps, diagram, 0, 0, 1, visited)

        if diagram.nodes:
            max_x = max(n.x + n.width for n in diagram.nodes)
            max_y = max(n.y + n.height for n in diagram.nodes)
            has_loop = any(e.style == "loop" for e in diagram.edges)
            loop_extra = self.h_spacing if has_loop else 0
            diagram.width = max_x + self.diagram_padding + loop_extra
            diagram.height = max_y + self.diagram_padding + (self.v_spacing if has_loop else 0)

        return diagram

    def _col_x(self, col):
        return col * (self.node_width + self.h_spacing)

    def _row_y(self, row):
        return row * (self.node_height + self.v_spacing)

    def _add_node(self, diagram, name, step_type, step_as, row, col):
        shape = STEP_SHAPES.get(step_type, "rect")
        label = self._make_label(name, step_type, step_as)
        return diagram.add_node(name, label, type=shape,
                                x=self._col_x(col), y=self._row_y(row),
                                width=self.node_width, height=self.node_height)

    def _step_info(self, step_name, steps):
        step = steps[step_name]
        step_type = step["type"]
        step_as = step.get("val_as", {}).get(step_type, {})
        return step_type, step_as

    def _place_chain(self, step_name, steps, diagram, row, col,
                     branch_col, visited):
        if step_name in visited or step_name not in steps:
            return row

        visited.add(step_name)
        step_type, step_as = self._step_info(step_name, steps)
        self._add_node(diagram, step_name, step_type, step_as, row, col)

        next_row = row + 1

        if step_type == "computer/algorithm/if":
            self._place_if_branch(step_name, step_as, steps, diagram,
                                  row, branch_col, visited)

        if step_type == "computer/algorithm/indexed/for_each":
            next_row = self._place_for_each(step_name, step_as, steps,
                                            diagram, row, branch_col, visited)

        next_step = step_as.get("next", "")
        if next_step and next_step in steps:
            edge_label = "done" if step_type == "computer/algorithm/indexed/for_each" else ""
            diagram.add_edge(step_name, next_step, label=edge_label)
            if next_step not in visited:
                return self._place_chain(next_step, steps, diagram,
                                         next_row, col, branch_col, visited)

        return next_row

    def _place_if_branch(self, parent_name, step_as, steps, diagram, row,
                         branch_col, visited):
        then_step = step_as.get("then", "")
        if not then_step or then_step not in steps or then_step in visited:
            return

        step_type, then_as = self._step_info(then_step, steps)
        self._add_node(diagram, then_step, step_type, then_as, row, branch_col)
        diagram.add_edge(parent_name, then_step, label="yes")
        visited.add(then_step)

    def _place_for_each(self, parent_name, step_as, steps, diagram, row,
                        branch_col, visited):
        body_step = step_as.get("body", "")
        if not body_step or body_step not in steps:
            return row + 1

        last_body = self._place_body_chain(body_step, steps, diagram,
                                           row, branch_col, branch_col + 1,
                                           visited)
        diagram.add_edge(parent_name, body_step, label="body")
        if last_body:
            diagram.add_edge(last_body, parent_name, label="loop", style="loop")

        max_body_y = max(
            (n.y for n in diagram.nodes if n.x >= self._col_x(branch_col)
             and n.y >= self._row_y(row)),
            default=self._row_y(row))
        max_body_row = int(round(max_body_y / (self.node_height + self.v_spacing)))
        return max(row + 1, max_body_row + 1)

    def _place_body_chain(self, step_name, steps, diagram, row, col,
                          branch_col, visited):
        if step_name in visited or step_name not in steps:
            return None

        visited.add(step_name)
        step_type, step_as = self._step_info(step_name, steps)
        self._add_node(diagram, step_name, step_type, step_as, row, col)
        last_step = step_name

        if step_type == "computer/algorithm/if":
            then_step = step_as.get("then", "")
            if then_step and then_step in steps and then_step not in visited:
                then_type, then_as = self._step_info(then_step, steps)
                self._add_node(diagram, then_step, then_type, then_as,
                               row, col + 1)
                diagram.add_edge(step_name, then_step, label="yes")
                visited.add(then_step)
                last_step = then_step

        return last_step

    def _make_label(self, step_name, step_type, step_as):
        if step_type == "computer/algorithm/assign":
            var = step_as.get("variable", "")
            frm = step_as.get("from", "")
            return f"{var} = {frm}"
        if step_type == "computer/algorithm/if":
            args = step_as.get("condition_args", [])
            cond = step_as.get("condition", "").rsplit("/", 1)[-1]
            if len(args) >= 2:
                return f"{args[0]} {cond}\n{args[1]}?"
            return f"{cond}?"
        if step_type == "computer/algorithm/assign_indexed":
            container = step_as.get("container", "")
            idx = step_as.get("index", "")
            frm = step_as.get("from", "")
            return f"{container}[{idx}] = {frm}"
        if step_type == "computer/algorithm/indexed/for_each":
            idx = step_as.get("index", "i")
            frm = step_as.get("from", 0)
            to = step_as.get("to_length", step_as.get("to", "?"))
            if step_as.get("to_length"):
                return f"for {idx}={frm}..len({to})"
            return f"for {idx}={frm}..{to}"
        if step_type == "computer/algorithm/return":
            var = step_as.get("variable", "")
            return f"return {var}"
        if step_type == "computer/algorithm/evaluate_expression":
            result = step_as.get("result_variable", "")
            return f"{result} = expr"
        if step_type == "computer/algorithm/evaluate_expression_fact":
            expr = step_as.get("expression_fact", "")
            result = step_as.get("result_variable", "")
            return f"{result} = eval({expr})"
        return step_name
