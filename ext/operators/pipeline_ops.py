from .names import Labels

from ..pipeline.integrity import PipelineScanner, ValidatorRegistry
from ..utils.logger import UniqueLogger
from ..ui.pipe_schema import PipeSchemaRegistry, PipeSchema

from bpy.types import Operator
from bpy.props import IntProperty, StringProperty
import bpy

from typing import Union, Optional
from json import dumps, loads

class PipeAddOperator(Operator):

    bl_idname = Labels.ADD_PIPE.value
    bl_label = "Add a new pipe to the pipeline"

    op_name: StringProperty(default="Nothing")  # type: ignore

    def execute(self, context):
        pipeline = context.scene.pipeline_data
        new_op = pipeline.operations.add()
        new_pipe_order = pipeline.get_last_operation_order()

        # Currently selected pipe is INSIDE a folder? If it is, we add to the folder instead.
        scene = context.scene

        # Set the order of the new pipe in the list.
        new_op.order = new_pipe_order
        new_op.operation_type = self.op_name
        new_op.enabled = True
        return { 'FINISHED' }


class PipeRemoveOperator(Operator):

    bl_idname = Labels.REMOVE_PIPE.value
    bl_label = "Select Node"

    def execute(self, context):
        pipeline = context.scene.pipeline_data
        index = pipeline.active_operation_index

        # Check if there are operations
        if not pipeline.operations:
            self.report({'WARNING'}, 'No operations to remove')
            return {'CANCELLED'}

        # Remove the operation at the active index
        pipeline.operations.remove(index)

        # Adjust active index if needed (if we removed the last item)
        if pipeline.active_operation_index >= len(pipeline.operations):
            pipeline.active_operation_index = max(0, len(pipeline.operations) - 1)

        return { 'FINISHED' }


class MenuOperator(Operator):
    bl_idname = Labels.ADD_MENU_LIST_.value
    bl_label = 'Add Operation'

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.popup_menu(self.draw_menu)
        return {'FINISHED'}

    def draw_menu(self, menu, context):
        layout = menu.layout
        layout.operator("randomizer.add_folder", text="Folder", icon="FILE")
        # Lighting category
        layout.menu('AddLightingCategoryPipeMenu', icon="LIGHT")
        layout.menu('AddCameraCategoryPipeMenu', icon="VIEW_CAMERA")
        layout.menu('AddObjectCategoryPipeMenu', icon="CUBE")
        layout.menu('AddMaterialCategoryPipeMenu', icon="MATERIAL")
        layout.menu('AddConstraintCategoryPipeMenu', icon="RESTRICT_INSTANCED_OFF")
        layout.menu('AddExperimentalCategoryPipeMenu', icon="EXPERIMENTAL")


class EditPipeOperator(Operator):
    bl_idname = Labels.EDIT_PIPE.value
    bl_label = "Select Node"

    op_index: IntProperty(default=0)        # type: ignore

    def execute(self, context):
        pipeline = context.scene.pipeline_data
        # Select the operation in the UIList
        pipeline.active_operation_index = self.op_index

        # Load the current pipe object and arrange the config panel so that it matches the
        # current pipe configuration.
        operation = pipeline.operations[self.op_index]
        op_name = operation.operation_type
        config_setup: PipeSchema = PipeSchemaRegistry.get(op_name)
        if config_setup:
            config = loads(operation.config)
            UniqueLogger.quick_log(operation.config)
            UniqueLogger.quick_log(str(operation.config))
            config_setup.apply_config_to_ui(context, operation=operation, config=config)

        # Switch to edit tab
        context.window_manager['pipeline_tab'] = 'config'
        return { 'FINISHED' }


class ScanPipelineOperator(Operator):

    bl_idname = Labels.SCAN_PIPELINE.value
    bl_label = "Scan Pipeline"

    def execute(self, context):
        scene = context.scene
        pipeline = scene.pipeline_data
        found_not_valid = PipelineScanner.scan(pipeline)

        self.report({ 'INFO' },
            f"Scanned {len(pipeline.operations)} operation{'s' if len(pipeline.operations) > 1 else ''}, "
            f"{found_not_valid} operation{'s' if len(pipeline.operations) > 1 else ''} were invalid.")
        return {'FINISHED'}


