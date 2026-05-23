from enum import Enum
from typing import Union, Optional

from bpy.types import PropertyGroup
from bpy.props import (EnumProperty, StringProperty, IntProperty, FloatVectorProperty,
                       CollectionProperty, PointerProperty, BoolProperty)

import bpy

class LabelingFormats(Enum):

    YOLO = "Yolo"
    YOLO_SPLIT = "Yolo Split"
    COCO = "COCO"

    @staticmethod
    def from_string(s: str) -> Optional['LabelingFormats']:
        if s == "YOLO":
            return LabelingFormats.YOLO
        return None


def get_label_classes_enum(_, context):
    """Generate enum items from label_classes"""
    labeling_data = context.scene.labeling_data
    items = [("None", "None", "")]

    for i, label_class in enumerate(labeling_data.label_classes):
        items.append((str(label_class.class_id), label_class.name, label_class.name))

    return items

class LabelClass(PropertyGroup):
    """ """
    name: StringProperty(default="Unnamed")                     # type: ignore
    class_id: IntProperty(default=0)                            # type: ignore
    parent_id: IntProperty(default=-1)                          # type: ignore
    color: FloatVectorProperty(subtype='COLOR',                 # type: ignore
        default=(0.2, 0.4, 0.8, 1.0),  # RGBA: mid-gray, fully opaque
        size=4,
        min=0.0,
        max=1.0
   )

class ObjectNameStr(PropertyGroup):
    """ Single object name. """
    obj_name: StringProperty(name="Name")                       # type: ignore

class ObjectLabel(PropertyGroup):
    """ """
    # This id is used to reference this assignment from the capture object operator.
    assignment_id: IntProperty(default=0)                       # type: ignore
    obj_names: CollectionProperty(type=ObjectNameStr)           # type: ignore
    # class_id: IntProperty()                                   # type: ignore
    class_id: EnumProperty(                                     # type: ignore
        items=get_label_classes_enum,
        name="Class Name"
    )

    is_entity: BoolProperty(default=False)                      # type: ignore


class Entity(PropertyGroup):

    # This id is used to refer to this particular entity declaration by operators.
    entity_id: IntProperty(default=0)                           # type: ignore
    entity_name: StringProperty(name="Name")                    # type: ignore
    obj_names: CollectionProperty(type=ObjectNameStr)           # type: ignore


class LabelRule(PropertyGroup):

    rule_type: EnumProperty(                                    # type: ignore
        items=[
            ('MATERIAL', 'Material', ''),
            ('NAME_CONTAINS', 'Name Contains', ''),
            ('COLLECTION', 'Collection', ''),
            ('NONE', 'None', ''),
        ], name = "Rule type"
    )

    # Rule parameters
    material_name: bpy.props.EnumProperty(                      # type: ignore
        name="Material",
        description="Select material to add",
        items= lambda self, context: [
            (mat.name, mat.name, "")
            for mat in bpy.data.materials
        ] or [("NONE", "No materials", "")]
    )
    name_filter: StringProperty()  # type: ignore
    collection_name: bpy.props.EnumProperty(                    # type: ignore
        name="Material",
        description="Select material to add",
        items=lambda self, context: [
            (c.name, c.name, "") for c in bpy.data.collections
        ] or [("NONE", "No Collection", "")]
    )

    class_id: EnumProperty(                                     # type: ignore
        items=get_label_classes_enum,
        name="Class Name"
    )

class LabelingPropData(PropertyGroup):

    do_superclasses: BoolProperty(default=False)                # type: ignore
    label_classes: CollectionProperty(type=LabelClass)          # type: ignore
    class_active_index: IntProperty(default=0)                  # type: ignore

    direct_labels: CollectionProperty(type=ObjectLabel)         # type: ignore
    direct_active_index: IntProperty(default=0)                 # type: ignore

    use_rules: BoolProperty(default=False)                      # type: ignore
    label_rules: CollectionProperty(type=LabelRule)             # type: ignore
    rule_active_index: IntProperty(default=0)                   # type: ignore

    default_class: EnumProperty(                                # type: ignore
        items=get_label_classes_enum,
        name="Default Class",
        description="Label assigned to objects that don't match any rules"
    )

    use_entities: BoolProperty(default=False)                   # type: ignore
    entities: CollectionProperty(type=Entity)                   # type: ignore
    entities_active_index: IntProperty(default=0)               # type: ignore


# Landmarks labeling


label_properties = {
    "labeling_data": PointerProperty(
        type=LabelingPropData
    )
}
