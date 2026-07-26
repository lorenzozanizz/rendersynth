from enum import Enum
from typing import Union, Optional
from dataclasses import dataclass

@dataclass
class LabelClass:
    """ """
    name: str
    class_id: int
    parent_id: int
    color: tuple =(0.2, 0.4, 0.8, 1.0),  # RGBA: mid-gray, fully opaque

@dataclass
class ObjectNameStr:
    """ Single object name. """
    obj_name: str

@dataclass
class ObjectLabel:
    """ """
    assignment_id: int
    obj_names: list
    class_id: tuple

    is_entity: bool


@dataclass
class Entity:

    entity_id: int
    entity_name: str
    obj_names: list


@dataclass
class LabelRule:

    material_name: tuple
    name_filter: str
    collection_name: tuple
    class_id: tuple

    rule_type: tuple = (
        ('MATERIAL', 'Material', ''),
        ('NAME_CONTAINS', 'Name Contains', ''),
        ('COLLECTION', 'Collection', ''),
        ('NONE', 'None', ''),
    )

@dataclass
class LabelingPropData:

    do_superclasses: bool
    label_classes: list
    class_active_index: int

    direct_labels: list
    direct_active_index: int

    use_rules: bool
    label_rules: list
    rule_active_index: int

    default_class: tuple

    use_entities: bool
    entities: list
    entities_active_index: int
