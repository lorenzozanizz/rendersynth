"""Configuration of UI properties for the Blender randomization pipeline.

Defines property groups used to control the main interface, pipeline operations,
and distribution settings within the addon, using the Blender's property system.

The properties are split into three kinds, ui properties, distribution properties and
operation properties, respectively used for the main UI panel, the distribution settings and
the pipe edit widgets.
"""

import os
from bpy.props import (
    StringProperty, IntProperty, BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, CollectionProperty, PointerProperty
)

from .formatting_config import LabelConfigDataProperty
from .labeling import PoseLabelSettings
from .pipe_editor import ImagePath, ObjectPosition, MaterialListItem, ObjectName, TypedNodeProperty, PaletteItem
from ..distribution.computation import ONE_D_DISTRIBUTIONS, UPPER_D_DISTRIBUTIONS
from ..distribution.color import ColorDistribution
from ..core.io.strategies import SupportedFormats

# UI properties for the main panel, output panel and class panel.
ext_ui_properties = {
    "pipeline_has_unsaved_changes": BoolProperty(default=False),
    "randomizer_pipeline_save_path": StringProperty(
        name="Output path",
        subtype='FILE_PATH',
        description="Path to save JSON config"
    ),
    "randomizer_config_use_file": BoolProperty(name="Use file path", default=True),
    "randomizer_config_path": StringProperty(
        name="Input path",
        subtype='FILE_PATH',
        description="Path to your JSON config"
    ),
    "randomizer_destination_path": StringProperty(
        name="Destination",
        subtype='FILE_PATH',
        description="Save folder destination"
    ),
    "randomizer_append_checkbox": BoolProperty(
        name="Initialize counter to last number",
        default=True,
        description="Start numbering at the last identified number in the destination folder",
    ),
    "randomizer_save_prefix": StringProperty(
        name="Prefix",
        description="File naming prefix for saved images"
    ),
    "randomizer_amount": IntProperty(
        name="Amount",
        description="Number of images to generate",
        min=0,
        default=100
    ),
    "randomizer_seed": IntProperty(
        name="Seed",
        description="Random seed for reproducibility",
        min=0,
        default=0
    ),
    "randomizer_do_labelize": BoolProperty(
        name="Generate labels for renders",
    default=True),
    "randomizer_label_format": EnumProperty(
        name="Format",
        items = lambda self, context: [  # type: ignore
            (formatting.value, formatting.value, f"Use {formatting.value} format.")
            for formatting in SupportedFormats
        ]
    ),
    "randomizer_logging_path": StringProperty(
        name="Log Path",
        subtype='FILE_PATH',
        description="Path where addon logs will be saved",
        default=os.path.expanduser("~/logs/")
    ),
    "randomizer_enable_logging": BoolProperty(
        name="Enable Logging",
        default=False,
        description="Enable Logging"
    )
}

# Properties which are to be used in the UI editor for pipes in the pipeline.
# Note that some properties may be reused for multiple different widgets.
operation_properties = {

    "use_distribution_tree": BoolProperty(
        name="Use advanced Distribution Editor nodes",
        default=False
    ),
    "selected_distribution_index": IntProperty(default=0),
    "distribution_dimension_error": StringProperty(default=""),
    "randomize_x": BoolProperty(default=True),
    "randomize_y": BoolProperty(default=True),
    "randomize_z": BoolProperty(default=True),
    "do_clamp": BoolProperty(
        name="Clamp",
        default=False,
        description="Start numbering at the last identified number in the destination folder"
    ),
    "clamping_factors": FloatVectorProperty(
        name="",
        size=2,
        default=(0.0, 0.0)
    ),
    "do_discretize": BoolProperty(
        name="Discretize values",
        default=False,
        description="Start numbering at the last identified number in the destination folder"
    ),
    "do_offset": BoolProperty(
        name="Offset mode",
        default=True,
        description="Consider the extracted values as offset to the current value."
    ),

    # A small comment on this:
    "simple_distribution_enum_0d": EnumProperty(
        name="Distribution",
        items=[("NONE", "None", "")]
    ),
    "simple_distribution_enum_1d": EnumProperty(
        name="Distribution",
        items= [(dist.name, dist.value.title(), "") for dist in ONE_D_DISTRIBUTIONS]
    ),
    "simple_distribution_enum_2d": EnumProperty(
        name="Distribution",
        items = [(dist.name, dist.value.title(), "") for dist in UPPER_D_DISTRIBUTIONS]
    ),
    "simple_distribution_enum_3d": EnumProperty(
        name="Distribution",
        items= [(dist.name, dist.value.title(), "") for dist in UPPER_D_DISTRIBUTIONS]
    ),
    "k_out_of_n": IntProperty(
        name="Pick k-out-of-N",
        default=1,
        min=1
    ),
    "targeted_objects_display": CollectionProperty(
        name="Targeted Objects",
        type=ObjectName
    ),
    "targeted_node": PointerProperty(
        name="Targeted Node",
        type=TypedNodeProperty
    ),
    "use_folder_mode": BoolProperty(
        name="Use Folder",
        description="Toggle between folder and individual files",
        default=True
    ),
    "image_folder": StringProperty(
        name="Image Folder",
        description="Path to image folder",
        subtype='DIR_PATH'
    ),
    "selected_image_path_index": IntProperty(default=0),
    "image_paths": CollectionProperty(type=ImagePath),
    "selected_position_index": IntProperty(default=0),
    "position_collection": CollectionProperty(type=ObjectPosition),
    "material_list": CollectionProperty(type=MaterialListItem),
    "material_list_index": IntProperty(default=0),

    "reusable_checkbox": BoolProperty(),
    "typed_object": PointerProperty(type=ObjectName),

    "labeling_config": PointerProperty(type=LabelConfigDataProperty),
    "pose_label_settings": PointerProperty(type=PoseLabelSettings)

}

