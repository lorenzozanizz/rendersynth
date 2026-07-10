"""

"""


from .tree_constants import *
from ..utils.logger import UniqueLogger
from ..constants import DISTRO_EDITOR_NAME

from typing import Dict, List, Any, Optional
import bpy


class NodeDistributionSerializer:
    """ Serialize a Distribution node tree into a plain, JSON-ready dict. """

    @staticmethod
    def _socket_index(sockets, target) -> int:
        for i, s in enumerate(sockets):
            if s == target:
                return i
        return -1

    @staticmethod
    def serialize(tree) -> Dict[str, Any]:
        if tree is None:
            raise ValueError("Cannot serialize a missing distribution tree")

        nodes_out: List[Dict[str, Any]] = []
        root_id: Optional[str] = None

        for node in tree.nodes:
            bl = node.bl_idname
            prop_names = NODE_PROPERTIES.get(bl)
            if prop_names is None:
                continue  # skip frames, reroutes and anything we don't model

            params = {name: NodeDistributionSerializer._read(node, name) for name in prop_names}

            input_defaults: Dict[str, float] = {}
            for i, sock in enumerate(node.inputs):
                if sock.bl_idname == SCALAR_IDNAME:
                    input_defaults[str(i)] = float(getattr(sock, 'default_value', 0.0))

            nodes_out.append({
                'id': node.name,
                'bl_idname': bl,
                'params': params,
                'location': [float(node.location.x), float(node.location.y)],
                'input_defaults': input_defaults,
            })
            if bl == ROOT_IDNAME:
                root_id = node.name

        links_out: List[Dict[str, Any]] = []
        for link in tree.links:
            links_out.append({
                'from_node': link.from_node.name,
                'from_socket': NodeDistributionSerializer._socket_index(link.from_node.outputs, link.from_socket),
                'to_node': link.to_node.name,
                'to_socket': NodeDistributionSerializer._socket_index(link.to_node.inputs, link.to_socket),
            })

        return {
            'format': SERIALIZED_FORMAT,
            'version': SERIALIZED_VERSION,
            'name': tree.name,
            'root': root_id,
            'nodes': nodes_out,
            'links': links_out,
        }

    @staticmethod
    def to_json(tree, indent: int = 2) -> str:
        import json
        return json.dumps(NodeDistributionSerializer.serialize(tree), indent=indent)

    @staticmethod
    def _read(node, prop: str):
        # Enum -> identifier string, others -> their plain python value.
        return getattr(node, prop)


class NodeDistributionDeserializer:
    """ Rebuild a Distribution node tree from its serialized form.

    Two flat passes (no recursion): create every node and apply its properties
    and typed-in socket defaults, then recreate the links.
    """

    @staticmethod
    def deserialize(data: Dict[str, Any], name: Optional[str] = None):
        if data.get('format') != SERIALIZED_FORMAT:
            raise ValueError("Unrecognised distribution serialization format")

        tree_name = name or data.get('name') or 'Distribution'
        tree = bpy.data.node_groups.new(tree_name, DISTRO_EDITOR_NAME)

        id_to_node: Dict[str, Any] = {}

        # Pass 1: nodes, properties, socket defaults.
        for nd in data.get('nodes', []):
            bl = nd['bl_idname']
            if bl not in NODE_PROPERTIES:
                UniqueLogger.quick_log(f"Skipping unknown node type during rebuild: {bl}")
                continue
            node = tree.nodes.new(bl)
            # Property order in NODE_PROPERTIES puts structural props first, so
            # dynamic sockets (Vectorize/Selector/Math/...) exist before linking.
            for prop in NODE_PROPERTIES[bl]:
                if prop in nd.get('params', {}):
                    try:
                        setattr(node, prop, nd['params'][prop])
                    except Exception as exc:  # noqa: BLE001 - one bad prop shouldn't abort
                        UniqueLogger.quick_log(f"Could not set {bl}.{prop}: {exc}")
            loc = nd.get('location')
            if loc and len(loc) == 2:
                node.location = (loc[0], loc[1])
            for idx_str, val in nd.get('input_defaults', {}).items():
                idx = int(idx_str)
                if idx < len(node.inputs) and node.inputs[idx].bl_idname == SCALAR_IDNAME:
                    node.inputs[idx].default_value = val
            id_to_node[nd['id']] = node

        # Pass 2: links.
        for lk in data.get('links', []):
            src = id_to_node.get(lk['from_node'])
            tgt = id_to_node.get(lk['to_node'])
            if src is None or tgt is None:
                continue
            fi, ti = lk['from_socket'], lk['to_socket']
            if 0 <= fi < len(src.outputs) and 0 <= ti < len(tgt.inputs):
                tree.links.new(src.outputs[fi], tgt.inputs[ti])
            else:
                UniqueLogger.quick_log(f"Dropping out-of-range link {lk}")

        return tree

    @staticmethod
    def from_json(text: str, name: Optional[str] = None):
        import json
        return NodeDistributionDeserializer.deserialize(json.loads(text), name=name)