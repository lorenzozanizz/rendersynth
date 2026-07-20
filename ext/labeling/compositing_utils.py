""" Utilities for managing Blender compositor node trees.

This module provides the NodeCompositor class, a lightweight wrapper
around Blender's compositor API for generating, linking, configuring,
grouping, and deleting compositor nodes programmatically.
"""
from collections.abc import Iterable
from typing import Any, Optional

class NodeCompositor:
    """
    Utility class for creating, linking, configuring, and managing compositor
    nodes inside a Blender scene node tree.

    The compositor stores generated nodes internally and provides helper
    methods for node grouping, lookup, deletion, and socket resolution.
    """

    def __init__(self, context):

        self.ctx = context
        scene = self.ctx.scene
        self.nodes: dict = {}

        # If node compositing is disabled, enable it programmaticaly
        # with bpy
        if not scene.use_nodes:
            # Enable compositing.
            scene.use_nodes = True

        # extract the scene node_tree which is the composite tree.
        # self.tree = self.ctx.scene.node_tree
        self.tree = getattr(scene, "node_tree", None)
        print("Scene of the compositor", self.ctx.scene)
        print("Context of the compositor", self.tree)
        if self.tree is None:
            self.tree = getattr(scene, "compositing_node_group", None)

        self.groups: dict = {}

    def gen_nodes(self, node_generation_config: dict) -> None:
        """ Generate compositor nodes from a configuration mapping.

        The configuration dictionary maps a node identifier to a tuple
        containing the Blender node type and a list of attribute assignments.

        :param node_generation_config: Node creation configuration.
        """
        # Generate all the configuration nodes in the main composite tree.
        # Note: this does not automatically genereate the render view nor the output.
        # The user has full flexibility and must specify all nodes.
        for node_name, (node_type, config) in node_generation_config.items():
            node = self.tree.nodes.new(type=node_type)
            self.nodes[node_name] = node
            for (attr_name, attr_val) in (cfg.values() for cfg in config):
                setattr(node, attr_name, attr_val)

    def link_nodes(self, node_linking_config: set[tuple]) -> None:
        """ Create links between compositor nodes.
        Ports may be specified either by socket name or by socket index.

        :param node_linking_config: Node linking configuration.
        """
        for ((from_n, to_n), (from_port, to_port)) in node_linking_config:
            # This supports two different port specification, either with its name
            # or with its 0-beginning index in the node outputs/inputs
            from_node = self.nodes[from_n]
            to_node = self.nodes[to_n]
            if isinstance(from_port, str):
                from_port = self._get_port_number(from_node, from_port, 'output')
            if isinstance(to_port, str):
                to_port = self._get_port_number(to_node, to_port, 'input')

            self.tree.links.new(from_node.outputs[from_port], to_node.inputs[to_port])

    def set_node_defaults(self, node_defaults: dict) -> None:
        """ Assign default values and properties to existing nodes.
        Assignments may target:
        - A socket default value
        - A vector component inside a socket value
        - A node attribute directly

        :param node_defaults: Mapping of node names to assignment definitions.
        """

        if not self.nodes or self.nodes is None:
            raise RuntimeError(f"Cannot set node defaults on an uninitialized {NodeCompositor.__name__}")

        for name, info in node_defaults.items():

            node = self.nodes.get(name)
            # If the name was not previously registered, halt early.
            if node is None:
                raise RuntimeError(f"Cannot set node defaults for node {name}")

            for assignment in info:
                print(assignment)
                if len(assignment) == 3:
                    socket, index, v = assignment
                    # vector item to assign
                    node.inputs[socket].default_value[index] = v
                else:
                    socket, v = assignment

                    if isinstance(socket, int):
                        node.inputs[socket].default_value = v
                    else:
                        setattr(node, socket, v)

    def register_names_as_group(self, group_name: str, names: Iterable[str]) -> None:
        """ Register a collection of node names as a logical group.
        If the name already exists, this throws an exception.

        :param group_name: Name of the group to register.
        :param names: Tuple containing node names.
        """
        if group_name in self.groups:
            raise RuntimeError(f"Group {group_name} already exists, cannot be registered. ")
        self.groups[group_name] = tuple(names)

    def unregister_group(self, group_name: str) -> None:
        """ Remove a previously registered node group.

        :param group_name: Name of the group to unregister.
        """
        self.groups.pop(group_name, None)

    def delete_node_group(self, group_name: str) -> None:
        """ Delete all nodes belonging to a registered group.

        :param group_name: Name of the group to delete.
        """
        names = self.groups.get(group_name)
        if not names:
            return
        for name in names:
            self.delete_node(name)

    def delete_node(self, node_name: str) -> None:
        """ Delete a node and its internal registration. The deletion is unchecked, e.g.
        this can throw an exception. """
        self.tree.nodes.remove(self.nodes[node_name])
        self.nodes.pop(node_name, None)

    def get_node(self, name: str) -> Optional[Any]:
        """ Retrieve a node by name """
        return self.nodes.get(name)

    def get_nodes(self) -> dict[str, Any]:
        """ Retrieve all the registered non-deleted nodes """
        return self.nodes

    @staticmethod
    def _get_port_number(node, name: str, node_type: str):
        """ Resolve a socket name to its corresponding socket index.

        :param node: Blender compositor node instance.
        :param name: Socket name to search for.
        :param node_type: Socket collection type, either 'input' or 'output'.
        :return: Socket index if found, otherwise -1.
        """
        if node_type == 'output':
            for idx, socket in enumerate(node.outputs):
                if socket.name == name:
                    return idx
            return -1
        else:
            for idx, socket in enumerate(node.inputs):
                if socket.name == name:
                    return idx
            return -1