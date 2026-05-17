"""
COCO format strategy for bounding box object detection.
Generates COCO-formatted JSON with image metadata and annotations.
"""

import json
from typing import Any, Collection, Literal
from datetime import datetime
from os.path import join

from .. import StorageSpec
from ....labeling.conversions import convert_camera_centered_to_coco
from ....labeling.conversions import convert_camera_point_list_absolute_pixels_y_inverted
from ....labeling.generator.data_structure import *
from ...configurations import RenderConfig, WritingConfig, BatchMetadata
from ..io_strategy import IOStrategy, FormatSpecification
from ..registry import LabelingFormatRegistry
from . import SupportedFormats


file_type = str
extension = str

@LabelingFormatRegistry.register_strategy(SupportedFormats.COCO.value)
class COCOFormatter(IOStrategy):
    """
    COCO format implementation for bounding box detection.
    Generates a single JSON file per batch with all images and annotations.
    """

    def ensure_directories(self) -> None:
        image_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "images/")
        self._make_dirs([image_dir])

    def __init__(self, write_config: WritingConfig, config: dict):
        super().__init__(write_config, config)
        self.bbox_precision = config.get('bbox_precision') or 2
        self.split = config.get('split') or ''

        # COCO structure - accumulated during batch processing
        self.coco_data = {
            "info": {
                "description": "Synthetically generated dataset using the Blendersynth extension",
                "version": "1.0",
                "year": datetime.now().year,
            },
            "images": [],
            "annotations": [],
            "categories": []
        }
        self.annotation_id_counter = 1
        self.marked_img_ids = set()

    def get_specification(self) -> FormatSpecification:
        return FormatSpecification(
            # Data structure
            single_file_per_image=False,  # COCO uses one global file
            global_metadata_required=True,
            # Annotation grouping
            aggregation_strategy="global",  # All images aggregated into one file
            # Hooks
            requires_class_declaration=True,
            supports_image_metadata=True,
            # Core geometry types
            requires_bbox=True
        )

    def get_storage_spec(self) -> StorageSpec:
        return StorageSpec(
            single_file_per_image=False
        )

    def get_subdir_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """
        COCO structure: images/ folder for images, root for annotations.json
        """
        if f_type == "image":
            return (self.split + "/" if self.split else "") + "images/"
        else:
            # Labels go in root or dedicated folder
            return (self.split + "/" if self.split else "") + ""

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """
        Images get individual filenames; annotations are in a single file.
        """
        if f_type == "image":
            return f"{self.write_cfg.prefix}_{shot_id}"
        else:
            # Single annotation file for all images
            return "instances"

    def transform_annotation(
        self,
        label: Label,
        shot_idx: int,
        shot_config: RenderConfig
    ) -> dict[str, Any]:
        """
        Transform a single annotation to COCO format.
        Does NOT create the annotation entry yet - that happens in aggregate_batch.
        """
        if not label.annotation_type == "bbox":
            raise RuntimeError("COCO bbox formatter only supports bbox annotations!")

        bbox = label.bbox
        coco_bbox = convert_camera_centered_to_coco(bbox, shot_config.width, shot_config.height)

        if shot_idx not in self.marked_img_ids:
            self.coco_data["images"].append({
                "id": shot_idx,
                "file_name": f"{self.get_filename_for(shot_idx, 'image')}.{self.write_cfg.image_extension.lower()}",
                "height": shot_config.height,  # Should be provided by RenderConfig
                "width": shot_config.width,  # Should be provided by RenderConfig
            })
            self.marked_img_ids.add(shot_idx)

        return {
            'bbox': coco_bbox,  # [x, y, width, height]
            'class_id': label.cls.class_id,
            'class_name': label.cls.name,
            'image_id': shot_idx,
            'width': shot_config.width,
            'height': shot_config.height
        }

    def aggregate_batch(
        self,
        annotations: list[dict[str, Any]],
        batch_metadata: BatchMetadata
    ) -> dict[str, list[dict]]:
        """
        Aggregate all annotations for a batch.
        Groups by image_id and builds COCO structure.
        """
        # Build categories from batch metadata
        categories = []
        for class_obj in batch_metadata.classes:
            categories.append({
                "id": class_obj.class_id,
                "name": class_obj.name,
                "supercategory": "object"
            })

        # Group annotations by image
        annotations_by_image = {}
        for ann in annotations:
            img_id = ann['image_id']
            if img_id not in annotations_by_image:
                annotations_by_image[img_id] = []
            annotations_by_image[img_id].append(ann)

        # Build COCO annotations with proper structure
        coco_annotations = []
        for img_id, img_annotations in annotations_by_image.items():
            for ann in img_annotations:
                coco_ann = {
                    "id": self.annotation_id_counter,
                    "image_id": img_id,
                    "category_id": ann['class_id'],
                    "bbox": ann['bbox'],
                    "area": ann['bbox'][2] * ann['bbox'][3],  # width * height
                    "iscrowd": 0,
                }
                coco_annotations.append(coco_ann)
                self.annotation_id_counter += 1

        return {
            "categories": categories,
            "annotations": coco_annotations,
            "num_images": batch_metadata.num_images
        }

    def serialize_image_labels(
            self,
            transformed: list[dict]
    ) -> Collection[tuple[file_type, extension, str]]:
        """
        Not used for COCO (global format).
        Per-image serialization doesn't apply here.
        """
        raise NotImplementedError(
            "COCO uses global aggregation via finalize(), not per-image serialization"
        )

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        """
        Final pass: build complete COCO JSON structure.
        Receives aggregated data from aggregate_batch + image info.
        """
        # Add categories
        self.coco_data["categories"] = aggregated['categories']
        self.coco_data["annotations"] = aggregated['annotations']

        # Serialize to JSON
        coco_json = json.dumps(self.coco_data, indent=2)

        return (("instances", ".json", coco_json),)


