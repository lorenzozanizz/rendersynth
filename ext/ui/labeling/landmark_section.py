import bpy
from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import (
    StringProperty, IntProperty, BoolProperty,
    CollectionProperty, PointerProperty
)

from ...operators.names import Labels

class KeypointItem(PropertyGroup):
    bone_name: StringProperty(name="Bone")                                  # type: ignore
    label: StringProperty(name="Label")                                     # type: ignore
    index: IntProperty(name="Index", min=0)                                 # type: ignore
    include: BoolProperty(name="Include", default=True)                     # type: ignore


class SkeletonConnectionItem(PropertyGroup):
    index_a: IntProperty(name="From", min=0)                                # type: ignore
    index_b: IntProperty(name="To", min=0)                                  # type: ignore

class RigItem(PropertyGroup):

    rig_name: StringProperty(name="")                                       # type: ignore
    enabled: BoolProperty(name="Enabled", default=True)                     # type: ignore
    identity: IntProperty(name="Identity", default=0)                       # type: ignore
    is_blender_rig: BoolProperty(name="Blender Rig", default=False)         # type: ignore


class PoseLabelSettings(PropertyGroup):

    # There can be multiple armatures.
    labeled_rigs: CollectionProperty(type=RigItem)                          # type: ignore
    selected_rig: IntProperty(name="Selected", default=0)                   # type: ignore

    keypoints: CollectionProperty(type=KeypointItem)                        # type: ignore
    keypoints_index: IntProperty(name="Active Keypoint", default=0)         # type: ignore

    connections: CollectionProperty(type=SkeletonConnectionItem)            # type: ignore
    connections_index: IntProperty(name="Active Connection", default=0)     # type: ignore



class KeypointList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
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
        row = layout.row(align=True)


class LandmarkSection:

    @staticmethod
    def draw(layout, context):
        settings = context.scene.pose_label_settings

        row = layout.row(align=True)
        # Armature selector
        # Add armatures, the add button is modal and allows to select the armature
        # separately.

        layout.label(text="Registered Armatures", icon='ARMATURE_DATA')
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

        col.operator(Labels.DETECT_BONES.value, icon='BONE_DATA', text='')
        col.separator()

        row = layout.row(align=True)
        row.prop(settings, "armature", text="")
        layout.separator()

        # Bone → keypoint mapping
        layout.label(text="Bone/Keypoint Mapping")
        row = layout.row(align=True)
        row.template_list(
            KeypointList.__name__, "keypoint_list",
            settings, "keypoints",
            settings, "keypoints_index",
            rows=5
        )
        row.separator()
        col = row.column(align=True)
        col.operator("rendersynth.add_keypoint", icon='ADD', text='')
        col.operator("rendersynth.remove_keypoint", icon='REMOVE', text='')
        col.separator()

        layout.separator()

        layout.label(text="Skeleton Connections")

        row = layout.row(align=True)
        # Skeleton connections
        row.template_list(
            ConnectionList.__name__, "connection_list",
            settings, "connections",
            settings, "connections_index",
            rows=3
        )
        row.separator()
        col = row.column(align=True)
        col.operator("rendersynth.add_connection", icon='ADD', text='')
        col.operator("rendersynth.remove_connection", icon='REMOVE', text='')
        col.separator()

        # Edit the active connection inline
        if settings.connections and settings.connections_index < len(settings.connections):
            active_conn = settings.connections[settings.connections_index]
            row = layout.row(align=True)
            row.prop(active_conn, "index_a", text="From")
            row.prop(active_conn, "index_b", text="To")
