"""
A file containing all the labels assigned to all operations inside the extension.
Note that the labels are divided by class and file, as to find them easily.

The labels are used around the other folders to avoid spreading "magic strings" and
to prevent dead-link operators which Blender cannot render and have no effect.

When a class requires to draw the corresponding property operator, it can access the
label as Labels.NAME.value

Operation labels which are terminated with _ are internal operations which are more likely
related to auxiliary GUI (e.g. menu drawing, etc...) although the distinction is
admittedly somewhat fuzzy

"""

from enum import Enum

class Labels(Enum):
    """ This class contains label for all operators used for all actions inside the
    extensions. To access an operator's use Labels.NAME.value
    """

    # ------------- Names inside core_ops.py ---------------
    # |
    # ( Generate a batch of data )
    GENERATE                = "randomizer.generate"
    # ( Preview a sample from the generated distribution [unseeded] )
    PREVIEW_SAMPLE          = "randomizer.preview"


    # ------------- Names inside pipeline_ops.py ---------------
    # |
    # ( Captures a general node form the shader material node-editor )
    CAPTURE_GENERAL_NODE    = "randomizer.capture_general_node"
    # ( Captures a value node form the shader material node-editor )
    CAPTURE_VALUE_NODE      = "randomizer.capture_value"
    # ( Remove a material from the sampling pool of the Material pipe )
    REMOVE_MATERIAL_POOL    = "randomizer.remove_material_from_list"
    # ( Add a material to the sampling pool of the Material pipe )
    ADD_MATERIAL_POOL       = "randomizer.add_material_to_list"
    # ( Add a position to the pool of sampled positions for the Move pipe )
    REMOVE_POSITION_POOL    = "randomizer.remove_position"
    # ( Remove a position from the pool of sampled positions for the Move pipe )
    ADD_POSITION_POOL       = "randomizer.add_position"
    # ( Capture the current position of an object (does not handle multiple objects) )
    CAPTURE_OBJ_POSITION    = "randomizer.capture_obj_position"
    # ( Capture the currently selected Image Texture shader node-editor node )
    CAPTURE_TEXTURE_NODE    = "randomizer.capture_texture"
    # ( Capture the currently selected objects, either a single one or a group )
    CAPTURE_OBJECTS         = "randomizer.capture_objects"
    # ( Capture a node of a given shader node type )
    CAPTURE_TYPED_NODE      = "randomizer.capture_typed_node"
    # ( Capture a single object of the given object type )
    TYPED_SINGLE_OBJ_CAPT   = "randomizer.typed_single_obj_capture"
    # ( Select the position of the cursor )
    ADD_CURSOR_POS          = "randomizer.select_cursor"
    # ( Edit the currently selected operation )
    EDIT_PIPE               = "randomizer.edit_operation"
    # ( Remove the currently selected operation )
    REMOVE_PIPE             = "randomizer.remove_operation"
    # ( Add a new pipe (operation) to the pipeline )
    ADD_PIPE                = "randomizer.add_operation"
    # ( Save the pipe currently being edited )
    SAVE_PIPE               = "randomizer.save_pipe"
    # ( An auxiliary operation used to draw the add menus (which represent possible pipes)  )
    ADD_MENU_LIST_          = "randomizer.add_operation_menu"
    # ( An operation which scans for the validity of all pipes in the pipeline. )
    SCAN_PIPELINE           = "randomizer.scan_pipeline"
    # ( Put an operation into a folder at the last place )
    INTO_FOLDER             = "randomizer.into_folder"
    # ( View the stored target objects, selecting them in the scene )
    VIEW_TARGET_SELECTED    = "randomizer.view_target_selected"

    # ------------- Names inside io_ops.py ---------------
    # |
    # ( Setup the logger directory and create the log file )
    SETUP_LOGGER_DIR        = "randomizer.setup_log"
    # ( Save a pipeline inside a JSON file as a human-readable dictionary )
    SAVE_PIPELINE_JSON      = "randomizer.save_pipeline"
    # ( Load a pipeline from a JSON file as inner pipe representation )
    LOAD_PIPELINE_JSON      = "randomizer.load_pipeline"
    # ( Open the log file directory using operative system utils. A bit messy on w11 noteblock )
    OPEN_LOG_DIRECTORY      = "randomizer.open_log_file"

    # ------------- Names inside graphical_ops.py ---------------
    # |
    # ( Add a special folder pipe which acts as a container of sub-pipes for neatness )
    ADD_FOLDER_MENU         = "randomizer.add_folder"
    # ( Open a folder in the pipeline viewer, visualizing the sub pipes )
    OPEN_FOLDER             = "randomizer.open_folder"
    # ( Set the current tab for the pipeline editor, e.g. list vs. edit pipe )
    CHANGE_VIEW_TAB_BUTTON_ = "randomizer.set_pipeline_tab"
    # ( Move a pipe down in the pipeline )
    PIPE_DOWN_OPERATION_    = "randomizer.down_operation"
    # ( Move the pipe up in the pipeline )
    PIPE_UP_OPERATION_      = "randomizer.up_operation"
    # ( Open the editor for the selected distribution in another workflow sidebar)
    OPEN_DISTRI_EDITOR      = "randomizer.open_distribution_editor"
    # ( Switch the labeling section [UI operation] )
    SWITCH_LABEL_SECTION    = "randomizer.switch_label_section"

    # ------------- Names inside labeling_ops.py ---------------
    # |
    # ( Add a new class to the available labels )
    ADD_LABEL_CLASS         = "randomizer.add_label_class"
    # ( Remove a class from the available labels )
    REMOVE_LABEL_CLASS      = "randomizer.remove_label_class"
    # ( Assign a label to an object )
    ADD_OBJECT_LABEL        = "randomizer.add_object_label"
    # ( Remove a label from an object )
    REMOVE_OBJECT_LABEL     = "randomizer.remove_object_label"
    # ( Add a labeling rule )
    ADD_LABEL_RULE          = "randomizer.add_label_rule"
    # ( Remove a labeling rule )
    REMOVE_LABEL_RULE       = "randomizer.remove_label_rule"
    # ( Capture the currently selected objects to be applied to the selected label assignment )
    CAPTURE_OBJECTS_LABEL   = "randomizer.capture_objects_label"
    # ( Capture the objects for the entity )
    CAPTURE_OBJECTS_ENTITY  = "randomizer.capture_objects_entity"
    # ( Let a label correspond to a multi-object entity )
    SELECT_ENTITY_LABEL     = "randomizer.select_entity_label"
    # ( Refresh the names assigned to labels in the pipeline, highlighting dead objects )
    REFRESH_LABEL_SETTINGS  = "randomizer.refresh_label_settings"
    # ( Add a multi-object entity )
    ADD_ENTITY              = "randomizer.add_entity"
    # ( Remove a multi-object entity )
    REMOVE_ENTITY           = "randomizer.remove_entity"

    # ------------- Names inside distribution_ops.py ---------------
    # |
    # ( Remove a target image path from the randomization pool )
    REMOVE_IMAGE_PATH_POOL  = "randomizer.remove_image_path"
    # ( Add a target image path to the randomization pool )
    ADD_IMAGE_PATH_POOL     = "randomizer.add_image_path"
    # ( Remove a distribution from the distribution selector list )
    REMOVE_DISTRIBUTION     = "randomizer.remove_distribution"
    # ( Add a distribution to the distribution selector list )
    ADD_DISTRIBUTION        = "randomizer.add_distribution"
    # ( Add a new color to the random palette )
    ADD_PALETTE_ITEM        = "randomizer.add_palette_item"
    # ( Remove a color from the random palette)
    REMOVE_PALETTE_ITEM     = "randomizer.remove_palette_item"
    # ( Add a gradient item to the random spectrum of colors )
    ADD_GRADIENT_ITEM       = "randomizer.add_gradient_item"
    # ( Remove a gradient item to teh random spectrum of colors )
    REMOVE_GRADIENT_ITEM    = "randomizer.remove_gradient_item"

    # ------------- Names inside distribution_ops.py ---------------
    # |
    # ( )
    VISUALIZE_SKELETON      = "randomizer.visualize_skeleton"
    #
    STOP_VISUALIZE_SKELETON = "randomizer.stop_skeleton"
    #
    ADD_RIG                 = "randomizer.add_rig"

    REMOVE_RIG              = "randomizer.remove_rig"

    ADD_CONNECTION          = "randomizer.add_connection"

    REMOVE_CONNECTION       = "randomizer.remove_connection"

    DETECT_BONES            = "randomizer.detect_bones"

    ADD_KEYPOINT            = "randomizer.add_keypoint"

    REMOVE_KEYPOINT         = "randomizer.remove_keypoint"

    # ------------- Default namespace names ---------------
    # |
    # ( Default operator to open a URL.  )
    OPEN_URL                = "wm.url_open"
