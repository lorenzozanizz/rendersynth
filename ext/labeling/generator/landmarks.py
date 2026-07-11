""" Extractor implementation producing skeleton/landmark annotations from the
rigs configured in Scene.pose_label_settings.

Classes: LandmarksExtractor
"""

from mathutils import Vector

from ...utils.timer import TimingContext
from ..class_engine import ClassificationEngine
from ..keypoint_resolver import KeypointPositionResolver
from ..ray_casting import project_3d_point, get_minimal_bounding_box_fast

from .extractor import Extractor
from .data_structure import *


class LandmarksExtractor(Extractor):
    """ Encapsulates skeleton/landmark keypoint extraction logic.

    Unlike BoundingBoxExtractor/PolygonExtractor, keypoints are exact, known 3D
    points (a bone head/tail or a mapped object's origin), not something approximated
    from a ray-cast point cloud. visible_objects is therefore unused here:
    rig configuration is read directly from context.scene.pose_label_settings,
    the same way ClassificationEngine reads context.scene.labeling_data.

    Stays strictly format-agnostic: it only ever produces canonical Label objects
    carrying KeypointAnnotation lists, with no format-specific ordering or
    encoding. That responsibility belongs to the IOStrategy consuming the resulting LabelData.
    """

    # Minimum distance, in Blender units, kept between the occlusion test ray
    # and the keypoint itself. Without this, the ray would almost always stop
    # on the rig's own mesh surface right at the keypoint, since keypoints
    # commonly sit on or inside that surface.
    OCCLUSION_EPSILON = 0.01

    def __init__(self, context):
        self.ctx = context

        self.timings: Dict[str, float] = dict()
        self.visible_rigs: Dict[str, Any] = dict()
        self.estimated_visibility: Dict[str, float] = dict()

    def extract(self,
        visible_objects,
        classifier: ClassificationEngine,
        entity_data,
        camera,
        estimate_visibility: bool = True,
        rendered_shot_data: Any = None, **kwargs
    ) -> LabelData:
        """ Extract the keypoints from the scene and conditionally estimate
        visibility with a single traced ray per keypoint. This does not make
        use of the visible objects, which is the reason why the extractor
        declares a very coarse resolution for the initial ray tracing pass.

        :param visible_objects: Unused: keypoint positions are resolved
            directly rather than derived from a ray-cast point cloud.
        :param classifier: Classifier used to resolve each rig's class_id
            into a LabelClass.
        :param entity_data: Unused: rigs are not part of the entity system.
        :param camera: Camera used to project keypoints into camera space.
        :param estimate_visibility: If true, an occlusion ray cast is
            performed per enabled keypoint to determine its visibility state.
        :param rendered_shot_data: Unused by this extractor.
        :param kwargs: extra key arguments, ignored here.
        """
        ret_data = LabelData()
        self.visible_rigs = dict()
        self.estimated_visibility = dict()

        settings = getattr(self.ctx.scene, "pose_label_settings", None)
        if settings is None:
            # should never happen if the extension is properly registered.
            return ret_data

        with TimingContext(self.timings, 'labeling'):

            depsgraph = self.ctx.evaluated_depsgraph_get()
            render = self.ctx.scene.render

            for rig in settings.labeled_rigs:
                # Rigs that are not enabled are explicitly excluded from the extraction.
                if not rig.enabled:
                    continue

                label = self._extract_rig(rig, classifier, camera, depsgraph, render, estimate_visibility)
                if label is None:
                    continue

                self.visible_rigs[rig.rig_name] = rig
                ret_data.add(label)

        return ret_data

    def _extract_rig(self, rig, classifier, camera, depsgraph, render, estimate_visibility: bool) -> Optional[Label]:
        """ Resolve, project and pack a single rig instance into a Label.

        :param rig: RigItem to extract.
        :param classifier: Classifier used to resolve rig.class_id.
        :param camera: Camera used to project keypoints into camera space.
        :param depsgraph: Evaluated depsgraph, used for occlusion ray casts.
        :param render: Scene render settings, used for projection.
        :param estimate_visibility: Whether to run the occlusion ray cast.
        :return: A Label with annotation_type "keypoints", or None if the
            rig has no keypoint that could be resolved at all.
        """

        # Delegate the world position identifier to another labeler object, but
        # these are raw 3D positions, not camera positions (which are resolved later)
        world_positions = KeypointPositionResolver.resolve_rig_positions(rig)
        if not world_positions:
            return None

        keypoints = []
        projected_points = []

        for keypoint in rig.keypoints:

            world_point = world_positions.get(keypoint.index)
            # If the keypoint is disabled, no position is computed for him.
            if world_point is None:
                continue

            camera_point = project_3d_point(camera, world_point, self.ctx, render)
            projected_points.append((camera_point.x, camera_point.y))

            visibility = 2
            if estimate_visibility:
                visibility = self._estimate_keypoint_visibility(world_point, camera, depsgraph)

            keypoints.append(KeypointAnnotation(
                name=keypoint.label,
                index=keypoint.index,
                x=camera_point.x,
                y=camera_point.y,
                visibility=visibility,
            ))

        cls = classifier.resolve_class_by_id(rig.class_id)

        visibility_ratio = None
        # Estimated visibility is computed simply as the proportion of visible bones
        # over the amount of activated keypoints.
        if estimate_visibility and keypoints:
            visible_count = sum(1 for kp in keypoints if kp.visibility == 2)
            visibility_ratio = visible_count / len(keypoints)
            self.estimated_visibility[rig.rig_name] = visibility_ratio

        # Get a box (not a convex hull or alpha shape!)
        bbox = get_minimal_bounding_box_fast(projected_points)

        return Label(
            rig.rig_name, cls,
            annotation_type="keypoints",
            is_entity=True,
            visibility=visibility_ratio if visibility_ratio is not None else 0.0,
            bbox=bbox,
            keypoints=keypoints,
            identity=rig.identity,
        )

    def _estimate_keypoint_visibility(self, world_point: Vector, camera, depsgraph) -> int:
        """ Determine whether a keypoint is occluded from the camera's point
        of view, using a single ray cast stopped just short of the keypoint.

        :param world_point: World-space location of the keypoint.
        :param camera: Camera the keypoint is being viewed from.
        :param depsgraph: Evaluated depsgraph to ray cast against.
        :return: 2 if visible, 1 if occluded (COCO visibility convention).
        """

        camera_origin = camera.matrix_world.translation
        offset = world_point - camera_origin
        distance = offset.length

        if distance <= self.OCCLUSION_EPSILON:
            # The keypoint coincides with the camera origin: treat as visible,
            # there is nothing meaningful to occlude it with.
            return 2

        direction = offset / distance
        max_distance = distance - self.OCCLUSION_EPSILON

        is_hit, *_ = self.ctx.scene.ray_cast(
            depsgraph, camera_origin, direction, distance=max_distance
        )

        return 1 if is_hit else 2

    def get_estimated_visibility(self) -> dict[str | Any, float]:
        """ Get the estimated visibility for each extracted rig instance """
        return self.estimated_visibility

    def get_visible_entities(self) -> Iterable[Any]:
        """ Get the rig instance names which produced a Label in the last extract() call """
        return self.visible_rigs.keys()

    def get_labeling_time(self) -> float:
        """ Get the time it took to compute the last extraction """
        return self.timings.get('labeling')

    @staticmethod
    def ray_casting_needs() -> dict[str, Any]:
        """ Get the ray casting configuration needs for this extractor. """
        # Keypoint positions are resolved directly rather than derived from
        # the ray-cast point cloud, so the frustum sampling that the
        # orchestrator performs before calling extract() is wasted work for this extractor.
        # Requesting the smallest possible resolution keeps that unavoidable cost negligible.
        return {
            'resolution_x': 1,
            'resolution_y': 1
        }