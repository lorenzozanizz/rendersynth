""" Preview renderer for convex-hull polygon annotations
(Label.annotation_type == "polygon"), produced by PolygonExtractor.

Classes: PolygonPreviewRenderer
"""

from typing import Optional

from ..generator.data_structure import Label
from ..conversions import (
    convert_camera_point_list_absolute_pixels_y_inverted,
    convert_camera_centered_to_absolute_pixels_y_inverted,
)
from ..ray_casting import get_minimal_bounding_box_fast
from ...utils.images import PixelCanvas, draw_polygon, draw_bounding_box
from .base import PreviewRenderer, PreviewStyle
from .common import draw_label_text
from .registry import PreviewRendererRegistry


@PreviewRendererRegistry.register
class PolygonPreviewRenderer(PreviewRenderer):
    """ Draws a Label's `polygon` convex hull as a closed polyline, optionally
    with a thin "ideal" (unoccluded, full 3D-projection) bbox outline, plus
    name/class/visibility text.
    """

    @staticmethod
    def annotation_types() -> tuple[str, ...]:
        return ("polygon",)

    def render(
        self, canvas: PixelCanvas, label: Label, color: tuple[float, float, float, float],
        width: int, height: int, style: PreviewStyle,
    ) -> Optional[str]:
        pixel_polygon = convert_camera_point_list_absolute_pixels_y_inverted(label.polygon, width, height)

        if style.show_geometry:
            draw_polygon(canvas, pixel_polygon, color, line_width=style.geometry_line_width)

        if style.show_ideal_bbox and label.ideal_bbox is not None:
            ix_min, iy_min, ix_max, iy_max = convert_camera_centered_to_absolute_pixels_y_inverted(
                label.ideal_bbox, width, height)
            draw_bounding_box(
                canvas, color, (ix_min, iy_min), (ix_max, iy_max),
                y_grows_up_to_down=False, line_width=style.ideal_bbox_line_width)

        # Text is anchored to the polygon's pixel-space bounds, same as the bbox renderer.
        x_min, y_min, x_max, y_max = get_minimal_bounding_box_fast(pixel_polygon)
        draw_label_text(canvas, label, color, x_min, y_min, x_max, y_max, style)
        return None