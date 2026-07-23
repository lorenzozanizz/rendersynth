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

class PixelMapExtractor(Extractor):
    """

    """

    def __init__(
        self, context, datatype: Literal['depth', 'normal'] ='depth', normalize_depth: bool = True,
        black_near: bool = True
    ):
        self.ctx = context

        self.timings = {}
        # Per pixel data map. This will be lazily initialized as a numpy array with required
        # pixel information.
        self.data_map = None

        self.black_near = black_near
        self.datatype = datatype
        self.normalized_depth = normalize_depth

        self.declared_strategy: Optional["IOStrategy"] = None
        self.active_output_context_node = None
        # Path extract() should attach to its Label, computed by prepare_for_shot() once the
        # strategy (hence the output directory/filename) is known for the
        # current shot. For more infos see prepare_for_shot()
        self._pending_map_path: Optional[str] = None

    def extract(self,
        visible_objects: dict[Any, list],
        classifier: ClassificationEngine,
        entity_data,
        camera,
        estimate_visibility: bool = True, **kwargs
    ) -> LabelData:
        """ Extract the required data. Per-pixel maps (depth/normal) aren't computed here,
        instead they're written to disk directly by the compositor node graph set up in get_context()
        by the render call that happens around this extractor's use (prepare_for_shot
        points the compositor's output node at the right path, the render call
        triggers the compositor to write the file, finalize_shot renames it to its
        final name). This method's job is just to report that path as a Label so the
        rest of the pipeline has something to point to.

        :param visible_objects: the unused raytracing data  (reduced to minimum)
        :param classifier: the unused classifier
        :param entity_data: unused entity data
        :param camera: unused camera
        :param estimate_visibility: unused visibility flag
        :param kwargs: None
        :return: A LabelData with a single Label if a shot has been
            prepared (see prepare_for_shot), otherwise an empty LabelData.
        """
        ret_data = LabelData()

        with (TimingContext(self.timings, 'labeling')):
            if self._pending_map_path is not None:
                ret_data.add(
                    Label(
                        obj_or_entity_name=self.datatype,
                        cls=None,
                        annotation_type="per_pixel",
                        is_entity=False,
                        visibility=1.0,
                        per_pixel_map=self._pending_map_path,
                    )
                )

        return ret_data

    def get_estimated_visibility(self) -> dict[Union[str, Any], float]:
        """ Get the estimated visibility for entities and objects """
        return {}

    def get_visible_entities(self):
        return ()

    def get_labeling_time(self) -> float:
        """ Get the time it took to compute the boxes and the visible objects """
        return self.timings['labeling']

    def get_visible_objects(self) -> Iterable[Any]:
        """ Get the visible objects """
        return ()

    def map_boxes(self, conv_func: Callable = None) -> Iterable[Any]:
        """ Get the camera centered bounding boxes """
        return ()

    def get_bbox_objects(self) -> dict:
        """ Get the mappings from object to bounding boxes """
        return {}

    def get_bbox_entities(self) -> dict:
        """ Get the mappings from object to bounding boxes """
        return {}

    # A development note:
    # generating programmatically compositing nodes is very undocumented in BPY.
    # https://imoverclocked.blogspot.com/2011/08/blender-25-compositing-from-python.html
    # was very helpful in the basics, and Blender's console was used to infer the
    # nodes IDs.
    # ! This code is very brittle to breaking changes in the Blender architecture !
    class CompositorDepthContext:

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

        def __init__(self, context, config: dict):
            self.config = config
            self.ctx = context
            self.prev_scene_use_nodes = None
            self.prev_scene_render_layer_z = None

            self.compositor = NodeCompositor(context=self.ctx)

        def __enter__(self):
            scene = self.ctx.scene

            # Initially extract the current render layer data.
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

            output_node = self.compositor.get_node("file_output")
            output_node.format.color_management = "OVERRIDE"
            output_node.format.view_settings.view_transform = "Raw"

            # Register the nodes together so that we can remove them at the same time when exiting
            self.compositor.register_names_as_group('depth_tree', self.name_types_depth.keys())

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

    class CompositorNormalContext:
        """

        """

        name_types_normals = {
            'render_layer': ('CompositorNodeRLayers', []),
            'file_output': ('CompositorNodeOutputFile', []),
            'normalize_node': ('ShaderNodeVectorMath', [{"name": "operation", "value": "NORMALIZE"}]),
            'add_node': ('ShaderNodeVectorMath', [{"name": "operation", "value": "ADD"}]),
            'multiply_node': ('ShaderNodeVectorMath', [{"name": "operation", "value": "MULTIPLY"}]),
            'separate_xyz': ('ShaderNodeSeparateXYZ', []),
            'combine_color': ('CompositorNodeCombineColor', [])
        }

        link_mappings_normals = {
            (('render_layer', 'normalize_node'), ('Normal', 0)),
            (('normalize_node', 'add_node'), (0, 0)),
            (('add_node', 'multiply_node'), (0, 0)),
            (('multiply_node', 'separate_xyz'), (0, 0)),
            (('separate_xyz', 'combine_color'), (0, 0)),
            (('separate_xyz', 'combine_color'), (1, 1)),
            (('separate_xyz', 'combine_color'), (2, 2)),
            (('combine_color', 'file_output'), (0, 0))
        }

        default_assignments_normal = {
            'add_node': (
                (1, 0, 1.0),
                (1, 1, 1.0),
                (1, 2, 1.0),
            ),
            'multiply_node': (
                (1, 0, 0.5),
                (1, 1, 0.5),
                (1, 2, 0.5),
            ),
            'file_output': (
                ('base_path', ''),
            )
        }

        def __init__(self, context, config: dict):
            self.config = config
            self.ctx = context
            self.prev_scene_use_nodes = None
            self.prev_scene_render_layer_normal = None

            self.compositor = NodeCompositor(context=self.ctx)

        def __enter__(self):
            scene = self.ctx.scene

            # Initially extract the current render layer data.
            self.prev_scene_use_nodes = scene.use_nodes
            self.prev_scene_render_layer_z = scene.view_layers["ViewLayer"].use_pass_z
            self.prev_scene_render_layer_normal = scene.view_layers["ViewLayer"].use_pass_normal

            # We have to instruct the rendering pass to preserve the normal
            scene.view_layers["ViewLayer"].use_pass_normal = True

            # Create the composite nodes: first create tbe nodes, then link them together and
            # finally set the node defaults (e.g. config the nodes)
            self.compositor.gen_nodes(self.name_types_normals)
            self.compositor.link_nodes(self.link_mappings_normals)
            self.compositor.set_node_defaults(self.default_assignments_normal)

            output_node = self.compositor.get_node("file_output")
            output_node.format.color_management = "OVERRIDE"
            output_node.format.view_settings.view_transform = "Raw"

            # Register the nodes together so that we can remove them at the same time when exiting
            self.compositor.register_names_as_group('normal', self.name_types_normals.keys())

        def __exit__(self, exc_type, exc_val, exc_tb):
            scene = self.ctx.scene

            # First restore the previous scene render layer data.
            scene.use_nodes = self.prev_scene_use_nodes
            scene.view_layers["ViewLayer"].use_pass_normal = self.prev_scene_render_layer_normal

            # Remove the composite nodes
            self.compositor.delete_node_group('normal')
            self.compositor.unregister_group('normal')

        def set_write_path(self, directory: Union[str, Path], name: str) -> None:
            node = self.compositor.get_node('file_output')
            if node is None:
                return
            node.base_path = directory
            node.file_slots[0].path = name

    def get_context(self) -> AbstractContextManager:
        config = {
            'normalize_depth': self.normalized_depth,
            'black_near': self.black_near,
        }
        if self.datatype == 'depth':
            self.active_output_context_node = PixelMapExtractor.CompositorDepthContext(self.ctx, config)
            return self.active_output_context_node
        else:
            self.active_output_context_node =  PixelMapExtractor.CompositorNormalContext(self.ctx, config)
            return self.active_output_context_node

    def prepare_for_shot(self, shot_idx: int) -> None:
        # For the default implementation, simply ignore the preparation: nothing needs
        # to be set up.
        if self.declared_strategy is None:
            self._pending_map_path = None
        else:
            write_dir = self.declared_strategy.get_full_dir_for(shot_idx, "map")
            filename = self.declared_strategy.get_filename_for(shot_idx, "map")
            self.active_output_context_node.set_write_path(write_dir, filename)
            # map_path = self.declared_strategy.get_full_path_for(shot_idx, "map")
            # print("Setting as output path: ", map_path)
            # self.active_output_context_node.set_write_path(map_path)

            # The compositor's file output node writes with Blender's current-frame
            # number appended to filename BUT finalize_shot() strips that suffix by renaming the
            # produced file to exactly this path once rendering has completed. Keep the ".png"
            # extension in sync with finalize_shot().
            self._pending_map_path = os.path.join(write_dir, f"{filename}.png")
        return

    def declare_folder_structure(self, folder_strategy: "IOStrategy") -> None:
        """

        :param folder_strategy:
        :return:
        """
        # The default implementation ignores the folder structure as it does not
        # require it.
        self.declared_strategy = folder_strategy

    @staticmethod
    def needs_folder_structure() -> bool:
        # The compositor writes depth/normal maps directly to disk, outside the
        # normal writer pipeline, so it needs to know a write location even when there is
        # no real OutputWriter (e.g. single-shot preview generation).
        return True

    def finalize_shot(self, shot_idx: int) -> None:
        """

        :param shot_idx:
        :return:
        """
        if self.declared_strategy is None or self.active_output_context_node is None:
            return

        directory = self.declared_strategy.get_full_dir_for(shot_idx, "map")
        prefix = self.declared_strategy.get_filename_for(shot_idx, "map")
        frame = self.ctx.scene.frame_current  # whatever Blender used as suffix for the current frame,
        # which is what is getting appended to the output of the compositor
        ext = ".png"  # or read from config/format

        produced = os.path.join(directory, f"{prefix}{frame:04d}{ext}")
        target = os.path.join(directory, f"{prefix}{ext}")

        if os.path.exists(produced) and produced != target:
            if os.path.exists(target):
                os.remove(target)
            os.rename(produced, target)