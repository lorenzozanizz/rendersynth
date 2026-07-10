import bpy

from typing import Optional

from bpy.types import Panel, Operator, PropertyGroup, UIList, Object
from bpy.props import (
    StringProperty, IntProperty, BoolProperty, EnumProperty,
    CollectionProperty, PointerProperty
)

from ...operators.names import Labels
from ...labeling.bpy_properties import get_label_classes_enum
from ..description import UILegendWidget as Legend

class KeypointItem(PropertyGroup):
    """ Single keypoint of a rig, resolved differently depending on
    RigItem.is_blender_rig:

    - If the owning rig is a blender rig, the keypoint resolves to a bone
      of RigItem.armature_ptr, identified by bone_name, and tail_or_head
      selects which end of the bone gives the 3D point.
    - If the owning rig is a virtual/custom rig, the keypoint resolves to
      real_obj directly and tail_or_head is not used.
    """

    label: StringProperty(name="Label")                                     # type: ignore
    index: IntProperty(name="Index", min=0)                                 # type: ignore
    enabled: BoolProperty(name="Include", default=True)                     # type: ignore

    # Used when the owning rig is not a blender rig: the keypoint position
    # is taken directly from this object's world position.
    real_obj: PointerProperty(name="Mapped Object", type=Object)            # type: ignore

    # Used when the owning rig is a blender rig: the keypoint position is
    # taken from this bone on the rig's armature_ptr.
    bone_name: StringProperty(name="Bone")                                  # type: ignore
    tail_or_head: BoolProperty(name="Tail", default=True)                   # type: ignore

def get_rig_keypoints_enum(_, context):
    """Generate enum items listing the currently selected rig's keypoints.

    Used so skeleton connections are picked by keypoint name instead of a
    raw, easily-mistyped index, while still being stored as the keypoint's
    stable index string underneath.
    """
    settings = context.scene.pose_label_settings
    rig = settings.get_current_rig()

    if rig is None or len(rig.keypoints) == 0:
        return [('NONE', "None", "")]

    return [
        (str(keypoint.index), keypoint.label or f"Keypoint {keypoint.index}", "")
        for keypoint in rig.keypoints
    ]


class SkeletonConnectionItem(PropertyGroup):
    """ Single skeleton edge between two keypoints of the same rig.

    Endpoints reference their KeypointItem.index (stable across reordering)
    rather than a position in the keypoints collection, and are edited
    through a name-based dropdown rather than a raw integer field.
    """

    index_a: EnumProperty(items=get_rig_keypoints_enum, name="From")    # type: ignore
    index_b: EnumProperty(items=get_rig_keypoints_enum, name="To")      # type: ignore

class RigItem(PropertyGroup):

    rig_name: StringProperty(name="Rig Name")                               # type: ignore
    enabled: BoolProperty(name="Enabled", default=True)                     # type: ignore

    # Persistent tracking id of this rig instance, unrelated to class_id below.
    # Two rigs of the same class_id (e.g. two "person" skeletons) must be
    # given distinct identity values so they can be told apart across shots,
    # e.g. when their paths cross.
    identity: IntProperty(name="Identity", default=0)                       # type: ignore

    # Semantic class/category this rig instance belongs to (e.g. "person").
    # Rig instances sharing the same class_id are expected to share the same
    # keypoint/skeleton topology, since formats such as COCO Keypoints define
    # one category per topology and multiple annotated instances against it.
    class_id: EnumProperty(                                                 # type: ignore
        items=get_label_classes_enum,
        name="Class Name"
    )

    # A rig may be really existing in blender, or it may be a virtual rig for
    # which the user must specify which blender objects have to be
    # mapped to bones
    is_blender_rig: BoolProperty(name="Blender Rig", default=False)         # type: ignore

    # Armature this rig's keypoints resolve bones against, when is_blender_rig
    # is True. Stored per-rig so it does not depend on the transient
    # PoseLabelSettings.selected_armature_pointer used only by the add-rig flow.
    armature_ptr: PointerProperty(                                          # type: ignore
        name="Armature",
        type=Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

    # Skeleton connections: which bones are connected to which
    connections: CollectionProperty(type=SkeletonConnectionItem)            # type: ignore
    connections_index: IntProperty(name="Active Connection", default=0)     # type: ignore

    # Actual bone/map data: Either real bones, or fake bones.
    keypoints: CollectionProperty(type=KeypointItem)                        # type: ignore
    keypoints_index: IntProperty(name="Active Keypoint", default=0)         # type: ignore

    # If the skeleton is currently being visualized
    is_being_visualized: BoolProperty(default=False)                        # type: ignore

class PoseLabelSettings(PropertyGroup):

    # There can be multiple armatures. each of them can have an identity and a class.
    labeled_rigs: CollectionProperty(type=RigItem)                          # type: ignore
    selected_rig: IntProperty(name="Selected", default=0)                   # type: ignore

    selected_armature_pointer: PointerProperty(                             # type: ignore
        name="Blender Armature",
        type=Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

    currently_visualizing: BoolProperty(default=False)                      # type: ignore

    def get_current_rig(self) -> Optional[None]:

        rigs = self.labeled_rigs
        rig_index = self.selected_rig
        selected_rig = None if rig_index < 0 or rig_index >= len(rigs) else rigs[rig_index]
        return selected_rig

class KeypointList(UIList):

    def draw_item(self, _context, layout, data, item, _icon, _active_data, _active_propname, index):

        # data is the owning RigItem (selected_rig, passed to template_list),
        # so which fields make sense to show depends on it, not on globals.
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "label", text="")

        if data.is_blender_rig:
            if data.armature_ptr is not None:
                # Real dropdown/search against the armature's actual bones,
                # instead of a free-typed, typo-prone string.
                row.prop_search(item, "bone_name", data.armature_ptr.data, "bones", text="")
            else:
                row.prop(item, "bone_name", text="")
            row.prop(item, "tail_or_head", toggle=True)
        else:
            row.prop(item, "real_obj", text="")


class ConnectionList(UIList):

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        row = layout.row(align=True)
        row.prop(item, 'index_a', text="")
        row.label(text="", icon='FORWARD')
        row.prop(item, 'index_b', text="")


class RegisteredSkeletonsList(UIList):

    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname, _index):
        scene = context.scene

        col = layout.column(align=True)

        top = col.row(align=True)
        top.prop(item, 'enabled', text="")
        top.label(text="", icon='ARMATURE_DATA' if item.is_blender_rig else 'EMPTY_AXIS')
        top.prop(item, 'rig_name', text="", emboss=False)
        top.prop(item, 'identity', text="ID")

        bottom = col.row(align=True)
        # if the class id is set, show a small band with the class color for clarity


        cls = next((cls for cls in scene.labeling_data.label_classes
                    if str(cls.class_id).lower() == item.class_id.lower()), None)
        if cls:
            sub = bottom.column(align=True)
            sub.scale_x = 0.3
            sub.prop(cls, 'color', text='')

        bottom.prop(item, 'class_id', text="")
        if item.is_blender_rig:
            bottom.prop(item, 'armature_ptr', text="")


