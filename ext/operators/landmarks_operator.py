from bpy.types import Operator

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
