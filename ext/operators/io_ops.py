from .names import Labels
from ..utils.logger import UniqueLogger
from ..constants import VERSION

import os
import json
import platform
import subprocess

from bpy.types import Operator
from bpy.props import StringProperty

import bpy


class PipelineSerializer:

    @staticmethod
    def get_description(scene) -> dict:
        """

        :param scene:
        :return:
        """
        pipe_desc = PipelineSerializer._get_pipe_description(scene)
        distribution_desc = PipelineSerializer._get_distributions_description(scene)
        return {
            # taken from constants.py at the root
            "version": VERSION,
            "operations": pipe_desc,
            "distributions": distribution_desc
        }

    @staticmethod
    def _get_distributions_description(_scene) -> dict:
        """

        :param _scene:
        :return:
        """
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
        return {
            'operations': [ {
                'operation_type': op.operation_type,
                'enabled': op.enabled,
            } for op in pipeline.operations ]
        }


class SavePipelineAsOperator(Operator):

    bl_idname = Labels.SAVE_PIPELINE_JSON.value
    bl_label = "Write back the pipeline"

    filepath: StringProperty(subtype='FILE_PATH', default='pipeline.json')          # type: ignore

    def execute(self, context):
        scene = context.scene
        before_serialized_repr = PipelineSerializer.get_description(scene)
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
        return {'FINISHED'}

    def invoke(self, context, _):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PipelineLoader:
    pass

class LoadPipelineOperator(Operator):

    bl_idname = Labels.LOAD_PIPELINE_JSON.value
    bl_label = "Load Pipeline"

    def execute(self, context):
        """Capture undo history by redirecting stdout"""
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


class SwitchLabelingTabOperator(Operator):

    bl_idname = Labels.SWITCH_LABEL_SECTION.value
    bl_label = "Switch Labeling mode"

    tab: StringProperty()                               # type: ignore

    def execute(self, context):

        context.window_manager['labeling_tab'] = self.tab
        return {'FINISHED'}

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

class VisualizeLandmarkConstellationOperator(Operator):
    
    pass

class InterruptConstellationOperator(Operator):
    pass