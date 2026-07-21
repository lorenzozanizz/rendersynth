from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from contextlib import nullcontext, AbstractContextManager
from os.path import join

from ...labeling.generator.data_structure import *
from ..configurations import RenderConfig, BatchMetadata, WritingConfig

# This is required here for typing purposes, for some reason pycharm does not detect
# the dataclasses below with the reimport
from dataclasses import dataclass

from ...labeling.writing_folder_structure import FolderStructure


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

class IOStrategy(FolderStructure, metaclass=ABCMeta):
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


    # If a substrategy wants to change this path and directory utilities, it can
    # easily override them dynamically.
    def get_full_dir_for(self, shot_idx: int, f_type: str) -> str:
        """ Absolute-ish directory (rooted at write_cfg.save_path) a file of this
        type would be written into.  """
        return join(self.write_cfg.save_path, self.get_subdir_for(shot_idx, f_type))

    def get_full_path_for(self, shot_idx: int, f_type: str, ext: str = "") -> str:
        """ Get the full file path (dir + filename [+ ext]) for a given content to be
        serialized. """
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        filename = self.get_filename_for(shot_idx, f_type)
        return join(self.get_full_dir_for(shot_idx, f_type), filename) + ext
