""" Module containing several constants definitions that are used throughout the code,
including pipe names and serialization constants.

The module contains the extension version, the urls of the repositories used in the
extension info panel, the names of the extension panels and the blender target version,
the names of the pipes used to register them to the various registries in the code for UI
and functionality, and names used in the serialization and deserialization of pipes.
"""

from enum import Enum

def panel_conflict_rename(name: str) -> str:
    """ Get the prefix to name the registered panels of the blender extension """
    return "VIEW3D_PT_" + name

# Names of the main panel and the category name
MAIN_PANEL_NAME = "Generator"
PANEL_CATEGORY  = "Rendersynth"

REPO_URL = "https://github.com/lorenzozanizz/rendersynth"
DOCU_URL = "https://lorenzozanizz.github.io/rendersynth/"

VERSION        = "1.0.0"
TARGET_VERSION = "4.5.0"

# Names of the internal distribution tree for arbitrary distributions
NODE_CATEGORIES_NAME = "DISTRIBUTION_NODE_CATEGORIES"
DISTRO_EDITOR_NAME   = "DistributionNodeTree"


class PipeNames(Enum):
    """ A class containing the key used to register all the pipes to all the registries
    in the code including UI, validation and operation.

    To access a key one writes PipeNames.NAME.value
    """

    # Special type of pipe which encloses a set of sub pipes.
    FOLDER      = "Folder"

    SCALE       = "Scale"
    ROTATION    = "Rotation"
    MOVE        = "Move"
    POSITION    = "Position"
    VISIBILITY  = "Visibility"
    LINE        = "Line"
    SELECT      = "Select"
    SPHERICAL   = "Sphere"          # (x)
    SCATTER     = "Scatter"         # (x)

    # Material
    MATERIAL    = "Material"
    TEXTURE     = "Texture"
    INTENSITY   = "Intensity"
    METALLIC    = "Metallic"
    ROUGHNESS   = "Roughness"
    NODE_PROP   = "Node Property"   # (x)
    BASE_COLOR  = "Base Color"      # (x)

    # Lighting
    TEMPERATURE = "Temperature"     # (x)
    POWER       = "Power"
    COLOR       = "Color"

    # Camera
    BEZIER_LOCK = "Bezier Lock"
    SPHERE_LOCK = "Sphere Lock"
    FOCAL_LEN   = "Focal Length"
    JITTER      = "Camera Jitter"   # (x)
    POV         = "Change POVs"     # (x)

    # Constraints
    OVERLAP     = "Overlap"         # (x)
    OCCLUSION   = "Occlusion"       # (x)
    DISTANCE    = "Distance"        # (x)
    BOUND       = "Bound"           # (x)
    GROUND      = "Ground"          # (x)

    # Noise
    MOTION_BLUR = "Motion Blur"     # (x)


class WidgetSerializationKeys(Enum):
    """ Keys that are used to serialize and deserialize the pipes in various
    stages of the code. This is done to use blender's property system to
    save the settings of a pipeline inside a .blend file.

    Using the enum keys instead of the strings helps prevent dangling references.
    """

    # Meta-name used for conditional widgets.
    ENABLED                     = "enabled"         # ^ Parent name

    TYPED_OBJ                   = "typed_obj"       # ^ Parent name
    TYPED_OBJ_NAME              = "name"

    BEZIER                      = "bezier"          # ^ Parent name
    BEZIER_NAME                 = "name"

    DIMENSION                   = "dimension"       # ^ Parent name

    SELECT                      = "select"          # ^ Parent name
    SELECT_K                    = "k"

    MATERIAL                    = "materials"       # ^ Parent name
    MATERIAL_LIST               = "materials"

    # Incomplete, a bit messy for now!
    PROPERTY = ""

    SHADER_NODE                 = "shader_node"     # ^ Parent name
    SHADER_MATERIAL             = "shader_mat"
    SHADER_LABEL                = "label"

    VALUE                       = "value"           # ^ Parent name
    VALUE_MATERIAL              = "material"
    VALUE_LABEL                 = "label"

    POSITION                    = "positions"       # ^ Parent name
    POSITION_LIST               = "positions"

    SIMPLE                      = "distribution"    # ^ Parent name
    SIMPLE_PRESET_NAME          = "preset"
    SIMPLE_OFFSET_MODE          = "do_offset"
    SIMPLE_DISCRETIZE           = "do_discretize"
    SIMPLE_CLAMP                = "do_clamp"
    SIMPLE_CLAMPING_EXTREMES    = "clamping_factors"
    SIMPLE_PARAMETERS           = "parameters"

    NODE                        = "distribution"    # ^ Parent name
    NODE_USE_TREE               = "use_tree"
    NODE_DISTRIBUTION           = "distribution"

    PATH                        = "textures"        # ^ Parent name
    PATH_USE_FOLDER             = "use_folder"
    PATH_FILES                  = "files"
    PATH_FOLDER                 = "folder"

    TEXTURE                     = "node"            # ^ Parent name
    TEXTURE_MATERIAL            = "material"
    TEXTURE_LABEL               = "label"

    OBJECT                      = "target"          # ^ Parent name
    OBJECT_NAMES                = "names"

    AXIS                        = "axis"            # ^ Parent name
    AXIS_DIMS                   = "dims"
    AXIS_RANDOMIZE_PREFIX_X     = "randomize_x"
    AXIS_RANDOMIZE_PREFIX_Y     = "randomize_y"
    AXIS_RANDOMIZE_PREFIX_Z     = "randomize_z"

    OFFSET                      = "offset"          # ^ Parent name
    OFFSET_MODE                 = "mode"


class StageDescriptions(Enum):

    ROTATION = """ Randomly rotate an object in 3d space.
    The rotation is applied to the Euler rotate of the target object(s). """


