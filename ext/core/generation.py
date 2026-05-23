import random
import bpy

from ..pipeline.bpy_properties import PipelineData
from ..pipeline.context import NestedPipelineContext

from .executable_pipeline import ExecutablePipeline
from .orchestrator import LabelingOrchestrator
from .configurations import LabelExtractionConfig, GenerationConfig, WritingConfig, RenderConfig, BatchMetadata
from .io import OutputWriter, IOStrategy
from .io import LabelingFormatRegistry
from ..utils.other import MultiContext


class Executor:
    """Compiled, reusable pipeline executor"""

    def __init__(self, context, data: PipelineData,
         gen_params: GenerationConfig,
         label_params: LabelExtractionConfig,
         write_params: WritingConfig,
         reporter = None
    ):
        self.data = data
        self.ctx = context
        self.parameters: GenerationConfig = gen_params
        self.write_params = write_params
        self.reporter = reporter

        self.pipeline: ExecutablePipeline = ExecutablePipeline(self.ctx, data, reporter)
        # Create the writer and assign the correct file handler
        io_strategy = self._get_strategy(label_params)
        self.writer = OutputWriter(write_params, io_strategy=io_strategy)

        self.labeling_orchestrator: LabelingOrchestrator = LabelingOrchestrator(
            self.ctx,
            # Parameters which control the folder structure, labeling etc...
            label_params,
            reporter,
            # The orchestrator will assign the label serialization strategy to the writer
            writer=self.writer
        )

    def compile_contexts(self) -> NestedPipelineContext:
        """

        :return:
        """
        full_context = self.pipeline.build_context_manager()
        return full_context


    def execute(self):
        """Execute all compiled operations"""

        scene       = self.ctx.scene
        amount      = self.parameters.amount
        seed        = self.parameters.seed

        # Seed the random library with the user requested seed.
        random.seed(seed)

        start_idx   = self.writer.compute_starting_index()

        # We disable the updates in the viewport so that the program does not crash or lag!
        # In the future, this will be set in the settings!
        update_viewport = NoViewportUpdate(disable=False)
        default_camera = self.ctx.scene.camera

        # Generate the progress bar
        wm = self.ctx.window_manager
        wm.progress_begin(0, amount)

        try:
            with update_viewport:

                # Hint the labeling orchestrator that generation is commencing
                labeling_context = self.labeling_orchestrator.begin_generation(self.parameters)
                full_context = self.compile_contexts()
                # And join the two contexts together
                with MultiContext(labeling_context, full_context):

                    for shot_idx in range(start_idx, start_idx + amount):
                        # Frame context enters/exits each iteration

                        self.writer.set_shot_index(shot_idx)
                        with full_context.frame_context():

                            # Execute pipeline
                            self.pipeline.execute()

                            render_cfg = RenderConfig(
                                width=scene.render.resolution_x,
                                height=scene.render.resolution_y,
                                image_ext=scene.render.image_settings.file_format,
                                camera=default_camera,
                            )

                            # First generate the target image, then we process the shot to generate
                            # labels. This is required for some labeling formats, which for example
                            # require to sample the pixel colors directly from the rendered scene!
                            write_path = self.writer.get_image_write_path()

                            # The orchestrator may need to prepare some things before acting. e.g.
                            # change compositor nodes.
                            self.labeling_orchestrator.prepare_for_shot(shot_idx=shot_idx)

                            # Renders
                            scene.render.filepath = write_path
                            bpy.ops.render.render(write_still=True)

                            # Run generation pipeline (handles extraction + formatting)
                            self.labeling_orchestrator.process_shot(
                                render_cfg,
                                rendered_data_path=write_path,
                                depsgraph=self.ctx.evaluated_depsgraph_get()
                            )


                        # ^ Frame context exits here—restores frame-level state, required for
                        # pipes that require per-frame restoring (e.g. those that act as offset
                        wm.progress_update(shot_idx-start_idx)

                    # ^ Global contexts exit here—restores global state
                # Instruct the orchestrator to end labeling. This may trigger I/O operations for
                # formats which require aggregating data over multiple frames.
                self.labeling_orchestrator.end_generation()

        finally:
            wm.progress_end()

        return {'FINISHED'}

    def _get_strategy(self, label_params: LabelExtractionConfig) -> IOStrategy:
        """ Generates the IOStrategy for the labeling and file writing process using the
        LabelExtractionConfig and (TBI) add-on preferences to control the image writing settings.

        :param label_params: LabelExtractionConfig object
        :return: the correct IOStrategy for said format
        """
        lbl_type = label_params.format
        strat = LabelingFormatRegistry.get_strategy(lbl_type)
        if strat is None:
            raise RuntimeError(f"No I/O strategy found for {lbl_type}, the generation could not happen.")
        strat_instance = strat(self.write_params, label_params.format_cfg)
        return strat_instance


class NoViewportUpdate:

    def __init__(self, disable):
        self.disable = disable

    def __enter__(self):
        # Disable the visibility of everything in the viewport only (not the rendering)
        # this will be restored at the end
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        return False