class LandmarkSection:
    """ Draws the skeleton/landmark labeling configuration: registered rigs,
    the selected rig's keypoint mapping, its skeleton connections, and the
    viewport visualization toggle. """

    @staticmethod
    def draw(layout, context):
        settings = context.scene.pose_label_settings

        # Rig list
        # Add rigs, the add button is modal and allows to select either an
        # existing Blender armature or define a custom/virtual rig.
        layout.label(text="Registered Rigs", icon='ARMATURE_DATA')
        row = layout.row(align=True)

        row.template_list(
            RegisteredSkeletonsList.__name__, "rig_list",
            settings, "labeled_rigs",
            settings, "selected_rig",
            rows=5
        )
        col = row.column(align=True)
        col.operator(Labels.ADD_RIG.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_RIG.value, icon='REMOVE', text='')
        col.separator()
        col.operator(Labels.DETECT_BONES.value, icon='BONE_DATA', text='')

        # Get the current rig to draw either the bone keypoint mapping or
        # general object to keypoint mapping.
        selected_rig = settings.get_current_rig()
        if selected_rig is None:
            # If no rig is available, nothing further can be configured.
            return

        # Bone/object -> keypoint mapping
        layout.separator()
        layout.label(text="Keypoint Mapping")
        row = layout.row(align=True)
        row.template_list(
            KeypointList.__name__, "keypoint_list",
            selected_rig, "keypoints",
            selected_rig, "keypoints_index",
            rows=5
        )
        col = row.column(align=True)
        col.operator(Labels.ADD_KEYPOINT.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_KEYPOINT.value, icon='REMOVE', text='')
        col.separator()
        col.operator(Labels.SANITIZE_BONE_MAPPING.value, icon='FILE_REFRESH', text='')

        # Even if the rig is not a blender rig, the user may want to specify
        # keypoint connections to describe the skeleton's topology.
        layout.separator()
        layout.label(text="Skeleton Connections")
        row = layout.row(align=True)

        col = row.column(align=True)
        Legend.draw(col, context, ["From", "To"])
        col.template_list(
            ConnectionList.__name__, "connection_list",
            selected_rig, "connections",
            selected_rig, "connections_index",
            rows=3
        )
        col = row.column(align=True)
        col.operator(Labels.ADD_CONNECTION.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_CONNECTION.value, icon='REMOVE', text='')

        # Viewport visualization toggle, kept as its own clearly labeled
        # action rather than tucked into a list's add/remove column.
        layout.separator()
        row = layout.row(align=True)
        if settings.currently_visualizing:
            row.operator(Labels.STOP_VISUALIZE_SKELETON.value, icon='HIDE_ON', text="Stop Visualizing")
        else:
            row.operator(Labels.VISUALIZE_SKELETON.value, icon='HIDE_OFF', text="Visualize Skeleton")