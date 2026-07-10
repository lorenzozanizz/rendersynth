from bpy.types import Operator, Object
from bpy.props import EnumProperty, StringProperty

from .names import Labels
from ..labeling.keypoint_resolver import KeypointPositionResolver
from ..labeling.skeleton_viewport import skeleton_viewport_drawer

class AutoDetectBonesOperator(Operator):
    bl_idname = Labels.DETECT_BONES.value
    bl_label = "Auto-detect"
    bl_description = "Populate keypoint list from the current rig's armature"

    def execute(self, context):
        settings = context.scene.pose_label_settings

        rig = settings.get_current_rig()
        if rig is None:
            self.report({'WARNING'}, "Select a rig first")
            return {'CANCELLED'}

        # Auto-detection can only work on blender rigs, because the information about
        # the bone hierarchy is already only present in blender rigs. a skeleton
        # composed of arbitrary objects cannot be automatically composed
        if not rig.is_blender_rig:
            self.report({'WARNING'}, "Auto-detect only applies to Blender rigs")
            return {'CANCELLED'}

        arm = rig.armature_ptr
        if arm is None or arm.type != 'ARMATURE':
            self.report({'WARNING'}, "Assign an armature to this rig first")
            return {'CANCELLED'}

        rig.keypoints.clear()

        # Deform bones are the ones that actually drive mesh deformation.
        # Decide here whether to filter to use_deform only or expose all bones.
        bones = [b for b in arm.data.bones if b.use_deform]

        # Note: This does not create CONNECTIONS between bones, only sets up the
        # bone names. This is because the hierarchy of bones is unreliable for
        # connections due to convenience/utility bones for inverse kinematics.
        for i, bone in enumerate(bones):
            item = rig.keypoints.add()
            item.bone_name = bone.name
            item.label = bone.name
            item.index = i
            item.enabled = True

        return {'FINISHED'}


class AddKeypointOperator(Operator):
    bl_idname = Labels.ADD_KEYPOINT.value
    bl_label = "Add"

    def execute(self, context):
        """ Add a keypoint to the skeleton of the currently selected rig. Note that a mapped keypoint
        can either be a real bone or a mapped object. """
        settings = context.scene.pose_label_settings
        # Get the currently selected skeleton. If no skeleton is available, just give up.

        rig = settings.get_current_rig()
        if rig is None:
            return {'CANCELLED'}

        item = rig.keypoints.add()
        item.index = len(rig.keypoints) - 1
        return { 'FINISHED' }


class RemoveKeypointOperator(Operator):

    bl_idname = Labels.REMOVE_KEYPOINT.value
    bl_label = "Remove"

    def execute(self, context):
        settings = context.scene.pose_label_settings

        rig = settings.get_current_rig()
        if rig is None:
            return {'CANCELLED'}

        idx = rig.keypoints_index
        if idx < len(rig.keypoints):
            rig.keypoints.remove(idx)
            rig.keypoints_index = max(0, idx - 1)
        return { 'FINISHED' }


class AddConnectionOperator(Operator):
    bl_idname = Labels.ADD_CONNECTION.value
    bl_label = "Add"

    def execute(self, context):
        settings = context.scene.pose_label_settings

        rig = settings.get_current_rig()
        if rig is None:
            return {'CANCELLED'}

        rig.connections.add()
        rig.connections_index = len(rig.connections) - 1
        return {'FINISHED'}


class RemoveConnectionOperator(Operator):
    bl_idname = Labels.REMOVE_CONNECTION.value
    bl_label = "Remove"

    def execute(self, context):
        settings = context.scene.pose_label_settings

        rig = settings.get_current_rig()
        if rig is None:
            return {'CANCELLED'}

        idx = rig.connections_index
        if idx < len(rig.connections):
            rig.connections.remove(idx)
            rig.connections_index = max(0, idx - 1)
        return {'FINISHED'}


class VisualizeSkeletonOperator(Operator):
    bl_idname = Labels.VISUALIZE_SKELETON.value
    bl_label = "Visualize Bones Configuration"
    bl_description = "Draw the current rig's keypoints and connections in the viewport"

    def execute(self, context):

        settings = context.scene.pose_label_settings
        if settings.currently_visualizing:
            self.report({'INFO'}, "The skeleton is already being visualized.")
            return {'CANCELLED'}

        rig = settings.get_current_rig()
        if rig is None:
            self.report({'WARNING'}, "Select a rig first")
            return {'CANCELLED'}

        # start visualizing and set the visualization active flag for the
        # skeleton settings.
        skeleton_viewport_drawer.start()
        settings.currently_visualizing = True
        rig.is_being_visualized = True

        return {'FINISHED'}


