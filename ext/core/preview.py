from pathlib import Path

from .executable_pipeline import ExecutablePipeline
from .generation import NoViewportUpdate
from .configurations import PreviewRenderConfig, LabelExtractionConfig, RenderConfig
from .orchestrator import LabelingOrchestrator

from ..labeling.generator import LabelData
from ..labeling.preview_renderers import PreviewRendererRegistry, PreviewStyle
from ..pipeline.bpy_properties import PipelineData
from ..pipeline.context import NestedPipelineContext

from ..utils.timer import TimingContext
from ..utils.images import PixelCanvas, draw_bitmap_text, font_size_fit_box_perc, estimate_text_pixel_height

from typing import Dict, Literal, Iterable
import tempfile
import os

import bpy


class PreviewGenerator:
    """ Generates a visual preview of a rendered scene with overlaid labeling annotations,
    class names and ids and estimated visibility.

    This class functions both as executor (compiling and executing a pipeline)
    and as a renderer, rendering the scene to a temporary image and overlaying annotation
    data such as bounding boxes, polygons, class labels.
    It also times statistics for debugging and visualization purposes.

    Drawing itself is delegated per-label to whatever PreviewRenderer is registered
    for that label's annotation_type (see preview_renderers): this class
    only handles picking which image ends up displayed, batching "overlay" renderers
    onto a single PixelCanvas, and the housekeeping around rendering the shot.
    """

    _preview_name = "__randomizer_preview.png"
    # Single, reused shot slot for preview generation: every preview run overwrites
    # the same temp files rather than accumulating a history, since only the latest
    # preview is ever shown
    _preview_shot_idx = 0

    def __init__(self, context, data: PipelineData,
                 parameters: PreviewRenderConfig,
                 label_params: LabelExtractionConfig, reporter=None):
        """ Initialize the preview generator with the given configurations and the
        PipelineData Blender property.

        :param context: the Blender context
        :param data: the data property
        :param parameters: configurations for the rendered preview
        :param reporter: an object capable of GUI reporting
        """

        self.data = data
        self.ctx = context
        self.parameters = parameters
        self.reporter = reporter

        self.pipeline = ExecutablePipeline(self.ctx, data, reporter)
        self.path = os.path.join(tempfile.gettempdir(), PreviewGenerator._preview_name)

        # The list of visible objects will be populated when the pipeline is executed once to
        # sample a random shot
        self.used_camera = None

        # Timing statistics
        self.timings: Dict[str, float] = { 'compile': self.pipeline.get_compilation_time() }

        self.labeling_orchestrator: LabelingOrchestrator = LabelingOrchestrator(
            self.ctx,
            # Parameters which control the folder structure, labeling etc...
            label_params,
            reporter,
            # The orchestrator will assign the label serialization strategy to the writer
            writer=None
        )

        # Some extractors (e.g. PixelMapExtractor, for depth/normal formats) write
        # files themselves outside the normal writer pipeline and need to know a
        # write location even though preview has no real OutputWriter. This does nothing
        # for extractors who don't need it.
        self.label_temp_dir = os.path.join(tempfile.gettempdir(), "randomizer_preview_labels")
        self.labeling_orchestrator.declare_temp_folder_structure(self.label_temp_dir)

    def compile_contexts(self) -> NestedPipelineContext:
        """ Obtains the context manager from the pipeline. The context manager has two
        context levels: a full context which restores the total state before the execution, and
        intermediate contexts which must restore state per-frame. For the preview, a single
        frame is generated so that the full context is used.

        :return: the NestedPipelineContext object with both frame and full context
        """
        full_context = self.pipeline.build_context_manager()
        return full_context

    def execute(self) -> None:
        """
        Execute the preview generation process.

        Runs the compiled pipeline within a controlled context, performs labeling
        using the configured labeling orchestrator, and renders the scene to a
        temporary file. Timing statistics for labeling and rendering are recorded.

        :return: None
        """

        scene = self.ctx.scene

        # We disable the updates in the viewport so that the program does not crash or lag!
        # In the future, this will be set in the settings!
        update_viewport = NoViewportUpdate(disable=False)

        with update_viewport:
            full_context = self.compile_contexts()
            with full_context:
                # Execute pipeline
                self.pipeline.execute()

                # We render in a temp path
                scene.render.filepath = self.path

                # Extractors that write files themselves outside the normal writer
                # pipeline (e.g. PixelMapExtractor, driving the compositor directly)
                # need the same prepare-render-finalize lifecycle a real batch run
                # gives them via generation.py's per-shot loop
                with self.labeling_orchestrator.get_extraction_context():
                    self.labeling_orchestrator.prepare_for_shot(shot_idx=self._preview_shot_idx)

                    with TimingContext(self.timings, 'render'):
                        bpy.ops.render.render(write_still=True)

                    self.labeling_orchestrator.terminate_preparation(shot_idx=self._preview_shot_idx)

                    default_camera = self.ctx.scene.camera
                    if not default_camera:
                        self.reporter.report(
                            {'WARNING'}, "No default camera was set, no labels preview could be generated")
                    else:
                        self.used_camera = default_camera
                        render_cfg = RenderConfig(
                            height=scene.render.resolution_x,
                            width=scene.render.resolution_y,
                            image_ext=scene.render.image_settings.file_format,
                            camera=default_camera,
                        )

                        with TimingContext(self.timings, 'labeling'):
                            self.labeling_orchestrator.process_shot(
                                render_cfg=render_cfg,
                                rendered_data_path=self.path,
                                depsgraph=self.ctx.evaluated_depsgraph_get()
                            )

        # ^ Global contexts exit here—restores global state

        return

    def _open_render_f12_menu(self) -> None:
        """ Open the Blender render view (F12) and load the generated preview image.

        Ensures that any previously loaded preview image is removed before opening
        the newly rendered image from the temporary file path.
        """

        # Opens the F12 render window and opens the newly temp rendered file. this file is later
        # opened and modified to draw over boxes, texts, etc...
        bpy.ops.render.opengl('INVOKE_DEFAULT')
        if img := bpy.data.images.get(self.path):
            bpy.data.images.remove(img)
        elif img := bpy.data.images.get(self._preview_name):
            bpy.data.images.remove(img)
        bpy.ops.image.open(filepath=self.path)

    @staticmethod
    def _swap_displayed_image(path: str) -> "bpy.types.Image":
        """ Replace the image currently shown in the render window with the image
        at path (e.g. a depth/normal map written by the compositor), removing
        whatever was already loaded under that name first so Blender doesn't reuse
        outdated cached pixel data.

        :param path: Filesystem path of the image to display.
        :return: The newly (re)loaded Blender image.
        """
        name = Path(path).name
        if img := bpy.data.images.get(name):
            bpy.data.images.remove(img)
        bpy.ops.image.open(filepath=path)
        return bpy.data.images[name]

    def display_and_render_preview(self,
                                   show_obj_name: bool = True,
                                   show_class_name_or_id: Literal["id", "name", "none"] = "id",
                                   show_obj_geometry: bool = True,
                                   show_entity: bool = True,
                                   ignore_default_class: str = "",
                                   show_visibility: bool = True,
                                   show_rendering_time: bool = True
                                   ) -> None:
        """
        :param show_entity:
        :param ignore_default_class:
        :param show_visibility:
        :param show_rendering_time:
        :param show_obj_geometry:
        :param show_obj_name:
        :param show_class_name_or_id:
        :return:
        """

        # Open the render f12 menu, then we will reopen the image and render some statistics
        # using the pixel raster.
        self._open_render_f12_menu()

        scene = self.ctx.scene
        label_data: LabelData = self.labeling_orchestrator.get_last_label_data()

        # self.visible is a { object, bounding_box } dictionary, but the extraction may have failed
        if not label_data:
            return

        width = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
        height = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)

        style = PreviewStyle(
            show_obj_name=show_obj_name,
            show_class_name_or_id=show_class_name_or_id,
            show_geometry=show_obj_geometry,
            show_visibility=show_visibility,
            max_preview_points=self.parameters.max_preview_points,
        )

        # Defaults to the RGB render; a "replace"-mode label (e.g. a per-pixel
        # depth/normal map) swaps this out entirely, below.
        displayed_img = bpy.data.images[PreviewGenerator._preview_name]

        with TimingContext(self.timings, 'annotating'):
            overlay_labels = []
            for label in label_data:
                renderer_cls = PreviewRendererRegistry.get_for(label.annotation_type)
                if renderer_cls is None:
                    # No renderer registered for this annotation_type: nothing to draw.
                    continue

                if renderer_cls.display_mode == "replace":
                    # The annotation IS the image (e.g. a depth/normal map already
                    # rendered to disk): swap the displayed image instead of drawing
                    # an overlay. A preview run only ever uses one extractor/format,
                    # so this never coexists with "overlay" labels in practice --
                    # there is nothing meaningful to overlay on a depth/normal map
                    # even if it did.
                    replacement_path = renderer_cls().render(None, label, (0, 0, 0, 0), width, height, style)
                    if replacement_path:
                        displayed_img = self._swap_displayed_image(replacement_path)
                    continue

                # Only classified objects have class/name info to draw.
                if not label.cls:
                    continue
                if ignore_default_class and label.cls.name == ignore_default_class:
                    continue
                if label.is_entity and not show_entity:
                    continue

                overlay_labels.append((label, renderer_cls))

            if overlay_labels:
                canvas = PixelCanvas(displayed_img)
                for label, renderer_cls in overlay_labels:
                    color = tuple(label.cls.color)
                    renderer_cls().render(canvas, label, color, width, height, style)

                # Overwrite the image buffer only once, avoiding the previious terrible
                # performance effect that would overwrite the image for every geometry piece
                # (box, point, etc...)
                canvas.flush()

        if show_rendering_time:
            self._render_bottom_left_time_stats(displayed_img, width)

    def _render_bottom_left_time_stats(self, img, width: int) -> None:
        """ Render timing statistics text in the bottom-left corner of the image.

        Displays compilation, rendering, labeling, and annotation durations which are respectively
        the time it takes to compile the pipeline, the time Blender took for rendering, the time
        it took to generate labels for visible objects and the time it took to draw over the initial
        render for preview.

        :param img: The image object to draw onto
        :param width: Width of the image in pixels
        """

        text = (f"Compiled in {self.timings['compile']:.2f}s, rendered in {self.timings['render']:.2f}s, "
                f"labeled in {self.timings['labeling']:.2f}s, annotated in {self.timings['annotating']:.2f}s")

        font_size = font_size_fit_box_perc(text, width, 0.5)
        draw_bitmap_text(img, text,
         (10, 10 + estimate_text_pixel_height("", font_size)),
            color=None, size=font_size
        )


    def _render_bottom_right_statistics(self) -> None:
        """ Placeholder for rendering additional statistics in the bottom-right corner.

        !! Currently unused !! Intended for future extensions such as displaying object
        counts or other metrics.
        """
        num_objects = len(self.labeling_orchestrator.visible_objects)

    @staticmethod
    def _render_geometry(_img, _color, pixel_space_geometry, _line_width: int = 4) -> None:
        """ Render annotations onto the image (e.g. polygons, bounding boxes etc...).
        Supports both bounding boxes and polygon geometries in pixel space.

        :param _img: The image object to draw onto
        :param _color: RGBA color tuple
        :param pixel_space_geometry: Geometry in pixel coordinates
        :param _line_width: Width of the drawn lines for the geometry
        """
        # Bounding box
        if type(pixel_space_geometry) == tuple:
            new_xyxy = pixel_space_geometry
            _p0 = (new_xyxy[0], new_xyxy[1])
            _p1 = (new_xyxy[2], new_xyxy[3])
            # draw_bounding_box(img, color, p0, p1, y_grows_up_to_down=False, line_width=line_width)
        if type(pixel_space_geometry) == list:
            pass
            # draw_polygon(img, pixel_space_geometry, color, line_width=line_width)

    @staticmethod
    def make_preview_render_data(label_data: LabelData) -> Iterable: # Iterable[PreviewRenderData]:
        """ Convert LabelData into preview render data structures. for easier consumption
        during annotation rendering.

        :param label_data: Iterable of label data objects
        :return: Iterable of PreviewRenderData instances
        """
        render_data = []
        for label in label_data:
            _geometry = None
            if label.annotation_type.startswith("polygon"):
                _geometry = label.polygon
            elif label.annotation_type.startswith("bbox"):
                _geometry = label.bbox

            # render_data.append(PreviewRenderData(label.obj_or_entity_name, label.visibility, label.cls,
            #     geometry, label.is_entity, label.annotation_type, ideal_bbox=label.ideal_bbox))
        return render_data