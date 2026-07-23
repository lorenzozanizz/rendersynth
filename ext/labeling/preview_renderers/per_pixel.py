""" Preview renderer for whole-image per-pixel map annotations (depth/normal)
(Label.annotation_type == "per_pixel"), produced by PixelMapExtractor.

Unlike every other renderer, the annotation IS the image: there is nothing to
draw on top of the RGB render, so this renderer works in "replace" mode so it reports the
path of the already-rendered depth/normal map so the caller can display that image in
place of the RGB render.

Classes: PerPixelPreviewRenderer
"""

from typing import Optional

from ..generator.data_structure import Label
from ...utils.images import PixelCanvas
from .base import PreviewRenderer, PreviewStyle
from .registry import PreviewRendererRegistry


@PreviewRendererRegistry.register
class PerPixelPreviewRenderer(PreviewRenderer):
    """ Reports the on-disk path of a whole-image depth/normal map so the caller
    can open it in place of the RGB render. Draws nothing into the shared
    overlay canvas as this renderer never has anything to compose on top of.
    """

    display_mode = "replace"

    @staticmethod
    def annotation_types() -> tuple[str, ...]:
        return ("per_pixel",)

    def render(
        self, canvas: Optional[PixelCanvas], label: Label, color: tuple[float, float, float, float],
        width: int, height: int, style: PreviewStyle,
    ) -> Optional[str]:
        # Simply return the pixel map given by the per pixel extractors. The renderer will
        # exchange this instead of the shot.
        return label.per_pixel_map