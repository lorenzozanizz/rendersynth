"""




"""


from .names import Labels
from ..labeling.class_engine import ClassificationEngine
from ..utils.logger import UniqueLogger
from ..constants import VERSION
from ..pipeline.integrity import PipelineScanner

import os
import json
import platform
import subprocess
from typing import Any

from bpy.types import Operator
from bpy.props import StringProperty

import bpy



class PipelineSerializer:
    """

    """

    @staticmethod
    def get_description(context) -> dict:
        """

        :param context:
        :return:
        """
        #
        scene = context.scene
        pipe_desc = PipelineSerializer._get_pipe_description(scene)
        distribution_desc = PipelineSerializer._get_distributions_description(scene)
        label_desc = PipelineSerializer._get_label_description(context)
        gen_desc = PipelineSerializer._get_generation_description(scene)
        return {
            # taken from constants.py at the root
            "version": VERSION,
            "operations": pipe_desc,
            "distributions": distribution_desc,
            "labeling": label_desc,
            #
            "generation": gen_desc
        }

    @staticmethod
    def _get_distributions_description(_scene) -> dict:
        """

        :param _scene:
        :return:
        """
        # Currently not implemented for arbitrary distributions, and standard distributions
        # do not require such a description.
        distributions = ()
        return {
            'distributions': distributions
        }

    @staticmethod
    def _get_pipe_description(scene) -> dict:
        """

        :param scene:
        :return:
        """
        pipeline = scene.pipeline_data
        # A small note on pipe validity: the information is not saved, instead when
        # a new pipeline is loaded the validity check is performed again from scratch.
        # this is to ensure that there cannot be "dangling" references.
        return {
            'operations': [ {
                'operation_type': op.operation_type,
                'enabled': op.enabled,
                'name': op.name,
                'order': op.order,
                'config': op.config
            } for op in pipeline.operations ]
        }

    @classmethod
    def _get_label_description(cls, scene):
        # Use the interface offered by the ClassificationEngine
        # to simplify our life here.
        engine = ClassificationEngine(scene)
        return engine.extract_class_labels_data()

    @classmethod
    def _get_generation_description(cls, scene):
        # Extract generic information about the generation (not about I/O),
        # e.g. seed, number of shots
        return {
            'amount': scene.randomizer_amount,
            'seed': scene.randomizer_seed
        }

class PipelineLoader:

    def __init__(self, scene):
        self.scene = scene

    def load(self, content: dict[str, Any]):
        #
        self._load_generation_settings(content.get("generation"))
        self._load_operations(content.get("operations"))
        self._load_distribution(content.get("distributions"))
        self._load_classes_data(content.get("labeling"))


    def _load_classes_data(self, data: dict):
        """
        Loads serialized labeling configuration back into the PropertyGroup.
        See load_labels.py for implementation details.
        """
        label_data = self.scene.labeling_data

        # Validate version
        version = data.get("version", 1)
        if version != 1:
            raise ValueError(f"Unsupported data version: {version}")

        # Clear existing data
        label_data.label_classes.clear()
        label_data.direct_labels.clear()
        label_data.label_rules.clear()
        label_data.entities.clear()

        # Load settings
        settings = data.get("settings", {})
        label_data.do_superclasses = settings.get("do_superclasses", False)
        label_data.use_rules = settings.get("use_rules", False)
        label_data.use_entities = settings.get("use_entities", False)
        label_data.default_class = settings.get("default_class", "")
        label_data.class_active_index = settings.get("class_active_index", 0)
        label_data.direct_active_index = settings.get("direct_active_index", 0)
        label_data.rule_active_index = settings.get("rule_active_index", 0)
        label_data.entities_active_index = settings.get("entities_active_index", 0)

        # Load label classes
        for cls_data in data.get("label_classes", []):
            cls = label_data.label_classes.add()
            cls.name = cls_data.get("name", "Unnamed")
            cls.class_id = cls_data.get("class_id", 0)
            cls.parent_id = cls_data.get("parent_id", -1)
            color = cls_data.get("color", [0.2, 0.4, 0.8, 1.0])
            if isinstance(color, (list, tuple)) and len(color) == 4:
                cls.color = color

        # Load direct labels
        for label_data_entry in data.get("direct_labels", []):
            label = label_data.direct_labels.add()
            label.assignment_id = label_data_entry.get("assignment_id", 0)
            label.class_id = label_data_entry.get("class_id", "")
            label.is_entity = label_data_entry.get("is_entity", False)

            for obj_name in label_data_entry.get("obj_names", []):
                obj_name_item = label.obj_names.add()
                obj_name_item.obj_name = obj_name

        # Load label rules
        for rule_data in data.get("label_rules", []):
            rule = label_data.label_rules.add()
            rule.rule_type = rule_data.get("rule_type", "NONE")
            rule.class_id = rule_data.get("class_id", "")

            if rule.rule_type == 'MATERIAL':
                rule.material_name = rule_data.get("material_name", "")
            elif rule.rule_type == 'NAME_CONTAINS':
                rule.name_filter = rule_data.get("name_filter", "")
            elif rule.rule_type == 'COLLECTION':
                rule.collection_name = rule_data.get("collection_name", "")

        # Load entities
        for entity_data in data.get("entities", []):
            entity = label_data.entities.add()
            entity.entity_id = entity_data.get("entity_id", 0)
            entity.entity_name = entity_data.get("entity_name", "")

            for obj_name in entity_data.get("obj_names", []):
                obj_name_item = entity.obj_names.add()
                obj_name_item.obj_name = obj_name

    def _load_distribution(self, param):

        if param is None:
            return

    def _load_operations(self, param):

        if param is None:
            return
        pipeline = self.scene.pipeline_data
        # NOTE: We do not clear the current pipes. The user may want to import a subset of
        # stages from another file, so we simply append.
        new_stages = param.get("operations")
        if not new_stages:
            return
        for stage in new_stages:
            new_stage = pipeline.operations.add()
            new_stage.operation_type = stage.get("operation_type")
            new_stage.enabled = stage.get("enabled", False)
            new_stage.config = stage.get("config", "")
            new_stage.order = stage.get("order")
            new_stage.name = stage.get("name")

        # Perform an overall validity check for the new pipes.
        PipelineScanner.scan(pipeline)

    def _load_generation_settings(self, param):

        if param is None:
            return

        amount = param.get('amount', 100)
        seed = param.get('seed', 0)
        self.scene.randomizer_amount = amount
        self.scene.randomizer_seed = seed


