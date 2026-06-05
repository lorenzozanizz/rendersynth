from abc import ABCMeta, abstractmethod
from typing import Optional

from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, IntProperty, CollectionProperty
from ..core.io import SupportedFormats


class LabelingConfigRegistry:
    """Registry for storing and retrieving label configuration handler classes."""

    _registry: dict[str, type['LabelConfigHandler']] = {}

    @classmethod
    def register(cls, name: str):
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
        pass

    @staticmethod
    @abstractmethod
    def extract(context) -> dict:
        pass


class LabelConfigDrawer:


    @staticmethod
    def draw(context, layout, label_type: str) -> None:
        serializing_subclass = LabelingConfigRegistry.get(label_type)
        return serializing_subclass.draw(context, layout)

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
        pass

    @staticmethod
    def extract(context) -> dict:
        pass


@LabelingConfigRegistry.register(SupportedFormats.PCD_CLASS_COLOR.value)
class PCDClassColorConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}


@LabelingConfigRegistry.register(SupportedFormats.CVAT_XML_IMAGES.value)
class PCDClassColorConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}



@LabelingConfigRegistry.register(SupportedFormats.PASCAL_VOC.value)
class PCDClassColorConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}



@LabelingConfigRegistry.register(SupportedFormats.COCO.value)
class PCDClassColorConfigHandler(LabelConfigHandler):

    @staticmethod
    def draw(context, layout) -> None:
        pass

    @staticmethod
    def extract(context) -> dict:
        return {}


class LabelConfigDataProperty(PropertyGroup):
    """


    """

    zero_padding: BoolProperty(default=True)    # type: ignore
    split: StringProperty(default="train")      # type: ignore



