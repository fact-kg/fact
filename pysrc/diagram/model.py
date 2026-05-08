from dataclasses import dataclass, field


@dataclass
class Node:
    id: str
    label: str
    type: str = ""
    x: float = 0
    y: float = 0
    width: float = 80
    height: float = 40
    style: str = ""


@dataclass
class Edge:
    source: str
    target: str
    label: str = ""
    style: str = ""


@dataclass
class Diagram:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    width: float = 800
    height: float = 600

    def add_node(self, id, label, **kwargs) -> Node:
        node = Node(id=id, label=label, **kwargs)
        self.nodes.append(node)
        return node

    def add_edge(self, source, target, **kwargs) -> Edge:
        edge = Edge(source=source, target=target, **kwargs)
        self.edges.append(edge)
        return edge
