"""User interface panels and lists for managing the pipeline editor in Blender GUI.

Defines UI components for displaying, editing, and organizing pipeline operations,
including panels, lists, and categorized menus for adding new operations in the pipeline editor.

Classes:
    RegistrationPanel: Main panel for viewing and editing the pipeline.
    PipelineOperationsList: UI list for displaying pipeline operations.
    AddObjectCategoryPipeMenu: Menu for adding object-related operations.
    AddCameraCategoryPipeMenu: Menu for adding camera-related operations.
    AddMaterialCategoryPipeMenu: Menu for adding material-related operations.
    AddLightingCategoryPipeMenu: Placeholder menu for lighting operations.
    AddConstraintCategoryPipeMenu: Placeholder menu for constraint operations.

"""
from .pipe_editor import OperationDrawerRegistry

from ..operators.names import Labels
from ..constants import PipeNames
from ..constants import PANEL_CATEGORY, panel_conflict_rename
from ..utils.logger import UniqueLogger

from bpy.types import Panel, UIList, Menu
from bpy.props import StringProperty, EnumProperty


# Reference to the blender default icons:
# Attempt to use each icon only once to avoid inconsistency in the list
# visuals.
pipe_to_ico_mapping = {

    PipeNames.SCALE: "CON_SIZELIKE",
    PipeNames.ROTATION: "CON_ROTLIKE",
    PipeNames.POSITION: "EMPTY_ARROWS",
    PipeNames.VISIBILITY: "MOD_OPACITY",
    PipeNames.MOVE: "EMPTY_AXIS",

    PipeNames.MATERIAL: "MATERIAL",
    PipeNames.TEXTURE: "NODE_TEXTURE",
    PipeNames.ROUGHNESS: "VPAINT_HLT",
    PipeNames.METALLIC: "TPAINT_HLT",
    PipeNames.NODE_PROP: "CURSOR",

    PipeNames.INTENSITY: "FORCE_TURBULENCE",
    PipeNames.LINE: "IPO_BACK",
    PipeNames.BASE_COLOR: "COLOR",

    PipeNames.FOCAL_LEN: "CAMERA_STEREO",
    PipeNames.BEZIER_LOCK: "IPO_BACK",
    PipeNames.SPHERE_LOCK: "MATSPHERE"

}

