from .panels import RandomizerPanel, SettingsPanel, InfoPanel
from .pipeline_list_viewer import (RegistrationPanel, AddCameraCategoryPipeMenu, AddLightingCategoryPipeMenu,
                                   AddObjectCategoryPipeMenu, AddMaterialCategoryPipeMenu, AddConstraintCategoryPipeMenu,
                                   PipelineOperationsList, AddExperimentalCategoryPipeMenu)
from .properties import ext_ui_properties, distribution_settings, operation_properties, color_distribution_settings
from .pipe_editor import (DistributionTreeList, PathsUIList, ImagePath, PositionsUIList, ObjectName, TypedNodeProperty,
                          ObjectPosition, MaterialListItem, MaterialUIList, PaletteItem)
from .formatting_config import LabelConfigDataProperty

from .labeling import classes as labeling_classes

from .handlers import sync_distribution_handler
from ..labeling.skeleton_viewport import skeleton_viewport_drawer


import bpy

def register_handlers():
    """Register all scene handlers."""
    bpy.app.handlers.depsgraph_update_post.append(sync_distribution_handler)


def unregister_handlers():
    """Unregister all scene handlers."""
    if sync_distribution_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sync_distribution_handler)

    # A skeleton visualization active at disable-time would otherwise leave
    # its draw handler registered forever, with no way left to remove it. if the extension
    # is the extension is uninstalled mid-visualization, stop visualization
    skeleton_viewport_drawer.stop()


classes = (
    RandomizerPanel, SettingsPanel, InfoPanel, RegistrationPanel, AddCameraCategoryPipeMenu,
    AddLightingCategoryPipeMenu, AddObjectCategoryPipeMenu, PipelineOperationsList, AddExperimentalCategoryPipeMenu,
    AddMaterialCategoryPipeMenu, AddConstraintCategoryPipeMenu, DistributionTreeList, PathsUIList,
    ImagePath, PositionsUIList, ObjectPosition, MaterialListItem, MaterialUIList, ObjectName, TypedNodeProperty,
    LabelConfigDataProperty, PaletteItem
) + labeling_classes

# Update the main UI properties of the pipeline with settings for the configuration of each pipe's distributions
# and properties regarding the pipeline operations
ext_ui_properties.update(operation_properties)
ext_ui_properties.update(distribution_settings)
ext_ui_properties.update(color_distribution_settings)

properties = ext_ui_properties