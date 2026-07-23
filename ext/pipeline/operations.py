"""



"""

from .operation_registry import OperationRegistry
from .context import *

from ..constants import PipeNames, WidgetSerializationKeys
from ..utils.logger import UniqueLogger
from ..distribution.computation import SamplerCompiler, Distribution
from ..distribution.bezier import BezierDistribution, BezierCurve

from typing import Any, List, Tuple, Callable
from abc import ABCMeta, abstractmethod
import os

import bpy

wsk = WidgetSerializationKeys

class PipelineOperation(DoubleFramedPipe, metaclass=ABCMeta):
    """Base class for all pipeline operations."""

    operation_type: str  # "randomize_position", "randomize_rotation", etc.

    @abstractmethod
    def compile(self, context, config: dict):
        """

        :param config:
        :return:
        """
        pass

    @abstractmethod
    def execute(self, context):
        """

        :param context:
        :return:
        """
        pass

class AxisSetMask:

    def __init__(self, config: dict[str, Any]):
        self.dimensions = config[wsk.DIMENSION.value]
        self.x = config[wsk.AXIS_RANDOMIZE_PREFIX_X.value]
        self.y = config[wsk.AXIS_RANDOMIZE_PREFIX_Y.value]
        self.z = config[wsk.AXIS_RANDOMIZE_PREFIX_Z.value]

    def dimensions(self):
        return self.dimensions

    def assign(self, vector_attribute: Any, value: Any):
        """

        :param vector_attribute:
        :param value:
        :return:
        """
        axes = [ax for ax in ['x', 'y', 'z'] if getattr(self, ax)]
        for axis, val in zip(axes, value):
            setattr(vector_attribute, axis, val)

    def increment(self, vector_attribute: Any, value: Any):
        """

        :param vector_attribute:
        :param value:
        :return:
        """
        idx = 0
        if self.x:
            vector_attribute.x += value[idx]
            idx += 1
        if self.y:
            vector_attribute.y += value[idx]
            idx += 1
        if self.z:
            vector_attribute.z += value[idx]
        return


class NumericRandomOperation(PipelineOperation, metaclass=ABCMeta):
    """

    """

    def __init__(self):

        self.offset_mode    = None
        self.dimension      = None
        self.distribution   = None
        self.axis           = None
        self.targets        = None

    def compile(self, context, config: dict):
        """

        :param context:
        :param config:
        :return:
        """

        # Simply extract the value from the config
        self.dimension = int(config[wsk.DIMENSION.value])
        # The distribution will be compiled (either a node or a preset distribution)
        self.distribution = SamplerCompiler.compile(config[wsk.NODE_DISTRIBUTION.value], self.dimension)

        # Extract the axis and the targets. the axis object is a simple interface for
        # assigning on different dimensions
        self.axis = AxisSetMask(config[wsk.AXIS.value])
        self.targets = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]

        # This is a boolean value
        self.offset_mode = config[wsk.OFFSET.value][wsk.OFFSET_MODE.value]

    @abstractmethod
    def get_context(self):
        """

        :return:
        """
        pass

    def get_global_context(self):
        return self.get_context()

    def get_frame_context(self):
        """

        :return:
        """
        if self.offset_mode:
            return self.get_context()
        else:
            return None

@OperationRegistry.register(PipeNames.SCALE.value)
class RandomizeScaleOperation(NumericRandomOperation):

    def execute(self, context):
        result = self.distribution.sample()
        for item in self.targets:
            obj = bpy.data.objects[item]
            if self.offset_mode:
                self.axis.increment(obj.scale, result)
            else:
                self.axis.assign(obj.scale, result)

    class ScaleContext(ContextManager):

        def __init__(self, items):
            self.items = items
            self.scales = []

        def __enter__(self):
            # Clear to avoid polluting and damaging the values
            self.scales.clear()
            for item in self.items:
                self.scales.append(tuple(bpy.data.objects[item].scale))

        def __exit__(self, exc_type, exc_val, exc_tb):
            for item, scale in zip(self.items, self.scales):
                bpy.data.objects[item].scale = scale

    def get_context(self):
        return RandomizeScaleOperation.ScaleContext(self.targets)