class RegistrationPanel(Panel):
    """ The panel containing information regarding the registrations of new sampling
    operations (to be determined)
    """

    bl_label = "Pipeline Editor"
    bl_idname = panel_conflict_rename("random_operator_registration")
    bl_options = { 'DEFAULT_CLOSED' }
    bl_space_type = 'VIEW_3D'
    bl_category = PANEL_CATEGORY
    bl_region_type = 'UI'
    bl_order = 1


    def draw(self, context):
        """

        :param context:
        :return:
        """
        # Currently Empty
        layout = self.layout
        # === TAB BAR ===
        row = layout.row()
        active = context.window_manager.get('pipeline_tab', 'ops')

        for tab_id, tab_label in [('ops', 'View Pipeline'), ('config', 'Edit Current')]:
            row.operator(Labels.CHANGE_VIEW_TAB_BUTTON_.value,
                         text=tab_label,
                         depress=(tab_id == active),
                         emboss=True).tab = tab_id

        layout.separator()
        scene = context.scene
        pipeline = scene.pipeline_data


        # === COLLECTION PROPERTIES - Use .add() ===
        # Add a new operation to the list

        # Which view are we in?
        if active == 'ops':
            self.draw_list_view(context, pipeline)
        elif active == 'config':
            self.draw_edit_view(context, pipeline)


    def draw_list_view(self, context, pipeline):
        """Show list of operations with +/- buttons"""
        layout = self.layout

        # Load/Save buttons
        layout.label(text=f"Pipeline length: {len(pipeline.operations)} operation"
                          f"{'' if len(pipeline.operations) == 1 else 's'}")

        layout.separator()
        # Create column header row.
        row = layout.row()
        list_col = row.column(align=True)

        legend = list_col.row(align=True)  # ensure same number of columns
        for lab in ("#", "Operation", "Name", "Enabled"):
            legend.label(text=lab)
        legend.enabled = False

        list_col.template_list(
            PipelineOperationsList.__name__,  # UIList class name
            'pipeline_operations',  # Unique ID
            pipeline,  # Data object
            'operations',  # Collection property name
            pipeline,  # Active data object
            'active_operation_index'  # Active index property name
        )

        col = row.column(align=True)
        col.operator(Labels.ADD_MENU_LIST_.value, icon='ADD', text='')
        col.operator(Labels.REMOVE_PIPE.value, icon='REMOVE', text='')
        col.separator()

        col.operator(Labels.INTO_FOLDER.value, icon="FOLDER_REDIRECT", text='')
        col.operator(Labels.PIPE_UP_OPERATION_.value, icon='BACK', text='')
        col.operator(Labels.PIPE_DOWN_OPERATION_.value, icon='FORWARD', text='')

        col.separator()

        col.operator(Labels.SCAN_PIPELINE.value, icon='FILE_REFRESH', text='')
        layout.separator()

        # === SAVE SECTION ===

        scene = context.scene

        main_row = layout.row(align=True)

        box = main_row.box()
        box.label(text="Load pipeline", icon="WORDWRAP_OFF")
        row = box.row(align=True)
        row.prop(scene, "randomizer_config_path", text="")
        row.operator(Labels.LOAD_PIPELINE_JSON.value, text="Load", icon="FILE")

        box = main_row.box()
        box.label(text='Save Pipeline', icon='FILE_TICK')
        row = box.row(align=True)
        row.prop(scene, "randomizer_pipeline_save_path", text="")
        row.operator(Labels.SAVE_PIPELINE_JSON.value, text="Save", icon="FILE_TICK")


    def draw_edit_view(self, context, pipeline):
        """Show detailed editor for selected operation"""
        layout = self.layout

        if not pipeline.operations:
            layout.label(text='There are no operations.')
            return

        op_index = pipeline.active_operation_index
        operation = pipeline.operations[op_index]

        # Header
        layout.label(text=f"Editing: {operation.operation_type}", icon='PREFERENCES')
        layout.separator()

        UniqueLogger.quick_log(str(operation.operation_type))
        reg_op = OperationDrawerRegistry.get(operation.operation_type)

        # setup_schema = PipeSchemaRegistry.get(str(operation.operation_type))
        # setup_schema.apply_config_to_ui(context, operation, { })

        # Draw the editor, having first set up the correct UI value with the schema and the
        # currently serialized data.
        if reg_op:
            reg_op.draw_editor(layout, context)

        layout.separator()
        # The save operator for a single pipe will return to the list view menu.
        layout.operator(Labels.SAVE_PIPE.value, text="Save").on_save_return = 'ops'


    def draw_filter(self, _context, layout):
        """Draw the filter options and search bar"""
        row = layout.row()

        # Search text input (automatic)
        row.prop(self, "filter_name", text="")

        # Filter by operation type (optional)
        row = layout.row(align=True)
        row.prop(self, "filter_operation_type", expand=True)

    def filter_items(self, _context, data, name):
        """Filter and sort items based on search"""
        items = getattr(data, name)

        # Create filter list (1 = show, 0 = hide)
        flt_flags = [self.bitflag_filter_item] * len(items)
        flt_neworder = list(range(len(items)))

        # Filter by search name
        if self.filter_name:
            for idx, item in enumerate(items):
                if self.filter_name.lower() not in item.operation_type.lower():
                    flt_flags[idx] = 0

        return flt_flags, flt_neworder

    # Add filter properties
    filter_name: StringProperty(default="", options={'TEXTSEARCH'}) # type: ignore
    filter_operation_type: EnumProperty( # type: ignore
        items=[
            ('ALL', 'All', 'Show all'),
            ('RANDOMIZE', 'Randomize', 'Show randomize ops'),
        ],
        default='ALL'
    )


