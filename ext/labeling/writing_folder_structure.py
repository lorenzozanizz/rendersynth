"""

"""
from abc import ABCMeta, abstractmethod
from typing import Union, Literal
from os import makedirs


class FolderStructure(metaclass=ABCMeta):

    @abstractmethod
    def get_subdir_for(self, shot_id: Union[int, ], f_type: str | Literal["image"]) -> str:
        """

        :param shot_id:
        :param f_type:
        :return:
        """
        pass

    @abstractmethod
    def get_filename_for(self, shot_id: Union[int,  ], f_type: str | Literal["image"]) -> str:
        """

        :param shot_id:
        :param f_type:
        :return:
        """
        pass

    @abstractmethod
    def ensure_directories(self) -> None:
        """ Create all the required directories for the given IO strategy """
        pass

    @staticmethod
    def _make_dirs(dirs: list[str]) -> None:
        """

        :param dirs:
        :return:
        """
        for directory in dirs:
            makedirs(directory, exist_ok=True)

