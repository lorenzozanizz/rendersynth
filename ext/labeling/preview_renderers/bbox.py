""" Preview renderer for axis-aligned bounding box annotations
(Label.annotation_type == "bbox"), produced by BoundingBoxExtractor.

Classes: BoundingBoxPreviewRenderer
"""

from typing import Optional

from ..generator.data_structure import Label
from ..conversions import convert_camera_centered_to_absolute_pixels_y_inverted
from ...utils.images import PixelCanvas, draw_bounding_box
from .base import PreviewRenderer, PreviewStyle
from .common import draw_label_text
from .registry import PreviewRendererRegistry


@PreviewRendererRegistry.register
class BoundingBoxPreviewRenderer(PreviewRenderer):
    """ Draws a Label's `bbox` as a rectangle, optionally with a thinner "ideal"
    (unoccluded, full 3D-projection) bbox outline, plus name/class/visibility text.
    """

    @staticmethod
    def annotation_types() -> tuple[str, ...]:
        return ("bbox",)

    def render(
        self, canvas: PixelCanvas, label: Label, color: tuple[float, float, float, float],
        width: int, height: int, style: PreviewStyle,
    ) -> Optional[str]:
        x_min, y_min, x_max, y_max = convert_camera_centered_to_absolute_pixels_y_inverted(
            label.bbox, width, height)

        if style.show_geometry:
            draw_bounding_box(
                canvas, color, (x_min, y_min), (x_max, y_max),
                y_grows_up_to_down=False, line_width=style.geometry_line_width)

        if style.show_ideal_bbox and label.ideal_bbox is not None:
            ix_min, iy_min, ix_max, iy_max = convert_camera_centered_to_absolute_pixels_y_inverted(
                label.ideal_bbox, width, height)
            draw_bounding_box(
                canvas, color, (ix_min, iy_min), (ix_max, iy_max),
                y_grows_up_to_down=False, line_width=style.ideal_bbox_line_width)

        draw_label_text(canvas, label, color, x_min, y_min, x_max, y_max, style)
        return None