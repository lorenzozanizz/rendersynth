from pathlib import Path

from .executable_pipeline import ExecutablePipeline
from .generation import NoViewportUpdate
from .configurations import PreviewRenderConfig, LabelExtractionConfig, RenderConfig
from .orchestrator import LabelingOrchestrator

from ..labeling.generator import LabelData
from ..labeling.bpy_properties import LabelClass
from ..labeling.conversions import convert_geometry_camera_to_absolute_y_inverted, convert_camera_centered_to_absolute_pixels
from ..labeling.ray_casting import geometry_bounds
from ..pipeline.bpy_properties import PipelineData
from ..pipeline.context import NestedPipelineContext

from ..utils.timer import TimingContext
from ..utils.images import (draw_bounding_box, draw_bitmap_text, font_size_fit_box_perc,
                            estimate_text_pixel_height, draw_polygon)

from dataclasses import dataclass
from typing import Dict, Iterable, Literal, Union
import tempfile
import os

import bpy


@dataclass
class PreviewRenderData:
    """
    Data container representing a single annotated object in the preview render.

    Stores all relevant information required to draw annotations such as bounding
    boxes or polygons, including object identity, classification, geometry, and
    visibility. LabelData is converted into a list of such objects before drawing.

    :param obj_name: Name of the object or entity
    :param visibility: Estimated visibility, if computed (0.0 to 1.0 as percentage)
    :param cls: Associated label class
    :param geometry: Geometry representation (bounding box, polygon, or some other structure)
    :param is_entity: Whether the item represents an entity rather than a standard object
    :param type: Type of annotation ("bbox" or "polygon")
    """

    obj_name: str
    visibility: float
    cls: LabelClass

    geometry: Union[
        tuple,  # bbox: (x, y, w, h)
        list[tuple],  # polygon: [(x1,y1), (x2,y2), ...]
        dict  # flexible structure
    ]

    is_entity: bool
    type: Literal["bbox", "polygon"]  # "bbox", "polygon", "depth"

    ideal_bbox: tuple[float, float, float, float] = None


