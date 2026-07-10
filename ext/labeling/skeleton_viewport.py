""" Viewport visualization of a rig's keypoints and skeleton connections, driven
by the VisualizeSkeletonOperator and StopVisualizeSkeletonOperator.

Kept in the labeling package, rather than under ui, so that both the
operators package and the ui package can import it directly without
introducing an import cycle (ui.panels already imports from operators.names
while ui's own __init__ is still executing, so anything operators imports
back from ui would be fragile).
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from .keypoint_resolver import KeypointPositionResolver


class SkeletonViewportDrawer:
    """ Owns the SpaceView3D draw handler used to visualize a rig's skeleton.

    Registering a gpu draw handler requires keeping a reference to the handle
    returned by draw_handler_add around, in order to remove it later. This class is the
    single place that reference lives, so starting a visualization twice in a row,
    or disabling the addon while a visualization is active, can never leave a stray
    handler behind that keeps drawing an unremovable "ghost" skeleton.
    """

    def __init__(self):
        self._handle = None
        self._shader = None
        self._point_shader = None

    @property
    def is_running(self) -> bool:
        """ Returns true if the drawing kernel is running """
        return self._handle is not None

    def start(self) -> None:
        """ Start drawing the currently selected rig's skeleton every frame. """

        if self.is_running:
            # Never stack handlers: tear down the previous one first, or every
            # earlier call would keep drawing alongside the new one forever.
            # This is a bit inconvenient for multiple rig setup, but makes it less
            # possible to mess things up and leave "ghost" drawings.
            self.stop()

        self._shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
        self._point_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        self._handle = bpy.types.SpaceView3D.draw_handler_add(
            self._draw, (), 'WINDOW', 'POST_VIEW'
        )

    def stop(self) -> None:
        """ Stop drawing and release the draw handler. Safe to call when not running. """

        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
        self._shader = None
        self._point_shader = None

    def _draw(self) -> None:
        """ Draw the skeleton connections and the keypoint points in the viewport using the
        blender GPU module for shading. Note that this function can only work if the
        gpy modules are activated.

        Points are drawn in red, while lines are bright yellow. Lines are undirected,
        as the bone structure is not assumed to be hierarchical.
        """
        settings = getattr(bpy.context.scene, "pose_label_settings", None)
        if settings is None:
            return

        rig = settings.get_current_rig()
        if rig is None:
            return

        positions = KeypointPositionResolver.resolve_rig_positions(rig)

        segments = self._build_connection_segments(rig, positions)
        if segments:
            batch = batch_for_shader(self._shader, 'LINES', {"pos": segments})
            self._shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
            self._shader.uniform_float("lineWidth", 3.5)
            self._shader.uniform_float("color", (1.0, 1.0, 0.0, 1.0))
            batch.draw(self._shader)

        points = list(positions.values())
        if points:
            gpu.state.point_size_set(8.0)
            point_batch = batch_for_shader(self._point_shader, 'POINTS', {"pos": points})
            self._point_shader.uniform_float("color", (1.0, 0.2, 0.2, 1.0))
            point_batch.draw(self._point_shader)

    @staticmethod
    def _build_connection_segments(rig, positions: dict) -> list:
        """ Build the segments connecting all the endpoints using the keypoints
        connections mapping built by the user. This is then given as the input to the
        Blender GPU shader to construct the lines joining the points.

        :param rig: The rig object storing the connections
        :param positions: positions of the point in space.
        :return: an ordered list [from0, to0, from1, to1, from2, to2]
        """
        segments = []
        for connection in rig.connections:
            point_a = SkeletonViewportDrawer._resolve_connection_point(connection.index_a, positions)
            point_b = SkeletonViewportDrawer._resolve_connection_point(connection.index_b, positions)
            if point_a is not None and point_b is not None:
                segments.append(point_a)
                segments.append(point_b)

        return segments

    @staticmethod
    def _resolve_connection_point(endpoint_id: str, positions: dict):
        """ Resolve the point corresponding to a connections inside the
        positions dictionary.

        :param endpoint_id: the id for the endpoint
        :param positions: the mapping of positions
        :return:
        """
        # Connection endpoints are stored as the string keypoint index
        # (see get_rig_keypoints_enum), with 'NONE' as the no-keypoints
        # sentinel value.
        try:
            return positions.get(int(endpoint_id))
        except (TypeError, ValueError):
            return None
        # Note for the implementation: this could've been made more easily with just
        # positions.get(., None) but was expanded for possible future changes


# Single shared drawer instance: there is only ever one viewport overlay to
# manage, mirroring how ui/__init__.py already tracks a single shared handler
# reference for scene handlers. Operators and the addon-level unregister()
# hook both act on this same instance rather than each holding their own.

# A small note: keeping an item like this in the global namespace is a bit cheap and
# may cause problems later on, but unfortunately the blender BPY property system
# which is largely used around the code to avoid keeping a blender-independent global state
# cannot work for complex objects which are not serializable in the blender sense. (like handlers)
skeleton_viewport_drawer = SkeletonViewportDrawer()