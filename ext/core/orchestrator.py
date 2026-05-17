""" The amin classes entrusted with the interface of the labelingOrchestrator, which is an abstractionto
let the executor for previews and batch generation not know about the implementation details fo the
label generation process.

Classes: LabelingOrchestrator
"""
from contextlib import AbstractContextManager
from typing import Dict, Collection, Any, Optional, Union

from pathlib import Path
from .configurations import LabelExtractionConfig, RenderConfig, GenerationConfig, BatchMetadata

from .io import OutputWriter
from ..labeling import PolygonExtractor

from ..labeling.generator import LabelData
from ..labeling.class_engine import ClassificationEngine
from ..labeling.generator import Extractor, BoundingBoxExtractor
from ..labeling.generator.point_clouds import PointCloudExtractor
from ..labeling.ray_casting import get_visible_objects_from_camera
from ..utils.other import MultiContext


class LabelingOrchestrator:
    """ The main class entrusted of the labeling process, which is entrusted with processing the scene data
     and generating labels based on the render configuration and the labeling format chosen by the user.
     The orchestrator manages the  IOWriter writing transactions, and propagates the end of generation
     and beginning of generation hooks to allow asynchronous writing (e.g. non 1-per-frame label)
     """

    def __init__(self, context, config: LabelExtractionConfig, reporter, writer: Optional[OutputWriter]):
        """ Initialize a LabelingOrchestrator object with the LabelingExtractorOrchestrator, the reporter, which is used
        to mark errors and warning in the extraction process, and the IOWriter which is used internally
        to propagate generate labels and propagate end and beginning of generation hooks. """

        self.config = config
        self.ctx = context

        # To report issues and errors in the generation
        self.reporter = reporter

        self.classifier = ClassificationEngine(self.ctx)
        self.visible_objects = None

        # Explicitly instantiate the label formatter and extractor based on the configuration
        self.extractor: Extractor = self._create_extractor()

        self.writer: OutputWriter = writer

        self.label_data = None

    def process_shot(self, render_cfg: RenderConfig, rendered_data_path: Union[Path | str], depsgraph) -> None:
        """ The orchestrator processes the shot obtaining the render config from the
        RendereConfig object which contains info about the camera, the width and the height of the current
        scene image. The shot is processed by extracting the labels from the image with ray casing
        using extractors depending on the label format.

        While processing the shot, the scene is evaluated with the Blender dependency graph.
        Labeling data is then generated with the extracted content, the label themselves are unordered
        and added to the same LabelData object

        :param render_cfg: The configuration of the rendered shot, including camera, width, height,
            etc...
        :param rendered_data_path: The path of the rendered shot, to be used when extracting pixel color data
        :param depsgraph: The dependency graph used to evaluate the scene when computing the ray casting points
        :return:
        """
        # Extract the visible objects from the scene, this corresponds to a dictionary mapping
        # blender 'Object' to a point cloud representing raytracing hits. Depending on the
        # labeling type, this becomes a polygon or a box or depth data (TBI)

        # Step 1] Extract the entity data from the scene, which is to be used by the extractor to
        # compose together multi-object entities.
        entity_scene_data = self.classifier.extract_entity_data()

        # Step 2] Extract the visible entities which are going to be bound and classified by the
        # extractor and classifier

        # Provide a default value for certain parameters, le the extractor express its needs for ray
        # casting.
        casting_params = {
            'resolution_x': int(self.ctx.scene.render.resolution_x * self.config.ray_casting_ratio),
            'resolution_y': int(self.ctx.scene.render.resolution_y * self.config.ray_casting_ratio)
        }
        casting_params.update(self.extractor.ray_casting_needs())

        self.visible_objects = get_visible_objects_from_camera(
            self.ctx.scene, depsgraph, render_cfg.camera,
            **casting_params, compute_mapping=True,
        )

        # Compute the bbox/polygon/etc from the scene using the given camera and ray tracing
        self.classifier.classify_visible_objects(
            self.visible_objects.keys()
        )

        self.label_data: LabelData = self.extractor.extract(
            visible_objects=self.visible_objects,
            classifier=self.classifier,
            entity_data=entity_scene_data,
            camera=render_cfg.camera,
            estimate_visibility=self.config.estimate_visibility,
            rendered_shot_data=rendered_data_path
        )

        if self.config.write_labels and self.writer is not None:
            # files = self.formatter.format(self.label_data, render_config)
            self.writer.write_shot(self.label_data, render_cfg)

        return

    def begin_generation(self, gen_cfg: GenerationConfig) -> AbstractContextManager:
        """

        :return:
        """
        # Propagate the beginning of generation hook to the writer.
        # the batch config is used to aggregate the data at the end of generation
        batch_metadata = BatchMetadata(
            gen_cfg.amount,
            self.classifier.get_classes()
        )
        self.writer.begin_batch(batch_metadata)

        writing_ctx = self.writer.get_context()
        extraction_ctx = self.extractor.get_context()

        return MultiContext(writing_ctx, extraction_ctx)

    def end_generation(self) -> None:
        """ Hook for the end of generation of the orchestrator. Internally, this
        prompts the IOWriter to end the processing batch and write aggregate files.
        """
        # Propagate the end of generation to the writer.
        self.writer.end_batch()

    def _create_extractor(self):
        return PointCloudExtractor(self.ctx)

    def get_last_label_data(self) -> Optional[LabelData]:
        """ Get the last lLabelData generated by the orchestrator """
        return self.label_data

    def get_raw_visible_data(self) -> dict[Any, Collection]:
        """ Get hte raw visible data, which is obtained by the orchestrator by computing
        ray casts and marking objects hich are hit by rays as being visible in the scene.

        :return: A dictionary where blender objects are associated with the ray-casted
        points in the normalized camera frustum space.
        """
        return self.visible_objects

    # ----- A set of timing routines to provide an interface to display them in the preview -----

    def get_timings(self) -> Dict[str, float]:
        """ """
        pass

    def get_raytracing_timing(self) -> float:
        """ """
        pass

    def get_classification_timing(self) -> float:
        """ """
        pass

    def get_io_timing(self) -> float:
        """ """
        pass