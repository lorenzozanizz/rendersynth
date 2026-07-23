""" Preview renderer for sampled point-cloud annotations produced by the PointCloudExtractor.

Rather than attempting an actual 3D scatter view, points are projected and
plotted directly onto the 2D preview render, using each point's distance from
the camera to regulate the width of the dot: closer points draw larger, farther
ones smaller

Classes: PointCloudPreviewRenderer
"""

import random
from typing import Optional

from ..generator.data_structure import Label
from ..conversions import convert_camera_point_list_absolute_pixels_y_inverted
from ..ray_casting import get_minimal_bounding_box_fast
from ...utils.images import PixelCanvas, draw_thick_pixel
from .base import PreviewRenderer, PreviewStyle
from .common import draw_label_text
from .registry import PreviewRendererRegistry

@PreviewRendererRegistry.register
class PointCloudPreviewRenderer(PreviewRenderer):
    """ Draws a Label's `point_cloud` as dots projected onto the 2D preview
    frame, distance-sized and, when available, colored from the per-point RGB
    sample, plus name/class/visibility text. To keep dense clouds from tanking
    preview responsiveness, points are random-subsampled down to
    `style.max_preview_points` before drawing.
    """

    @staticmethod
    def annotation_types() -> tuple[str, ...]:
        return ("point_cloud",)

    def render(
        self, canvas: PixelCanvas, label: Label, color: tuple[float, float, float, float],
        width: int, height: int, style: PreviewStyle,
    ) -> Optional[str]:
        raw_points = list(label.point_cloud or [])
        if not raw_points or not style.show_geometry:
            return None

        points = [self._normalize_cloud_entry(entry) for entry in raw_points]
        if len(points) > style.max_preview_points:
            points = random.sample(points, style.max_preview_points)

        pixel_xy = convert_camera_point_list_absolute_pixels_y_inverted(
            [(x, y) for x, y, _, _ in points], width, height)

        z_values = [z for _, _, z, _ in points]
        z_min, z_max = min(z_values), max(z_values)
        z_range = z_max - z_min
        size_span = style.point_cloud_max_dot_size - style.point_cloud_min_dot_size

        for (x, y, z, point_color), (px, py) in zip(points, pixel_xy):
            # Normalized depth within this cloud: 0 = nearest point, 1 = farthest.
            # This way we dont get points which are too large and clutter the screen,
            # also note that manually drawing in the buffer like that is pretty expensive!
            t = (z - z_min) / z_range if z_range > 1e-6 else 0.0
            dot_size = max(1, round(style.point_cloud_max_dot_size - t * size_span))
            dot_color = (point_color[0], point_color[1], point_color[2], 1.0) if point_color else color
            draw_thick_pixel(canvas.pixels, dot_color, px, py, dot_size, canvas.width, canvas.height)

        x_min, y_min, x_max, y_max = get_minimal_bounding_box_fast(pixel_xy)
        draw_label_text(canvas, label, color, x_min, y_min, x_max, y_max, style)

        return None

    @staticmethod
    def _normalize_cloud_entry(entry: tuple) -> tuple:
        """ This function is used to normalize the shape of the emitted values of the
        PointCloudExtractor (x, y, z), or ((x, y, z), rgb_color)
        pairs. Normalize both into (x, y, z, rgb_color_or_None).

        :param entry: One entry from Label.point_cloud.
        :return: (x, y, z, rgb_color_or_None).
        """
        if len(entry) == 3:
            x, y, z = entry
            return x, y, z, None
        (x, y, z), point_color = entry
        return x, y, z, point_color
