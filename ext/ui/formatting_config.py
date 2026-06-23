"""
Registry-based labeling configuration handlers and Blender property definitions.

This module provides a plugin-style registry for label configuration handlers,
allowing label format specific UI drawing and configuration extraction logic
to be registered and retrieved dynamically. It also defines abstract handler
interfaces and Blender property groups used for label export configuration.
"""

from abc import ABCMeta, abstractmethod
from typing import Optional

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, FloatProperty
from ..core.io import SupportedFormats


class LabelingConfigRegistry:
    """
    Registry for storing and retrieving label configuration handler classes.

    This registry enables dynamic registration and lookup of
    :class:`LabelConfigHandler` implementations based on a unique
    label format identifier.
    """

    _registry: dict[str, type['LabelConfigHandler']] = {}

    @classmethod
    def register(cls, name: str):
        """ Register a label configuration handler class.

        This method is intended to be used as a decorator for LabelConfigHandle subclasses.

        :param name: Unique identifier associated with the handler.
        :type name: str
        :return: Decorator that registers the handler class.
        :rtype: Callable[[type[LabelConfigHandler]], type[LabelConfigHandler]]
        """
        def decorator(handler_class: type['LabelConfigHandler']) -> type['LabelConfigHandler']:
            if name in cls._registry:
                raise ValueError(f"Handler with name '{name}' is already registered")
            cls._registry[name] = handler_class
            return handler_class

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[type['LabelConfigHandler']]:
        return cls._registry.get(name)

    @classmethod
    def get_or_raise(cls, name: str) -> type['LabelConfigHandler']:
        """ Retrieve a registered handler by name.

        :param name: Name of the registered handler.
        :type name: str
        """
        if name not in cls._registry:
            raise KeyError(f"No handler registered with name '{name}'. Available: {list(cls._registry.keys())}")
        return cls._registry[name]

    @classmethod
    def list_registered(cls) -> list[str]:
        """Return list of all registered handler names."""
        return list(cls._registry.keys())

    @classmethod
    def unregister(cls, name: str) -> bool:
        if name in cls._registry:
            del cls._registry[name]
            return True
        return False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered handlers (useful for testing)."""
        cls._registry.clear()


class LabelConfigHandler(metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def draw(context, layout) -> None:
        """

        :param context:
        :param layout:
        :return:
        """
        pass

    @staticmethod
    @abstractmethod
    def extract(context) -> dict:
        """

        :param context:
        :return:
        """
        pass

    @staticmethod
    def _draw_props(layout, source, props) -> None:
        """

        :param layout:
        :param source:
        :param props:
        :return:
        """
        for prop in props:
            layout.prop(source, prop)

class LabelConfigDrawer:

    @staticmethod
    def draw(context, layout, label_type: str) -> None:
        drawer = LabelingConfigRegistry.get(label_type)
        if drawer is not None:
            # Wrap the drawing into a box:
            box = layout.box()
            box.label(text="Labeling Settings", icon='SETTINGS')
            drawer.draw(context, box)

    @staticmethod
    def extract(context, label_type: str) -> dict:
        serializing_subclass = LabelingConfigRegistry.get(label_type)
        if serializing_subclass is None:
            return {}
        return serializing_subclass.extract(context)


@LabelingConfigRegistry.register(SupportedFormats.ULTRALYTICS_YOLO.value)
class UltralyticsYoloConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        source = context.scene.labeling_config
        LabelConfigHandler._draw_props(layout, source,
            ('zero_padding', 'split', 'ray_casting_precision', 'precision')
       )

    @staticmethod
    def extract(context) -> dict:
        properties = context.scene.labeling_config
        return {

        }


@LabelingConfigRegistry.register(SupportedFormats.PCD_CLASS_COLOR.value)
class PCDClassColorConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}


@LabelingConfigRegistry.register(SupportedFormats.CVAT_XML_IMAGES.value)
class CVATXMLConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}



@LabelingConfigRegistry.register(SupportedFormats.PASCAL_VOC.value)
class PascalVOCConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}



@LabelingConfigRegistry.register(SupportedFormats.COCO.value)
class COCOConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}

@LabelingConfigRegistry.register(SupportedFormats.COCO_SEGMENTATION.value)
class COCOSegmentationConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}


@LabelingConfigRegistry.register(SupportedFormats.COCO_KEYPOINTS.value)
class COCOKeypointsConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}


@LabelingConfigRegistry.register(SupportedFormats.PCD_CLASS.value)
class PCDClassConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}


@LabelingConfigRegistry.register(SupportedFormats.PCD.value)
class PCDConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}

class LabelConfigDataProperty(PropertyGroup):
    """


    """

    # used in []
    zero_padding: BoolProperty(default=True, name="Zero-pad result names")          # type: ignore
    # used in []
    split: StringProperty(default="train", name="Folder split")                     # type: ignore

    # used in: [YOLO]
    precision: IntProperty(name="BBox float precision", default=3,                  # type: ignore
        min=1
    )
    # used in [YOLO, COCO*, CVAT]
    ray_casting_precision: FloatProperty(name="Ray-casting precision", default=0.1,  # type: ignore
        min = 0.0,
        max = 1.0
    )

    # used in [PCD*]
    sampling_type: EnumProperty(                                                    # type: ignore
        items=[("Uniform", "Uniform", "Uniform"),],
        name="Sampling Type"
    )

    # used in [PCD*]
    generate_info: BoolProperty(default=False, name="Generate metadata")            # type: ignore
