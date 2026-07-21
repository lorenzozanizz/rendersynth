from collections.abc import Collection
from pathlib import Path
from os.path import join, isfile
from os import listdir
from contextlib import nullcontext, AbstractContextManager

import re

from ...labeling import LabelData
from ..configurations import WritingConfig, RenderConfig, BatchMetadata
from .io_strategy import IOStrategy


class OutputWriter:

    def __init__(self, config: WritingConfig,
                 io_strategy: IOStrategy = None):
        self.config = config
        self._batch_metadata = None

        self.io_strategy: IOStrategy = io_strategy
        if self.io_strategy is not None:
            self.spec = self.io_strategy.get_specification()
        self.pending_annotations = []
        # The index of the current shot being written. This influences the unique label/image name.
        self.shot_idx = 0

    def get_config(self) -> WritingConfig:
        return self.config

    def set_strategy(self, strategy: IOStrategy):
        self.io_strategy = strategy
        # This is information related to the kind of data that the strategy requires in order
        # to correctly generate labels.
        self.spec = self.io_strategy.get_specification()

    def set_shot_index(self, idx: int) -> None:
        self.shot_idx = idx

    def get_strategy(self) -> IOStrategy:
        """ Get the current writing strategy for the output writer. """
        return self.io_strategy

    def begin_batch(self, batch_metadata: BatchMetadata) -> None:
        """Called once before rendering begins"""
        # Store the batch metadata for the end of generation callback.
        self._batch_metadata = batch_metadata
        # create all required subdirectories.
        self.io_strategy.ensure_directories()

    def write_shot(
        self,
        annotations: LabelData,
        render_config: RenderConfig
    ) -> None:
        """Called per-shot. May not write immediately (e.g., COCO batches)"""

        self.io_strategy.signal_begin_shot()
        # Transform annotations to format-specific representation
        transformed = [
            self.io_strategy.transform_annotation(ann, self.shot_idx, render_config)
            for ann in annotations
        ]

        # Store or write immediately depending on aggregation strategy
        if self.spec.aggregation_strategy == "per_image":
            # YOLO case: write immediately
            self._write_image_labels(transformed)
        else:
            # COCO case: accumulate
            self.pending_annotations.append((self.shot_idx, transformed))

    def _write_image_labels(self, transformed: list[dict]) -> None:
        """For per-image formats (YOLO)"""
        # Serialize transformed data, the content contains information about
        # file type (internal to the filesystem handler, extension and content)
        serialized_items = self.io_strategy.serialize_image_labels(transformed)
        self._write_serialized_content(serialized_items)

    def end_batch(self) -> None:
        """Called once after all shots rendered"""
        # Note: this is executed independently of the aggregation type, formats which
        # require no aggregation will simply do nothing in their implementations.
        # Aggregate all pending annotations
        aggregated = self.io_strategy.aggregate_batch(
            self._flatten_pending(),
            self._batch_metadata
        )

        # Finalize (compute derived fields, wrap in JSON, etc.)
        finalized_content = self.io_strategy.finalize(aggregated)
        if not finalized_content:
            return
        self._write_serialized_content(finalized_content)

    def _write_serialized_content(self, serialized_content: Collection[tuple[str, str, str]]) -> None:
        """

        :param serialized_content:
        :return:
        """

        for (file_type, ext, file_content) in serialized_content:

            # Note: to write image types of labels (e.g. for normal maps or depth maps,
            # we use blender's image writing API to avoid injecting a dependency.

            # Ensure that the extension is properly formatted.
            if not ext.startswith("."):
                ext = f".{ext}"

            write_dir = self.io_strategy.get_full_path_for(self.shot_idx, file_type, ext)
            # name = self.io_strategy.get_filename_for(self.shot_idx, f_type=file_type)
            # path = self.io_strategy.get_subdir_for(self.shot_idx, f_type=file_type)
            # write_dir = join(self.config.save_path, path, name) + ext
            # ^ Previous version of the code, changed after extending the IOStrategy to expose fully
            # writing paths for the given strategy.

            with open(write_dir, 'w') as f:
                f.write(file_content)

    def _flatten_pending(self) -> list[dict]:
        """Flatten accumulated annotations for batch strategies"""
        return [ann for _, anns in self.pending_annotations for ann in anns]

    def get_image_write_path(self) -> str:
        """Get full path where image will be saved"""
        filename = self.io_strategy.get_filename_for(self.shot_idx, "image")
        return join(self.get_image_folder(), filename)

    def get_image_folder(self) -> str:
        """Get folder where images are stored"""
        subdir = self.io_strategy.get_subdir_for(self.shot_idx, "image")
        return join(self.config.save_path, subdir)

    def compute_starting_index(self) -> int:
        """ A function which computes the starting index at which the new files
        have to be offset, e.g. if the from_last setting has been set the new generated data
        will continue counting from the last value

        :return: the new index
        """
        prefix = self.config.prefix
        if self.config.from_last:
            # We have to inspect the data folder, if there are already fils with the same root and
            # some indexes are already present, start counting from the last
            return self._analyze_folder_last_index(self.get_image_folder(), prefix)
        return 0

    @staticmethod
    def _analyze_folder_last_index(path_root: str | Path, prefix) -> int:
        """ Analyze the given folder searching for all files with the correct name schema.
        This extracts the file with the biggest index, and starts counting from that index.

        :param path_root: The path at which the files are examined
        :param prefix: the prefix of the file
        :return: the last index
        """
        # If the path does not exist yet, the index is simply 0.
        try:
            entries = listdir(path_root)
        except FileNotFoundError:
            return 0
        files = [f for f in entries if isfile(join(path_root, f))]

        # Find all files matching "prefix_index" pattern
        pattern = re.compile(rf"{re.escape(prefix)}_(\d+)")
        indices = []

        for file in files:
            match = pattern.match(file)
            if match:
                indices.append(int(match.group(1)))

        # Get the last index, or -1 (which becomes 0 when i add +1) if no matches
        last_index = max(indices) if indices else -1
        next_index = last_index + 1
        return next_index

    def get_context(self) -> AbstractContextManager:
        if self.io_strategy is None:
            return nullcontext()
        else:
            return self.io_strategy.get_context()

