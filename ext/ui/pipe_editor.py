"""Registry and UI drawer implementations for pipeline operation editors.

Provides a system to register and retrieve UI drawer classes associated with
specific pipeline operation types, enabling modular and extensible editor UIs.
When a new pipe is to be created, its editor must be added to the registry. The
actual editors can use a series of widgets which enhance reusability and modularity.
This enables reutilization of properties for multiple editors.

Classes:
    OperationDrawerRegistry: Manages registration and lookup of operation drawers.
    PipeDrawer: Abstract base class for all operation UI drawers.
    ScalarPropertyDrawer: Shared drawer for scalar/vector-based operations.
    ... Implementations of pipe editors UI

Example:
    >>> # Adding a new drawer to the editor drawer registry
    >>> from ext.ui.pipe_editor import OperationDrawerRegistry
    >>> @OperationDrawerRegistry.register("pipe_ex_name")
    >>> class NewPipe(PipeDrawer):
    >>>    pass
"""

# Import all the widgets that are used multiple times to facilitate the
# drawing of individual pipe component editors.
from .pipe_edit_widgets import *
from .description import DescriptionWidget

from ..constants import PipeNames, StageDescriptions
from ..distribution.computation import Distribution

from abc import ABC

class OperationDrawerRegistry:

    _drawers = {}

    @classmethod
    def register(cls, op_type: str):
        def decorator(drawer_cls):
            cls._drawers[op_type] = drawer_cls
            return drawer_cls
        return decorator

    @classmethod
    def get(cls, op_type: str):
        return cls._drawers.get(op_type)

    @classmethod
    def get_all_types(cls) -> list:
        """Get all available operation types."""
        return list(cls._drawers.keys())

class PipeDrawer(ABC):
    """Base class for all pipeline operations."""

    operation_type: str  # "Scale", "Rotation", etc

    @staticmethod
    def draw_editor(layout, context) -> None:
        """Draw this operation's editor UI."""
        pass


