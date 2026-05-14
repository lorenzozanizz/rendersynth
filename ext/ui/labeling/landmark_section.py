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


class PoseLabelSettings(PropertyGroup):

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


class AutoDetectBonesOperator(Operator):
    bl_idname = "rendersynth.auto_detect_bones"
    bl_label = "Auto-detect"
    bl_description = "Populate keypoint list from the selected armature"

    def execute(self, context):
        settings = context.scene.pose_label_settings
        arm = settings.armature

        if arm is None or arm.type != 'ARMATURE':
            self.report({'WARNING'}, "Select an armature first")
            return {'CANCELLED'}

        settings.keypoints.clear()

        # Deform bones are the ones that actually drive mesh deformation.
        # Decide here whether to filter to use_deform only or expose all bones.
        bones = [b for b in arm.data.bones if b.use_deform]

        for i, bone in enumerate(bones):
            item = settings.keypoints.add()
            item.bone_name = bone.name
            item.label = bone.name
            item.index = i
            item.include = True

        return {'FINISHED'}


class AddKeypointOperator(Operator):
    bl_idname = "rendersynth.add_keypoint"
    bl_label = "Add"

    def execute(self, context):
        settings = context.scene.pose_label_settings
        item = settings.keypoints.add()
        item.index = len(settings.keypoints) - 1
        settings.keypoints_index = len(settings.keypoints) - 1
        return {'FINISHED'}


class RemoveKeypointOperator(Operator):
    bl_idname = "rendersynth.remove_keypoint"
    bl_label = "Remove"

    def execute(self, context):
        settings = context.scene.pose_label_settings
        idx = settings.keypoints_index
        if idx < len(settings.keypoints):
            settings.keypoints.remove(idx)
            settings.keypoints_index = max(0, idx - 1)
        return {'FINISHED'}


class AddConnectionOperator(Operator):
    bl_idname = "rendersynth.add_connection"
    bl_label = "Add"

    def execute(self, context):
        settings = context.scene.pose_label_settings
        settings.connections.add()
        settings.connections_index = len(settings.connections) - 1
        return {'FINISHED'}


class RemoveConnectionOperator(Operator):
    bl_idname = "rendersynth.remove_connection"
    bl_label = "Remove"

    def execute(self, context):
        settings = context.scene.pose_label_settings
        idx = settings.connections_index
        if idx < len(settings.connections):
            settings.connections.remove(idx)
            settings.connections_index = max(0, idx - 1)
        return {'FINISHED'}


class SavePoseConfigOperator(Operator):
    bl_idname = "rendersynth.save_pose_config"
    bl_label = "Save Configuration"
    bl_description = "Serialize keypoint mapping and skeleton connections to the pipeline JSON"

    def execute(self, context):
        settings = context.scene.pose_label_settings

        keypoints = [
            {
                "bone": kp.bone_name,
                "label": kp.label,
                "index": kp.index,
                "include": kp.include,
            }
            for kp in settings.keypoints
        ]

        connections = [
            [c.index_a, c.index_b]
            for c in settings.connections
        ]

        # Hook this into your existing pipeline serialization instead of printing
        print("Keypoints:", keypoints)
        print("Skeleton:", connections)

        self.report({'INFO'}, "Pose configuration saved")
        return {'FINISHED'}


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
        layout.template_list(
            KeypointList.__name__, "keypoint_list",
            settings, "keypoints",
            settings, "keypoints_index",
            rows=5
        )
        row = layout.row(align=True)
        row.operator("rendersynth.add_keypoint", icon='ADD')
        row.operator("rendersynth.remove_keypoint", icon='REMOVE')

        layout.separator()

        # Skeleton connections
        layout.label(text="Skeleton Connections")
        layout.template_list(
            ConnectionList.__name__, "connection_list",
            settings, "connections",
            settings, "connections_index",
            rows=3
        )

        # Edit the active connection inline
        if settings.connections and settings.connections_index < len(settings.connections):
            active_conn = settings.connections[settings.connections_index]
            row = layout.row(align=True)
            row.prop(active_conn, "index_a", text="From")
            row.prop(active_conn, "index_b", text="To")

        row = layout.row(align=True)
        row.operator("rendersynth.add_connection", icon='ADD')
        row.operator("rendersynth.remove_connection", icon='REMOVE')

        layout.separator()
        layout.operator("rendersynth.save_pose_config", icon='FILE_TICK')