class PreviewGenerator:
    """ Generates a visual preview of a rendered scene with overlaid labeling annotations,
    class names and ids and estimated visibility.

    This class functions both as executor (compiling and executing a pipeline)
    and as a renderer, rendering the scene to a temporary image and overlaying annotation
    data such as bounding boxes, polygons, class labels.
    It also times statistics for debugging and visualization purposes.
    """

    _preview_name = "__randomizer_preview.png"

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
                with TimingContext(self.timings, 'render'):
                    bpy.ops.render.render(write_still=True)

                default_camera = self.ctx.scene.camera
                if not default_camera:
                    self.reporter.report({'WARNING'}, "No default camera was set, no labels preview could be generated")
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

    def display_and_render_preview(self,
                                   show_obj_name: bool = True,
                                   show_class_name_or_id: str = "id",
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
        img = bpy.data.images[PreviewGenerator._preview_name]

        # self.visible is a { object, bounding_box } dictionary, but the extraction may have failed
        if not self.labeling_orchestrator.get_last_label_data():
            return

        width = int(scene.render.resolution_x * scene.render.resolution_percentage / 100)
        height = int(scene.render.resolution_y * scene.render.resolution_percentage / 100)

        render_data = PreviewGenerator.make_preview_render_data(self.labeling_orchestrator.get_last_label_data())
        with TimingContext(self.timings, 'annotating'):
            for data in render_data:

                match_class = data.cls
                # Only classified objects have a bounding box and label info
                if not match_class:
                    continue
                elif ignore_default_class and match_class.name == ignore_default_class:
                    continue
                if data.is_entity and not show_entity:
                    continue

                # Draw the information related to the object, conditional on the render flags and
                # the preview settings.
                self._render_object_info(img, data, width, height,
                     show_class_name_or_id=show_class_name_or_id, show_geometry=show_obj_geometry,
                     show_obj_name=show_obj_name, show_visibility=show_visibility)

        if show_rendering_time:
            self._render_bottom_left_time_stats(img, width)

    def _render_object_info(self, img, data: PreviewRenderData, width: int, height: int,
                            # Flags which are used to conditionally draw various elements in the object info
                            show_geometry: bool = True, show_obj_name: bool = True,
                            show_class_name_or_id: str = "id", show_visibility: bool = True,
                            show_unoccluded_bbox: bool = False) -> None:
        """ Renders information (geometry, object name, class id, estimated visibility) ù
        for a single object starting from its PreviewRanderData

        :param img: the blender img object
        :param width: width of the canvas
        :param height: height of the canvas
        :param show_geometry: whether to show geometry of the object
        :param show_obj_name: whether to show object name
        :param show_class_name_or_id: whether to show class name or id
        :param show_visibility: whether to show estimated visibility
        :param show_unoccluded_bbox: whether to show unoccluded bbox
        """
        # new_xyxy is the bounding box in pixel integer space
        # We have to invert the ys, because blender image pixel API has the y values of the bottom row
        # as 0, which is the opposite way

        # Residue from the old implementation, which could only handle bboxes
        # new_xyxy = convert_camera_centered_to_absolute_pixels_y_inverted(xyxy, width, height)
        # p0 = (new_xyxy[0], new_xyxy[1])
        # p1 = (new_xyxy[2], new_xyxy[3])

        pixel_geo = convert_geometry_camera_to_absolute_y_inverted(data.geometry, width, height)

        color_prop = tuple(data.cls.color)
        color = (color_prop[0], color_prop[1], color_prop[2], color_prop[3])

        # box_width = abs(new_xyxy[0] - new_xyxy[2])
        x_min, y_min, x_max, y_max = geometry_bounds(pixel_geo)
        geometry_width = int(abs(x_max-x_min))
        # Draw the bounding box first, so that the text is visible in all cases, hopefully.
        if show_geometry:
            self._render_geometry(img, color, line_width=7, pixel_space_geometry=pixel_geo)
        if show_unoccluded_bbox:
            unoccluded_pixel_geo = convert_camera_centered_to_absolute_pixels(data.ideal_bbox, width, height)
            self._render_geometry(img, color, line_width=2, pixel_space_geometry=unoccluded_pixel_geo)
        if show_obj_name or (show_class_name_or_id != "none"):

            text = f"" if show_class_name_or_id == "none" else \
                f" {data.cls.name}" if show_class_name_or_id == "name" else f"{data.cls.class_id}"
            if show_obj_name:
                text = f"{data.obj_name}" + (" - " if text else "") + text
            # Generate in a single pass the text to be written, then write it.

            font_size = font_size_fit_box_perc(text, geometry_width, 0.9)
            draw_bitmap_text(
                img, text, (x_min + 20, 10 + y_max + estimate_text_pixel_height("", font_size)),
                color=color, size=font_size)

        if show_visibility:
            # estimated_occlusion = float(estimate_occlusion_3d(obj, self.used_camera, self.ctx, scene.render, xyxy))
            text = f"{int(data.visibility * 100)}%"

            font_size = font_size_fit_box_perc(text, geometry_width, 0.3)
            draw_bitmap_text(img, text, (x_min + 20, y_min - 10),
                             color=color, size=font_size)


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
    def _render_geometry(img, color, pixel_space_geometry, line_width: int = 4) -> None:
        """ Render annotations onto the image (e.g. polygons, bounding boxes etc...).
        Supports both bounding boxes and polygon geometries in pixel space.

        :param img: The image object to draw onto
        :param color: RGBA color tuple
        :param pixel_space_geometry: Geometry in pixel coordinates
        :param line_width: Width of the drawn lines for the geometry
        """
        # Bounding box
        if type(pixel_space_geometry) == tuple:
            new_xyxy = pixel_space_geometry
            p0 = (new_xyxy[0], new_xyxy[1])
            p1 = (new_xyxy[2], new_xyxy[3])
            draw_bounding_box(img, color, p0, p1, y_grows_up_to_down=False, line_width=line_width)
        if type(pixel_space_geometry) == list:
            draw_polygon(img, pixel_space_geometry, color, line_width=line_width)

    @staticmethod
    def make_preview_render_data(label_data: LabelData) -> Iterable[PreviewRenderData]:
        """ Convert LabelData into preview render data structures. for easier consumption
        during annotation rendering.

        :param label_data: Iterable of label data objects
        :return: Iterable of PreviewRenderData instances
        """
        render_data = []
        for label in label_data:
            geometry = None
            if label.annotation_type.startswith("polygon"):
                geometry = label.polygon
            elif label.annotation_type.startswith("bbox"):
                geometry = label.bbox

            render_data.append(PreviewRenderData(label.obj_or_entity_name, label.visibility, label.cls,
                geometry, label.is_entity, label.annotation_type, ideal_bbox=label.ideal_bbox))
        return render_data