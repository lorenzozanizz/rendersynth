""" Shared resolution logic for turning a configured KeypointItem into an actual
world-space location. Kept as a single reusable class so that every consumer
(the viewport skeleton visualizer, and later the keypoints Extractor)
resolves bone/object mappings the exact same way.

"""

from typing import Optional

from mathutils import Vector


class KeypointPositionResolver:
    """ Resolves KeypointItem/RigItem pairs to world-space positions.

    A keypoint resolves differently depending on the owning rig:

    - Blender rig (RigItem.is_blender_rig is True): the keypoint's bone_name
      is looked up on RigItem.armature_ptr's pose bones, and tail_or_head
      selects which end of the bone gives the point.
    - Custom rig (RigItem.is_blender_rig is False): the keypoint's real_obj
      is used directly.
    """

    @staticmethod
    def resolve_location(rig, keypoint) -> Optional[Vector]:
        """ Resolve a single keypoint to a world-space location.

        :param rig: RigItem owning the keypoint.
        :param keypoint: KeypointItem to resolve.
        :return: World-space Vector, or None if the mapping is incomplete
            or no longer valid (e.g. a deleted object, or a bone that does
            not exist on the armature anymore).
        """

        if rig.is_blender_rig:
            return KeypointPositionResolver._resolve_bone_location(rig, keypoint)
        return KeypointPositionResolver._resolve_object_location(keypoint)

    @staticmethod
    def _resolve_bone_location(rig, keypoint) -> Optional[Vector]:
        """

        :param rig:
        :param keypoint:
        :return:
        """
        armature = rig.armature_ptr
        if armature is None or armature.type != 'ARMATURE':
            return None

        pose_bone = armature.pose.bones.get(keypoint.bone_name)
        if pose_bone is None:
            return None

        local_point = pose_bone.tail if keypoint.tail_or_head else pose_bone.head
        return armature.matrix_world @ local_point

    @staticmethod
    def _resolve_object_location(keypoint) -> Optional[Vector]:
        """ This resolves the true position of a real Blender object (not a
        blender bone, which can have both a tail and head position corresponding
        to its lower and bigger end respectively.

        :param keypoint: The blender object surrogate for the keypoint
        :return: a position
        """
        if keypoint.real_obj is None:
            return None
        return keypoint.real_obj.matrix_world.translation

    @staticmethod
    def resolve_rig_positions(rig, only_enabled: bool = True) -> dict:
        """ Resolve every keypoint of a rig at once.

        :param rig: RigItem whose keypoints should be resolved.
        :param only_enabled: If True, skip keypoints with enabled set to False.
        :return: Dictionary mapping KeypointItem.index to its resolved
            world-space Vector. Keypoints that fail to resolve are omitted.
        """

        positions = {}
        for keypoint in rig.keypoints:
            if only_enabled and not keypoint.enabled:
                continue
            location = KeypointPositionResolver.resolve_location(rig, keypoint)
            if location is not None:
                positions[keypoint.index] = location

        return positions