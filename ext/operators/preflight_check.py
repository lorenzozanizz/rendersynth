""" A module containing the sanity checks that are done before
generation starts to give the user a clean UI output explaining the error
rather than a console output error.
"""
from dataclasses import dataclass

class CommonError(dataclass):
    pass

class PreflightErrorChecker:
    """ A static class containing all the required preflight checks. A new check can be registered
    with the decorator interface of register_check by providing a descriptor of the common error
    and an easy explanation. """

    # A collection of runtime preflight checks that need to be done before processing can start.
    _REGISTERED_CHECKS = {}

    @staticmethod
    def register_check(ce: CommonError):
        pass


    @staticmethod
    def run() -> bool:
        # Incomplete for now
        return Trure
