from abc import ABCMeta, abstractmethod
from typing import Any
from collections.abc import Collection
from os import makedirs
from contextlib import nullcontext, AbstractContextManager

from ...labeling.generator.data_structure import *
from ..configurations import RenderConfig, BatchMetadata, WritingConfig

# This is requierd here for typing purposes, for some reason pycharm does not detect
# the dataclasses below with the reimport
from dataclasses import dataclass


@dataclass
class StorageSpec:
    """ Declares how files are organized on disk (independent of format) """

    # Organization
    single_file_per_image: bool  # YOLO style vs COCO style


@dataclass
class FormatSpecification:
    """ Declares what types of annotations a format supports """

    # Data structure
    single_file_per_image: bool  # YOLO, VS format: True. COCO: False
    global_metadata_required: bool  # COCO needs it; YOLO doesn't

    # Annotation grouping
    aggregation_strategy: Literal["per_image", "per_batch", "global"]

    # Hooks
    requires_class_declaration: bool
    supports_image_metadata: bool

    # Core geometry types
    requires_bbox: bool = False
    requires_polygon: bool = False
    requires_keypoints: bool = False
    requires_depth: bool = False


# Just some syntactic sugar types
file_type = str
extension = str

class IOStrategy(metaclass=ABCMeta):
    """Define what a format needs; don't directly write files"""

    def __init__(self, write_config: WritingConfig, format_config: dict) -> None:
        self.config = format_config
        self.write_cfg = write_config

    @abstractmethod
    def get_specification(self) -> FormatSpecification:
        """Declare format requirements and capabilities"""
        pass

    @abstractmethod
    def serialize_image_labels(
        self,
        transformed: list[dict]
    ) -> Collection[tuple[file_type, extension, str]]:
        """ This functions is called when serializing per-image labels.

        :param transformed:
        :return:
        """
        pass

    @abstractmethod
    def transform_annotation(
        self,
        label: Label,
        shot_idx: int,
        shot_config: RenderConfig
    ) -> dict[str, Any]:
        """ Transform canonical annotation to format-specific dict """
        pass

    @abstractmethod
    def aggregate_batch(
        self,
        annotations: list[dict[str, Any]],
        batch_metadata: BatchMetadata
    ) -> dict[str, list[dict]]:
        """
        Aggregate multiple images' annotations.
        Returns structure ready for serialization.
        E.g., COCO returns {"images": [...], "annotations": [...], "categories": [...]}
        """
        pass

    @abstractmethod
    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        """
        Final pass: add metadata, compute derived fields, etc.
        Returns {filename: content} ready to write.
        """
        pass

    @abstractmethod
    def get_storage_spec(self) -> StorageSpec:
        """Declare directory structure and naming"""
        pass

    @abstractmethod
    def get_subdir_for(self, shot_id: Union[int, ], f_type: file_type | Literal["image"]) -> str:
        pass

    @abstractmethod
    def get_filename_for(self, shot_id: Union[int,  ], f_type: file_type | Literal["image"]) -> str:
        pass

    @abstractmethod
    def ensure_directories(self) -> None:
        """ Create all the required directories for the given IO strategy """
        pass

    @staticmethod
    def _make_dirs(dirs: list[str]) -> None:
        """
        """
        for directory in dirs:
            makedirs(directory, exist_ok=True)

    @staticmethod
    def get_context() -> AbstractContextManager:
        # Default implementation: do nothing.
        # If a particular strategy has to change the blender context, it must implement a
        # side effect free context manager.
        return nullcontext()

    @staticmethod
    def signal_begin_shot():
        """

        :return:
        """
        return
