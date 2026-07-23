""" Rendersynth, an extension for Blender

This addon generates synthetic datasets by applying randomized
transformations to objects in the scene and rendering multiple images.
The purpose is to synthetically generate computer visions dataset for various
tasks.

Features:
- Load configuration from JSON
- Generation oF JSON configuration directly from the extensions in Blender
- Randomize object position, rotation, and material textures, visibility
- Batch render images automatically
- Export datasets for computer vision pipelines (YOLO)


GitHub: https://github.com/lorenzozanizz/rendersynth
Documentation: https://lorenzozanizz.github.io/rendersynth/


Version: 1.0.0
Blender: 4.x
License: MIT
"""

bl_info = {
    "name": "Rendersynth",
    "author": "lorenzozanizz",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "Sidebar > Randomizer",
    "description": "Load a JSON config randomize objects render N images",
    "category": "Render",
}

import sys

# When testing we must not import all classes, because some ui classes are not stubbed and
# at test time bpy is not present. We prevent registration by checking that our test library
# was not imported.
if 'pytest' not in sys.modules:

    from .constants import NODE_CATEGORIES_NAME

    from .ui import classes as ui_classes
    from .operators import operators as ops_classes
    from .distribution import classes as dist_classes
    from .distribution import node_categories
    from .pipeline import classes as pipe_classes
    from .labeling import classes as labeling_classes

    from .labeling import properties as labeling_properties
    from .pipeline import properties as pipeline_properties
    from .ui import register_handlers, unregister_handlers
    from .ui import properties as ui_properties

    from .utils.logger import UniqueLogger

    import bpy
    from nodeitems_utils import register_node_categories, unregister_node_categories

    registration_classes = (
        *pipe_classes,
        *dist_classes,
        *ops_classes,
        *ui_classes,
        *labeling_classes
    )

    # Construct a dictionary with all properties declarations across all modules
    properties = {}
    for properties_set in (ui_properties, pipeline_properties, labeling_properties):
        properties.update(properties_set)


def register():
    """ Register the classes and properties for the GUI extension
    """
    # Register all the required classes
    for cls in registration_classes:
        bpy.utils.register_class(cls)

    # Define all the attributes for the GUI
    for prop_name, prop_value in properties.items():
        setattr(bpy.types.Scene, prop_name, prop_value)

    register_node_categories(NODE_CATEGORIES_NAME, node_categories)
    register_handlers()

def unregister():
    """ Unregister the classes and properties for the GUI extension
    """

    unregister_node_categories(NODE_CATEGORIES_NAME)

    # Delete all registered properties in the environment
    for prop in properties:
        delattr(bpy.types.Scene, prop)

    # Unregister all previously registered classes
    for cls in reversed(registration_classes):
        bpy.utils.unregister_class(cls)

    UniqueLogger.cleanup()
    unregister_handlers()

def uninstall():
    print("Uninstalling extension...")
