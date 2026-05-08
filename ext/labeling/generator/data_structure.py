"""Data structures for frame annotations.

Defines Label objects for individual entity annotations and LabelData containers
for managing collections of labels within a frame.
"""

from dataclasses import dataclass
from typing import Optional, Literal, Union, Dict, Any

from ..bpy_properties import LabelClass


@dataclass
class Label:
    """Single entity annotation with geometry and metadata.

    Represents a labeled object or entity with its geometric representation
    (bounding box or polygon), semantic class, visibility estimate, and
    optional segmentation data.

    :param obj_or_entity_name: Identifier string for the object or entity.
    :param cls: Semantic label class, or None if unclassified.
    :param annotation_type: Type of geometric annotation ("bbox" or "polygon").
    :param is_entity: Whether this label represents a multi-mesh entity (True)
        or a single object (False).
    :param visibility: Visibility ratio in [0, 1]. Defaults to 0.0.
    :param is_crowd: Whether the annotation represents a crowd region. Defaults to False.
    :param ideal_bbox: 2D bounding box in ideal/canonical space as (x, y, w, h), or None.
    :param bbox: 2D bounding box in camera/image space as (x, y, w, h), or None.
    :param polygon: List of (x, y) vertices defining a 2D convex hull or mask polygon, or None.
    :param segmentation: Run-length encoded segmentation mask, or None.
    :param attributes: Dictionary of format-specific attributes (e.g., for CVAT), or None.
    """

    obj_or_entity_name: str
    cls: Optional[LabelClass]

    annotation_type: Literal["bbox", "polygon"]  # "bbox", "polygon", "depth"

    # Whether a label belongs to a single object or to a composite multi-mesh entity
    is_entity: bool
    visibility: float = 0.0

    is_crowd: bool = False

    # Bounding box for the mesh object in ideal space
    ideal_bbox: tuple[float, float, float, float] = None
    bbox: tuple[float, float, float, float] = None
    polygon: list[tuple[float, float]] = None
    segmentation: list[int] = None # run length encoding

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
