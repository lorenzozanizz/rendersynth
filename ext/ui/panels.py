from .formatting_config import LabelConfigDrawer
from ..operators.names import Labels
from ..constants import *

from bpy.types import Panel

class RandomizerPanel(Panel):
    """ The main panel for the randomizer class, containing the hooks for the
    configuration file, the saving file, the amount of samples, the seed for the
    random generators, the prefix to the save files, the label save format
    """

    bl_label = MAIN_PANEL_NAME
    bl_category = PANEL_CATEGORY
    bl_idname = panel_conflict_rename("random_dataset")
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 0

    def draw(self, context):
        """

        """

        layout = self.layout
        scene = context.scene

        layout.prop(scene, "randomizer_destination_path")
        layout.prop(scene, "randomizer_save_prefix")

        layout.separator()  # Adds vertical space
        row = layout.row()
        row.label(text="Amount:")
        row.prop(scene, "randomizer_amount", text="")
        row = layout.row()
        row.label(text="Seed:")
        row.prop(scene, "randomizer_seed", text="")

        layout.separator()  # Adds vertical space
        layout.prop(scene, "randomizer_do_labelize")
        layout.prop(scene, "randomizer_label_format")

        # Now render the labeling properties, different for each format.
        LabelConfigDrawer.draw(context, layout, scene.randomizer_label_format)

        layout.prop(scene, "randomizer_append_checkbox")

        layout.separator()  # Adds vertical space
        row = layout.row()
        row.operator(Labels.GENERATE.value, text="Generate", icon="TRIA_RIGHT")
        row.operator(Labels.PREVIEW_SAMPLE.value, text="", icon="HIDE_OFF")

    def extract_data(self, context) -> dict:
        return { }


class SettingsPanel(Panel):
    """ The main panel for the randomizer class, containing the hooks for the
    configuration file, the saving file, the amount of samples, the seed for the
    random generators, the prefix to the save files, the label save format
    """

    bl_label = "Settings"
    bl_category = PANEL_CATEGORY
    bl_idname = panel_conflict_rename("random_settings")
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = { 'DEFAULT_CLOSED' }

    bl_order = 3

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # Title
        row = layout.row(align=True)
        row.label(text="Logging", icon='GREASEPENCIL')

        row.prop(scene, "randomizer_enable_logging")

        box = layout.box()
        box.enabled = scene.randomizer_enable_logging
        box.prop(scene, "randomizer_logging_path")
        row = box.row(align=True)

        row.operator(Labels.OPEN_LOG_DIRECTORY.value, text="Open logs", icon="KEY_MENU")
        row.operator(Labels.SETUP_LOGGER_DIR.value, text="Save path", icon="FILE_TICK")
        layout.separator()


class InfoPanel(Panel):
    """ The panel containing information regarding the extension, its version,
    the version it was developed for, a link to the original repository and
    the documentation.
    """

    bl_label = "Info"
    bl_idname = panel_conflict_rename("random_info")
    bl_category = PANEL_CATEGORY
    bl_options = { 'DEFAULT_CLOSED' }
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_order = 4

    def draw(self, _context):
        layout = self.layout

        # Title
        col = layout.column(align=True)
        col.label(text=MAIN_PANEL_NAME, icon='INFO')
        col.separator()

        # Version Info
        col.label(text=f"Version: {VERSION}")
        col.label(text=f"Tested on Blender {TARGET_VERSION}")
        col.separator()

        # Links section
        col = layout.column(align=True)
        col.label(text="Links:")

        row = col.row()
        op = row.operator(Labels.OPEN_URL.value, text="GitHub", icon='URL')
        op.url = REPO_URL
        op = row.operator(Labels.OPEN_URL.value, text="Documentation", icon='FILE_FOLDER')
        op.url = DOCU_URL