class StopVisualizeSkeletonOperator(Operator):
    bl_idname = Labels.STOP_VISUALIZE_SKELETON.value
    bl_label = "Stop Viewing Bones Configuration"
    bl_description = "Stop drawing the current rig's keypoints and connections in the viewport"

    def execute(self, context):

        settings = context.scene.pose_label_settings
        if not settings.currently_visualizing:
            self.report({'INFO'}, "No skeleton is being visualized currently.")
            return {'CANCELLED'}

        # stop visualizing
        skeleton_viewport_drawer.stop()
        settings.currently_visualizing = False
        # mark the interrupted visualization in the per-skeleton visualization flag
        rig = settings.get_current_rig()
        if rig is not None:
            rig.is_being_visualized = False

        return {'FINISHED'}



class AddRigOperator(Operator):
    """Add rig (Blender armature or custom) to list"""
    bl_idname = Labels.ADD_RIG.value
    bl_label = "Add Rig"

    # Modal selection mode
    mode: EnumProperty(items=[                                              # type: ignore
        ('BLENDER', "Blender Armature", "Use existing Blender rig"),
        ('CUSTOM', "Custom Rig", "Define non-Blender rig by name")
    ], default='BLENDER', name="Rig Mode")

    custom_rig_name: StringProperty(name="Rig Name", default="")            # type: ignore

    def draw(self, context):
        settings = context.scene.pose_label_settings
        layout = self.layout
        layout.prop(self, "mode")

        if self.mode == 'BLENDER':
            layout.prop(settings, "selected_armature_pointer")
        else:
            layout.prop(self, "custom_rig_name")

    def execute(self, context):
        settings = context.scene.pose_label_settings
        if self.mode == 'BLENDER':
            armature = settings.selected_armature_pointer
            if not armature:
                self.report({'WARNING'}, "Select a Blender armature!")
                return {'CANCELLED'}
            rig_name = armature.name
            is_blender = True
        else:
            if not self.custom_rig_name.strip():
                self.report({'WARNING'}, "Enter a rig name!")
                return {'CANCELLED'}
            rig_name = self.custom_rig_name
            is_blender = False

        # Add to list
        rig = settings.labeled_rigs.add()
        rig.rig_name = rig_name
        rig.is_blender_rig = is_blender
        if is_blender:
            rig.armature_ptr = armature
        settings.selected_rig = len(settings.labeled_rigs) - 1

        return {'FINISHED'}

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)


class RemoveRigOperator(Operator):
    bl_idname = Labels.REMOVE_RIG.value
    bl_label = "Remove Rig"

    def execute(self, context):
        settings = context.scene.pose_label_settings
        idx = settings.selected_rig

        if 0 <= idx < len(settings.labeled_rigs):
            settings.labeled_rigs.remove(idx)
            settings.selected_rig = min(idx, len(settings.labeled_rigs) - 1)
            return {'FINISHED'}

        self.report({'WARNING'}, "No rig selected")
        return {'CANCELLED'}

class SanitizeBoneMappingOperator(Operator):
    bl_idname = Labels.SANITIZE_BONE_MAPPING.value
    bl_label = "Sanitize Bone Mapping Rig"
    bl_description = "Drop keypoints whose mapped bone or object no longer exists"

    def execute(self, context):
        settings = context.scene.pose_label_settings

        rig = settings.get_current_rig()
        if rig is None:
            self.report({'WARNING'}, "Select a rig first")
            return {'CANCELLED'}

        # Collect indices back to front, so removal does not shift the
        # indices of keypoints still to be checked.
        stale_positions = [
            position for position, keypoint in enumerate(rig.keypoints)
            if KeypointPositionResolver.resolve_location(rig, keypoint) is None
        ]

        for position in reversed(stale_positions):
            rig.keypoints.remove(position)

        rig.keypoints_index = min(rig.keypoints_index, max(0, len(rig.keypoints) - 1))

        if stale_positions:
            self.report({'INFO'}, f"Removed {len(stale_positions)} stale keypoint(s)")
        else:
            self.report({'INFO'}, "No stale keypoints found")

        return {'FINISHED'}