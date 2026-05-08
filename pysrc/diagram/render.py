from diagram.model import Diagram


def to_json(diagram: Diagram) -> dict:
    return {
        "width": diagram.width,
        "height": diagram.height,
        "nodes": [
            {
                "id": n.id,
                "label": n.label,
                "type": n.type,
                "x": n.x,
                "y": n.y,
                "width": n.width,
                "height": n.height,
                "style": n.style,
            }
            for n in diagram.nodes
        ],
        "edges": [
            {
                "source": e.source,
                "target": e.target,
                "label": e.label,
                "style": e.style,
            }
            for e in diagram.edges
        ],
    }
