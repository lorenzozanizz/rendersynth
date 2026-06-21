"""
PCD (Point Cloud Data) Format Writer for Blender Extension
Writes point clouds with position, color, and class information.
"""
from os.path import join
from typing import Collection
import json

from .. import StorageSpec
from ....labeling.generator.data_structure import *
from ...configurations import RenderConfig, WritingConfig
from ..io_strategy import IOStrategy, FormatSpecification
from ..registry import LabelingFormatRegistry
from . import SupportedFormats

file_type = str
extension = str


@LabelingFormatRegistry.register_strategy(SupportedFormats.PCD_CLASS_COLOR.value)
class PCDFormatter(IOStrategy):
    """ Point Cloud Data (PCD) format writer.

    Outputs:
    - Individual .pcd files per image (containing point clouds with color and class)
    - A metadata.json file mapping annotations to their PCD files
    - A classes.json file with class definitions
    """

    def __init__(self, write_config: WritingConfig, config: dict):
        super().__init__(write_config, config)
        self.coordinate_precision = config.get('coordinate_precision', 6)
        self.tracked_annotations = []
        self.class_registry = {}

        self.cloud_id = 0

    def ensure_directories(self) -> None:
        """ Create directory structure for PCD output """
        pcd_dir = join(self.write_cfg.save_path, "point_clouds/")
        metadata_dir = join(self.write_cfg.save_path, "metadata/")
        self._make_dirs([pcd_dir, metadata_dir])

    def get_specification(self) -> FormatSpecification:
        """ Declare PCD format capabilities """
        return FormatSpecification(
            # Data structure
            single_file_per_image=True,
            global_metadata_required=True,
            # Annotation grouping
            aggregation_strategy="per_image",  # Need batch processing for metadata
            # Hooks
            requires_class_declaration=True,
            supports_image_metadata=True,
            # Core geometry types
            requires_bbox=False,  # Using point clouds instead
            requires_polygon=False,
            requires_keypoints=False,
            requires_depth=False,
        )

    def serialize_image_labels(self, transformed: list[dict]) -> Collection[tuple[file_type, extension, str]]:
        """ Serialize transformed annotations to PCD format.

        Each transformed dict contains:
        - shot_idx: image index
        - class_id: numeric class identifier
        - class_name: human-readable class name
        - point_cloud: set of (point_3d, rgb_color) tuples
        - bbox: bounding box (optional)
        - visibility: visibility score (optional)
        """
        pcd_files = []

        for label_dict in transformed:
            shot_idx = label_dict.get('shot_idx')
            point_cloud = label_dict.get('point_cloud')
            class_id = label_dict.get('class_id')
            class_name = label_dict.get('class_name')

            if point_cloud is None:
                continue

            # Register class
            if class_id not in self.class_registry:
                self.class_registry[class_id] = class_name

            # Generate PCD content
            pcd_content = self._generate_pcd_content(point_cloud, class_id, class_name)

            # Store metadata for this annotation
            self.tracked_annotations.append({
                'shot_idx': shot_idx,
                'class_id': class_id,
                'class_name': class_name,
                'point_count': len(point_cloud),
                'visibility': label_dict.get('visibility'),
                'bbox': label_dict.get('bbox'),
            })

            pcd_files.append(('point_cloud', '.pcd', pcd_content))

        return tuple(pcd_files)

    def _generate_pcd_content(self, point_cloud: set, class_id: int, class_name: str) -> str:
        """ Generate PCD file content from point cloud data.

        Point cloud format: set of tuples (point_xyz, rgb_color)
        where point_xyz = (x, y, z) and rgb_color = (r, g, b) [0-255]
        """
        # Header
        point_count = len(point_cloud)
        lines = [
            "# .PCD - Point Cloud Data file format\n",
            f"# Generated from Blender annotation system with Rendersynth\n",
            f"# Class: {class_name} (ID: {class_id})\n",
            "VERSION .7\n", "FIELDS x y z r g b class\n",
            "SIZE 4 4 4 1 1 1 4\n", "TYPE f f f u u u u\n", f"COUNT {point_count}\n",
            f"WIDTH {point_count}\n", "HEIGHT 1\n",
            "VIEWPOINT 0 0 0 1 0 0 0\n", f"POINTS {point_count}\n",
            "DATA ascii\n"
        ]

        # Define fields: x, y, z (position) + r, g, b (color) + class (label)
        # Point data
        for point_data in point_cloud:
            # Handle both unpacked tuples and direct point data
            if isinstance(point_data, tuple) and len(point_data) == 2:
                point_xyz, rgb_color = point_data
            else:
                # Fallback: assume it's a point with embedded color info
                point_xyz = point_data[:3]
                rgb_color = point_data[3:6] if len(point_data) > 3 else (255, 255, 255)

            x, y, z = point_xyz

            # Handle color extraction
            if isinstance(rgb_color, (tuple, list)):
                r, g, b = int(rgb_color[0]), int(rgb_color[1]), int(rgb_color[2])
            else:
                # If single color value (grayscale), replicate
                r = g = b = int(rgb_color)

            # Clamp color values to valid range
            r = max(0, min(255, r)); g = max(0, min(255, g)); b = max(0, min(255, b))

            # Format: x y z r g b class_id
            line = (
                f"{x:.{self.coordinate_precision}f} "
                f"{y:.{self.coordinate_precision}f} "
                f"{z:.{self.coordinate_precision}f} "
                f"{r} {g} {b} {class_id}\n"
            )
            lines.append(line)

        return "".join(lines)

    def signal_begin_shot(self):
        self.cloud_id = 0

    def transform_annotation(
            self,
            label: Label,
            shot_idx: int,
            shot_config: RenderConfig
    ) -> dict[str, Any]:
        """
        Transform canonical Label to PCD-specific format.

        Extract point cloud and color data from the label.
        """
        if label.point_cloud is None:
            return {}

        return {
            'shot_idx': shot_idx,
            'class_id': label.cls.class_id,
            'class_name': label.cls.name,
            'point_cloud': label.point_cloud,
            'visibility': label.visibility,
            'bbox': label.bbox,
            'is_entity': label.is_entity,
        }

    def aggregate_batch(
        self,
        annotations: list[dict[str, Any]],
        batch_metadata: Any
    ) -> dict[str, Any]:
        """
        Aggregate batch annotations.
        Prepare class definitions and global metadata.
        """
        return {
            'annotations': self.tracked_annotations,
            'classes': self.class_registry,
            'batch_metadata': {
                'total_annotations': len(self.tracked_annotations),
                'total_points': sum(ann['point_count'] for ann in self.tracked_annotations),
                'image_prefix': batch_metadata.prefix if hasattr(batch_metadata, 'prefix') else self.write_cfg.prefix,
            }
        }

    def finalize(self, aggregated: dict[str, Any]) -> Collection[tuple[file_type, extension, str]]:
        """
        Finalize output: create metadata and class definition files.
        """
        output_files = []

        # Generate classes.json
        classes_content = json.dumps({
            'classes': [
                {'id': cid, 'name': cname}
                for cid, cname in sorted(self.class_registry.items())
            ],
            'total_classes': len(self.class_registry),
        }, indent=2)
        output_files.append(('classes', '.json', classes_content))

        # Generate annotations.json (metadata mapping)
        annotations_content = json.dumps({
            'annotations': aggregated['annotations'],
            'batch_info': aggregated['batch_metadata'],
            'format': 'PCD',
            'total_annotations': len(aggregated['annotations']),
        }, indent=2, default=str)  # default=str handles non-serializable types
        output_files.append(('annotations', '.json', annotations_content))

        # Generate a README explaining the structure
        output_files.append(('README', '.md', PCDFormatter.README_CONTENT))

        return tuple(output_files)

    def get_storage_spec(self) -> StorageSpec:
        """Declare storage organization"""
        return StorageSpec(single_file_per_image=True)

    def get_subdir_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """ Return subdirectory for file type """
        if f_type == "image":
            return "images/"
        elif f_type == "point_cloud":
            return "point_clouds/"
        elif "README" in f_type or  "metadata" in f_type or "classes" in f_type or "annotations" in f_type:
            return "metadata/"
        else:
            return "data/"

    def get_filename_for(self, shot_id: int, f_type: file_type | Literal["image"]) -> str:
        """ Generate filename for shot and file type """
        prefix = self.write_cfg.prefix

        if f_type == "image":
            return f"{prefix}_{shot_id}"
        elif f_type == "classes":
            return "classes"
        elif f_type == "annotations":
            return "annotations"
        elif f_type == "README":
            return "README"
        else:  # point_cloud
            n = f"{prefix}_{shot_id}_{self.cloud_id}"
            self.cloud_id += 1
            return n

    README_CONTENT = """# Point Cloud Dataset (PCD Format)
    ## Structure
    
    point_clouds/         - Individual .pcd files (one per annotation)
    metadata/
      - classes.json    - Class definitions and mappings
      - annotations.json - Annotation metadata and point cloud references
      - README.md       - This file
    
    ## PCD File Format
    
    Each .pcd file contains point cloud data with the following fields:
    
    - **x, y, z** (float): 3D coordinates in camera space
    - **r, g, b** (uint8): RGB color values (0-255)
    - **class** (uint32): Class ID for semantic labeling
    
    ### Example Header
    
    # .PCD v.7 - Point Cloud Data file format
    VERSION .7
    FIELDS x y z r g b class
    SIZE 4 4 4 1 1 1 4
    TYPE f f f u u u u
    POINTS 1000
    DATA ascii
    
    ## Classes
    
    Classes are defined in classes.json:
    {
      "classes": [
        {"id": 0, "name": "background"},
        {"id": 1, "name": "person"}
      ],
      "total_classes": 2
    }
    
    ## Metadata
    
    Annotation metadata is stored in `annotations.json` with:
    - Point cloud reference
    - Class assignment
    - Visibility scores
    - Bounding box data (if available)
    
    ## Notes
    
    - All coordinates are in camera-centric space (-1 to 1)
    - Colors are pre-extracted from rendered images
    - Each annotation is independent (entities may share points)
    """.replace('    ', '')
    # note: we remove the beginning tabs to avoid an ugly indentation in the README