class IntoFolderOperator(Operator):

    bl_idname = Labels.INTO_FOLDER.value
    bl_label = "Put into folder"

    def execute(self, context):
        return { 'FINISHED' }

class CaptureObjectsOperator(Operator):
    """Capture currently selected objects"""

    bl_idname = Labels.CAPTURE_OBJECTS.value
    bl_label = "Capture Objects"

    limit_obj: IntProperty(default=0)               # type: ignore

    def execute(self, context):
        scene = context.scene
        selected = context.selected_objects

        if not selected:
            self.report({ 'WARNING' }, "No objects selected")
            return { 'CANCELLED' }

        # Store names
        name_list = scene.targeted_objects_display

        captured_amount = 0
        name_list.clear()
        for obj in selected:
            nm = name_list.add()
            nm.obj_name = obj.name
            captured_amount += 1
            if captured_amount >= self.limit_obj and self.limit_obj:
                break

        self.report({ 'INFO' }, f"Captured {len(selected)} objects")
        return { 'FINISHED' }


class TypedSingleObjectTargeter(Operator):

    bl_idname = Labels.TYPED_SINGLE_OBJ_CAPT.value
    bl_label = "Selects a single object of given type"

    select_type: StringProperty(default="")                   # type: ignore

    def execute(self, context):

        scene = context.scene
        active_object = context.active_object

        if self.select_type and active_object.type.lower() != self.select_type.lower():
            self.report({ 'WARNING' }, "Selected object is not of type '{}'".format(self.select_type))
            return { 'CANCELLED' }

        scene.typed_object.obj_name = active_object.name

        return { 'FINISHED' }

def get_selected_node_and_material(
        reporter, context, node_name: Optional[str] = None, node_type: Optional[str] = None,
        has_attributes: tuple[str] = None
    ) -> tuple:
    """

    :param node_type:
    :param reporter:
    :param context:
    :param node_name:
    :param has_attributes:
    :return:
    """

    # Get active editor area
    for area in context.screen.areas:
        if area.type != 'NODE_EDITOR':
            continue
        # Get the node tree
        space = area.spaces.active
        node_tree = space.node_tree
        if not node_tree:
            continue
        mat_name = "Unknown Material"
        if hasattr(space, "id") and space.id:
            mat_name = space.id.name

        # Find selected nodes
        for node in node_tree.nodes:
            if not node.select:
                continue
            # If the node_name value is set, check if the node matches
            if node_name is not None and node_name not in node.bl_idname:
                return None, None
            # If the node_name value is set, check if the node matches
            UniqueLogger.quick_log(f"NODE TYPE: {node_type} e {node.type.lower()}")
            if node_type is not None and node_type.lower() not in node.type.lower():
                return None, None
            if has_attributes and node.attributes:
                search_attributes = set(att.lowerr() for att in has_attributes)
                for input_socket in node.inputs:
                    # e.g. nodes
                    if input_socket.name.lower() in search_attributes:
                        search_attributes.remove(input_socket.name.lower())
                if search_attributes:
                    return None, None
                else:
                    return node, mat_name
            # At this point the node is selected and is of the correct node type.
            if not node.label or node.bl_label.strip() == "":
                reporter.report({'WARNING'}, f"Node must have a label to ensure safety!")
                return None, None
            else:
                return node, mat_name
    return None, None


class TypedNodeCaptureOperator(Operator):
    """Capture currently selected objects"""

    bl_idname = Labels.CAPTURE_TYPED_NODE.value
    bl_label = "Capture a Typed node"

    node_type: StringProperty(default="")         # type: ignore
    node_id: StringProperty(default="")           # type: ignore

    def execute(self, context):
        scene = context.scene
        selected, mat_name = get_selected_node_and_material(
            self, context, node_name=self.node_id, node_type=self.node_type)

        if not selected:
            return { 'CANCELLED' }

        # Store name
        lab = selected.label
        mat_prop = scene.targeted_node
        mat_prop.node_label = lab
        mat_prop.mat_name = mat_name

        self.report({ 'INFO' }, f"Captured: {mat_name} > {lab}")
        return { 'FINISHED' }


