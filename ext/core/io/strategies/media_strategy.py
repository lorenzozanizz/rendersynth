from typing import Union, Collection
from os.path import join

from ..io_strategy import IOStrategy, FormatSpecification
from ..registry import LabelingFormatRegistry
from . import SupportedFormats
from .. import StorageSpec
from ....labeling.generator.data_structure import *
from ...configurations import RenderConfig, BatchMetadata


file_type = str
extension = str

@LabelingFormatRegistry.register_strategy(SupportedFormats.IMAGE_ONLY.value)
class ImageOnlyStrategy(IOStrategy):

    def get_specification(self) -> FormatSpecification:
        return FormatSpecification(
            # Data structure
            single_file_per_image=True,
            global_metadata_required=False,
            # Annotation grouping
            aggregation_strategy="per_image",  # Per-image style
            requires_class_declaration=False,
            supports_image_metadata=True,  # Can store image size, depth, etc.
            requires_bbox=False
        )

    def serialize_image_labels(self, transformed: list[dict]) -> Collection[tuple[file_type, extension, str]]:
        return ()

    def transform_annotation(self, label: Label, shot_idx: int, shot_config: RenderConfig) -> dict[str, Any]:
        pass

    def aggregate_batch(self, annotations: list[dict[str, Any]], batch_metadata: BatchMetadata) -> dict[
        str, list[dict]]:
        pass

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        pass

    def get_storage_spec(self) -> StorageSpec:
        return StorageSpec(
            single_file_per_image=True
        )

    def get_subdir_for(self, shot_id: Union[int,], f_type: file_type | Literal["image"]) -> str:
        """
        Pascal VOC structure: images/ and annotations/ folders
        """
        return "images/"

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """ Generate filename for image or annotation. """
        base_name = f"{self.write_cfg.prefix}_{shot_id:04d}" if self.write_cfg.zero_pad else f"{self.write_cfg.prefix}_{shot_id}"
        return base_name

    def ensure_directories(self) -> None:
        """ """
        image_dir = join(self.write_cfg.save_path, "images/")
        self._make_dirs([image_dir])

