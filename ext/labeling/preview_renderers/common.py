""" Shared drawing helpers reused by multiple "overlay" PreviewRenderers. Kept
separate from base.py so it's opt-in reuse rather than something every renderer
must inherit -- renderers whose geometry doesn't reduce to a simple rectangular
bound (e.g. per-pixel maps) have no reason to depend on this module.

Functions: draw_label_text
"""

from ..generator.data_structure import Label
from ...utils.images import PixelCanvas, draw_bitmap_text, font_size_fit_box_perc, estimate_text_pixel_height
from .base import PreviewStyle


def draw_label_text(
    canvas: PixelCanvas,
    label: Label,
    color: tuple[float, float, float, float],
    x_min: float, y_min: float, x_max: float, y_max: float,
    style: PreviewStyle,
) -> None:
    """ Draw the name/class-id text (above the geometry) and estimated-visibility
    text (below the geometry) conventionally shown for a label, shared by every
    overlay renderer whose geometry has a rectangular pixel-space bound (bbox,
    polygon, keypoints).

    :param canvas: Shared PixelCanvas for the current preview frame.
    :param label: The Label being annotated.
    :param color: RGBA color associated with the label's class.
    :param x_min: Left bound of the label's geometry, in pixel space.
    :param y_min: Bottom bound of the label's geometry, in pixel space (Blender convention).
    :param x_max: Right bound of the label's geometry, in pixel space.
    :param y_max: Top bound of the label's geometry, in pixel space (Blender convention).
    :param style: Display options for this frame.
    """
    geometry_width = int(abs(x_max - x_min))

    x_min = int(x_min)
    y_max = int(y_max)
    y_min = int(y_min)

    if style.show_obj_name or style.show_class_name_or_id != "none":
        text = "" if style.show_class_name_or_id == "none" else \
            f" {label.cls.name}" if style.show_class_name_or_id == "name" else f"{label.cls.class_id}"
        if style.show_obj_name:
            text = f"{label.obj_or_entity_name}" + (" - " if text else "") + text

        font_size = font_size_fit_box_perc(text, geometry_width, 0.9)
        draw_bitmap_text(
            canvas, text, (x_min + 20, 10 + y_max + estimate_text_pixel_height("", font_size)),
            color=color, size=font_size)

    if style.show_visibility:
        text = f"{int(label.visibility * 100)}%"
        font_size = font_size_fit_box_perc(text, geometry_width, 0.3)
        draw_bitmap_text(canvas, text, (x_min + 20, y_min - 10), color=color, size=font_size)