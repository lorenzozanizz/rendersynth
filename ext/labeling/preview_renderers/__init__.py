""" Subpackage used to facilitate access to the various preview renderers without
referencing the exact file: importing this module registers every renderer with
PreviewRendererRegistry.

Concrete renderer modules (bbox, polygon, keypoints, point_cloud, per_pixel) are
added here as they are implemented; each registration is a decorator import side
effect, so simply importing the module here is sufficient to make it available
via PreviewRendererRegistry.get_for(...).
"""

from .base import PreviewRenderer, PreviewStyle
from .registry import PreviewRendererRegistry

from .bbox import BoundingBoxPreviewRenderer
from .polygon import PolygonPreviewRenderer
from .keypoints import KeypointsPreviewRenderer
from .point_cloud import PointCloudPreviewRenderer
from .per_pixel import PerPixelPreviewRenderer