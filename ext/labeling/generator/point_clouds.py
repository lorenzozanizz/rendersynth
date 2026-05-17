from typing import Callable
import bpy
from pathlib import Path


from .data_structure import *

from ..ray_casting import (union_bounding_boxes, compute_camera_space_boxes, get_minimal_bounding_box_fast,
                           estimate_visibility_3d, compute_bbox_area, compute_area_ratio)
from ..class_engine import ClassificationEngine
from .extractor import Extractor, LabelData
from ...utils.logger import UniqueLogger
from ...utils.timer import TimingContext


class PointCloudExtractor(Extractor):
    """ Encapsulates bbox extraction logic """

    def __init__(self, context, extract_color=False):
        self.ctx = context
        self.extract_color = extract_color

        self.timings: Dict[str, float] = dict()
        self.visible_objects = dict()
        self.visible_entities = dict()
        self.estimated_visibility = dict()

    def extract(self,
        visible_objects: Dict[Any, list],
        classifier: ClassificationEngine,
        entity_data,
        camera,
        estimate_visibility: bool = True,
        rendered_shot_data: Any = None,
        **kwargs
    ) -> LabelData:
        """

        :param rendered_shot_data:
        :param visible_objects:
        :param classifier:
        :param entity_data:
        :param camera:
        :param estimate_visibility:
        :param kwargs:
        :return:
        """
        ret_data = LabelData()

        image_data = None
        if self.extract_color:
            if not rendered_shot_data:
                raise RuntimeError("Cannot extract color for point cloud labeling without rendered shot data. ")
            if img := bpy.data.images.get(rendered_shot_data):
                bpy.data.images.remove(img)
            bpy.ops.image.open(filepath=rendered_shot_data)
            name = Path(rendered_shot_data).name
            image_data = bpy.data.images[name]
            UniqueLogger.quick_log(image_data.__str__())
            UniqueLogger.quick_log(image_data.pixels.__str__())

        with (TimingContext(self.timings, 'labeling')):

            deps = self.ctx.evaluated_depsgraph_get()
            # Compute raw point clouds corresponding to each computed object.
            # now convert those point clouds into bound boxes.  (in-place)
            recomposed_clouds = {}
            for obj, cloud_data in visible_objects.items():
                points = [(x,y,z) for z, (x,y) in cloud_data]
                recomposed_clouds[obj] = (points, get_minimal_bounding_box_fast(points))
            self.visible_objects = recomposed_clouds

            # There are simple objects visibility, not entities.
            for obj, ( cloud_data, bbox )in self.visible_objects.items():
                cls = classifier.map_obj(obj)
                if not cls:
                    continue

                orig_bbox = None
                if estimate_visibility:
                    vis, orig_bbox = estimate_visibility_3d(
                        obj, camera, deps, self.ctx, self.ctx.scene.render, bbox, area_func=compute_bbox_area)
                    self.estimated_visibility[obj] = float(vis)

                if self.extract_color:
                    cloud_data = self.extract_color_data(image_data, cloud_data)

                ret_data.add(
                    Label(obj.name, cls, point_cloud=cloud_data,
                          bbox=bbox, visibility=self.estimated_visibility.get(obj), annotation_type="bbox",
                          is_entity=False, ideal_bbox=orig_bbox)
                )
            # If required, estimate visibility (No entity mode)
            if not entity_data:
                return ret_data

            # Now we have to reconcile multi-object entities. Note the following thing: we have computed
            # bounding boxes for each smaller point cloud, so now we must join them together.
            # The operation of joining the clouds before computing the bboxes and computing the total
            # box is equivalent mathematically!
            visible_named_objects = {obj.name: (obj, bbox) for obj, (ps, bbox) in self.visible_objects.items()}

            for entity_name, components in entity_data.items():

                cls = classifier.map_entity(entity_name)
                if not cls:
                    continue

                visible_components = [k for k in components if visible_named_objects.get(k) is not None]
                # If no subcomponent is visible, leave early.
                if not visible_components:
                    continue
                bboxes = [visible_named_objects[name][1][1] for name in visible_components]
                clouds = [visible_named_objects[name][1][0] for name in visible_components]
                if not bboxes or clouds:
                    continue

                total_visible_bbox = union_bounding_boxes(bboxes)
                # Note: we are not deleting sub objects, the user may want to differentiate them! e.g. hands in a body
                self.visible_entities[entity_name] = total_visible_bbox

                # The estimation of visibility is a bit more delicate, we have to unify also camera space 3d boxes.
                # (which are not the ones obtained empirically with raytracing, but are obtained with .bound_box instead)

                if estimate_visibility:
                    # We are only using visible objects (there may be more in the entity declaration)

                    camera_space_sub_boxes = compute_camera_space_boxes(
                        (visible_named_objects[name][0] for name in visible_components),
                         camera, deps, self.ctx, self.ctx.scene.render)

                    total_camera_bbox = union_bounding_boxes(camera_space_sub_boxes.values())
                    self.estimated_visibility[entity_name] = compute_area_ratio(
                            total_visible_bbox, total_camera_bbox,
                           area_func_1=compute_bbox_area, area_func_2=compute_bbox_area)

                total_cloud = set.union(*(set(ps) for ps in clouds))

                if self.extract_color:
                    cloud_data = self.extract_color_data(image_data, cloud_data)


                ret_data.add(
                    Label(entity_name, cls,
                          bbox=total_visible_bbox,
                          point_cloud=total_cloud,
                          visibility=self.estimated_visibility.get(entity_name), annotation_type="bbox",
                          is_entity=True)
                )

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

    def extract_color_data(self, image: Any, cloud_data: Iterable) -> Iterable:
        """

        :param image:
        :param cloud_data:
        :return:
        """
        ps = set()
        width = image.width
        height = image.height
        pixels = image.pixels
        for p in cloud_data:
            x_p = min(width, max(0, int((p[0] + 1) * width / 2)))
            y_p = min(height, max(0, height - int((p[1] + 1) * height / 2)))
            ps.add((p, self.get_rgb_color(pixels, x_p, y_p, width)))
        return ps

    @staticmethod
    def get_rgb_color(pixels, x_p, y_p, width) -> tuple:
        """

        :param pixels:
        :param x_p:
        :param y_p:
        :param width:
        :return:
        """
        # Assume RGBA pixels...
        return tuple(pixels[(y_p*width+x_p)*4:(y_p*width+x_p)*4+3])

    def ray_casting_needs(self) -> dict:
        return {
            'compute_dist': True
        }
