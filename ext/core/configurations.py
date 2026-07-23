from dataclasses import dataclass
from typing import Literal, Any


@dataclass
class GenerationConfig:
    """ Set of configurations used to control the generation process. """
    # python's "random" is seeded with this value for reproducibility.
    seed: int
    amount: int


@dataclass
class BatchMetadata:
    """Context about the full batch being written"""

    num_images: int
    classes: list[Any]


@dataclass
class LabelExtractionConfig:
    """ Set of configurations used to control the way labels are extracted, from their format
     to whether they are written to memory using the writing configurations. """

    format: str
    format_cfg: dict
    write_labels: bool

    # The precision of ray casting: a sample is selected every width * ratio pixels, height * ratio pixels
    ray_casting_ratio: float = 0.1
    # If enabled, the extraction engine will also attempt to compute the estimated visibility:
    # what this means depends on the type of geometry extracted!
    estimate_visibility: bool = True


@dataclass
class WritingConfig:
    """ Set of configuration used to control the way the files are written,
    from the write directory to the prefix to the subdirectory split.
    """
    from_last: bool
    save_path: str
    prefix: str
    folder_structure: Literal["yolo"] = "yolo"
    image_extension: str = ".png"
    split: str = "train"
    # Zero pad the shot idx to fit the entire batch amount
    zero_pad: bool = True

@dataclass
class PreviewRenderConfig:
    """ A separate set of configurations options which only targe the rendered
    preview window and not the execution of the orchestrator pipeline (i.e. this
    only influences the way the preview is rendered) """

    show_visibility: bool = True
    show_obj_name: bool = True

    show_geometry: bool = True
    show_class_name_or_id: Literal["id", "none", "name"] = "id"

    show_timings: bool = True
    # If the default class is applied to a large number of objects, the user may
    # wish to disable it.
    ignore_default_class: bool = True

    # Point cloud labels can carry far more points than are useful to plot in a
    # preview; this caps how many are drawn (random-subsampled) per label.
    max_preview_points: int = 2000

@dataclass
class RenderConfig:
    """ Render configuration extracted from Blender's render config at generation time.
    These are used to map camera-centered coordinates to pixel coordinates for certain
    labeling strategies and to handle the preview.
    """
    width: int
    height: int
    # Taken from the blender render settings for the current scene.
    image_ext: str

    # The blender camera object which captured the scene. May be selected dynamically
    # in some way.
    camera: Any