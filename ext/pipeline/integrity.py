from .operations import PipelineOperation
from ..constants import PipeNames, WidgetSerializationKeys, DISTRO_EDITOR_NAME

from abc import ABCMeta, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Union, Optional
from json import loads

import bpy

from ..utils.logger import UniqueLogger

wsk = WidgetSerializationKeys

class PipeValidator(metaclass=ABCMeta):
    """

    """
    @staticmethod
    @abstractmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        pass


class ValidationResult:
    """

    """

    def __init__(self):
        self.is_valid: bool = True
        self.messages: list[ValidationMessage] = []

    def add_error(self, message: str) -> None:
        self.messages.append(ValidationMessage('ERROR', message))

    def add_warning(self, message: str) -> None:
        self.messages.append(ValidationMessage('WARNING', message))

    def has_errors(self) -> bool:
        return next((msg for msg in self.messages if 'ERROR' in msg.message), None) is None

    def make_summary(self) -> str:
        return ""


@dataclass
class ValidationMessage:
    """

    """
    type: str
    message: str
    context: Optional[str] = None


class ValidatorRegistry:
    """Registry of all available operations."""

    _operations = {}

    @classmethod
    def register(cls, op_type: str):
        def decorator(drawer_cls):
            cls._operations[op_type] = drawer_cls
            return drawer_cls
        return decorator

    @classmethod
    def get(cls, operation_type: str) -> Optional[PipeValidator]:
        """Get an operation instance by type."""
        if operation_type not in cls._operations:
            return None
        return cls._operations[operation_type]()

    @classmethod
    def get_all_types(cls) -> list:
        """Get all available operation types."""
        return list(cls._operations.keys())

class NumericPropertyValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        axi_ok = AxisTargetValidator.validate(config[wsk.AXIS.value])
        obj_ok = ObjectTargeterValidator.validate(config[wsk.OBJECT.value])
        dis_ok = NodeDistributionSelectorValidator.validate(config[wsk.NODE.value])
        return axi_ok and obj_ok and dis_ok

@ValidatorRegistry.register(PipeNames.SCALE.value)
class ScaleValidator(NumericPropertyValidator):
    pass

@ValidatorRegistry.register(PipeNames.POSITION.value)
class PositionValidator(NumericPropertyValidator):
    pass

@ValidatorRegistry.register(PipeNames.ROTATION.value)
class RotationValidator(NumericPropertyValidator):
    pass

@ValidatorRegistry.register(PipeNames.MOVE.value)
class MoveValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation,  config: dict) -> bool:
        obj_ok = ObjectTargeterValidator.validate(config[wsk.OBJECT.value])
        pos_ok = PositionListSelectorValidator.validate(config[wsk.POSITION.value])
        return obj_ok and pos_ok


@ValidatorRegistry.register(PipeNames.POV.value)
class MoveValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation,  config: dict) -> bool:
        conditional = ConditionalValidator(ObjectTargeterValidator)
        obj_ok = conditional.validate(partial_config=config[wsk.OBJECT.value])
        pos_ok = PositionListSelectorValidator.validate(config[wsk.POSITION.value])
        return obj_ok and pos_ok


@ValidatorRegistry.register(PipeNames.VISIBILITY.value)
class VisibilityValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation,  config: dict) -> bool:
        obj_ok = ObjectTargeterValidator.validate(config[wsk.OBJECT.value])
        dis_ok = SimplifiedDistributionSelectorValidator.validate(config[wsk.SIMPLE.value])
        return obj_ok and dis_ok


@ValidatorRegistry.register(PipeNames.MATERIAL.value)
class MaterialValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        obj_ok = ObjectTargeterValidator.validate(config[wsk.OBJECT.value])
        mat_ok = MaterialSelectorValidator.validate(config[wsk.MATERIAL.value])
        return mat_ok and obj_ok

@ValidatorRegistry.register(PipeNames.TEXTURE.value)
class TextureValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        return False

@ValidatorRegistry.register(PipeNames.INTENSITY.value)
class IntensityValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        # Just ensure that the node does exist and ensure the distribution is OK.
        val_ok = LabeledNodeValidator.validate(partial_config=config[wsk.VALUE.value])
        dis_ok = NodeDistributionSelectorValidator.validate(partial_config=config[wsk.NODE.value])
        return val_ok and dis_ok

