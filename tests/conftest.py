import sys
import types
from math import sqrt
from unittest.mock import MagicMock


# Create a real Vector class since mathutils is mocked
class Vector:
    def __init__(self, values):
        self.values = list(values)

    def __getitem__(self, index):
        return self.values[index]

    def __setitem__(self, index, value):
        self.values[index] = value

    def __iter__(self):
        return iter(self.values)

    def __sub__(self, other):
        return Vector([a - b for a, b in zip(self.values, other.values)])

    def __add__(self, other):
        return Vector([a + b for a, b in zip(self.values, other.values)])

    def __mul__(self, scalar):
        return Vector([v * scalar for v in self.values])

    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    @property
    def length(self):
        return sqrt(sum(v ** 2 for v in self.values))

    def __repr__(self):
        return f"Vector({self.values})"

    def __eq__(self, other):
        return self.values == other.values

# The addon subclasses things like bpy.types.Node, bpy.types.PropertyGroup,
# bpy.types.Operator, nodeitems_utils.NodeCategory, etc. and because of that
# a bare MagicMock() cannot stand in for inheritance, which
# doesn't raise, but produces a `Foo` that is itself a MagicMock
# rather than a real type, which then breaks anything that treats Foo as a
# class later (e.g. legacy type hints, isinstance checks, any other
# subclassing).
#
# Instead, any attribute access under this namespace lazily creates and
# caches a real, trivial class with that name.
class _AutoStubNamespace(types.ModuleType):
    def __getattr__(self, name):
        stub = type(name, (), {"__init__": lambda self, *a, **k: None})
        setattr(self, name, stub)
        return stub


bpy_types = _AutoStubNamespace("bpy.types")
bpy_props = _AutoStubNamespace("bpy.props")
nodeitems_utils_mod = _AutoStubNamespace("nodeitems_utils")

bpy_mock = MagicMock()
bpy_mock.types = bpy_types
bpy_mock.props = bpy_props

sys.modules['bpy'] = bpy_mock
sys.modules['bpy.types'] = bpy_types
sys.modules['bpy.props'] = bpy_props
sys.modules['nodeitems_utils'] = nodeitems_utils_mod

# gpu / gpu_extras are only used for viewport drawing (drawing callbacks,
# shaders); nothing in this codebase subclasses them, so a plain MagicMock
# is sufficient here (unlike bpy.types / nodeitems_utils above).
sys.modules['gpu'] = MagicMock()
sys.modules['gpu_extras'] = MagicMock()
sys.modules['gpu_extras.batch'] = MagicMock()

# Mock mathutils with our real Vector
mathutils_mock = MagicMock()
mathutils_mock.Vector = Vector
sys.modules['mathutils'] = mathutils_mock