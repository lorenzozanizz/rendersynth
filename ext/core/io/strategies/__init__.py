"""


"""
from enum import Enum

class SupportedFormats(Enum):
    """

    """

    #
    IMAGE_ONLY = "Media Only"

    #
    ULTRALYTICS_YOLO = "Ultralytics YOLO"
    COCO = "COCO"
    COCO_SEGMENTATION = "COCO Segmentation"
    COCO_KEYPOINTS = "COCO Keypoints"
    PASCAL_VOC = "Pascal VOC"
    CVAT_XML_IMAGES = "CVAT XML Images"

    # Point clouds .pcd with varying degrees of detail
    PCD_CLASS_COLOR = "PCD Class Color"
    PCD_CLASS = "PCD Class"
    PCD = "PCD"

    #
    THERMAL = "Thermal"
    DEPTH_PNG = "Depth"
    NORMAL = "Normal"

from .coco_strategy import *
from .yolo_strategy import *
from .pascal_strategy import *
from .cvat_xml_strategy import *
from .pcloud_strategy import *
from .depth_strategy import *
# from .nmap_strategy import *