"""

"""
from abc import ABCMeta, abstractmethod
from typing import Union, Literal
from os import makedirs

class FolderStructure(metaclass=ABCMeta):

    @abstractmethod
    def get_subdir_for(self, shot_id: Union[int, ], f_type: str | Literal["image"]) -> str:
        """ Get the name of the subdirectory for the given file type and shot id. The
        interface allows for different shot ids to be positioned at different directories.
        Naturally all possible directories need to be instantiated.

        :param shot_id: The id of the shot
        :param f_type: The type of file being written, user defined
        :return: the name of the subdir
        """
        pass

    @abstractmethod
    def get_filename_for(self, shot_id: Union[int,  ], f_type: str | Literal["image"]) -> str:
        """ Get the name of the file for a given shot id and file type (user defined)

        :param shot_id: The id of the shot
        :param f_type: The type of file being written, user defined
        :return: the filename
        """
        pass

    @abstractmethod
    def ensure_directories(self) -> None:
        """ Create all the required directories for the given IO strategy """
        pass

    @staticmethod
    def _make_dirs(dirs: list[str]) -> None:
        """ A small private utility function which simply creates
        all directories in a given list of strings.

        :param dirs: list of directory substrings (full paths or relative)
        """
        for directory in dirs:
            makedirs(directory, exist_ok=True)