class CaptureTextureOperator(Operator):
    """Capture currently selected objects"""

    bl_idname = Labels.CAPTURE_TEXTURE_NODE.value
    bl_label = "Capture Texture"

    def execute(self, context):
        scene = context.scene
        selected, mat_name = get_selected_node_and_material(self, context, 'ShaderNodeTexImage')

        if not selected:
            return { 'CANCELLED' }

        # Store name
        lab = selected.label
        mat_prop = scene.targeted_texture_node
        mat_prop.node_label = lab
        mat_prop.mat_name = mat_name

        self.report({ 'INFO' }, f"Captured: {mat_name} > {lab}")
        return { 'FINISHED' }


class CaptureObjectPositionOperator(Operator):

    bl_idname = Labels.CAPTURE_OBJ_POSITION.value
    bl_label = "Capture Object Position"

    def execute(self, context):
        obj = bpy.context.active_object
        if not obj:
            self.report({ 'WARNING' }, "No objects selected")
            return {'CANCELLED'}
        positions = context.scene.position_collection
        new_op = positions.add()
        new_op.pos = obj.location

        self.report({'INFO'}, f"Captured position from currently selected object.")
        return {'FINISHED'}


class CaptureCursorPositionOperator(Operator):

    bl_idname = Labels.ADD_CURSOR_POS.value
    bl_label  = "Capture the position of the cursor"

    def execute(self, context):
        scene = context.scene
        cursor_loc = scene.cursor.location

        positions = context.scene.position_collection
        new_op = positions.add()
        new_op.pos = cursor_loc
        return { 'FINISHED' }


class ViewTargetSelectedOperator(Operator):
    bl_idname = "randomizer.view_target_selected"
    bl_label = "View Target Selected"

    # Pass in which collection to use, taken from the scene
    collection_attribute: StringProperty()      # type: ignore
    name_attribute: StringProperty()            # type: ignore

    def execute(self, context):
        scene = context.scene

        collection = scene
        try:
            # Handle attributes like scene.data.collection
            for attr in self.collection_attribute.split('.'):
                collection = getattr(collection, attr)
        except KeyError:
            self.report({'ERROR'}, f"Unknown collection: {self.collection_path}")
            return {'CANCELLED'}

        # Deselect all first
        bpy.ops.object.select_all(action='DESELECT')

        selected_count = 0
        missing_count = 0

        for item in collection:
            # Handle different item types
            if hasattr(item, self.name_attribute):  # ObjectLabel has obj_names collection
                obj_name_item = getattr(item, self.name_attribute)
                obj = scene.objects.get(obj_name_item)
                if obj:
                    obj.select_set(True)
                    selected_count += 1
                else:
                    self.report({'WARNING'}, f"Object not found: {obj_name_item}")
                    missing_count += 1
        # Set one as active if any were selected
        if selected_count > 0 and scene.objects:
            context.view_layer.objects.active = scene.objects[0]

        # Final report
        self.report({'INFO'}, f"Selected {selected_count} objects ({missing_count} not found)")
        return {'FINISHED'}

class PositionAddOperator(Operator):

    bl_idname = Labels.ADD_POSITION_POOL.value
    bl_label = "Add a new target position"

    op_name: StringProperty(default="Nothing")  # type: ignore

    def execute(self, context):
        positions = context.scene.position_collection
        positions.add()
        return { 'FINISHED' }


class PositionRemoveOperator(Operator):

    bl_idname = Labels.REMOVE_POSITION_POOL.value
    bl_label = "Delete the selected target position"

    def execute(self, context):
        scene = context.scene
        positions = context.scene.position_collection
        index = scene.selected_position_index

        if not positions:
            self.report({'WARNING'}, 'No Position to remove')
            return {'CANCELLED'}

        positions.remove(index)

        if scene.selected_position_index >= len(positions):
            scene.selected_position_index = max(0, len(positions) - 1)

        return { 'FINISHED' }


