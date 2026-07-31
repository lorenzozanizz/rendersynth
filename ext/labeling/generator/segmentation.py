from contextlib import AbstractContextManager
from typing import Union, List, Tuple, Collection
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
    Extractor producing a flat-color class segmentation map using a dynamically
    generated Cryptomatte -> color-mix -> color-add compositor chain, with one
    Cryptomatte/Mix pair per class present in the scene.
    """

    def get_estimated_visibility(self) -> dict[str | Any, float]:
        pass

    def get_visible_entities(self) -> Iterable[Any]:
        pass

    def __init__(self, context, png_or_exr: Literal["png", "exr"] = "png"):
        self.ctx = context
        self.timings = {}
        self.png_or_exr = png_or_exr

        self.declared_strategy: Optional["IOStrategy"] = None
        self.active_output_context_node = None
        self._pending_map_path: Optional[str] = None
        self._matte_pending_map = None
        self.declared_output_nodes = []


    def extract(self, visible_objects, classifier, entity_data, camera, estimate_visibility: bool = True,
                rendered_shot_data: Any = None, **kwargs) -> LabelData:
        """ Mirrors PixelMapExtractor.extract(): the actual pixel data is written
        directly to disk by the compositor node graph during the render call that
        wraps this extractor's use. This just reports the resulting path.
        """
        ret_data = LabelData()

        with TimingContext(self.timings, 'labeling'):
            if self._pending_map_path is not None:
                ret_data.add(
                    Label(
                        obj_or_entity_name="segmentation",
                        cls=None,
                        annotation_type="per_pixel",
                        is_entity=False,
                        visibility=1.0,
                        per_pixel_map=self._pending_map_path,
                    )
                )

        return ret_data

    def declare_scene_objects(self, all_objects: Iterable, class_engine: ClassificationEngine) -> None:
        """

        :param all_objects:
        :param class_engine:
        :return:
        """
        # Compute the required matte mappings
        matte_mappings = class_engine.request_full_mapping(list(all_objects))
        self._matte_pending_map = matte_mappings

    def prepare_for_shot(self, shot_idx: int) -> None:
        if self.declared_strategy is None:
            self._pending_map_path = None
            return

        write_dir = self.declared_strategy.get_full_dir_for(shot_idx, "segmentation")
        filename = self.declared_strategy.get_filename_for(shot_idx, "segmentation")

        self.active_output_context_node.set_write_path(write_dir, filename)

        self._pending_map_path = os.path.join(write_dir, f"{filename}.{self.png_or_exr}")

    def get_context(self) -> AbstractContextManager:
        config = {"png_or_exr": self.png_or_exr}
        self.active_output_context_node = SegmentationExtractor.CryptoMatteSegmentationCompositor(self.ctx, config)
        self.active_output_context_node.assign_mappings(self._matte_pending_map)
        return self.active_output_context_node

    def declare_folder_structure(self, folder_strategy: "IOStrategy") -> None:
        self.declared_strategy = folder_strategy

    def finalize_shot(self, shot_idx: int) -> None:
        if self.declared_strategy is None or self.active_output_context_node is None:
            return

        directory = self.declared_strategy.get_full_dir_for(shot_idx, "segmentation")
        prefix = self.declared_strategy.get_filename_for(shot_idx, "segmentation")
        frame = self.ctx.scene.frame_current
        ext = f".{self.png_or_exr}"

        produced = os.path.join(directory, f"{prefix}{frame:04d}{ext}")
        target = os.path.join(directory, f"{prefix}{ext}")

        if os.path.exists(produced) and produced != target:
            if os.path.exists(target):
                os.remove(target)
            os.rename(produced, target)

    @staticmethod
    def needs_folder_structure() -> bool:
        # The compositor writes depth/normal maps directly to disk, outside the
        # normal writer pipeline, so it needs to know a write location even when there is
        # no real OutputWriter (e.g. single-shot preview generation).
        return True

    # A development note:
    # generating programmatically compositing nodes is very undocumented in BPY.
    # See the same comment in per_pixel.py.
    # The following crypto matte guide was especially useful:
    # https://www.graphicsandprogramming.net/eng/tutorial/blender/compositor/cryptomatte-in-blender2-8-a-revolution
    class CryptoMatteSegmentationCompositor:
        """ Builds a variable-length Cryptomatte -> Mix -> Add compositor chain,
        with one Cryptomatte + color Mix node per class present in the scene, and
        N-1 chained additive Mix nodes accumulating them into a single class map.
        """

        GROUP_NAME = "segmentation_tree"

        # Utilities for the NodeCompositor object to create nodes.
        base_nodes = {
            "render_layer": ('CompositorNodeRLayers', []),
        }

        base_link_config: set = set()

        base_default_config = {
        }

        def __init__(self, context, config: dict):
            self.config = config
            self.ctx = context

            self.prev_scene_use_nodes = None
            self.prev_use_pass_cryptomatte_object = None

            self.compositor = NodeCompositor(context=self.ctx)
            self.output_nodes: List[str] = []

            self.matte_mappings: Optional[dict] = None
            # Configurations taken from the outer extractor straight out of the
            # blender scene
            self.png_or_exr: Literal["png", "exr"] = config.get("png_or_exr")
            self.split_map_per_class: Literal["single", "per_class"] = config.get("split_map_per_class")
            self.discretize = config.get("discretize")

        def __enter__(self):
            scene = self.ctx.scene
            view_layer = scene.view_layers["ViewLayer"]

            self.prev_scene_use_nodes = scene.use_nodes
            self.prev_use_pass_cryptomatte_object = view_layer.use_pass_cryptomatte_object

            scene.use_nodes = True
            view_layer.use_pass_cryptomatte_object = True

            # This function is the main hook for the composite tree constructor, which changes
            # based on the output format (EXR/PNG) and the choice of distinguishing one mask per class
            self.rebuild_for_objects(self.matte_mappings)

            for output_node in self.output_nodes:
                output_node = self.compositor.get_node(output_node)
                if self.png_or_exr == 'PNG':
                    output_node.format.file_format = 'PNG'
                    # Like other extractors we need to disable color management and gamma correction
                    # to get the real colors output.
                    output_node.format.color_management = "OVERRIDE"
                    output_node.format.view_settings.view_transform = "Raw"
                else:
                    # OpenEXR raw numerical formatting.
                    output_node.format.file_format = "OPENEXR MULTILAYER"
                    output_node.format.color_management = "OVERRIDE"
                    # The data we have to store is not a color data, so we instruct openexr to NOt apply any
                    # gamma correction or the sorts.
                    output_node.format.linear_colorspace_settings.name = "NON-COLOR"


            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            scene = self.ctx.scene
            view_layer = scene.view_layers["ViewLayer"]

            scene.use_nodes = self.prev_scene_use_nodes
            view_layer.use_pass_cryptomatte_object = self.prev_use_pass_cryptomatte_object

            # This deletes all nodes, default and non default.
            self.compositor.delete_node_group(self.GROUP_NAME)
            self.compositor.unregister_group(self.GROUP_NAME)

        def assign_mappings(self, mappings: Dict[str, LabelClass]) -> None:
            self.matte_mappings = mappings

        def set_write_path(self, directory: Union[str, Path], name: str) -> None:
            node = self.compositor.get_node("file_output")
            if node is None:
                return
            node.base_path = str(directory)
            node.file_slots[0].path = name

        def build_exr_multiple_outputs(self, class_to_objects: Dict[str, List[str]], class_colors: Dict[str, tuple]) -> None:
            pass

        def build_exr_single_output(self, class_to_objects: Dict[str, List[str]], class_colors: Dict[str, tuple]) -> None:
            pass

        def rebuild_for_objects(self, mapping: Dict[str, LabelClass]) -> None:
            """ Tears down the previous per-class node chain (if any) and rebuilds
            it from the current object -> class mapping. Must run after __enter__.
            """
            if self.matte_mappings is None:
                raise RuntimeError("Cannot construct a compositor tree with cryptomattes as the mappings "
                                   "were not previously assigned to the compositor context. ")

            class_to_objects: Dict[str, List[str]] = {}
            class_colors: Dict[str, tuple] = {}
            for obj_name, label_cls in mapping.items():
                cls_id = str(label_cls.class_id)
                class_to_objects.setdefault(cls_id, []).append(obj_name)
                class_colors[cls_id] = tuple(label_cls.color)

            if not class_to_objects:
                # Nothing classified: leave file_output unlinked rather than erroring.
                return

            builder_func = None
            if self.png_or_exr == "png" and self.split_map_per_class == "single":
                builder_func = self.build_png_single_output
            elif self.png_or_exr == "png" and self.split_map_per_class == "per_class":
                builder_func = self.build_png_multiple_outputs
            elif self.png_or_exr == "exr" and self.split_map_per_class == "single":
                builder_func = self.build_exr_single_output
            elif self.png_or_exr == "exr" and self.split_map_per_class == "per_class":
                builder_func = self.build_exr_multiple_outputs
            if builder_func is None:
                raise ValueError("The configuration parameters for the segmentation extractor are incorrect "
                                 "and do not correspond to a compositor node tree builder.")

            node_config, link_config, default_config, class_node_names = builder_func(
                class_to_objects, class_colors
            )

            # Enrich the computed nodes with the default configurations.
            node_config.update(self.base_nodes)
            default_config.update(self.base_default_config)

            self.compositor.gen_nodes(node_config)
            self.compositor.link_nodes(link_config)
            self.compositor.set_node_defaults(default_config)

            class_node_names = list(class_node_names) + list(self.base_nodes.keys())
            self.compositor.register_names_as_group(self.GROUP_NAME, class_node_names)


        def delete_previous_node_group(self) -> None:
            if 'segmentation_classes' in self.compositor.groups:
                self.compositor.delete_node_group('segmentation_classes')
                self.compositor.unregister_group('segmentation_classes')
            self.output_nodes = None

        def build_png_single_output(
            self, class_to_objects: Dict[str, List[str]], class_colors: Dict[str, tuple]
        ) -> Tuple[dict, set, dict, list]:
            """ Builds one Cryptomatte + color Mix node per class, then chains N-1 additive
            Mix nodes to accumulate them into a single class map. This is used for PNG output,
            one file per shot mode. One-file-per-class distinguishes each cryptomatte object node.
            """
            node_config: dict = {}
            link_config: set = set()
            default_config: dict = {}
            class_node_names: list = []

            view_layer_name = self.ctx.scene.view_layers["ViewLayer"].name
            layer_id = f"{view_layer_name}.CryptoObject"

            prev_color_add_name: Optional[str] = None

            node_config["file_output"] =  ('CompositorNodeOutputFile', [])

            for cls_id, obj_names in class_to_objects.items():
                crypto_name = f"cryptomatte_{cls_id}"
                mix_name = f"mix_{cls_id}"
                thresh_name = f"threshold_{cls_id}"
                color = class_colors.get(cls_id, (1.0, 1.0, 1.0))

                node_config[crypto_name] = (
                    'CompositorNodeCryptomatteV2',
                    [
                        {"name": "source", "value": "RENDER"},
                        {"name": "layer_name", "value": layer_id},
                        {"name": "matte_id", "value": ",".join(obj_names)},
                    ]
                )
                if self.discretize:
                    # Add a threshold node and put it in between the matte and the mixer to get clean boundaries.
                    node_config[thresh_name] = (
                        'CompositorNodeMath',
                        [
                            {"name": "operation", "value": "GREATER_THAN"},
                        ]
                    )
                node_config[mix_name] = (
                    'ShaderNodeMix',
                    [
                        {"name": "data_type", "value": "RGBA"},
                        {"name": "blend_type", "value": "MIX"},
                    ]
                )
                class_node_names.extend([crypto_name, mix_name])

                link_config.add((("render_layer", crypto_name), ('Image', 'Image')))
                if not self.discretize:
                    link_config.add(((crypto_name, mix_name), ('Matte', 'Factor')))
                else:
                    # If we are discretizing, we need an intermediate link.
                    link_config.add(((crypto_name, thresh_name), ('Matte', 0)))  # Matte -> Value input 0
                    link_config.add(((thresh_name, mix_name), ('Value', 'Factor')))  # thresholded -> Factor

                # Set as default value for the "A" and "B of the mixer just
                # the color to be written for the class and full BLACK (0, 0, 0, 1.0) RGBA
                default_config[mix_name] = [
                    ('A', 0, 0.0), ('A', 1, 0.0), ('A', 2, 0.0), ('A', 3, 1.0),
                    ('B', 0, color[0]), ('B', 1, color[1]), ('B', 2, color[2]), ('B', 3, 1.0),
                ]

                if prev_color_add_name is None:
                    prev_color_add_name = mix_name
                else:
                    add_name = f"add_{cls_id}"
                    # If there is already a previous add color, e.g. we are not at the first
                    # considered class, we have to mix the two colors with a
                    # factor of 1.0
                    node_config[add_name] = (
                        'ShaderNodeMix',
                        [
                            {"name": "data_type", "value": "RGBA"},
                            {"name": "blend_type", "value": "ADD"},
                        ]
                    )
                    class_node_names.append(add_name)

                    link_config.add(((prev_color_add_name, add_name), ('Result', 'A')))
                    link_config.add(((mix_name, add_name), ('Result', 'B')))
                    # THIS is important: without this we would dim out some of the color information
                    # for no reason.
                    default_config[add_name] = [(0, 1.0)]

                    prev_color_add_name = add_name

            final_node_name = prev_color_add_name
            self.output_nodes = ["file_output"]
            if final_node_name is not None:
                link_config.add(
                    # Finally link the last node to the file output, the last node is
                    # the mix/add of all previous nodes.
                    ((final_node_name, "file_output"), ("Result", "Image"))
                )
            return node_config, link_config, default_config, class_node_names

        def build_png_multiple_outputs(self, class_to_objects: Dict[str, List[str]], class_colors: Dict[str, tuple]) \
                -> Tuple[dict, set, dict, list]:
            """ Builds one Cryptomatte + color Mix node per class, then chains N-1 additive
            Mix nodes to accumulate them into a single class map. This is used for PNG output,
            one file per shot mode. One-file-per-class distinguishes each cryptomatte object node.
            """
            node_config: dict = {}
            link_config: set = set()
            default_config: dict = {}
            class_node_names: list = []

            view_layer_name = self.ctx.scene.view_layers["ViewLayer"].name
            layer_id = f"{view_layer_name}.CryptoObject"

            # Reset the output nodes
            self.output_nodes = []

            for cls_id, obj_names in class_to_objects.items():

                crypto_name = f"cryptomatte_{cls_id}"
                mix_name = f"mix_{cls_id}"
                out_name = f"out_{cls_id}"
                color = class_colors.get(cls_id, (1.0, 1.0, 1.0))

                node_config[crypto_name] = (
                    'CompositorNodeCryptomatteV2',
                    [
                        {"name": "source", "value": "RENDER"},
                        {"name": "layer_name", "value": layer_id},
                        {"name": "matte_id", "value": ",".join(obj_names)},
                    ]
                )
                node_config[mix_name] = (
                    'ShaderNodeMix',
                    [
                        {"name": "data_type", "value": "RGBA"},
                        {"name": "blend_type", "value": "MIX"},
                    ]
                )
                class_node_names.extend([crypto_name, mix_name])

                link_config.add((("render_layer", crypto_name), ('Image', 'Image')))
                link_config.add(((crypto_name, mix_name), ('Matte', 'Factor')))

                # Set as default value for the "A" and "B of the mixer just
                # the color to be written for the class and full BLACK (0, 0, 0, 1.0) RGBA
                default_config[mix_name] = [
                    ('A', 0, 0.0), ('A', 1, 0.0), ('A', 2, 0.0), ('A', 3, 1.0),
                    ('B', 0, color[0]), ('B', 1, color[1]), ('B', 2, color[2]), ('B', 3, 1.0),
                ]
                # No Add node should be inserted here, instead insert an output node and configure it.
                node_config[out_name] = (
                    'CompositorNodeOutputFile', []
                )
                self.output_nodes.append("file_output")
                link_config.add(((mix_name, out_name), ("Result", "Image")))

            return node_config, link_config, default_config, class_node_names