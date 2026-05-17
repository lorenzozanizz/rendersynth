from contextlib import AbstractContextManager
from typing import Iterable, Any, Union, Callable

import bpy

from .. import Extractor, LabelData
from ..class_engine import ClassificationEngine
from ...utils.timer import TimingContext

from ..ray_casting import (union_bounding_boxes, compute_camera_space_boxes, get_minimal_bounding_box_fast,
                           estimate_visibility_3d, compute_bbox_area, compute_area_ratio)
from ..class_engine import ClassificationEngine

from .extractor import Extractor
from .data_structure import *

class PixelMapExtractor(Extractor):



    def __init__(self, context, datatype: str='depth'):
        self.ctx = context

        self.timings: dict[str, float] = dict()
        self.visible_objects = dict()
        self.visible_entities = dict()
        self.estimated_visibility = dict()

        # Per pixel data map. This will be lazily initialized as a numpy array with required
        # pixel information.
        self.data_map = None
        self.datatype = datatype

    def extract(self,
        visible_objects: dict[Any, list],
        classifier: ClassificationEngine,
        entity_data,
        camera,
        estimate_visibility: bool = True, **kwargs
    ) -> LabelData:
        """

        :param visible_objects:
        :param classifier:
        :param entity_data:
        :param camera:
        :param estimate_visibility:
        :param kwargs:
        :return:
        """
        ret_data = LabelData()

        if self.data_map is None:

            pass
        # just a quick check, ensure the dimensions are still the same, just as a
        # sanity check.
        if True:
            pass

        with (TimingContext(self.timings, 'labeling')):
            pass

        return ret_data

    def get_estimated_visibility(self) -> dict[Union[str, Any], float]:
        """ Get the estimated visibility for entities and objects """
        return self.estimated_visibility

    def get_visible_entities(self):
        return self.visible_entities.keys()

    def get_labeling_time(self) -> float:
        """ Get the time it took to compute the boxes and the visible objects """
        return self.timings['labeling']

    def get_visible_objects(self) -> Iterable[Any]:
        """ Get the visible objects """
        return self.visible_objects.keys()

    def map_boxes(self, conv_func: Callable = None) -> Iterable[Any]:
        """ Get the camera centered bounding boxes """
        if not conv_func:
            return self.visible_objects.values()
        else:
            return (conv_func(bbox) for bbox in self.visible_objects.values())

    def get_bbox_objects(self) -> dict:
        """ Get the mappings from object to bounding boxes """
        return self.visible_objects

    def get_bbox_entities(self) -> dict:
        """ Get the mappings from object to bounding boxes """
        return self.visible_entities

    def ray_casting_needs(self):
        pass

    # A development note:
    # generating programmatically compositing nodes is very undocumented in BPY.
    # https://imoverclocked.blogspot.com/2011/08/blender-25-compositing-from-python.html
    # was very helpful in the basics, and Blender's console was used to infer the
    # nodes IDs.
    # ! This code is very brittle to breaking changes in the Blender architecture !
    class CompositorNodesContext:

        def __init__(self, context, datatype: str):
            self.data_type = datatype
            self.ctx = context
            self.prev_scene_use_nodes = None
            self.prev_scene_render_layer_normal = None
            self.prev_scene_render_layer_z = None

        def __enter__(self):
            scene = self.ctx.scene

            # Initially extract the current render layer data.
            self.prev_scene_use_nodes = scene.use_nodes
            self.prev_scene_render_layer_z = scene.view_layers["ViewLayer"].use_pass_z
            self.prev_scene_render_layer_normal = scene.view_layers["ViewLayer"].use_pass_normal

        def __exit__(self, exc_type, exc_val, exc_tb):
            scene = self.ctx.scene

            # First restore the previous scene render layer data.
            scene.use_nodes = self.prev_scene_use_nodes
            scene.view_layers["ViewLayer"].use_pass_z = self.prev_scene_render_layer_z
            scene.view_layers["ViewLayer"].use_pass_normal = self.prev_scene_render_layer_normal

    def get_context(self) -> AbstractContextManager:
        return PixelMapExtractor.CompositorNodesContext(self.ctx, self.datatype)