class AddMaterialToListOperator(Operator):
    """Add selected material to list"""
    bl_idname = Labels.ADD_MATERIAL_POOL.value
    bl_label = "Add Material"

    # Dropdown property with all materials
    material: bpy.props.EnumProperty(                               # type: ignore
        name="Material",
        description="Select material to add",
        items= lambda self, context: [                              # type: ignore
            (mat.name, mat.name, "")
            for mat in bpy.data.materials
        ] or [("NONE", "No materials", "")]
    )

    def execute(self, context):
        scene = context.scene

        mat = bpy.data.materials.get(self.material)

        if not mat:
            self.report({'WARNING'}, "Material not found")
            return { 'CANCELLED' }

        for item in scene.material_list:
            if item.material == mat:
                self.report({'INFO'}, f"{mat.name} already in list")
                return { 'CANCELLED' }

        new_item = scene.material_list.add()
        new_item.material = mat

        self.report({'INFO'}, f"Added {mat.name}")
        return {'FINISHED'}

    def invoke(self, context, _event):
        return context.window_manager.invoke_props_dialog(self)


class RemoveMaterialFromListOperator(Operator):
    """Remove material from list"""
    bl_idname = Labels.REMOVE_MATERIAL_POOL.value
    bl_label = "Remove"

    def execute(self, context):
        scene = context.scene
        idx = scene.material_list_index

        if idx < len(scene.material_list):
            scene.material_list.remove(idx)

        return {'FINISHED'}

class CaptureValueNode(Operator):

    bl_idname = Labels.CAPTURE_VALUE_NODE.value
    bl_label = "Capture Value Node"

    def execute(self, context):
        scene = context.scene
        selected, mat_name = get_selected_node_and_material(self, context, 'ShaderNodeValue')

        if not selected:
            return { 'CANCELLED' }

        # Store name
        lab = selected.label
        mat_prop = scene.targeted_value_node
        mat_prop.node_label = lab
        mat_prop.mat_name = mat_name

        self.report({ 'INFO' }, f"Captured: {mat_name} > {lab}")
        return { 'FINISHED' }


class CaptureAndModifyNodeProperties(Operator):

    bl_idname = Labels.CAPTURE_GENERAL_NODE.value
    bl_label = "Capture Node"

    def execute(self, context):

        node, mat_name = get_selected_node_and_material(self, context, None)

        if not node:
            return {'CANCELLED'}

        # Store name
        lab = node.label
        # context.scene.targeted_material_display = f"{mat_name} > {lab}"
        UniqueLogger.quick_log(f"Node: {node.name} ({node.bl_label})")

        UniqueLogger.quick_log(f"Node: {node.name} ({node.bl_label})")
        UniqueLogger.quick_log(f"Node Type: {node.bl_idname}\n")

        UniqueLogger.quick_log("INPUTS:")
        UniqueLogger.quick_log("-" * 60)
        for input_socket in node.inputs:
            # e.g. nodes
            UniqueLogger.quick_log(f"  Name: {input_socket.name}")
            UniqueLogger.quick_log(f"  Type: {input_socket.type}")
            UniqueLogger.quick_log(f"  Default Value: {input_socket.default_value}")
            UniqueLogger.quick_log(f"  BL IDName: {input_socket.bl_idname}")

        self.report({'INFO'}, f"Captured: {mat_name} > {lab}")
        return {'FINISHED'}


class SavePipeOperator(Operator):

    bl_idname = Labels.SAVE_PIPE.value
    bl_label = "randomizer.save_pipe"

    on_save_return: StringProperty(default="")     # type: ignore

    def execute(self, context):

        scene = context.scene
        # Take the name of the current pipe and extract the required PipeSchema,
        # which is an auxiliary class used to serialize the UI into a json.
        pipeline = scene.pipeline_data
        op_index = pipeline.active_operation_index
        operation = pipeline.operations[op_index]

        op_name = str(operation.operation_type)
        # Interrogate the registry
        schema = PipeSchemaRegistry.get(op_name)
        if schema is not None:

            config = schema.extract_config_from_ui(context, operation)
            serialized = dumps(config)

            UniqueLogger.quick_log(serialized)
            # Now we write back the serialized dictionary in a blender property associated with the pipe.
            # The overhead of saving strings and deserializing is minimal because the heavy task (generation)
            # initially deserializes all the pipeline into dictionaries.
            operation.config = serialized

            # We must now call the validator and ensure that the pipe is correctly configured, to display as a
            # warning sign
            validator = ValidatorRegistry.get(op_name)
            if validator:
                operation.valid = validator.validate(operation, config)

        if self.on_save_return:
            # Change back to tab
            context.window_manager['pipeline_tab'] = self.on_save_return
        return { 'FINISHED' }