class SavePipelineAsOperator(Operator):

    bl_idname = Labels.SAVE_PIPELINE_JSON.value
    bl_label = "Write back the pipeline"

    filepath: StringProperty(subtype='FILE_PATH', default='pipeline.json')          # type: ignore

    def execute(self, context):
        scene = context.scene
        before_serialized_repr = PipelineSerializer.get_description(context)
        try:
            # Get the path from the scene property
            path = scene.randomizer_pipeline_save_path
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(before_serialized_repr, f, indent=2)
        except Exception as e:
            self.report({'ERROR'}, f'Failed to save: {str(e)}')
            return {'CANCELLED'}

        self.report({'INFO'}, f'Saved pipeline to {path}')
        return { 'FINISHED' }

    def invoke(self, context, _):
        scene = context.scene
        path = scene.randomizer_pipeline_save_path
        if not path or path.isspace():
            context.window_manager.fileselect_add(self)
            return { 'RUNNING_MODAL' }
        else:
            self.execute(context)
            return { 'FINISHED' }


class LoadPipelineOperator(Operator):

    bl_idname = Labels.LOAD_PIPELINE_JSON.value
    bl_label = "Load Pipeline"


    def execute(self, context):
        scene = context.scene
        try:
            # Get the path from the scene property
            path = scene.randomizer_config_path
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'r', encoding="utf-8") as f:
                content = json.load(f)

            loader = PipelineLoader(scene)
            loader.load(content)
        except Exception as e:
            self.report({'ERROR'}, f'Failed to load: {str(e)}')
            return {'CANCELLED'}

        self.report({'INFO'}, f'Loaded pipeline from {path}')
        return {'FINISHED'}

    def invoke(self, context, _):
        scene = context.scene
        path = scene.randomizer_config_path
        if not path or path.isspace():
            context.window_manager.fileselect_add(self)
            return { 'RUNNING_MODAL' }
        else:
            self.execute(context)
            return {'FINISHED'}


class OpenLogsOperator(Operator):
    """Open the log file in default editor"""
    bl_idname = Labels.OPEN_LOG_DIRECTORY.value
    bl_label = "Open Log File"

    def execute(self, _context):
        """

        :param _context:
        :return:
        """

        if not UniqueLogger.available():
            self.report({ 'ERROR' }, "Log file does not exist.")
            return { 'CANCELLED' }

        # Open file with default app
        log_path = UniqueLogger.get_path()
        try:
            if platform.system() == "Windows":
                os.startfile(log_path)
            # https://wenku.csdn.net/answer/3pg0xo8hc0
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", log_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", log_path])

        except Exception as e:
            self.report({ 'ERROR' }, f"Could not open log file: {e}.")

        return { 'FINISHED' }


class ApplyLogPathOperator(Operator):

    bl_idname = Labels.SETUP_LOGGER_DIR.value
    bl_label = "Apply Log Path"

    @staticmethod
    def _setup_logger_from_scene(context) -> bool:
        """ Setup logger using scene property """

        try:
            # Clean up the previous logger, e.g. generate a new writing path
            UniqueLogger.cleanup()
            # Now set up the new logger which sets multiple logger variables (the path,
            # the availability of the logger with UniqueLogger.available())
            directory = context.scene.randomizer_logging_path
            UniqueLogger.initialize_logging(directory)
            return True

        except Exception as e:
            context.report({'ERROR'}, f"Could not setup logger: {e}.")
            return False

    def execute(self, context):
        """

        :param context:
        :return:
        """
        if ApplyLogPathOperator._setup_logger_from_scene(context):
            self.report({'INFO'}, "Logger updated!")
            return { 'FINISHED' }
        else:
            self.report({'ERROR'}, "Failed to update logger")
            return { 'CANCELLED' }