class PipelineOperationsList(UIList):

    def draw_item(self, _context, layout, _data, item, _icon, _active_data, _active_propname, index):

        operation = item
        op_type = operation.operation_type
        if op_type.lower() == "folder":
            self.draw_folder(_context, layout, _data, item, _icon, _active_data, _active_propname, index)
        else:
            self.draw_pipe(_context, layout, _data, item, _icon, _active_data, _active_propname, index)

    def draw_pipe(self, _context, layout, _data, item, _icon, _active_data, _active_propname, index):

        op_type = item.operation_type
        # Left side: icon + operation name
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.scale_x = 0.3  # Make it tiny
        sub.label(text=f"{index + 1}")

        type_enum = next(en for en in PipeNames if en.value == op_type)
        row.label(text=op_type, icon=pipe_to_ico_mapping[type_enum])

        # Middle: show some property
        row.prop(item, "name", text="", emboss=False)
        row.prop(item, 'enabled', text='')
        # Right side: edit button
        # (NOTE: This should not be here for a folder special pipe, instead there should be a special
        # "open" button)
        row.operator(Labels.EDIT_PIPE.value, text='', icon='GREASEPENCIL').op_index = index

        if not item.valid:
            row.label(text="", icon="WARNING_LARGE")


    def draw_folder(self, _context, layout, data, item, _icon, _active_data, _active_propname, index):

        row = layout.row(align=True)
        row.operator(Labels.OPEN_FOLDER.value, icon="RIGHTARROW", text='')
        row.label(text="└ Folder")



# Submenu for lighting operations
class AddLightingCategoryPipeMenu(Menu):
    """ Menu category for lighting operations """

    bl_label = 'Lighting'
    bl_idname = 'AddLightingCategoryPipeMenu'

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        layout.label(text='Lighting')


# Submenu for constraint operations
class AddConstraintCategoryPipeMenu(Menu):
    """ Menu category for constraints operations """

    bl_label = 'Constraints'
    bl_idname = 'AddConstraintCategoryPipeMenu'

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        layout.label(text='Constraints')


# Submenu for object operations
class AddObjectCategoryPipeMenu(Menu):
    """ Menu category for operations involving objects"""

    bl_label = 'Object'
    bl_idname = 'AddObjectCategoryPipeMenu'

    def draw(self, context):
        layout = self.layout
        for name in (
            PipeNames.ROTATION, PipeNames.MOVE, PipeNames.POSITION, PipeNames.SCALE, PipeNames.VISIBILITY,
            PipeNames.LINE
        ):
            layout.operator(Labels.ADD_PIPE.value, text=name.value,
                            icon=pipe_to_ico_mapping[name]).op_name = name.value

# Submenu for camera operations
class AddCameraCategoryPipeMenu(Menu):
    """ Menu category for camera operations """

    bl_label = 'Camera'
    bl_idname = 'AddCameraCategoryPipeMenu'

    def draw(self, context):
        layout = self.layout

        for name in (
            PipeNames.BEZIER_LOCK, PipeNames.SPHERE_LOCK, PipeNames.FOCAL_LEN, PipeNames.JITTER, PipeNames.DISTANCE,
            PipeNames.POV
        ):
            layout.operator(Labels.ADD_PIPE.value, text=name.value,
                            icon=pipe_to_ico_mapping[name]).op_name = name.value

# Submenu for material operations
class AddMaterialCategoryPipeMenu(Menu):
    """ Menu category for material operations """

    bl_label = 'Material'
    bl_idname = 'AddMaterialCategoryPipeMenu'

    def draw(self, context):
        layout = self.layout
        for name in (
            PipeNames.MATERIAL, PipeNames.TEXTURE, PipeNames.METALLIC, PipeNames.ROUGHNESS,
            PipeNames.INTENSITY, PipeNames.NODE_PROP, PipeNames.BASE_COLOR
        ):
            layout.operator(Labels.ADD_PIPE.value, text=name.value,
                            icon=pipe_to_ico_mapping[name]).op_name = name.value

class AddExperimentalCategoryPipeMenu(Menu):
    """ Menu category for experimental/unstable operations """

    bl_label = 'Experimental'
    bl_idname = 'AddExperimentalCategoryPipeMenu'

    def draw(self, context):
        layout = self.layout

