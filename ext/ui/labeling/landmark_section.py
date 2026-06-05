import bpy

from typing import Optional

from bpy.types import Panel, Operator, PropertyGroup, UIList, Object
from bpy.props import (
    StringProperty, IntProperty, BoolProperty,
    CollectionProperty, PointerProperty
)

from ...operators.names import Labels

class KeypointItem(PropertyGroup):

    label: StringProperty(name="Label")                                     # type: ignore
    index: IntProperty(name="Index", min=0)                                 # type: ignore
    enabled: BoolProperty(name="Include", default=True)                     # type: ignore

    # Conditionally active if this is a mapped (virtual)
    real_obj: PointerProperty(name="Mapped Object", type=Object)            # type: ignore
    bone_name: StringProperty(name="Bone")                                  # type: ignore

    # Conditionally active if this is a real bone
    tail_or_head: BoolProperty(name="Include", default=True)                # type: ignore
    bone_obj: PointerProperty(                                              # type: ignore
        name="Mapped Bone",
        type=Object,
        poll=lambda self, obj: obj.type == 'BONE'
    )

class SkeletonConnectionItem(PropertyGroup):
    index_a: IntProperty(name="From", min=0)                                # type: ignore
    index_b: IntProperty(name="To", min=0)                                  # type: ignore

class RigItem(PropertyGroup):

    rig_name: StringProperty(name="Rig Name")                               # type: ignore
    enabled: BoolProperty(name="Enabled", default=True)                     # type: ignore
    identity: IntProperty(name="Identity", default=0)                       # type: ignore

    # A rig may be really existing in blender, or it may be a virtual rig for
    # which the user must specify which blender objects have to be
    # mapped to bones
    is_blender_rig: BoolProperty(name="Blender Rig", default=False)         # type: ignore

    # Skeleton connections: which bones are connected to which
    connections: CollectionProperty(type=SkeletonConnectionItem)            # type: ignore
    connections_index: IntProperty(name="Active Connection", default=0)     # type: ignore

    # Actual bone/map data: Either real bones, or fake bones.
    keypoints: CollectionProperty(type=KeypointItem)                        # type: ignore
    keypoints_index: IntProperty(name="Active Keypoint", default=0)         # type: ignore


class PoseLabelSettings(PropertyGroup):

    # There can be multiple armatures.
    labeled_rigs: CollectionProperty(type=RigItem)                          # type: ignore
    selected_rig: IntProperty(name="Selected", default=0)                   # type: ignore

    selected_armature_pointer: PointerProperty(                             # type: ignore
        name="Blender Armature",
        type=Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

    def get_current_rig(self) -> Optional[None]:

        rigs = self.labeled_rigs
        rig_index = self.selected_rig
        selected_rig = None if rig_index < 0 or rig_index >= len(rigs) else rigs[rig_index]
        return selected_rig

class KeypointList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):

        # Use the current context to view if the current rig is a real
        # rig or a virtual rig.

        row = layout.row(align=True)
        row.prop(item, "include", text="")
        row.prop(item, "bone_name", text="", emboss=False)
        row.prop(item, "label", text="")
        row.prop(item, "index", text="")


class ConnectionList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.label(text=f"[{item.index_a}, {item.index_b}]")

class RegisteredSkeletonsList(UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        settings = context.scene.pose_label_settings
        rigs = settings.labeled_rigs
        rig_index = settings.selected_rig
        selected_rig = None if rig_index < 0 or rig_index >= len(rigs) else rigs[rig_index]
        if selected_rig is None:
            # If no rig is available, just return
            return
        # Bone name, enabled, identity, etc... are shared between real bones and mappings.
        row = layout.row(align=True)


        if selected_rig.is_blender_rig:
            row.prop(item, 'b_obj', text='')
        else:
            row.prop(item, 'tail_or_head', text='')
"""    bone_name: StringProperty(name="Bone")                                  # type: ignore

    label: StringProperty(name="Label")                                     # type: ignore
    index: IntProperty(name="Index", min=0)                                 # type: ignore
    enabled: BoolProperty(name="Include", default=True)                     # type: ignore
    tail_or_head: BoolProperty(name="Include", default=True)                # type: ignore

    # Conditionally active if this is a mapped (virtual)
    b_obj: PointerProperty(name="Mapped Object", type=Object)               # type: ignore
"""






class LandmarkSection:

    @staticmethod
    def draw(layout, context):
        settings = context.scene.pose_label_settings

        # Armature selector
        # Add armatures, the add button is modal and allows to select the armature
        # separately.
        layout.label(text="Registered Armatures", icon='ARMATURE_DATA')
        row = layout.row(align=True)

        row.template_list(
            RegisteredSkeletonsList.__name__, "rig_list",
            settings, "labeled_rigs",
            settings, "selected_rig",
            rows=5
        )
        row.separator()
        col = row.column(align=True)
        col.operator(Labels.ADD_RIG.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_RIG.value, icon='REMOVE', text='')
        col.separator()
        col.operator(Labels.DETECT_BONES.value, icon='BONE_DATA', text='')


        # Get the current armature to print either the bone keypoint mapping or
        # general object to keypoint mapping.
        rigs = settings.labeled_rigs
        rig_index = settings.selected_rig
        selected_rig = None if rig_index < 0 or rig_index >= len(rigs) else rigs[rig_index]
        if selected_rig is None:
            # If no rig is available, just return
            return

        # Bone → keypoint mapping
        layout.label(text="Bone/Keypoint Mapping")
        row = layout.row(align=True)
        row.template_list(
            KeypointList.__name__, "keypoint_list",
            selected_rig, "keypoints",
            selected_rig, "keypoints_index",
            rows=5
        )
        row.separator()
        col = row.column(align=True)
        col.operator(Labels.ADD_KEYPOINT.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_KEYPOINT.value, icon='REMOVE', text='')
        col.separator()

        # Even if the skeleton is not a blender rig, the user may want to specify bone
        # connections.
        layout.separator()
        layout.label(text="Skeleton Connections")
        row = layout.row(align=True)
        # Skeleton connections
        row.template_list(
            ConnectionList.__name__, "connection_list",
            selected_rig, "connections",
            selected_rig, "connections_index",
            rows=3
        )
        row.separator()
        col = row.column(align=True)
        col.operator(Labels.ADD_CONNECTION.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_CONNECTION.value, icon='REMOVE', text='')
        col.separator()

