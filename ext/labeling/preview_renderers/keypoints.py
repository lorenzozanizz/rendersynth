""" Preview renderer for skeleton/landmark keypoint annotations
(Label.annotation_type == "keypoints"), produced by LandmarksExtractor.

This annotation_type was previously unreachable in the preview: the old
dispatch only recognized "bbox"/"polygon" prefixes, so a "keypoints" label fell
through with geometry=None and crashed downstream on conversion.

Classes: KeypointsPreviewRenderer
"""

from typing import Optional

from ..generator.data_structure import Label
from ..conversions import convert_camera_point_list_absolute_pixels_y
from ..ray_casting import get_minimal_bounding_box_fast
from ...utils.images import PixelCanvas, draw_thick_pixel, draw_line
from .base import PreviewRenderer, PreviewStyle
from .common import draw_label_text
from .registry import PreviewRendererRegistry


@PreviewRendererRegistry.register
class KeypointsPreviewRenderer(PreviewRenderer):
    """ Draws a Label's `keypoints` as dots which are dimmed when occluded, skipped when
    not labeled (COCO visibility 0) connected by skeleton_edges, plus
    name/class/visibility text anchored to the keypoints' pixel-space bounds as in
    the case of bounding boxes. This requires some carful handling of out-of-screen texts.
    """

    @staticmethod
    def annotation_types() -> tuple[str, ...]:
        return ("keypoints",)

    def render(
        self, canvas: PixelCanvas, label: Label, color: tuple[float, float, float, float],
        width: int, height: int, style: PreviewStyle,
    ) -> Optional[str]:

        print("Im rendering the skeeltonozzos diddio")
        # Visual weight for keypoint dots and skeleton connectors, kept independent of
        # PreviewStyle.geometry_line_width since normally keypoints are much smaller shapes than
        # a bbox/polygon outline.
        _KEYPOINT_DOT_SIZE = 8
        _SKELETON_LINE_WIDTH = 3

        # Occluded keypoints with COCO visibility == 1 are still drawn, but dimmed towards
        # gray so a glance at the preview distinguishes them from clearly-visible ones.
        # NOTE: This depends on the extraction, if visibility was enabled!
        _OCCLUDED_DIM_FACTOR = 0.4

        keypoints = label.keypoints or []
        if not keypoints:
            return None

        pixel_points = convert_camera_point_list_absolute_pixels_y(
            [(kp.x, kp.y) for kp in keypoints], width, height)

        # index -> pixel position, only for keypoints actually labeled, so skeleton
        # edges referencing a missing/unlabeled endpoint are skipped cleanly.
        pixel_by_index = {
            kp.index: pixel_points[i]
            for i, kp in enumerate(keypoints) if kp.visibility != 0
        }

        if style.show_geometry:
            # We plot every line in between the keypoints first, as to not
            # overwrite the dots that we write later.
            for index_a, index_b in (label.skeleton_edges or ()):
                p_a = pixel_by_index.get(index_a)
                p_b = pixel_by_index.get(index_b)
                if p_a is None or p_b is None:
                    continue
                draw_line(canvas.pixels, p_a, p_b, color, canvas.width, canvas.height,
                          line_width=_SKELETON_LINE_WIDTH)

            # For each point, depending if the point is visible or not, we draw thick pixels
            # of given radius at the position of keypoints in theimage camera space.
            for kp, pixel_point in zip(keypoints, pixel_points):
                if kp.visibility == 0:
                    continue
                dot_color = color if kp.visibility == 2 else self._dim_color(color, _OCCLUDED_DIM_FACTOR)
                draw_thick_pixel(
                    canvas.pixels, dot_color, pixel_point[0], pixel_point[1],
                    _KEYPOINT_DOT_SIZE, canvas.width, canvas.height)

        visible_pixel_points = [p for kp, p in zip(keypoints, pixel_points) if kp.visibility != 0]
        if visible_pixel_points:
            x_min, y_min, x_max, y_max = get_minimal_bounding_box_fast(visible_pixel_points)
            draw_label_text(canvas, label, color, x_min, y_min, x_max, y_max, style)

        return None

    @staticmethod
    def _dim_color(color: tuple[float, float, float, float], factor: float) -> tuple[float, float, float, float]:
        """ Blend an RGBA color towards mid-gray. this is to be used when
        visualizing depth.

        :param color: Source RGBA color.
        :param factor: 0.0 leaves the color unchanged, 1.0 makes it fully mid-gray. Controls the
        blending effect intensity.
        :return: The dimmed RGBA color.
        """
        r, g, b, a = color
        return r + (0.5 - r) * factor, g + (0.5 - g) * factor, b + (0.5 - b) * factor, a