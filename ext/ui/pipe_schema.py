"""Schema definitions and registry for pipeline operation configurations.

Provides a framework to register, extract, and apply configuration schemas
for different pipeline operations, enabling serialization and UI synchronization.
All pipes need to have a serialization and deserialization schema to dump and
load from memory, either through a json file or through a blender property.

Classes:
    PipeSchemaRegistry: Manages registration and retrieval of operation schemas.
    PipeSchema: Abstract base class for defining UI-to-config transformations.
    ScalarPropertyDrawer: Base schema for scalar/vector-based operations.
    ... other schema implementations

Example:
    >>> from ext.ui.pipe_schema import PipeSchemaRegistry
    >>> PipeSchemaRegistry.register("pipe_name")
    >>> class NewPipeSchema(PipeSchemaRegistry):
    >>> pass
"""

from .pipe_edit_widgets import *

from ..constants import PipeNames

from abc import ABC, abstractmethod
from typing import Union, Optional

from ..pipeline import PipelineOperation

wsk = WidgetSerializationKeys

class PipeSchemaRegistry:
    """Registry of all available operations."""

    _pipes_schema = {}

    @classmethod
    def register(cls, op_type: str):
        if op_type in cls._pipes_schema:
            raise RuntimeError(f"Duplicate operation type {op_type}")
        def decorator(drawer_cls):
            cls._pipes_schema[op_type] = drawer_cls
            return drawer_cls
        return decorator

    @classmethod
    def get(cls, operation_type: str) -> Optional['PipeSchema']:
        """Get a schema instance by type."""
        if operation_type not in cls._pipes_schema:
            return None
        return cls._pipes_schema[operation_type]()

    @classmethod
    def get_all_types(cls) -> list:
        """Get all available schemas types."""
        return list(cls._pipes_schema.keys())


class PipeSchema(ABC):
    """

    """

    @staticmethod
    @abstractmethod
    def extract_config_from_ui(context, operation) -> dict:
        """

        :param context:
        :param operation:
        :return:
        """
        pass

    @staticmethod
    @abstractmethod
    def apply_config_to_ui(context, operation, config) -> None:
        """

        :param context:
        :param operation:
        :param config:
        :return:
        """
        pass


@PipeSchemaRegistry.register(PipeNames.VISIBILITY.value)
class VisibilitySchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic =  {
            "dimension": 1,
            "target": ObjectTargeter.extract_data(context),
            "distribution": SimplifiedDistributionSelector.extract_data(context, dim=1)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ObjectTargeter.reset(context)
            SimplifiedDistributionSelector.reset(context, dim=1, name=Distribution.BERNOULLI.name)
            return

