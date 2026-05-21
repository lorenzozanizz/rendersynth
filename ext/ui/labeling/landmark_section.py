import bpy
from bpy.types import Panel, Operator, PropertyGroup, UIList
from bpy.props import (
    StringProperty, IntProperty, BoolProperty,
    CollectionProperty, PointerProperty
)

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

class PoseLabelSettings(PropertyGroup):

    # There can be multiple armatures.

    armature: PointerProperty(                                              # type: ignore
        name="Armature",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
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

        # Armature selector
        layout.label(text="Armature", icon='ARMATURE_DATA')
        row = layout.row(align=True)
        row.prop(settings, "armature", text="")
        row.operator("rendersynth.auto_detect_bones", text="Auto-detect")

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
