""" A module containing the interface for the extractor, which is the interface designed
to extract and pack geometry data for objects and entities from the scene. Geometry is unified
into a single Label interface.

Classes: Extractor
"""


from abc import abstractmethod, ABCMeta
from typing import Any, Dict, Callable
from contextlib import nullcontext

from .data_structure import *
from ..writing_folder_structure import FolderStructure

class Extractor(metaclass=ABCMeta):
    """
    The main interface for geometry extractors from the render scene, which use ray casting
    inside the camera frustum to generate labels, grouping points reached by rays and imputing them
    to objects and entities. Different extractors may extract different geometries in general.  """

    @abstractmethod
    def extract(self,
            visible_objects,
            classifier,
            entity_data,
            camera,
            estimate_visibility: bool = True,
            rendered_shot_data: Any = None, **kwargs
        ) -> LabelData:
        """ Extract the geometry of the identified objects and label from the scene, the data is
        then packed into LabelData objects which are iterables over a list of labels including geometry data,
        class data.

        Note: LabelData is not specific to the format, but different formats may decide to employ
        different extractors to reduce the computational burden of finding the geometry from the scene
        :param visible_objects: Mapping which associates visible Blender objects to raw point clouds.
        :param classifier: Classifier used to extract entities.
        :param entity_data: Entity data.
        :param camera: Camera used to extract geometry from.
        :param estimate_visibility: If true, estimate the visibility of objects in the scene from the
            canonical bounding box.
        :param rendered_shot_data: the rendered shot as a Blender Image object, with its raw pixel data
        :return: A LabelData object.
        """
        pass

    @abstractmethod
    def get_estimated_visibility(self) -> dict[ str | Any, float]:
        """ Get the estimated visibility for entities and objects """
        pass

    @abstractmethod
    def get_visible_entities(self) -> Iterable[Any]:
        """ Get the entities which are visible in the scene, e.g. those which are
        reachable by ray-casting inside the camera frustum.

        :returns: An iterable over the visible Blender objects
        """
        pass

    def get_labeling_time(self) -> float:
        """ Get the time it took to compute the boxes and the visible objects """
        pass

    def get_visible_objects(self) -> Iterable[Any]:
        """ Get the visible objects """
        pass

    def map_boxes(self, conv_func: Callable = None) -> Iterable[Any]:
        """ Get the camera centered bounding boxes """
        pass

    def get_bbox_objects(self) -> Dict:
        """ Get the mappings from object to bounding boxes """
        pass

    def get_bbox_entities(self) -> Dict:
        """ Get the mappings from object to bounding boxes """
        pass

    @staticmethod
    def declare_folder_structure(folder_strategy: FolderStructure) -> None:
        """

        :param folder_strategy:
        :return:
        """
        # The default implementation ignores the folder structure as it does not
        # require it.
        return

    # Declare this in the parent extractor class as static and not abstract, so only
    # extractors (like per_pixel) which need to override this are influenced.
    @staticmethod
    def needs_folder_structure() -> bool:
        """ Whether this extractor requires a folder structure/IOStrategy to be
        declared via declare_folder_structure() even when there is no real
        OutputWriter for example for preview generation.

        Extractors that write files themselves outside the normal writer
        pipeline should override this to return True so callers without a writer (e.g.
        PreviewGenerator) know to declare a throwaway one.

        :return: False by default.
        """
        return False

    @staticmethod
    def ray_casting_needs() -> dict[str, Any]:
        return {}

    @staticmethod
    def get_context():
        # Default implementation
        return nullcontext()

    @staticmethod
    def prepare_for_shot(shot_idx: int) -> None:
        """

        :param shot_idx:
        :return:
        """
        # For the default implementation, simply ignore the preparation: nothing needs
        # to be set up.
        return

    @staticmethod
    def finalize_shot(shot_idx: int) -> None:
        """

        :param shot_idx:
        :return:
        """
        # For the default implementation, simply ignore the preparation: nothing needs
        # to be set up.
        return
