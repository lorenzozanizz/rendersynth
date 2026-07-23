""" Base interfaces for the preview rendering system: pluggable renderers that draw
(or, for "replace"-mode formats, substitute) a single Label's annotation into the
preview window, dispatched by Label.annotation_type via PreviewRendererRegistry.

This mirrors the Extractor/IOStrategy split already used on the extraction and serialization with
 one canonical data type (Label), many pluggable implementations picked by format.

Classes: PreviewStyle, PreviewRenderer
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional

from ..generator.data_structure import Label
from ...utils.images import PixelCanvas


@dataclass
class PreviewStyle:
    """ Display options for a single preview frame.

    :param show_obj_name: Whether to draw the object/entity name.
    :param show_class_name_or_id: "name", "id" or "none".
    :param show_geometry: Whether to draw the annotation geometry itself.
    :param show_visibility: Whether to draw the estimated visibility percentage.
    :param show_ideal_bbox: Whether to draw the thin unoccluded/ideal bounding box,
        for renderers that support it.
    :param max_preview_points: Cap on how many points a point-cloud label draws
        (random-subsampled if the label carries more than this).
    :param geometry_line_width: Line width used for the primary geometry outline.
    :param ideal_bbox_line_width: Line width used for the thin ideal-bbox outline.
    """


    # This configuration is now wrapped in a dataclass rather than being manually set
    # in the code lazily.
    # Future updates will have a small per-format labeling system.
    show_obj_name: bool = True
    show_class_name_or_id: Literal["id", "name", "none"] = "id"
    show_geometry: bool = True
    show_visibility: bool = True
    show_ideal_bbox: bool = False

    # For points clouds, this limits the abount of points shown, which are possibly large.
    max_preview_points: int = 2000
    geometry_line_width: int = 7
    ideal_bbox_line_width: int = 2

    # Point-cloud dots are sized by each point's distance from the camera
    # (Label.point_cloud entries carry this as their z component), clamped to
    # this pixel-size range: closer points draw larger, farther ones smaller.
    point_cloud_min_dot_size: int = 1
    point_cloud_max_dot_size: int = 6


class PreviewRenderer(ABC):
    """ Draws a single Label into the preview frame. One subclass handles the
    list of Label.annotation_type values it declares via annotation_types(),
    resolved at draw time through the PreviewRendererRegistry.

    Two display modes:
      - "overlay" (default): draws on top of the existing RGB render, into a
        PixelCanvas shared by every overlay renderer in the frame (bbox,
        polygon, keypoints, point_cloud).
      - "replace": the annotation itself IS the image to display (e.g. a
        rendered depth/normal map produced to disk by the compositor). Instead
        of drawing into the RGB canvas, the renderer reports which image path should be
        displayed in its place and does not open the rendered temp image, rather the new generated
        label. .
    """

    display_mode: Literal["overlay", "replace"] = "overlay"

    @staticmethod
    @abstractmethod
    def annotation_types() -> tuple[str, ...]:
        """ The Label.annotation_type value (one or more) his renderer handles.

        :return: A tuple of annotation_type strings, e.g. ("bbox",).
        """
        pass

    @abstractmethod
    def render(
        self,
        canvas: PixelCanvas,
        label: Label,
        color: tuple[float, float, float, float],
        width: int,
        height: int,
        style: PreviewStyle,
    ) -> Optional[str]:
        """ Render the given label's annotation for the current preview frame.

        Overlay renderers draw directly into canvas (without flushing it, since it is
        shared across every label drawn this frame) and return None.

        Replace-mode renderers ignore canvas and instead return the filesystem path of the
        image that should be displayed in place of the RGB render the caller (PreviewGenerator)
         is responsible for actually swapping the displayed image in the Blender image buffer.

        :param canvas: Shared PixelCanvas for the current preview frame.
        :param label: The Label to render.
        :param color: RGBA color associated with the label's class.
        :param width: Width of the preview image in pixels.
        :param height: Height of the preview image in pixels.
        :param style: Display options for this frame.
        :return: A replacement image path for "replace"-mode renderers, else None.
        """
        pass