        ObjectTargeter.setup_from_config(config["target"], context)
        SimplifiedDistributionSelector.setup_from_config(config["distribution"], context, dim=1)

class ScalarPropertyDrawer(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dim = AxisTarget.get_selected_axis_dimension(context.scene)
        dic = {
            "dimension": dim,
            "axis": AxisTarget.extract_data(context),
            wsk.OFFSET.value: OffsetMode.extract_data(context),
            "target": ObjectTargeter.extract_data(context),
            "distribution": NodeDistributionSelector.extract_data(context, dim=dim)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ObjectTargeter.reset(context)
            NodeDistributionSelector.reset(context)
            OffsetMode.reset(context)
            AxisTarget.reset(context)
        else:
            dimension = config["dimension"]
            AxisTarget.setup_from_config(config["axis"], context)
            ObjectTargeter.setup_from_config(config["target"], context)
            OffsetMode.setup_from_config(config[wsk.OFFSET.value], context)
            NodeDistributionSelector.setup_from_config(config["distribution"], context, dim=dimension)


@PipeSchemaRegistry.register(PipeNames.SCALE.value)
class ScaleSchema(ScalarPropertyDrawer):
    pass


@PipeSchemaRegistry.register(PipeNames.ROTATION.value)
class RotationSchema(ScalarPropertyDrawer):
    pass


@PipeSchemaRegistry.register(PipeNames.POSITION.value)
class PositionSchema(ScalarPropertyDrawer):
    pass

@PipeSchemaRegistry.register(PipeNames.MOVE.value)
class MoveSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.OBJECT.value: ObjectTargeter.extract_data(context),
            wsk.POSITION.value: PositionListSelector.extract_data(context)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ObjectTargeter.reset(context)
            PositionListSelector.reset(context)
        else:
            ObjectTargeter.setup_from_config(config["target"], context)
            PositionListSelector.setup_from_config(config["positions"], context)

@PipeSchemaRegistry.register(PipeNames.TEXTURE.value)
class TextureSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.TEXTURE.value: ImageTextureTargeter.extract_data(context),
            wsk.PATH.value: PathListSelector.extract_data(context)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ImageTextureTargeter.reset(context)
            PathListSelector.reset(context)
        else:
            ImageTextureTargeter.setup_from_config(config["node"], context)
            PathListSelector.setup_from_config(config["textures"], context)

@PipeSchemaRegistry.register(PipeNames.SELECT.value)
class SelectSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        scene = context.scene
        dic = {
            wsk.SELECT.value: { wsk.SELECT_K.value : scene.k_out_of_n },
            wsk.OBJECT.value: ObjectTargeter.extract_data(context),
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ObjectTargeter.reset(context)
        else:
            ObjectTargeter.setup_from_config(config["target"], context)


@PipeSchemaRegistry.register(PipeNames.MATERIAL.value)
class MaterialSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            "target": ObjectTargeter.extract_data(context),
            wsk.MATERIAL.value: MaterialSelector.extract_data(context)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ObjectTargeter.reset(context)
            MaterialSelector.reset(context)
        else:
            ObjectTargeter.setup_from_config(config["target"], context)
            MaterialSelector.setup_from_config(config["materials"], context)

class MaterialSimplePropertySchema(PipeSchema):

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            MaterialSelector.reset(context)
            OffsetMode.reset(context)
            NodeDistributionSelector.reset(context)
        else:
            NodeDistributionSelector.setup_from_config(config["distribution"], context, dim=1)
            MaterialSelector.setup_from_config(config["materials"], context)
            OffsetMode.setup_from_config(config[wsk.OFFSET.value], context)

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            "distribution": NodeDistributionSelector.extract_data(context, dim=1),
            "materials": MaterialSelector.extract_data(context),
            wsk.OFFSET.value: OffsetMode.extract_data(context)
        }
        return dic


class SimpleMaterialPropertySchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.OFFSET.value: OffsetMode.extract_data(context),
            wsk.SHADER_NODE.value: TypedNodeTargeter.extract_data(context),
            wsk.NODE.value: NodeDistributionSelector.extract_data(context, dim=1),
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            NodeDistributionSelector.reset(context)
            OffsetMode.reset(context)
            TypedNodeTargeter.reset(context)
        else:
            OffsetMode.setup_from_config(config[wsk.OFFSET.value], context)
            TypedNodeTargeter.setup_from_config(config[wsk.SHADER_NODE.value], context)
            NodeDistributionSelector.setup_from_config(config["distribution"], context, dim=1)


@PipeSchemaRegistry.register(PipeNames.ROUGHNESS.value)
class RoughnessEditor(SimpleMaterialPropertySchema):
    pass

@PipeSchemaRegistry.register(PipeNames.METALLIC.value)
class MetallicEditor(SimpleMaterialPropertySchema):
    pass


@PipeSchemaRegistry.register(PipeNames.INTENSITY.value)
class RandomizeNodeIntensitySchema(PipeSchema):

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ValueTargeter.reset(context)
            NodeDistributionSelector.reset(context)
            OffsetMode.reset(context)
        else:
            OffsetMode.setup_from_config(config[wsk.OFFSET.value], context)
            ValueTargeter.setup_from_config(config["value"], context)
            NodeDistributionSelector.setup_from_config(config["distribution"], context, dim=1)

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.VALUE.value: ValueTargeter.extract_data(context),
            "distribution": NodeDistributionSelector.extract_data(context, dim=1),
            wsk.OFFSET.value: OffsetMode.extract_data(context)
        }
        return dic

@PipeSchemaRegistry.register(PipeNames.BEZIER_LOCK.value)
class BezierLockCameraSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        """ """
        conditional = ConditionalWidget(ObjectTargeter)
        dic = {
            wsk.TYPED_OBJ.value: TypedObjectTargeter.extract_data(context),
            wsk.OBJECT.value: conditional.extract_data(context),
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        """ """
        conditional = ConditionalWidget(ObjectTargeter)
        if not config:
            conditional.reset(context)
            TypedObjectTargeter.reset(context)
        else:
            conditional.setup_from_config(config[wsk.OBJECT.value], context)
            TypedObjectTargeter.setup_from_config(config[wsk.TYPED_OBJ.value], context )

@PipeSchemaRegistry.register(PipeNames.FOCAL_LEN.value)
class FocalLengthSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.NODE_DISTRIBUTION.value: NodeDistributionSelector.extract_data(context, dim=1)
        }
        return dic


    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            NodeDistributionSelector.reset(context)
        else:
            NodeDistributionSelector.setup_from_config(config["distribution"], context, dim=1)


@PipeSchemaRegistry.register(PipeNames.LINE.value)
class MoveAlongLineSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.TYPED_OBJ.value: TypedObjectTargeter.extract_data(context),
            wsk.OBJECT.value: ObjectTargeter.extract_data(context),
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            ObjectTargeter.reset(context)
            TypedObjectTargeter.reset(context)
        else:
            ObjectTargeter.setup_from_config(config[wsk.OBJECT.value], context)
            TypedObjectTargeter.setup_from_config(config[wsk.TYPED_OBJ.value], context)


class SimpleLightAttributeSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.TYPED_OBJ.value: TypedObjectTargeter.extract_data(context),
            wsk.NODE.value: NodeDistributionSelector.extract_data(context, dim=1),
            wsk.OFFSET.value: OffsetMode.extract_data(context)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        if not config:
            NodeDistributionSelector.reset(context)
            TypedObjectTargeter.reset(context)
            OffsetMode.reset(context)
        else:
            OffsetMode.setup_from_config(config[wsk.OFFSET.value], context)
            NodeDistributionSelector.setup_from_config(config[wsk.NODE.value], context, dim=1)
            TypedObjectTargeter.setup_from_config(config[wsk.TYPED_OBJ.value], context)


@PipeSchemaRegistry.register(PipeNames.TEMPERATURE.value)
class LightTemperatureSchema(SimpleLightAttributeSchema):
    pass

@PipeSchemaRegistry.register(PipeNames.POWER.value)
class LightPowerSchema(SimpleLightAttributeSchema):
    pass

@PipeSchemaRegistry.register(PipeNames.COLOR.value)
class LightColorSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        dic = {
            wsk.TYPED_OBJ.value: TypedObjectTargeter.extract_data(context),
        }
        return dic


    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:

        if not config:
            TypedObjectTargeter.reset(context)
            ColorDistributionSelector.reset(context)
        else:
            TypedObjectTargeter.setup_from_config(config[wsk.TYPED_OBJ.value], context)

@PipeSchemaRegistry.register(PipeNames.POV.value)
class ChangePovSchema(PipeSchema):

    @staticmethod
    def extract_config_from_ui(context, operation) -> dict:
        """ """
        conditional = ConditionalWidget(ObjectTargeter)
        dic = {
            wsk.OBJECT.value: conditional.extract_data(context),
            wsk.POSITION.value:  PositionListSelector.extract_data(context)
        }
        return dic

    @staticmethod
    def apply_config_to_ui(context, operation, config) -> None:
        """ """
        conditional = ConditionalWidget(ObjectTargeter)
        if not config:
            conditional.reset(context)
            PositionListSelector.reset(context)
        else:
            conditional.setup_from_config(config[wsk.OBJECT.value], context)
            PositionListSelector.setup_from_config(config[wsk.POSITION.value], context )
