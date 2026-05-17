"""
CVAT XML Format Implementation

This module implements the CVAT XML export format as defined by Intel's Computer Vision Annotation Tool.

"""

from typing import Any, Collection, Literal
from datetime import datetime
from os.path import join
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from .. import StorageSpec
from ....labeling.conversions import convert_camera_centered_to_coco
from ....labeling.generator.data_structure import *
from ...configurations import RenderConfig, WritingConfig, BatchMetadata
from ..io_strategy import IOStrategy, FormatSpecification
from ..registry import LabelingFormatRegistry
from . import SupportedFormats

file_type = str
extension = str



@LabelingFormatRegistry.register_strategy(SupportedFormats.CVAT_XML_IMAGES.value)
class CVATFormatter(IOStrategy):
    """ CVAT XML Format Exporter
    """

    def ensure_directories(self) -> None:
        image_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "images/")
        self._make_dirs([image_dir])

    def __init__(self, write_config: WritingConfig, config: dict):
        super().__init__(write_config, config)
        self.split = config.get('split', '')
        self.task_id = config.get('task_id', 1)
        self.task_name = config.get('task_name', 'Generated Annotations')
        self.image_metadata = {}  # Store image dimensions: {shot_id: (width, height)}
        self.annotations_list = []  # Accumulate annotations
        self.images_list = []  # Accumulate image metadata
        self.classes_map = {}  # Map class names to IDs

    def get_specification(self) -> FormatSpecification:
        """
        CVAT supports a comprehensive set of annotation types.
        Uses global aggregation strategy with a single XML output file.
        """
        return FormatSpecification(
            # Data structure
            single_file_per_image=False,  # CVAT uses a single global XML
            global_metadata_required=True,  # Requires metadata section
            # Annotation grouping
            aggregation_strategy="global",  # All annotations in one file
            # Hooks
            requires_class_declaration=True,  # CVAT XML requires label declarations
            supports_image_metadata=True,  # Stores image width/height
            # Core geometry types
            requires_bbox=False,  # Optional
            requires_polygon=False,  # Optional
            requires_keypoints=False  # Optional
        )

    def transform_annotation(
        self,
        label: Label,
        shot_idx: int,
        shot_config: RenderConfig
    ) -> dict[str, Any]:
        """
        Transform canonical camera-centeered annotation to CVAT XML format.

        CVAT supports multiple geometry types. This method converts the canonical
        Label object to a CVAT-compatible dictionary representation.
        """
        # Keep track of image widths
        self.image_metadata[shot_idx] = (shot_config.width, shot_config.height)
        result = {
            'shot_idx': shot_idx,
            'label_name': label.cls.name,
            'label_id': label.cls.class_id,
            'occluded': 0,
            'attributes': {}
        }

        if label.annotation_type == "bbox":
            bbox = label.bbox
            result['type'] = 'box'
            # Convert to CVAT box format: (xtl, ytl, xbr, ybr)
            mapped_bbox = convert_camera_centered_to_coco(bbox, shot_config.width, shot_config.height)
            result['geometry'] = {
                'xtl': float(mapped_bbox[0]),
                'ytl': float(mapped_bbox[1]),
                'xbr': float(mapped_bbox[2]),
                'ybr': float(mapped_bbox[3])
            }
        else:
            raise RuntimeError(f"Unsupported annotation type: {label.annotation_type}")

        return result

    def serialize_image_labels(
            self,
            transformed: list[dict]
    ) -> Collection[tuple[file_type, extension, str]]:
        """
        For CVAT, individual images don't have their own label files.
        Instead, annotations are accumulated in aggregate_batch().
        This method stores metadata for later use.
        """
        # CVAT uses global aggregation, so this is useless
        # The actual serialization happens in finalize()
        return tuple()

    def aggregate_batch(
            self,
            annotations: list[dict[str, Any]],
            batch_metadata: BatchMetadata
    ) -> dict[str, Any]:
        """
        Aggregate all annotations into CVAT XML structure.

        This method is called once per batch and collects all transformed annotations
        along with image metadata to create the final XML structure.

        :param annotations: List of transformed annotation dicts
        :param batch_metadata: Batch context (num_images, classes)
        :return: Dictionary containing CVAT XML structure ready for finalization
        """
        # Build class mapping
        self.classes_map = {cls.class_id: cls.name for cls in batch_metadata.classes}

        # Group annotations by image/shot
        annotations_by_shot = {}
        for ann in annotations:
            shot_idx = ann['shot_idx']
            if shot_idx not in annotations_by_shot:
                annotations_by_shot[shot_idx] = []
            annotations_by_shot[shot_idx].append(ann)

        return {
            'annotations_by_shot': annotations_by_shot,
            'num_images': batch_metadata.num_images,
            'classes': batch_metadata.classes
        }

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        """
        Build the final CVAT XML file from aggregated annotations.

        This creates a properly formatted XML document with:
        - Metadata section (task info, labels)
        - Image sections with nested annotations
        """
        annotations_by_shot = aggregated.get('annotations_by_shot', {})
        num_images = aggregated.get('num_images', 0)
        classes = aggregated.get('classes', [])

        # Create root element
        root = Element('annotations')

        # Add version
        version_elem = SubElement(root, 'version')
        version_elem.text = '1.0'

        # Add metadata section
        meta_elem = SubElement(root, 'meta')
        task_elem = SubElement(meta_elem, 'task')

        SubElement(task_elem, 'id').text = str(self.task_id)
        SubElement(task_elem, 'name').text = self.task_name
        SubElement(task_elem, 'size').text = str(num_images)
        SubElement(task_elem, 'mode').text = 'annotation'
        SubElement(task_elem, 'created').text = datetime.now().isoformat() + 'Z'
        SubElement(task_elem, 'updated').text = datetime.now().isoformat() + 'Z'

        # Add labels section
        labels_elem = SubElement(task_elem, 'labels')
        for cls in classes:
            label_elem = SubElement(labels_elem, 'label')
            SubElement(label_elem, 'name').text = cls.name
            SubElement(label_elem, 'id').text = str(cls.class_id)

        # Add image annotations
        for shot_idx in sorted(annotations_by_shot.keys()):
            image_annotations = annotations_by_shot[shot_idx]

            # The image metadata was
            width = self.image_metadata.get(shot_idx, (1920, 1080))[0]
            height = self.image_metadata.get(shot_idx, (1920, 1080))[1]

            image_filename = self.get_filename_for(shot_idx, "image") + self.write_cfg.image_extension

            # Create image element
            image_elem = SubElement(
                root,
                'image',
                id=str(shot_idx),
                name=image_filename,
                width=str(width),
                height=str(height)
            )

            # Add annotations for this image
            for ann in image_annotations:
                self._add_annotation_element(image_elem, ann)

        # Pretty-print XML
        xml_str = self._prettify_xml(root)

        return ('annotations', '.xml', xml_str),

    def _add_annotation_element(self, parent: Element, annotation: dict[str, Any]) -> None:
        """
        Helper method to add an annotation element (box, polygon, etc.) to the XML tree.
        """
        ann_type = annotation['type']
        geometry = annotation['geometry']

        if ann_type == 'box':
            box_elem = SubElement(
                parent,
                'box',
                label=annotation['label_name'],
                xtl=str(geometry['xtl']),
                ytl=str(geometry['ytl']),
                xbr=str(geometry['xbr']),
                ybr=str(geometry['ybr']),
                occluded=str(annotation['occluded'])
            )
            self._add_attributes(box_elem, annotation.get('attributes', {}))

    @staticmethod
    def _add_attributes(parent: Element, attributes: dict[str, Any]) -> None:
        """
        Helper method to add custom attributes to an annotation element.
        """
        for attr_name, attr_value in attributes.items():
            attr_elem = SubElement(parent, 'attribute', name=attr_name)
            attr_elem.text = str(attr_value)

    @staticmethod
    def _prettify_xml(elem: Element) -> str:
        """
        Return a pretty-printed XML string.
        """
        rough_string = tostring(elem, encoding='unicode')
        reparsed = parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def get_storage_spec(self) -> StorageSpec:
        """
        CVAT uses a single global XML file, so all annotations go in one place.
        Images are stored in a separate directory.
        """
        return StorageSpec(
            single_file_per_image=False
        )

    def get_subdir_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """
        CVAT stores images in an 'images/' directory and the annotations XML at root.
        """
        if f_type == "image":
            return "images/"
        else:
            # Labels are stored at root level
            return ""

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """
        CVAT stores a single annotations.xml file.
        Images are named based on shot_id.
        """
        if f_type == "image":
            shot_id_str = str(shot_id).zfill(6) if self.write_cfg.zero_pad else str(shot_id)
            return f"{self.write_cfg.prefix}_{shot_id_str}"
        else:
            return "annotations"