# Properties which are particular to the distribution selection in the
# distribution widget.
distribution_settings = {

    # Scalars
    'dist_min': FloatProperty(name="Minimum", default=0.0),
    'dist_max': FloatProperty(name="Maximum", default=1.0),
    'dist_mean': FloatProperty(name="Mean", default=0.5),
    'dist_std': FloatProperty(name="Standard Dev.", default=0.1),
    'dist_alpha': FloatProperty(name="Alpha", default=2.0, min=0.0),
    'dist_beta': FloatProperty(name="Beta", default=2.0, min=0.0),
    'dist_p': FloatProperty(name="P", description="Probability", default=0.5, max=1.0, min=0.0),
    'dist_n': IntProperty(name="N", default=10, min=0),
    'dist_variance': FloatProperty(name="Variance", default=1.0),

    # Vectors
    # ( we will use the first two entries of the vector for 2d distributions
    'dist_mean_vec': FloatVectorProperty(name="Mean", size=3, default=(0, 0, 0)),
    'dist_min_vec': FloatVectorProperty(name="Minimum Vector", size=3, default=(0, 0, 0)),
    'dist_max_vec': FloatVectorProperty(name="Maximum Vector", size=3, default=(1, 1, 1)),

    # To implement a matrix we may use 2d/3 float vector properties... i dont know
    # if its worth the hassle, for now keep that feature incomplete in this version!
    # 'dist_cov_matrix': ...

}

color_dist_enum = [
    ('NONE', 'None', 'No color distribution'),
    (ColorDistribution.UNIFORM_COLOR.name, ColorDistribution.UNIFORM_COLOR.value, 'Uniform Random RGB'),
    (ColorDistribution.UNIFORM_HSV.name, ColorDistribution.UNIFORM_HSV.value, 'Uniform Random HSV'),
    (ColorDistribution.GAUSSIAN_RGB.name, ColorDistribution.GAUSSIAN_RGB.value, 'Gaussian RGB'),
    (ColorDistribution.PALETTE_SAMPLER.name, ColorDistribution.PALETTE_SAMPLER.value, 'Weighted Palette Sampling'),
]

color_distribution_settings = {
    'color_dist_preset': EnumProperty(
        name="Color Distribution",
        description="Select a color distribution method",
        items=color_dist_enum,
        default='NONE'
    ),
    'color_dist_hsv_sat_min': FloatProperty(
        name="Saturation Min",
        description="Minimum saturation value",
        default=0.5,
        min=0.0,
        max=1.0
    ),
    'color_dist_hsv_sat_max': FloatProperty(
        name="Saturation Max",
        description="Maximum saturation value",
        default=1.0,
        min=0.0,
        max=1.0
    ),
    'color_dist_hsv_val_min': FloatProperty(
        name="Value Min",
        description="Minimum value (brightness)",
        default=0.7,
        min=0.0,
        max=1.0
    ),
    'color_dist_hsv_val_max': FloatProperty(
        name="Value Max",
        description="Maximum value (brightness)",
        default=1.0,
        min=0.0,
        max=1.0
    ),
    'color_dist_base_color': FloatVectorProperty(
        name="Base Color",
        description="Center color for Gaussian distribution",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0)
    ),
    'color_dist_gaussian_variance': FloatProperty(
        name="Variance",
        description="Standard deviation for Gaussian distribution",
        default=0.1,
        min=0.0,
        soft_max=1.0
    ),
    'color_dist_palette_items': CollectionProperty(
        type=PaletteItem,
        name="Palette Colors",
        description="Colors and weights for palette-based sampling"
    ),
    'color_dist_palette_index': IntProperty(
        name="Palette Index",
        description="Active palette item index",
        min=0,
        default=0
    )
}