"""

"""
from os.path import join
from typing import Any, Collection

from .. import StorageSpec
from ....labeling.conversions import convert_camera_centered_to_yolo
from ....labeling.generator.data_structure import *
from ...configurations import RenderConfig, WritingConfig
from ..io_strategy import IOStrategy, FormatSpecification
from ..registry import LabelingFormatRegistry
from . import SupportedFormats


file_type = str
extension = str


@LabelingFormatRegistry.register_strategy(SupportedFormats.ULTRALYTICS_YOLO.value)
class YoloFormatter(IOStrategy):
    """

    """

    def ensure_directories(self) -> None:
        image_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "images/")
        label_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "labels/")
        self._make_dirs([image_dir, label_dir])

    def __init__(self, write_config: WritingConfig, config: dict):
        super().__init__(write_config, config)
        self.bbox_precision = config.get('bbox_precision', 3)
        self.split = config.get('split', '')

        self.marked_img_ids = set()

    def serialize_image_labels(self, transformed: list[dict]) -> Collection[tuple[file_type, extension, str]]:
        lines = []
        for label in transformed:
            cls_id = label['id']
            yolo_coos = label['bbox']

            lines.append(f"{cls_id} "
                         f"{yolo_coos[0]:.{self.bbox_precision}f} "
                         f"{yolo_coos[1]:.{self.bbox_precision}f} "
                         f"{yolo_coos[2]:.{self.bbox_precision}f} "
                         f"{yolo_coos[3]:.{self.bbox_precision}f}\n")

        return ('label', '.txt', "".join(lines)),

    def get_storage_spec(self) -> StorageSpec:
        pass

    def get_subdir_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """

        :param shot_id:
        :param f_type:
        :return:
        """
        if f_type == "image":
            return (self.split + "/" if self.split else "") + "images/"
        elif "metadata" in f_type:
            return "" # Keep parent directory
        else: return (self.split + "/" if self.split else "") + "labels/"

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        if f_type == "yaml_metadata":
            return "data"
        elif f_type == "txt_metadata":
            return self.split if self.split else "images"
        else:
            return f"{self.write_cfg.prefix}_{shot_id}"

    def transform_annotation(self, label: Label, shot_idx: int, shot_config: RenderConfig) -> dict[str, Any]:
        if not label.annotation_type == "bbox":
            raise RuntimeError("Wrong annotation type in YOLO formatter!")
        bbox = label.bbox

        if shot_idx not in self.marked_img_ids:
            self.marked_img_ids.add(shot_idx)

        return {
            # Notice that geometry from the Label data is expressed in the camera centered -1..1 coordinate space.
            'bbox': convert_camera_centered_to_yolo(bbox),
            'id': label.cls.class_id
        }

    def get_specification(self) -> FormatSpecification:

        return FormatSpecification(
            # Data structure
            single_file_per_image = True,
            global_metadata_required = False,
            # Annotation grouping
            aggregation_strategy = "per_image",
            # Hooks
            requires_class_declaration = False,
            supports_image_metadata = False,
            # Core geometry types
            requires_bbox = True
        )

    def aggregate_batch(self, annotations, batch_metadata) -> dict[str, Any]:
        # Nothing to aggregate for YOLO
        return {}

    def finalize(self, aggregated) -> Collection[tuple[file_type, extension, str]]:
        # Used to generate the train.txt and data.yaml
        # first generate teh data.yaml, no aggregated data required.
        if self.split:
            yaml_content = f"path:  ./\n{self.split}: {self.split}.txt"
        else:
            yaml_content = f"path:  ./\nimages: images.txt"
        # Now generate the content of the txt. file
        txt_content = []
        for recorded_img in self.marked_img_ids:

            line = (f'images/{self.split + "/" if self.split else ""}'
                f'{self.get_filename_for(recorded_img, "image")}.{self.write_cfg.image_extension.lower()}\n')
            txt_content.append(line)
        txt_content = ''.join(txt_content)
        return ('txt_metadata', '.txt', txt_content), ('yaml_metadata', '.yaml', yaml_content)