@LabelingFormatRegistry.register_strategy(SupportedFormats.COCO_SEGMENTATION.value)
class COCOSegmentation(IOStrategy):
    """
    COCO format implementation for instance segmentation.
    Produces a single annotations JSON per batch with polygon segmentation masks.
    The polygon vertices are stored as a flat [x1, y1, x2, y2, ...] list, per COCO spec.
    """

    def ensure_directories(self) -> None:
        image_dir = join(self.write_cfg.save_path, (self.split + "/" if self.split else "") + "images/")
        self._make_dirs([image_dir])

    def __init__(self, write_config: WritingConfig, config: dict):
        super().__init__(write_config, config)
        self.split = config.get('split') or ''
        self.bbox_precision = config.get('bbox_precision') or 2

        self.coco_data = {
            "info": {
                "description": "Synthetically generated dataset using the Blendersynth extension",
                "version": "1.0",
                "year": datetime.now().year,
            },
            "images": [],
            "annotations": [],
            "categories": []
        }
        self.annotation_id_counter = 1
        self.marked_img_ids = set()

    def get_specification(self) -> FormatSpecification:
        return FormatSpecification(
            single_file_per_image=False,
            global_metadata_required=True,
            aggregation_strategy="global",
            requires_class_declaration=True,
            supports_image_metadata=True,
            requires_polygon=True,
        )

    def get_storage_spec(self) -> StorageSpec:
        return StorageSpec(single_file_per_image=False)

    def get_subdir_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        if f_type == "image":
            return (self.split + "/" if self.split else "") + "images/"
        return self.split + "/" if self.split else ""

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        if f_type == "image":
            return f"{self.write_cfg.prefix}_{shot_id}"
        return "instances_segmentation"

    def transform_annotation(
        self,
        label: Label,
        shot_idx: int,
        shot_config: RenderConfig
    ) -> dict[str, Any]:

        if label.annotation_type != "polygon" or label.polygon is None:
            raise RuntimeError(
                f"COCOSegmentation requires polygon annotations, got '{label.annotation_type}' "
                f"for object '{label.obj_or_entity_name}'. Use PolygonExtractor."
            )
        if shot_idx not in self.marked_img_ids:
            self.coco_data["images"].append({
                "id": shot_idx,
                "file_name": f"{self.get_filename_for(shot_idx, 'image')}.{self.write_cfg.image_extension.lower()}",
                "height": shot_config.height,
                "width": shot_config.width,
            })
            self.marked_img_ids.add(shot_idx)

        pixel_polygon = convert_camera_point_list_absolute_pixels_y_inverted(
            label.polygon, shot_config.width, shot_config.height
        )
        # COCO segmentation: flat [x1, y1, x2, y2, ...]
        flat_polygon = [coord for point in pixel_polygon for coord in point]

        # Derive bbox from polygon bounds for the annotation's bbox field (required by COCO spec)
        xs = [p[0] for p in pixel_polygon]
        ys = [p[1] for p in pixel_polygon]
        x_min, y_min = min(xs), min(ys)
        bbox_w = max(xs) - x_min
        bbox_h = max(ys) - y_min

        return {
            'image_id': shot_idx,
            'class_id': label.cls.class_id,
            'class_name': label.cls.name,
            'segmentation': flat_polygon,
            'bbox': [round(x_min, self.bbox_precision), round(y_min, self.bbox_precision),
                     round(bbox_w, self.bbox_precision), round(bbox_h, self.bbox_precision)],
            'area': round(bbox_w * bbox_h, self.bbox_precision),
        }

    def serialize_image_labels(self, transformed: list[dict]) -> Collection[tuple[file_type, extension, str]]:
        raise NotImplementedError("COCOSegmentation uses global aggregation via finalize().")

    def aggregate_batch(
        self,
        annotations: list[dict[str, Any]],
        batch_metadata: BatchMetadata
    ) -> dict[str, Any]:
        categories = [
            {"id": cls.class_id, "name": cls.name, "supercategory": "object"}
            for cls in batch_metadata.classes
        ]
        coco_annotations = []
        for ann in annotations:
            coco_annotations.append({
                "id": self.annotation_id_counter,
                "image_id": ann['image_id'],
                "category_id": ann['class_id'],
                "segmentation": [ann['segmentation']],  # COCO expects list of polygons
                "bbox": ann['bbox'],
                "area": ann['area'],
                "iscrowd": 0,
            })
            self.annotation_id_counter += 1

        return {"categories": categories, "annotations": coco_annotations}

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        self.coco_data["categories"] = aggregated["categories"]
        self.coco_data["annotations"] = aggregated["annotations"]
        return (("instances_segmentation", ".json", json.dumps(self.coco_data, indent=2)),)

@LabelingFormatRegistry.register_strategy(SupportedFormats.COCO_KEYPOINTS.value)
class COCOLandmarks(IOStrategy):
    pass