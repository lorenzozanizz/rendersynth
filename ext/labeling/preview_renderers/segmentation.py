
from typing import Optional

from ..generator.data_structure import Label
from ...utils.images import PixelCanvas
from .base import PreviewRenderer, PreviewStyle
from .registry import PreviewRendererRegistry


@PreviewRendererRegistry.register
class SegmentationPreviewRenderer(PreviewRenderer):

    @staticmethod
    def annotation_types() -> tuple[str, ...]:
        # This is used for both segmentation PNG and segmentation EXR
        return ("segmentation",)

    def render(
        self, canvas: Optional[PixelCanvas], label: Label, color: tuple[float, float, float, float],
        width: int, height: int, style: PreviewStyle,
    ) -> Optional[str]:
        # Simply return the pixel map given by the per pixel extractors. The renderer will
        # exchange this instead of the shot.
        return label.per_pixel_map