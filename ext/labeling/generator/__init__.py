""" Subpackage used to facilitate access to the various generators without referencing
the exact file: all generator will be included here.
"""

from .bounding_box import BoundingBoxExtractor
from .convex_hull import PolygonExtractor
from .landmarks import LandmarksExtractor
from .per_pixel import PixelMapExtractor
from .extractor import Extractor

from .data_structure import *