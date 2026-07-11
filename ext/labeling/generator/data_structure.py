"""Data structures for frame annotations.

Defines Label objects for individual entity annotations and LabelData containers
for managing collections of labels within a frame.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any

from ..bpy_properties import LabelClass


@dataclass
class KeypointAnnotation:
    """Single named point of a skeleton/landmark annotation.

    Represents one resolved keypoint of a rig instance, already projected
    into camera-centered [-1, 1] space, together with its identity within
    the rig and its estimated visibility state.

    :param name: Display label of the keypoint, as configured by the user.
    :param index: Stable index of the keypoint within its rig, used to
        resolve skeleton connections and to keep a consistent ordering
        across formats.
    :param x: Camera-centered x coordinate in [-1, 1].
    :param y: Camera-centered y coordinate in [-1, 1].
    :param visibility: Visibility state of the keypoint. Follows the COCO
        convention: 0 not labeled, 1 labeled but occluded, 2 labeled and
        visible. Formats that do not need this granularity may ignore it.
    """

    name: str
    index: int
    x: float
    y: float
    visibility: int = 2


@dataclass
class Label:
    """Single entity annotation with geometry and metadata.

    Represents a labeled object or entity with its geometric representation
    (bounding box, polygon or keypoints), semantic class, visibility estimate,
    and optional segmentation data.

    :param obj_or_entity_name: Identifier string for the object or entity.
    :param cls: Semantic label class, or None if unclassified.
    :param annotation_type: Type of geometric annotation ("bbox", "polygon" or "keypoints").
    :param is_entity: Whether this label represents a multi-mesh entity (True)
        or a single object (False).
    :param visibility: Visibility ratio in [0, 1]. Defaults to 0.0.
    :param is_crowd: Whether the annotation represents a crowd region. Defaults to False.
    :param ideal_bbox: 2D bounding box in ideal/canonical space as (x, y, w, h), or None.
    :param bbox: 2D bounding box in camera/image space as (x, y, w, h), or None.
    :param polygon: List of (x, y) vertices defining a 2D convex hull or mask polygon, or None.
    :param segmentation: Run-length encoded segmentation mask, or None.
    :param keypoints: List of KeypointAnnotation composing a skeleton/landmark
        annotation, or None. Only meaningful when annotation_type is "keypoints".
    :param skeleton_edges: List of (KeypointItem.index, KeypointItem.index) pairs
        describing the rig's skeleton topology, or None. Only meaningful when
        annotation_type is "keypoints".
    :param identity: Persistent tracking identity of the annotated instance
        across shots (e.g. a rig instance), or None when the annotation type
        does not require identity tracking.
    :param attributes: Dictionary of format-specific attributes (e.g., for CVAT), or None.
    """

    obj_or_entity_name: str
    cls: Optional[LabelClass]

    annotation_type: Literal["bbox", "polygon", "keypoints"]  # "bbox", "polygon", "keypoints", "depth"

    # Whether a label belongs to a single object or to a composite multi-mesh entity
    is_entity: bool
    visibility: float = 0.0

    is_crowd: bool = False

    # Bounding box for the mesh object in ideal space
    ideal_bbox: tuple[float, float, float, float] = None
    bbox: tuple[float, float, float, float] = None
    polygon: list[tuple[float, float]] = None
    segmentation: list[int] = None # run length encoding
    point_cloud: Iterable = None
    # depth maps, normal maps, etc... (numpy arrays usually)
    per_pixel_map = None

    # Skeleton/landmark geometry, used when annotation_type == "keypoints"
    keypoints: list[KeypointAnnotation] = None
    # Skeleton topology: pairs of KeypointItem.index, used when annotation_type == "keypoints"
    skeleton_edges: list[tuple[int, int]] = None
    # Persistent identity of the annotated instance, used for tracking across shots
    identity: Optional[int] = None

    # e.g. for CVAT formats
    attributes: dict[str, Any] =  None

class LabelData:
    """ Container for all annotations in a single frame.

    Manages a collection of Label objects indexed by entity/object name,
    providing dict-like iteration and access patterns.
    """

    def __init__(self):
        """ Initialize an empty data container """
        self.data: Dict[str, Label] = dict()

    def __iter__(self):
        """ Iterate over all Label objects in the container.

        :return: Iterator of Label instances. """
        return iter(self.data.values())

    def items(self):
        """ Get label entries with their identifiers.

        :return: Iterator of (name, Label) tuples.
        """
        return self.data.items()

    def __getitem__(self, item: str):
        """ Retrieve a label by object/entity name.

        :param item: Object or entity name string.
        :return: Label object, or None if not found. """
        return self.data.get(item)

    def add(self, new_lab: Label):
        """ Add or update a label in the container.

        :param new_lab: Label instance to add. Overwrites existing label with same name. """
        self.data[new_lab.obj_or_entity_name] = new_lab