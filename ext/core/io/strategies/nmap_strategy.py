from typing import Union, Literal, Any, Collection

from . import IOStrategy
from . import SupportedFormats
from ... import StorageSpec, BatchMetadata, RenderConfig, FormatSpecification, LabelingFormatRegistry
from ....labeling import Label

file_type = str
extension = str

@LabelingFormatRegistry.register_strategy(SupportedFormats.NORMAL.value)
class NormalMapStrategy(IOStrategy):

    def get_specification(self) -> FormatSpecification:
        pass

    def serialize_image_labels(self, transformed: list[dict]) -> Collection[tuple[file_type, extension, str]]:
        pass

    def transform_annotation(self, label: Label, shot_idx: int, shot_config: RenderConfig) -> dict[str, Any]:
        pass

    def aggregate_batch(self, annotations: list[dict[str, Any]], batch_metadata: BatchMetadata) -> dict[
        str, list[dict]]:
        pass

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        pass

    def get_storage_spec(self) -> StorageSpec:
        pass

    def get_subdir_for(self, shot_id: Union[int,], f_type: file_type | Literal["image"]) -> str:
        pass

    def get_filename_for(self, shot_id: Union[int,], f_type: file_type | Literal["image"]) -> str:
        pass

    def ensure_directories(self) -> None:
        pass

