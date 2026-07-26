from contextlib import AbstractContextManager
from typing import Callable, Union, Optional
from pathlib import Path
import os

from ..compositing_utils import NodeCompositor

from ...utils.timer import TimingContext

from ..class_engine import ClassificationEngine

from .extractor import Extractor
from .data_structure import *
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...core.io.io_strategy import IOStrategy

class SegmentationExtractor(Extractor):
    """

    """

    def extract(self, visible_objects, classifier, entity_data, camera, estimate_visibility: bool = True,
                rendered_shot_data: Any = None, **kwargs) -> LabelData:
        pass

    def get_estimated_visibility(self) -> dict[str | Any, float]:
        pass

    def get_visible_entities(self) -> Iterable[Any]:
        pass

    # A development note:
    # generating programmatically compositing nodes is very undocumented in BPY.
    # See the same comment in per_pixel.py.
    # The following crypto matte guide was especially useful:
    # https://www.graphicsandprogramming.net/eng/tutorial/blender/compositor/cryptomatte-in-blender2-8-a-revolution
    class CryptoMatteSegmentationCompositor:
        """ The main classin charge of generating the crypto matte chain of color mix and add
        to compose the class map (for PNGs) and the complete EXR file for EXR. """


        def __init__(self, context, config: dict):
            self.config = config
            self.ctx = context
            self.prev_scene_use_nodes = None
            self.prev_scene_render_layer_z = None
            self.png_or_exr: Literal["png", "exr"] = config.get("png_or_exr")

            self.compositor = NodeCompositor(context=self.ctx)

        name_types_depth = {
            'render_layer': ('CompositorNodeRLayers', []),
            'file_output': ('CompositorNodeOutputFile', []),
            'invert_node': ('CompositorNodeInvert', []),
            'normalize_node': ('CompositorNodeNormalize', []),
            'combine_node': ('CompositorNodeCombineColor', [])
        }

        link_mappings_depth = {
            (('render_layer', 'normalize_node'), ('Depth', 0)),
            (('normalize_node', 'combine_node'), (0, 2)),
            (('combine_node', 'invert_node'), (0, 1)),
            (('invert_node', 'file_output'), (0, 0))
        }

        default_assignments_depth = {
            'file_output': (('base_path', ''), ),
            'combine_node': (('mode', 'HSV'),)
        }

        def __enter__(self):
            scene = self.ctx.scene

            # Initially extract the current render layer data so that we can re-
            self.prev_scene_use_nodes = scene.use_nodes
            self.prev_scene_render_layer_z = scene.view_layers["ViewLayer"].use_pass_z
            self.prev_scene_render_layer_normal = scene.view_layers["ViewLayer"].use_pass_normal

            # We have to instruct the rendering pass to preserve the depth data.
            scene.view_layers["ViewLayer"].use_pass_z = True

            # Create the composite nodes: first create tbe nodes, then link them together and
            # finally set the node defaults (e.g. config the nodes)
            self.compositor.gen_nodes(self.name_types_depth)
            self.compositor.link_nodes(self.link_mappings_depth)
            self.compositor.set_node_defaults(self.default_assignments_depth)

            # This is necessary for PNG: Avoid the gamma correction by overrriding the color management.
            output_node = self.compositor.get_node("file_output")
            output_node.format.color_management = "OVERRIDE"
            output_node.format.view_settings.view_transform = "Raw"

            # Register the nodes together so that we can remove them at the same time when exiting
            self.compositor.register_names_as_group('segmentation_tree', self.name_types_depth.keys())

        def __exit__(self, exc_type, exc_val, exc_tb):
            scene = self.ctx.scene

            # First restore the previous scene render layer data.
            scene.use_nodes = self.prev_scene_use_nodes
            scene.view_layers["ViewLayer"].use_pass_z = self.prev_scene_render_layer_z

            # Remove the composite nodes
            self.compositor.delete_node_group('depth_tree')
            self.compositor.unregister_group('depth_tree')

        def set_write_path(self, directory: Union[str, Path], name: str) -> None:
            node = self.compositor.get_node('file_output')
            if node is None:
                return
            node.base_path = directory
            node.file_slots[0].path = name
