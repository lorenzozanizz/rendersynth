"""
Pascal VOC format strategy for bounding box object detection.
Generates one XML annotation file per image.
"""

from typing import Any, Collection, Literal
from xml.etree.ElementTree import Element, SubElement, tostring
from os.path import join
import xml.dom.minidom

from .. import StorageSpec
from ....labeling.conversions import convert_camera_centered_to_pascal_voc
from ....labeling.generator.data_structure import *
from ...configurations import RenderConfig, WritingConfig, BatchMetadata
from ..io_strategy import IOStrategy, FormatSpecification
from ..registry import LabelingFormatRegistry
from . import SupportedFormats


file_type = str
extension = str

@LabelingFormatRegistry.register_strategy(SupportedFormats.PASCAL_VOC.value)
class PascalVOCFormatter(IOStrategy):
    """
    Pascal VOC format implementation for bounding box detection.
    Generates one XML file per image with annotations.
    """

    def ensure_directories(self) -> None:
        image_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "images/")
        label_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "annotations/")
        self._make_dirs([image_dir, label_dir])

    def __init__(self, write_config: WritingConfig, config: dict):
        super().__init__(write_config, config)
        self.split = config.get('split') or ''
        self.xml_indent = config.get('xml_indent') or 2

    def get_specification(self) -> FormatSpecification:
        return FormatSpecification(
            # Data structure
            single_file_per_image=True,  # Pascal VOC: one XML per image (like YOLO)
            global_metadata_required=False,
            # Annotation grouping
            aggregation_strategy="per_image",  # Per-image style
            # Hooks
            requires_class_declaration=False,  # Class names are strings in XML
            supports_image_metadata=True,  # Can store image size, depth, etc.
            # Core geometry types
            requires_bbox=True
        )

    def get_storage_spec(self) -> StorageSpec:
        return StorageSpec(
            single_file_per_image=True
        )

    def get_subdir_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """
        Pascal VOC structure: images/ and annotations/ folders
        """
        if f_type == "image":
            return (self.split + "/" if self.split else "") + "images/"
        else:
            # Annotations go in separate folder
            return (self.split + "/" if self.split else "") + "annotations/"

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """
        Generate filename for image or annotation.
        """
        base_name = f"{self.write_cfg.prefix}_{shot_id:04d}" if self.write_cfg.zero_pad else f"{self.write_cfg.prefix}_{shot_id}"
        return base_name

    def transform_annotation(
            self,
            label: Label,
            shot_idx: int,
            shot_config: RenderConfig
    ) -> dict[str, Any]:
        """
        Transform a single annotation to Pascal VOC format.
        """
        if not label.annotation_type == "bbox":
            raise RuntimeError("Pascal VOC formatter only supports bbox annotations!")

        bbox = label.bbox
        # Convert from camera-centered [-1,1] to Pascal VOC [xmin, ymin, xmax, ymax] in pixels
        pascal_bbox = convert_camera_centered_to_pascal_voc(bbox, shot_config.width, shot_config.height)

        return {
            'bbox': pascal_bbox,  # [xmin, ymin, xmax, ymax] in pixels
            'class_name': label.cls.name,
            'difficult': 0,  # Could be parameterized
            'truncated': 0,  # Could be parameterized
            'occluded': 0  # Could be parameterized
        }

    def serialize_image_labels(
            self,
            transformed: list[dict],
            shot_idx: int = 0,
            render_config: RenderConfig = None
    ) -> Collection[tuple[file_type, extension, str]]:
        """
        Serialize annotations for a single image to Pascal VOC XML format.

        :param transformed: List of transformed annotations
        :param shot_idx: Image index (used for filename)
        :param render_config: RenderConfig with image dimensions
        :return: Tuple of (filename, extension, content)
        """
        # Create root annotation element
        annotation = Element('annotation')

        # Add folder (optional, but common in Pascal VOC)
        folder = SubElement(annotation, 'folder')
        folder.text = 'dataset'

        # Add filename
        base_name = f"{self.write_cfg.prefix}_{shot_idx:04d}" if self.write_cfg.zero_pad else f"{self.write_cfg.prefix}_{shot_idx}"
        filename = SubElement(annotation, 'filename')
        filename.text = base_name + self.write_cfg.image_extension

        # Add path (optional)
        path = SubElement(annotation, 'path')
        path.text = self.write_cfg.save_path

        # Add source information (optional but standard)
        source = SubElement(annotation, 'source')
        database = SubElement(source, 'database')
        database.text = 'Synthetic Dataset'
        annotation_source = SubElement(source, 'annotation')
        annotation_source.text = 'Synthetic'
        image_source = SubElement(source, 'image')
        image_source.text = 'Synthetic'

        # Add image size
        if render_config:
            size = SubElement(annotation, 'size')
            width = SubElement(size, 'width')
            width.text = str(render_config.width)
            height = SubElement(size, 'height')
            height.text = str(render_config.height)
            depth = SubElement(size, 'depth')
            depth.text = '3'  # RGB

        # Add segmented flag (optional)
        segmented = SubElement(annotation, 'segmented')
        segmented.text = '0'

        # Add objects (annotations)
        for ann in transformed:
            obj = SubElement(annotation, 'object')

            # Class name
            name = SubElement(obj, 'name')
            name.text = ann['class_name']

            # Pose (optional)
            pose = SubElement(obj, 'pose')
            pose.text = 'Unspecified'

            # Truncated flag
            truncated = SubElement(obj, 'truncated')
            truncated.text = str(ann.get('truncated', 0))

            # Difficult flag
            difficult = SubElement(obj, 'difficult')
            difficult.text = str(ann.get('difficult', 0))

            # Occluded flag (optional)
            occluded = SubElement(obj, 'occluded')
            occluded.text = str(ann.get('occluded', 0))

            # Bounding box
            bndbox = SubElement(obj, 'bndbox')
            xmin, ymin, xmax, ymax = ann['bbox']

            xmin_elem = SubElement(bndbox, 'xmin')
            xmin_elem.text = str(int(xmin))

            ymin_elem = SubElement(bndbox, 'ymin')
            ymin_elem.text = str(int(ymin))

            xmax_elem = SubElement(bndbox, 'xmax')
            xmax_elem.text = str(int(xmax))

            ymax_elem = SubElement(bndbox, 'ymax')
            ymax_elem.text = str(int(ymax))

        # Convert to pretty-printed XML string
        xml_string = self._prettify_xml(annotation)

        # Return tuple: (filename_without_ext, extension, content)
        return ((base_name, '.xml', xml_string),)

    def aggregate_batch(
            self,
            annotations: list[dict[str, Any]],
            batch_metadata: BatchMetadata
    ) -> dict[str, Any]:
        """
        Not used for per-image format.
        Pascal VOC creates one file per image, no aggregation needed.
        """
        return { }

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        """
        Not used for per-image format.
        Pascal VOC creates one file per image, no finalization needed.
        """
        return ()

    @staticmethod
    def _prettify_xml(element: Element) -> str:
        """
        Return a pretty-printed XML string for the Element.
        """
        rough_string = tostring(element, encoding='unicode')
        reparsed = xml.dom.minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")