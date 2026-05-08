from typing import Iterable

from .extractor import Extractor
from .data_structure import *

class LandmarksExtractor(Extractor):

    def extract(self, visible_objects, classifier, entity_data, camera, estimate_visibility: bool = True,
                **kwargs) -> LabelData:
        """

        :param visible_objects:
        :param classifier:
        :param entity_data:
        :param camera:
        :param estimate_visibility:
        :param kwargs:
        :return:
        """
        pass

    def get_estimated_visibility(self) -> dict[str | Any, float]:
        pass

    def get_visible_entities(self) -> Iterable[Any]:
        pass