class ScalarPropertyDrawer(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :return:
        """
        ObjectTargeter.draw(layout, context)
        layout.separator()
        AxisTarget.draw(layout, context)
        layout.separator()
        #
        OffsetMode.draw(layout, context)
        NodeDistributionSelector.draw(layout, context,
                                      dim=AxisTarget.get_selected_axis_dimension(context.scene))


# The following operations all use the same format defined just above as they
# all are vector properties (notice that these classes are just a matter of UI,
# the distinction between the operation is given by the pipe op_name

@OperationDrawerRegistry.register(PipeNames.SCALE.value)
class RandomizeScaleOperation(ScalarPropertyDrawer):
    """

    """
    pass

@OperationDrawerRegistry.register(PipeNames.ROTATION.value)
class RandomizeRotationOperation(ScalarPropertyDrawer):
    """

    """

    @staticmethod
    def draw_editor(layout, context) -> None:
        DescriptionWidget.draw(
            layout, context, message=StageDescriptions.ROTATION.value)
        ScalarPropertyDrawer.draw_editor(layout, context)

@OperationDrawerRegistry.register(PipeNames.POSITION.value)
class RandomizePositionOperation(ScalarPropertyDrawer):
    """

    """
    pass

@OperationDrawerRegistry.register(PipeNames.TEXTURE.value)
class RandomizeTextureOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :return:
        """
        ImageTextureTargeter.draw(layout, context)
        layout.separator()
        PathListSelector.draw(layout, context)


@OperationDrawerRegistry.register(PipeNames.VISIBILITY.value)
class RandomizeVisibilityOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        # Allow the user to select the object for which visibility is to change
        ObjectTargeter.draw(layout, context)
        layout.separator()
        SimplifiedDistributionSelector.draw_for(
            layout, context, Distribution.BERNOULLI.name, label="Probability")

@OperationDrawerRegistry.register(PipeNames.MOVE.value)
class RandomizeMoveOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        ObjectTargeter.draw(layout, context)
        layout.separator()
        PositionListSelector.draw(layout, context)

@OperationDrawerRegistry.register(PipeNames.MATERIAL.value)
class RandomizeMaterialOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        ObjectTargeter.draw(layout, context)
        layout.separator()
        MaterialSelector.draw(layout, context)

@OperationDrawerRegistry.register(PipeNames.SELECT.value)
class RandomizeSelectOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        scene = context.scene
        layout.prop(scene, 'k_out_of_n', text="Number of items (K)")
        ObjectTargeter.draw(layout, context)


@OperationDrawerRegistry.register(PipeNames.METALLIC.value)
class RandomizeMetallicOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        MaterialSelector.draw(layout, context)
        OffsetMode.draw(layout, context)
        NodeDistributionSelector.draw(layout, context, dim=1)

@OperationDrawerRegistry.register(PipeNames.ROUGHNESS.value)
class RandomizeRoughnessOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        MaterialSelector.draw(layout, context)
        OffsetMode.draw(layout, context)
        NodeDistributionSelector.draw(layout, context, dim=1)

@OperationDrawerRegistry.register(PipeNames.INTENSITY.value)
class RandomizeNodeIntensityOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        ValueTargeter.draw(layout, context)
        OffsetMode.draw(layout, context)
        NodeDistributionSelector.draw(layout, context, dim=1)

@OperationDrawerRegistry.register(PipeNames.FOCAL_LEN.value)
class FocalLengthOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        NodeDistributionSelector.draw(layout, context)

@OperationDrawerRegistry.register(PipeNames.NODE_PROP.value)
class RandomizeNodePropOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        """

        :param layout:
        :param context:
        :return:
        """
        PropertyTargeter.draw(layout, context)
        OffsetMode.draw(layout, context)
        NodeDistributionSelector.draw(layout, context, dim = 1)


@OperationDrawerRegistry.register(PipeNames.BEZIER_LOCK.value)
class BezierLockCameraOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        typed = TypedObjectTargeter(obj_type="CURVE")
        typed.draw(layout, context)
        # If the user wants to lock the camera to a point, he must specify said point
        conditional = ConditionalWidget(ObjectTargeter, ask_text="Lock camera to object")
        conditional.draw(layout, context)

@OperationDrawerRegistry.register(PipeNames.POV.value)
class ChangePOVOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        # If the user wants to lock the camera to a point, he must specify said point
        conditional = ConditionalWidget(ObjectTargeter, ask_text="Lock camera to object")
        conditional.draw(layout, context)
        layout.separator()
        PositionListSelector.draw(layout, context)

@OperationDrawerRegistry.register(PipeNames.LINE.value)
class MoveAlongLineOperation(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        # The user selects a target object, then a line.
        ObjectTargeter.draw(layout, context)
        typed = TypedObjectTargeter(obj_type="CURVE")
        typed.draw(layout, context)

class SimpleMaterialPropertyEditor(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        # Simple properties only have the distribution to edit.
        typed_selector = TypedNodeTargeter(text="Shader Node:", node_type='bsdf')
        typed_selector.draw(layout, context)
        NodeDistributionSelector.draw(layout, context, dim=1)

@OperationDrawerRegistry.register(PipeNames.ROUGHNESS.value)
class RoughnessEditor(SimpleMaterialPropertyEditor):
    pass

@OperationDrawerRegistry.register(PipeNames.METALLIC.value)
class MetallicEditor(SimpleMaterialPropertyEditor):
    pass

@OperationDrawerRegistry.register(PipeNames.BASE_COLOR.value)
class ColorEditor(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        pass

class SimpleLightAttributeEditor(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        typed_selector = TypedObjectTargeter(obj_type="LIGHT")
        typed_selector.draw(layout, context)
        layout.separator()
        OffsetMode.draw(layout, context)
        layout.separator()
        NodeDistributionSelector.draw(layout, context, dim=1)


@OperationDrawerRegistry.register(PipeNames.TEMPERATURE.value)
class LightTemperatureEditor(SimpleLightAttributeEditor):
    pass

@OperationDrawerRegistry.register(PipeNames.POWER.value)
class LightPowerEditor(SimpleLightAttributeEditor):
    pass

@OperationDrawerRegistry.register(PipeNames.COLOR.value)
class LightColorEditor(PipeDrawer):

    @staticmethod
    def draw_editor(layout, context) -> None:
        typed_selector = TypedObjectTargeter(obj_type="LIGHT")
        typed_selector.draw(layout, context)
        ColorDistributionSelector.draw(layout, context)
