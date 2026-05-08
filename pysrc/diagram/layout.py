from abc import ABC, abstractmethod
from diagram.model import Diagram, Node, Edge


class Layout(ABC):
    @abstractmethod
    def layout(self, **kwargs) -> Diagram:
        pass


class TreeLayout(Layout):
    def __init__(self, node_width=100, node_height=40,
                 h_spacing=20, v_spacing=60):
        self.node_width = node_width
        self.node_height = node_height
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing

    def layout(self, root, children_fn, label_fn=None, type_fn=None) -> Diagram:
        if label_fn is None:
            label_fn = lambda n: str(n)
        if type_fn is None:
            type_fn = lambda n: ""

        diagram = Diagram()
        positions = {}
        counter = [0]

        def count_leaves(node):
            children = children_fn(node)
            if not children:
                return 1
            return sum(count_leaves(c) for c in children)

        def assign_positions(node, depth, leaf_offset):
            node_id = f"n{counter[0]}"
            counter[0] += 1

            children = children_fn(node)
            if not children:
                x = leaf_offset * (self.node_width + self.h_spacing)
                y = depth * (self.node_height + self.v_spacing)
                diagram.add_node(node_id, label_fn(node), type=type_fn(node),
                                 x=x, y=y, width=self.node_width, height=self.node_height)
                positions[id(node)] = node_id
                return leaf_offset + 1

            child_ids = []
            current_offset = leaf_offset
            for child in children:
                current_offset = assign_positions(child, depth + 1, current_offset)
                child_ids.append(positions[id(child)])

            first_child = next(n for n in diagram.nodes if n.id == child_ids[0])
            last_child = next(n for n in diagram.nodes if n.id == child_ids[-1])
            x = (first_child.x + last_child.x) / 2
            y = depth * (self.node_height + self.v_spacing)

            diagram.add_node(node_id, label_fn(node), type=type_fn(node),
                             x=x, y=y, width=self.node_width, height=self.node_height)
            positions[id(node)] = node_id

            for child_id in child_ids:
                diagram.add_edge(node_id, child_id)

            return current_offset

        assign_positions(root, 0, 0)

        if diagram.nodes:
            max_x = max(n.x + n.width for n in diagram.nodes)
            max_y = max(n.y + n.height for n in diagram.nodes)
            diagram.width = max_x + self.h_spacing
            diagram.height = max_y + self.v_spacing

        return diagram
