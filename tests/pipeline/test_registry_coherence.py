""" Cross-registry coherence checks.

Several independent registries in the codebase are all keyed by the same
PipeNames values (constants.py PipeNames): the operation registry, the
validator registry, the UI drawer registry and the schema registry.
Since these are maintained by hand in different files, it's easy for a pipe to be
present into one registry and not in another. This module asserts that
every pipe that is registered somewhere is registered everywhere
"""
import pytest

from ext.constants import PipeNames
from ext.pipeline.operation_registry import OperationRegistry
from ext.pipeline.integrity import ValidatorRegistry
from ext.ui.pipe_editor import OperationDrawerRegistry
from ext.ui.pipe_schema import PipeSchemaRegistry

# Import for side effects: registration happens via decorators at
# class-definition time.
import ext.pipeline.operations
import ext.pipeline.integrity
import ext.ui.pipe_editor
import ext.ui.pipe_schema


REGISTRIES = {
    "operation": OperationRegistry,
    "validator": ValidatorRegistry,
    "drawer": OperationDrawerRegistry,
    "schema": PipeSchemaRegistry,
}

# Pipes that ARE registered somewhere but not everywhere yet, and are
# still work-in-progress (they have (x)" markers in constants.py).
KNOWN_INCOMPLETE_PIPES = {
    PipeNames.BASE_COLOR.value,  # only in validator + drawer
    PipeNames.COLOR.value,       # only in drawer + schema
    PipeNames.NODE_PROP.value,   # only in drawer
}


def _snapshot():
    """{registry_name: set(registered PipeNames.value keys)}"""
    return {name: set(reg.get_all_types()) for name, reg in REGISTRIES.items()}


@pytest.fixture(scope="module")
def registry_snapshot():
    return _snapshot()


# Computed once at collection time (not inside a fixture) so it can drive
# @pytest.mark.parametrize below.
_REGISTERED_PIPE_VALUES = set().union(*_snapshot().values())
_PIPES_TO_CHECK = [p for p in PipeNames if p.value in _REGISTERED_PIPE_VALUES]


def test_no_unknown_keys_registered(registry_snapshot):
    """ Every registered key must correspond to a real PipeNames member.

    Catches typos and auto-completion false positives that would
    otherwise silently create a dead, unreachable registry entry.
    """
    valid_values = {p.value for p in PipeNames}
    for reg_name, keys in registry_snapshot.items():
        unknown = keys - valid_values
        assert not unknown, f"{reg_name!r} registry has keys not in PipeNames: {unknown}"


def test_registries_are_coherent(registry_snapshot):
    """ A pipe registered anywhere must be registered everywhere (not counting
    pipes explicitly marked as known work-in-progress)."""
    all_registered = set().union(*registry_snapshot.values())
    pipes_to_check = all_registered - KNOWN_INCOMPLETE_PIPES

    problems = []
    for pipe in sorted(pipes_to_check):
        missing_from = [name for name, keys in registry_snapshot.items() if pipe not in keys]
        if missing_from:
            problems.append(f"{pipe!r} is missing from: {', '.join(missing_from)}")

    assert not problems, "Registry coherence violations found:" + "\n".join(problems)


@pytest.mark.parametrize("pipe", _PIPES_TO_CHECK, ids=lambda p: p.name)
def test_pipe_registration_status(pipe, registry_snapshot):
    """ A check for each pipe, checking exactly which registrations is not present """
    if pipe.value in KNOWN_INCOMPLETE_PIPES:
        pytest.skip(f"{pipe.value!r} is a known work-in-progress pipe")

    missing = [name for name, keys in registry_snapshot.items() if pipe.value not in keys]
    assert not missing, f"{pipe.value!r} is missing from: {missing}"