@OperationRegistry.register(PipeNames.INTENSITY.value)
class RandomizeIntensityOperation(PipelineOperation):

    def __init__(self):

        self.distribution = None
        self.node = None
        self.offset_mode = None

    def compile(self, context, config: dict):
        # Note: the value is assumed to be scalar!... for now
        # The distribution will be compiled (either a node or a preset distribution)
        self.distribution = SamplerCompiler.compile(config[wsk.NODE_DISTRIBUTION.value], dim=1)
        node_label = config[wsk.VALUE.value][wsk.VALUE_LABEL.value]
        material = config[wsk.VALUE.value][wsk.VALUE_MATERIAL.value]
        # Already extract the target node.
        material = bpy.data.materials.get(material)
        nodes = material.node_tree.nodes
        self.node = next(node for node in nodes if node.label == node_label)

        # This is a boolean value
        self.offset_mode = config[wsk.OFFSET.value][wsk.OFFSET_MODE.value]

    def execute(self, context):

        # Extract a value, then find the target node and change its value.
        value = self.distribution.sample()[0]
        if self.offset_mode:
            self.node.outputs[0].default_value += value
        else:
            self.node.outputs[0].default_value = value

    class PropertyValueContext:

        def __init__(self, node):
            self.node = node
            self.prev_val = None

        def __enter__(self):
            """ Enter the node value context manger """
            self.prev_val = self.node.outputs[0].default_value

        def __exit__(self, exc_type, exc_val, exc_tb):
            """ Exit the node value context manger """
            self.node.outputs[0].default_value = self.prev_val

    def get_global_context(self):
        """ Get the global context for the property value, which is entrusted with
        the job of restoring the context of the value for the selected node
        :return: a Context object.
        """
        return RandomizeIntensityOperation.PropertyValueContext(self.node)

    def get_frame_context(self):
        """

        :return:
        """
        return RandomizeIntensityOperation.PropertyValueContext(self.node)