@ValidatorRegistry.register(PipeNames.SELECT.value)
class SelectValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        obj_ok = ObjectTargeterValidator.validate(config[wsk.OBJECT.value])
        return obj_ok

class SimpleMaterialPropertyValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        sha_ok = TypedNodeValidator.validate(config[wsk.SHADER_NODE.value])
        dis_ok = NodeDistributionSelectorValidator.validate(config[wsk.SIMPLE.value])
        return dis_ok and sha_ok

@ValidatorRegistry.register(PipeNames.ROUGHNESS.value)
class RoughnessEditor(SimpleMaterialPropertyValidator):
    pass

@ValidatorRegistry.register(PipeNames.METALLIC.value)
class MetallicEditor(SimpleMaterialPropertyValidator):
    pass

@ValidatorRegistry.register(PipeNames.BASE_COLOR.value)
class ColorEditor:

    @staticmethod
    def draw_editor(layout, context) -> None:
        pass

@ValidatorRegistry.register(PipeNames.BEZIER_LOCK.value)
class CameraBezierLockValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:

        obj_ok = TypedObjectValidator.validate(partial_config=config[wsk.TYPED_OBJ.value])
        conditional = ConditionalValidator(ObjectTargeterValidator)
        pos_ok = conditional.validate(partial_config=config[wsk.OBJECT.value])

        return obj_ok and pos_ok

@ValidatorRegistry.register(PipeNames.LINE.value)
class MoveAlongLineValidator(PipeValidator):


    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:

        obj_ok = TypedObjectValidator.validate(partial_config=config[wsk.TYPED_OBJ.value])
        tar_ok = ObjectTargeterValidator.validate(partial_config=config[wsk.OBJECT.value])

        return obj_ok and tar_ok

@ValidatorRegistry.register(PipeNames.FOCAL_LEN.value)
class FocalLengthValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        # Just check that the distribution is fine
        dis_ok = NodeDistributionSelectorValidator.validate(partial_config=config[wsk.SIMPLE.value])
        return dis_ok


@ValidatorRegistry.register(PipeNames.TEXTURE.value)
class TextureValidator(PipeValidator):
    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        nod_ok = LabeledNodeValidator.validate(partial_config=config[wsk.TEXTURE.value])
        img_ok = PathListSelectorValidator.validate(partial_config=config[wsk.PATH.value])
        return nod_ok and img_ok

class SimpleLightAttributeValidator(PipeValidator):

    @staticmethod
    def validate(pipe: PipelineOperation, config: dict) -> bool:
        dis_ok = NodeDistributionSelectorValidator.validate(partial_config=config[wsk.NODE.value])
        light_ok = TypedObjectValidator.validate(partial_config=config[wsk.TYPED_OBJ.value])
        return dis_ok and light_ok

@ValidatorRegistry.register(PipeNames.TEMPERATURE.value)
class LightTemperatureEditor(SimpleLightAttributeValidator):
    pass

@ValidatorRegistry.register(PipeNames.POWER.value)
class LightPowerEditor(SimpleLightAttributeValidator):
    pass


class WidgetValidator(metaclass=ABCMeta):
    """

    """
    @staticmethod
    @abstractmethod
    def validate(partial_config: dict) -> bool:
        pass


class ConditionalValidator(WidgetValidator):

    def __init__(self, target_cls):
        self.target = target_cls

    def validate(self, partial_config: dict) -> bool:
        UniqueLogger.quick_log("Validate conditional" + partial_config.__str__())
        is_enabled = partial_config[wsk.ENABLED.value]
        if is_enabled:
            return self.target.validate(partial_config)
        else:
            return True

class TypedObjectValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        obj = partial_config[wsk.TYPED_OBJ_NAME.value]
        # The pipe is not OK if it has no target. "OK" means useful and working.
        if not obj:
            return False
        try:
            obj = bpy.data.objects[obj]
        except KeyError:
            return False
        if not obj:
            return False
        return True


class AxisTargetValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        """

        :param partial_config:
        :return:
        """
        do_x = partial_config[wsk.AXIS_RANDOMIZE_PREFIX_X.value]
        do_y = partial_config[wsk.AXIS_RANDOMIZE_PREFIX_Y.value]
        do_z = partial_config[wsk.AXIS_RANDOMIZE_PREFIX_Z.value]
        return do_x or do_y or do_z


#
class ObjectTargeterValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        # We simply ensure that all the objects do exist in the bpy data.
        objects = partial_config[wsk.OBJECT_NAMES.value]
        # The pipe is noto OK if it has no target. "OK" means useful and working.
        if not objects:
            return False
        for name in objects:
            name: str
            # Note that this searches for objects in all the different scenes of the active
            # file, not just the current context.
            try:
                obj = bpy.data.objects[name]
            except KeyError:
                return False
            if not obj:
                return False
        return True

#
class PathListSelectorValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        is_folder = partial_config[wsk.PATH_USE_FOLDER.value]
        # Only ensure that the list is non-empty, do not perform the directory check here
        # instead the existence of the folder is checked at runtime when loading textures.
        if not is_folder:
            file_list = partial_config[wsk.PATH_FILES.value]
            if not file_list:
                return False
        else:
            directory = partial_config[wsk.PATH_FOLDER.value]
            if not directory:
                return False
        return True


#
class NodeDistributionSelectorValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:

        use_tree = partial_config['use_tree']
        if use_tree:
            name = partial_config['distribution']
            tree = next(
                (ng for ng in bpy.data.node_groups
                 if ng.bl_idname == DISTRO_EDITOR_NAME and ng.name == name),
                None
            )
            if tree is None:
                return False
        else:
            preset = partial_config['preset']
            if preset.lower() == "None":
                return False
        return True

#
class SimplifiedDistributionSelectorValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        """ Pretty much any distribution is correct by design, as the numeric attributes
        have boundaries which prevent mathematically illegal values. """
        dis_name = partial_config[wsk.SIMPLE_PRESET_NAME.value]
        if not dis_name or dis_name.lower() == "none":
            return False
        else:
            return True

#
class PositionListSelectorValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        positions = partial_config[wsk.POSITION_LIST.value]
        return len(positions) != 0

#
class MaterialSelectorValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        """

        :param partial_config:
        :return:
        """

        # We simply ensure that all the materials listed do exist in the bpy data.
        materials = partial_config[wsk.MATERIAL_LIST.value]
        if not materials:
            return False
        for mat in materials:
            mat: str
            try:
                tree = bpy.data.materials.get(mat)
            except KeyError:
                return False
            if not tree:
                return False
        return True


#
class PropertyTargeterValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:
        pass


class TypedNodeValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:

        material = partial_config[wsk.SHADER_MATERIAL.value]
        if not material:
            return False
        try:
            tree = bpy.data.materials.get(material)
            label = partial_config[wsk.SHADER_LABEL.value]
        except KeyError:
            return False
        if not tree or not tree.use_nodes:
            return False
        node_tree = tree.node_tree
        found_node = None

        for node in node_tree.nodes:
            if node.label == label:
                found_node = node
                break

        if not found_node:
            return False
        return True



class LabeledNodeValidator(WidgetValidator):

    @staticmethod
    def validate(partial_config: dict) -> bool:

        material = partial_config[wsk.VALUE_MATERIAL.value]
        if not material:
            return False
        try:
            tree = bpy.data.materials.get(material)
            label = partial_config[wsk.VALUE_LABEL.value]
        except KeyError:
            return False
        if not tree or not tree.use_nodes:
            return False
        node_tree = tree.node_tree
        found_node = None

        for node in node_tree.nodes:
            if node.label == label:
                found_node = node
                break

        if not found_node:
            return False
        return True


class PipelineScanner:
    """

    """

    @staticmethod
    def scan(pipeline_data) -> int:
        """

        :param pipeline_data:
        :return:
        """

        found_not_valid = 0
        for pipe in pipeline_data.operations:
            op_type = pipe.operation_type
            validator = ValidatorRegistry.get(op_type)
            if not validator:
                continue
            config = loads(pipe.config)
            validate_result = validator.validate(pipe, config)
            pipe.valid = validate_result
            if not validate_result:
                found_not_valid += 1
        return found_not_valid