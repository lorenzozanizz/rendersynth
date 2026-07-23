""" Registry mapping Label.annotation_type values to their PreviewRenderer
implementation, mirroring the decorator-based registration LabelingFormatRegistry
provides for IOStrategy (ext/core/io/registry.py).

Classes: PreviewRendererRegistry
"""

from typing import Dict, Optional, Type

from .base import PreviewRenderer


class PreviewRendererRegistry:
    """ Registry of preview renderers, keyed by the Label.annotation_type
    value(s) they handle.

    Decorator-only for now: renderers are registered by decorating their class
    and being imported (see preview_renderers/__init__.py). There is no runtime
    `register_new` counterpart yet, unlike LabelingFormatRegistry.
    """

    _renderers: Dict[str, Type[PreviewRenderer]] = {}

    @classmethod
    def register(cls, renderer_cls: Type[PreviewRenderer]) -> Type[PreviewRenderer]:
        """ Class decorator: registers a PreviewRenderer under every
        annotation_type value it declares via `annotation_types()`.

        :param renderer_cls: The PreviewRenderer subclass to register.
        :return: The same class, unmodified, so the decorator is transparent.
        """
        for annotation_type in renderer_cls.annotation_types():
            cls._renderers[annotation_type] = renderer_cls
        return renderer_cls

    @classmethod
    def get_for(cls, annotation_type: str) -> Optional[Type[PreviewRenderer]]:
        """ Resolve the PreviewRenderer class registered for a given
        Label.annotation_type.

        :param annotation_type: The Label.annotation_type value to resolve.
        :return: The registered PreviewRenderer subclass, or None if no
            renderer has been registered for this annotation_type.
        """
        return cls._renderers.get(annotation_type)