@OperationRegistry.register(PipeNames.TEXTURE.value)
class RandomizeTextureOperation(PipelineOperation):

    def __init__(self):
        self.node = None
        self.image_paths = None
        self.use_folder_mode = None
        self.image_folder = None
        self.distribution = None

    def compile(self, context, config: dict):
        """

        :param context:
        :param config:
        :return:
        """

        # Extract texture node target
        node_config = config[wsk.TEXTURE.value]
        material_name = node_config["material"]
        node_label = node_config["label"]

        # Get the material and find the target node
        material = bpy.data.materials.get(material_name)
        if not material or not material.use_nodes:
            return

        nodes = material.node_tree.nodes
        self.node = next(
            (node for node in nodes if node.label == node_label),
            None
        )
        # Extract image paths/folder configuration
        path_config = config[wsk.PATH.value]
        self.use_folder_mode = path_config[wsk.PATH_USE_FOLDER.value]

        # Load all image paths from folder, if the selection already specifies individual items
        # just use those
        if self.use_folder_mode:
            self.image_folder = path_config[wsk.PATH_FOLDER.value]
            self.image_paths = self._load_images_from_folder(self.image_folder)
        else:
            self.image_paths = path_config[wsk.PATH_FILES.value]

        self.distribution = SamplerCompiler.make_distribution(
            Distribution.CATEGORICAL_UNIFORM.name, 1, n=len(self.image_paths) - 1)

    @staticmethod
    def _load_images_from_folder(folder_path: str) -> list:
        """Load all image file paths from a folder"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.exr', '.tiff', '.webp'}
        images = []

        try:
            for file in os.listdir(folder_path):
                if os.path.splitext(file)[1].lower() in image_extensions:
                    images.append(os.path.join(folder_path, file))
        except (OSError, FileNotFoundError):
            return []

        return sorted(images)

    def execute(self, context):
        if not self.node or not self.image_paths:
            return
        # Select a random image path
        selected_material_idx = min(max(0, int(self.distribution.sample()[0])), len(self.image_paths) - 1)
        selected_path = self.image_paths[selected_material_idx]

        image = bpy.data.images.load(selected_path, check_existing=True)
        if self.node.type == 'TEX_IMAGE':
            self.node.image = image

    class TextureContext:

        def __init__(self, node):
            self.node = node
            self.prev_image = None

        def __enter__(self):
            """Store the current image"""
            if self.node and self.node.type == 'TEX_IMAGE':
                self.prev_image = self.node.image

        def __exit__(self, exc_type, exc_val, exc_tb):
            """Restore the previous image"""
            if self.node and self.node.type == 'TEX_IMAGE':
                self.node.image = self.prev_image

    def get_global_context(self):
        """Get context manager for global (full render) state"""
        return RandomizeTextureOperation.TextureContext(self.node)

    def get_frame_context(self):
        """Get context manager for per-frame state"""
        return RandomizeTextureOperation.TextureContext(self.node)


@OperationRegistry.register(PipeNames.POSITION.value)
class RandomizePositionOperation(NumericRandomOperation):

    def execute(self, context):
        result = self.distribution.sample()
        for item in self.targets:
            obj = bpy.data.objects[item]
            if self.offset_mode:
                self.axis.increment(obj.location, result)
            else:
                self.axis.assign(obj.location, result)

    class PositionContext(ContextManager):

        def __init__(self, items):
            self.items = items
            self.location = []

        def __enter__(self):
            # Clear to avoid polluting and damaging the values
            self.location.clear()
            for item in self.items:
                self.location.append(tuple(bpy.data.objects[item].location))

        def __exit__(self, exc_type, exc_val, exc_tb):
            for item, location in zip(self.items, self.location):
                bpy.data.objects[item].location = location

    def get_context(self):
        return RandomizePositionOperation.PositionContext(self.targets)


@OperationRegistry.register(PipeNames.MOVE.value)
class RandomizeMoveOperation(PipelineOperation):

    def __init__(self):

        self.distribution   = None
        self.targets        = None
        self.positions      = None

    def get_frame_context(self):
        return RandomizePositionOperation.PositionContext(self.targets)

    def get_global_context(self):
        return RandomizePositionOperation.PositionContext(self.targets)

    def compile(self, context, config: dict):
        self.targets = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
        # The distribution will be compiled ( a discrete uniform )
        self.positions = config[wsk.POSITION.value][wsk.POSITION_LIST.value]
        self.distribution = SamplerCompiler.make_distribution(
            Distribution.CATEGORICAL_UNIFORM.name, 1, n=len(self.positions) - 1)

    def execute(self, context):
        # One dimensional result, a discrete uniform variable
        result = min(max(0, self.distribution.sample()[0]), len(self.positions) - 1)

        # Extract a position randomly:
        position = self.positions[result]
        for item in self.targets:
            obj = bpy.data.objects[item]
            obj.location = position


class SimpleMaterialPropertyOperation(PipelineOperation):

    def __init__(self):
        self.distribution = None
        self.node = None
        self.offset_mode = None

    def compile(self, context, config: dict):
        self.distribution = SamplerCompiler.compile(config[wsk.NODE_DISTRIBUTION.value], dim=1)

        node_label = config[wsk.SHADER_NODE.value][wsk.SHADER_LABEL.value]
        material = config[wsk.SHADER_NODE.value][wsk.SHADER_MATERIAL.value]
        # Already extract the target node.
        material = bpy.data.materials.get(material)
        nodes = material.node_tree.nodes
        self.node = next(node for node in nodes if node.label == node_label)

        # This is a boolean value
        self.offset_mode = config[wsk.OFFSET.value][wsk.OFFSET_MODE.value]

    def execute(self, context):
        value = self.distribution.sample()[0]
        self.set_prop(self.node, value, offset=self.offset_mode)

    @abstractmethod
    def set_prop(self, node: Any, value: Any, offset: bool) -> None:
        pass

    @abstractmethod
    def get_prop(self, node: Any) -> Any:
        pass

    class SimplePropertyContext(ContextManager):

        def __init__(self, node, get_prop: Callable, set_prop: Callable):
            self.prop = None
            self.node = node
            self.get = get_prop
            self.set = set_prop

        def __enter__(self):
            self.prop = self.get(self.node)

        def __exit__(self, exc_type, exc_val, exc_tb):
            # No offset, just reset the value to the initial value.
            self.set(self.node, self.prop, offset=False)

    def get_global_context(self):
        return SimpleMaterialPropertyOperation.SimplePropertyContext(self.node, self.get_prop, self.set_prop)

    def get_frame_context(self):
        return SimpleMaterialPropertyOperation.SimplePropertyContext(self.node, self.get_prop, self.set_prop)

@OperationRegistry.register(PipeNames.ROUGHNESS.value)
class RoughnessMaterialPropertyOperation(SimpleMaterialPropertyOperation):

    def set_prop(self, node: Any, value: Any, offset: bool) -> None:
        for inp in node.inputs:
            if inp.name.lower() == 'roughness':
                if offset:
                    inp.default_value += value
                else:
                    inp.default_value = value
                return
        # Do nothing if the property is not found.
        return


    def get_prop(self, node) -> Any:
        for inp in node.inputs:
            if inp.name.lower() == 'roughness':
                return inp.default_value
        return 0

@OperationRegistry.register(PipeNames.METALLIC.value)
class MetallicMaterialPropertyOperation(SimpleMaterialPropertyOperation):

    def set_prop(self, node: Any, value: Any, offset: bool) -> None:
        for inp in node.inputs:
            if inp.name.lower() == 'metallic':
                if offset:
                    inp.default_value += value
                else:
                    inp.default_value = value
                return
        # Do nothing if the property is not found.
        return


    def get_prop(self, node) -> Any:
        for inp in node.inputs:
            if inp.name.lower() == 'metallic':
                return inp.default_value
        return 0


@OperationRegistry.register(PipeNames.SELECT.value)
class SelectOperation(PipelineOperation):

    def get_global_context(self):
        return RandomizeVisibilityOperation.VisibilityContext(self.targets)

    def get_frame_context(self):
        return RandomizeVisibilityOperation.VisibilityContext(self.targets)

    def compile(self, context, config: dict):
        self.targets = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
        # UNIFORM_K_OUT_OF_N
        self.k = config[wsk.SELECT.value][wsk.SELECT_K.value]
        UniqueLogger.quick_log(f"N and K {self.k} {len(self.targets)}")
        self.distribution = SamplerCompiler.make_distribution(
            Distribution.UNIFORM_K_OUT_OF_N.name, 1, k=self.k, n=len(self.targets))

    def __init__(self):

        self.distribution = None
        self.targets = None
        self.k = None

    def execute(self, context):
        # One dimensional result, a bernoulli
        l = len(self.targets)
        if self.k >= l:
            return
        result = self.distribution.sample()[0]
        for res in result:
            if res < 0 or res >= l:
                continue
            obj = bpy.data.objects[self.targets[res]]
            RandomizeVisibilityOperation.hide(obj)




@OperationRegistry.register(PipeNames.MATERIAL.value)
class RandomizeMaterialOperation(PipelineOperation):

    def get_global_context(self):
        return RandomizeMaterialOperation.MaterialContext(self.targets)

    def get_frame_context(self):
        return RandomizeMaterialOperation.MaterialContext(self.targets)

    def compile(self, context, config: dict):
        self.targets = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
        self.material_list = config[wsk.MATERIAL.value][wsk.MATERIAL_LIST.value]
        # Compile distribution for material selection (categorical over material list)
        self.distribution = SamplerCompiler.make_distribution(
            Distribution.CATEGORICAL_UNIFORM.name, 1, n=len(self.material_list) - 1)


    def __init__(self):
        self.distribution = None
        self.targets = None
        self.material_list = None

    def execute(self, context):
        # Sample from distribution to select a material, the distribution is ensured to be
        # a categorical  created internally.
        selected_material_idx = min(max(0, int(self.distribution.sample()[0])), len(self.material_list) - 1)

        selected_material_name = self.material_list[selected_material_idx]
        selected_material = bpy.data.materials.get(selected_material_name)

        if not selected_material:
            return

        # Apply to all target objects
        for obj_name in self.targets:
            obj = bpy.data.objects[obj_name]
            self.apply_material(obj, selected_material)

    @staticmethod
    def apply_material(obj, material) -> None:
        """ Apply material to the object (assumes single material). The reason this
        function is kept separate is to encourage maintainability if in the future
        multi-material objects were to be supported in some way.

        :param obj: The target blender object
        :param material: the material
        """
        if not obj.data.materials:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material

    class MaterialContext(ContextManager):

        def __init__(self, items):
            self.items = items
            self.material_states: List[tuple] = []

        def __enter__(self):
            self.material_states.clear()
            for item in self.items:
                obj = bpy.data.objects[item]
                # Get the first material (or None if no materials), WE IGNORE THE
                # multi-material configuration
                current_material = obj.data.materials[0] if obj.data.materials else None
                self.material_states.append((item, current_material))

        def __exit__(self, exc_type, exc_val, exc_tb):
            for item, material in self.material_states:
                obj = bpy.data.objects[item]
                # The object originally had either one material or zero, so either
                # clear the material list or add the previous one.
                if material is None:
                    obj.data.materials.clear()
                else:
                    if not obj.data.materials:
                        obj.data.materials.append(material)
                    else:
                        obj.data.materials[0] = material

@OperationRegistry.register(PipeNames.ROTATION.value)
class RandomizeRotationOperation(NumericRandomOperation):

    def execute(self, context):
        result = self.distribution.sample()
        for item in self.targets:
            obj = bpy.data.objects[item]
            if self.offset_mode:
                self.axis.increment(obj.rotation_euler, result)
            else:
                self.axis.assign(obj.rotation_euler, result)

    class RotationContext(ContextManager):

        def __init__(self, items):
            self.items = items
            self.rotations = []

        def __enter__(self):
            # Clear to avoid polluting and damaging the values
            self.rotations.clear()
            for item in self.items:
                self.rotations.append(tuple(bpy.data.objects[item].rotation_euler))

        def __exit__(self, exc_type, exc_val, exc_tb):
            for item, rot in zip(self.items, self.rotations):
                bpy.data.objects[item].rotation_euler  = rot

    def get_context(self):
        return RandomizeRotationOperation.RotationContext(self.targets)


@OperationRegistry.register(PipeNames.VISIBILITY.value)
class RandomizeVisibilityOperation(PipelineOperation):

    def get_global_context(self):
        return RandomizeVisibilityOperation.VisibilityContext(self.targets)

    def get_frame_context(self):
        return RandomizeVisibilityOperation.VisibilityContext(self.targets)

    def compile(self, context, config: dict):
        self.targets = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
        # The distribution will be compiled ( a bernoulli )
        self.distribution = SamplerCompiler.compile(config[wsk.NODE_DISTRIBUTION.value], dim=1)

    def __init__(self):

        self.distribution   = None
        self.targets        = None

    def execute(self, context):
        # One dimensional result, a bernoulli

        result = self.distribution.sample()[0]
        for item in self.targets:
            obj = bpy.data.objects[item]
            if result > 0.5:
                self.hide(obj)

    @staticmethod
    def hide(obj) -> None:
        obj.hide_render = True
        obj.visible_camera = False
        obj.visible_diffuse = False
        obj.visible_glossy = False
        obj.visible_shadow = False
        obj.visible_transmission = False
        obj.visible_volume_scatter = False
        obj.hide_set(True)

    class VisibilityContext(ContextManager):

        def __init__(self, items):
            self.items = items
            # We actually need to change multiple attributes per object: not only are we
            # interested in the general render visibility, but also to the transparency to
            # rays and other computations that are required for labeling in general.
            self.visibilities: List[tuple] = []

        def __enter__(self):
            # Clear to avoid polluting and damaging the values
            self.visibilities.clear()
            for item in self.items:
                obj = bpy.data.objects[item]
                self.visibilities.append(self.extract(obj))

        def __exit__(self, exc_type, exc_val, exc_tb):
            for item, state in zip(self.items, self.visibilities):
                obj = bpy.data.objects[item]
                self.restore(obj, state)

        @staticmethod
        def restore(obj, state) -> None:
            obj.hide_render = state[0]
            obj.visible_camera = state[1]
            obj.visible_diffuse = state[2]
            obj.visible_glossy = state[3]
            obj.visible_shadow = state[4]
            obj.visible_transmission = state[5]
            obj.visible_volume_scatter = state[6]
            obj.hide_set( state[7] )

        @staticmethod
        def extract(obj) -> Tuple:
            return (
                obj.hide_render, obj.visible_camera, obj.visible_diffuse, obj.visible_glossy,
                obj.visible_shadow, obj.visible_transmission, obj.visible_volume_scatter, obj.hide_get()
            )


@OperationRegistry.register(PipeNames.FOCAL_LEN.value)
class FocalLengthOperation(PipelineOperation):

    def __init__(self):
        self.distribution = None
        self.camera = None

    def compile(self, context, config: dict):
        scene = context.scene
        # Get the current scene camera
        self.camera = scene.camera
        self.distribution = SamplerCompiler.compile(config[wsk.NODE_DISTRIBUTION.value], dim=1)

    def execute(self, context):
        """ Execute the focal length operation, which rnadomizes the focal length of the scene
        camera. """
        # Sample a scalar value, then assign the camera focal length.
        value = self.distribution.sample()
        self.camera.lens = value

    class CameraFocalLengthContext(ContextManager):

        def __init__(self, camera):
            self.camera = camera
            self.initial_focal = self.camera.lens

        def __enter__(self):
            self.initial_focal = self.camera.lens

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.camera.lens = self.initial_focal

    def get_global_context(self):
        return FocalLengthOperation.CameraFocalLengthContext(self.camera)

    def get_frame_context(self):
        return FocalLengthOperation.CameraFocalLengthContext(self.camera)


@OperationRegistry.register(PipeNames.BEZIER_LOCK.value)
class BezierLockOperation(PipelineOperation):

    def __init__(self):
        self.target_camera = None
        self.bezier_distribution = None

        self.enable_lock = False
        self.lock_target = None

    def compile(self, context, config: dict):
        self.target_camera = context.scene.camera

        self.enable_lock = config[wsk.OBJECT.value][wsk.ENABLED.value]

        curve = config[wsk.TYPED_OBJ.value][wsk.TYPED_OBJ_NAME.value]
        curve_obj = bpy.data.objects[curve]

        if self.enable_lock:
            obj_names = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
            first_obj = obj_names[0]
            self.lock_target = bpy.data.objects[first_obj]

        self.bezier_distribution = BezierDistribution(
            BezierCurve.from_blender_curve(curve_obj),
        )

    def execute(self, context):

        point = self.bezier_distribution.sample()
        self.target_camera.location = point


    def get_global_context(self):
        return BezierLockOperation.BezierLockContext(self.target_camera, self.lock_target, do_lock=self.enable_lock)

    def get_frame_context(self):
        return None

    class BezierLockContext(ContextManager):

        def __init__(self, target, virtual_obj, do_lock: bool):
            self.target = target
            self.constraint = None

            self.do_lock = do_lock
            self.virtual_object = virtual_obj
            self.initial_camera_pos = None
            self.initial_camera_rot = None

        def __enter__(self):
            self.initial_camera_pos = self.target.location
            self.initial_camera_rot = self.target.rotation_euler
            if self.do_lock:
                self.constraint = self.target.constraints.new(type='TRACK_TO')
                self.constraint.target = self.virtual_object

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.do_lock:
                self.target.constraints.remove(self.constraint)
            self.target.location = self.initial_camera_pos
            self.target.rotation_euler = self.initial_camera_rot

@OperationRegistry.register(PipeNames.LINE.value)
class MoveAlongLineOperation(PipelineOperation):

    def __init__(self):
        self.targets = None
        self.bezier_distribution = None

    def compile(self, context, config: dict):
        self.targets = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
        curve = config[wsk.TYPED_OBJ.value][wsk.TYPED_OBJ_NAME.value]
        curve_obj = bpy.data.objects[curve]

        self.bezier_distribution = BezierDistribution(
            BezierCurve.from_blender_curve(curve_obj),
        )

    def execute(self, context):
        point = self.bezier_distribution.sample()
        for item in self.targets:
            obj = bpy.data.objects[item]
            obj.location = point

    def get_global_context(self):
        return RandomizePositionOperation.PositionContext(self.targets)

    def get_frame_context(self):
        return RandomizePositionOperation.PositionContext(self.targets)


class SimpleLightPropertyOperation(PipelineOperation):

    def __init__(self):
        self.distribution = None
        self.target = None
        self.offset_mode = None

    def compile(self, context, config: dict):
        self.distribution = SamplerCompiler.compile(config[wsk.NODE_DISTRIBUTION.value], dim=1)
        target = config[wsk.TYPED_OBJ.value][wsk.TYPED_OBJ_NAME.value]
        # Lights are NOT in data.objects, rather they are inside data.lights
        self.target = bpy.data.lights.get(target)

        # This is a boolean value
        self.offset_mode = config[wsk.OFFSET.value][wsk.OFFSET_MODE.value]

    def execute(self, context):
        value = self.distribution.sample()[0]
        self.set_prop(self.target, value, offset=self.offset_mode)

    @abstractmethod
    def set_prop(self, target: Any, value: Any, offset: bool) -> None:
        pass

    @abstractmethod
    def get_prop(self, target: Any) -> Any:
        pass

    def get_global_context(self):
        return SimpleMaterialPropertyOperation.SimplePropertyContext(self.target, self.get_prop, self.set_prop)

    def get_frame_context(self):
        return SimpleMaterialPropertyOperation.SimplePropertyContext(self.target, self.get_prop, self.set_prop)

@OperationRegistry.register(PipeNames.POWER.value)
class LightPowerPropertyOperation(SimpleLightPropertyOperation):

    def set_prop(self, target: Any, value: Any, offset: bool) -> None:
        if offset:
            self.target.energy += value
        else:
            self.target.energy = value
        return


    def get_prop(self, target) -> Any:
        return self.target.energy

@OperationRegistry.register(PipeNames.TEMPERATURE.value)
class LightTemperaturePropertyOperation(SimpleLightPropertyOperation):

    def set_prop(self, target: Any, value: Any, offset: bool) -> None:
        if offset:
            self.target.temperature += value
        else:
            self.target.temperature = value
        return


    def get_prop(self, target) -> Any:
        return self.target.temperature


@OperationRegistry.register(PipeNames.POV.value)
class ChangePOVOperation(PipelineOperation):

    def __init__(self):
        self.target_camera = None
        self.positions = None
        self.distribution = None

        self.enable_lock = False
        self.lock_target = None

    def compile(self, context, config: dict):
        self.target_camera = context.scene.camera
        self.enable_lock = config[wsk.OBJECT.value][wsk.ENABLED.value]

        if self.enable_lock:
            obj_names = config[wsk.OBJECT.value][wsk.OBJECT_NAMES.value]
            first_obj = obj_names[0]
            self.lock_target = bpy.data.objects[first_obj]

        # The distribution will be compiled ( a discrete uniform )
        self.positions = config[wsk.POSITION.value][wsk.POSITION_LIST.value]
        self.distribution = SamplerCompiler.make_distribution(
            Distribution.CATEGORICAL_UNIFORM.name, 1, n=len(self.positions) - 1)

    def execute(self, context):
        point = self.distribution.sample()
        self.target_camera.location = point


    def get_global_context(self):
        return BezierLockOperation.BezierLockContext(self.target_camera, self.lock_target, do_lock=self.enable_lock)

    def get_frame_context(self):
        return None
