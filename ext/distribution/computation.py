"""
The rationale is that the Distribution tree is compiled into a set of these subclasses so that the
extraction of data can happen without interrogating the bpy data component every time.


"""

from .tree_writing import NodeDistributionSerializer
from ..constants import WidgetSerializationKeys, DISTRO_EDITOR_NAME
from ..utils.logger import UniqueLogger
from ..utils.math_funcs import geometric, pick_k_from_n

from enum import Enum
from math import pi, sqrt, cos, sin
from abc import abstractmethod, ABCMeta
from typing import List, Dict, Any, Callable

import random
import numpy as np

import bpy

wsk = WidgetSerializationKeys

# Use a common sampling raw distribution for all kinds of entries, in this way
# we can apply the seed to this single RNG and obtain reproducibility.
class Distribution(Enum):
    """ An enum for the supported distributions, all these distributions are available
    in the simple distribution editor and can be customized with parameters which
    are taken from the mathematical definition of the distribution.

    """

    BERNOULLI                       = "Bernoulli"
    UNIFORM                         = "Uniform"
    BETA                            = "Beta"
    GEOMETRIC                       = "Geometric"
    BINOMIAL                        = "Binomial"
    GAUSSIAN                        = "Gaussian"
    CATEGORICAL_UNIFORM             = "Categorical Uniform"

    UNIFORM_K_OUT_OF_N              = "Uniform K out of N"
    UNIFORM_SPHERE                  = "Uniform Sphere"
    MULTIVARIATE_UNIFORM            = "Multivariate Uniform"
    MULTIVARIATE_GAUSSIAN           = "Multivariate Gaussian"
    MULTIVARIATE_ISOTROPIC_GAUSSIAN = "Multivariate Isotropic Gaussian"

    NONE                            = "None"

# One dimensional distributions to be used when the datatype to be randomized is scalar
ONE_D_DISTRIBUTIONS = (
    Distribution.UNIFORM, Distribution.GEOMETRIC, Distribution.GAUSSIAN,
    Distribution.BETA, Distribution.BINOMIAL, Distribution.BERNOULLI, Distribution.CATEGORICAL_UNIFORM
)

# These are the distributions available for multidimensional distributions. In reality, it is
# also possible to change this to have 2D and 3D separately
UPPER_D_DISTRIBUTIONS = (
    Distribution.MULTIVARIATE_UNIFORM, Distribution.MULTIVARIATE_GAUSSIAN, Distribution.MULTIVARIATE_ISOTROPIC_GAUSSIAN
)

class CompiledSampler(metaclass=ABCMeta):
    """Base sampler interface"""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return dimensionality of samples"""
        pass

    @abstractmethod
    def sample(self) -> List[float]:
        """Sample a vector of shape (dimension,)"""
        pass


class SphereDistribution(CompiledSampler):

    def __init__(self, params: dict, _dim: int = 3) -> None:
        """ """
        self.center = params['center']
        self.radius = params['radius']

    @property
    def dimension(self) -> int:
        """ """
        # Again, we assume this to be 3.
        return 3

    def sample(self) -> List[float]:
        """

        :return:
        """
        x, y, z = self.center
        # We use a standard ( a bit less than naive ) sampling technique for the sphere, to avoid
        # oversampling near the poles. We sample the polar coordinates uniformly, then convert the
        # point to a cartesian coordinate.
        # Uniform longitude [0, 2π]
        theta = 2 * pi * random.random()

        # Uniform on sphere (not uniform in latitude!)
        # cos(phi) uniform in [-1, 1] ensures uniform surface distribution
        cos_phi = 2 * random.random() - 1
        sin_phi = sqrt(1 - cos_phi ** 2)

        # Convert to Cartesian
        px = x + self.radius * sin_phi * cos(theta)
        py = y + self.radius * sin_phi * sin(theta)
        pz = z + self.radius * cos_phi

        return [px, py, pz]

class ConstantSampler(CompiledSampler):
    def __init__(self, value: float):
        self._value = value

    @property
    def dimension(self) -> int:
        return 1

    def sample(self) -> List[float]:
        return [self._value]

class PresetSampler(CompiledSampler):
    """ The main class for the compilation and utilization of preset distributions,
    encompassing sampling and randomization logic by assigning to distributions a mathematical
     implementation.

    The class represents a CompiledSampler which allows to sample from a default distribution,
     which can be concatenated and alternated in a node-like fashion
    """

    @staticmethod
    def _sample_k_out_of_n(params: dict, dim: int):
        n = params['n']
        k = params['k']
        return [ pick_k_from_n(n, k) for _ in range(dim)]

    @staticmethod
    def _sample_categorical_uniform(params: Dict[str, Any], dim: int ):
        """

        :param params:
        :param dim:
        :return:
        """
        n = params['n']
        return [random.randint(0, n) for _ in range(dim)]

    @staticmethod
    def _sample_uniform(params: Dict[str, Any], dim: int):
        return [random.uniform(params['min'], params['max']) for _ in range(dim)]

    @staticmethod
    def _sample_bernoulli(params: Dict[str, Any], dim: int):
        return [1 if random.random() < params['p'] else 0 for _ in range(dim)]

    @staticmethod
    def _sample_beta(params: Dict[str, Any], dim: int):
        offs = params['min']
        ratio = params['max']-params['min']
        return [offs + ratio*random.betavariate(params['alpha'], params['beta']) for _ in range(dim)]

    @staticmethod
    def _sample_geometric(params: Dict[str, Any], dim: int):
        return [geometric(params['p']) for _ in range(dim)]

    @staticmethod
    def _sample_binomial(params: Dict[str, Any], dim: int):
        return [int(np.random.binomial(params['n'], params['p'])) for _ in range(dim)]

    @staticmethod
    def _sample_gaussian(params: Dict[str, Any], dim: int):
        return [random.normalvariate(params['mean'], params['std']) for _ in range(dim)]

    @staticmethod
    def _sample_uniform_sphere(params: Dict[str, Any], dim: int):
        dis = SphereDistribution(params['center'], params['radius'])
        return dis.sample()

    @staticmethod
    def _sample_multivariate_uniform(params: Dict[str, Any], dim: int):
        max_vect = params['max_vec']
        min_vect = params['min_vec']
        return [random.uniform(min_vect[i], max_vect[i]) for i in range(dim)]

    @staticmethod
    def _sample_multivariate_gaussian(params: Dict[str, Any], dim: int):
        # Currently a stub: the problem is expressing all 9 covariate
        # coefficients in the UI.
        return [0 for _ in range(dim)]

    @staticmethod
    def _sample_isotropic_gaussian(params: Dict[str, Any], dim: int):
        mean_vec = params['mean_vec']
        std = params['variance']
        if len(mean_vec) != dim:
            raise ValueError(f"mean length {len(mean_vec)} != dimension {dim}")

        return [random.gauss(mean_vec[i], std) for i in range(dim)]

    @staticmethod
    def _get_sampler(type_e: Distribution) -> Callable:
        """

        :param type_e:
        :return:
        """
        d = Distribution
        dis = {
            d.NONE:                             lambda _1, _2: None,
            d.UNIFORM:                          PresetSampler._sample_uniform,
            d.BERNOULLI:                        PresetSampler._sample_bernoulli,
            d.BETA:                             PresetSampler._sample_beta,
            d.GEOMETRIC:                        PresetSampler._sample_geometric,
            d.BINOMIAL:                         PresetSampler._sample_binomial,
            d.GAUSSIAN:                         PresetSampler._sample_gaussian,
            d.UNIFORM_K_OUT_OF_N:                       PresetSampler._sample_k_out_of_n,
            d.CATEGORICAL_UNIFORM:              PresetSampler._sample_categorical_uniform,
            d.MULTIVARIATE_UNIFORM:             PresetSampler._sample_multivariate_uniform,
            d.MULTIVARIATE_GAUSSIAN:            PresetSampler._sample_multivariate_gaussian,
            d.UNIFORM_SPHERE:                   PresetSampler._sample_uniform_sphere,
            d.MULTIVARIATE_ISOTROPIC_GAUSSIAN:  PresetSampler._sample_isotropic_gaussian
        }[type_e]
        UniqueLogger.quick_log("I GOT THE SAMPLER: " + dis.__str__())
        return dis

    def __init__(self, config: Dict[str, Any], dim):
        """

        :param config:
        :param dim:
        """

        self.config = config
        self.dim = dim

        self.params = None
        self.type = Distribution.NONE
        # This attribute will be "not None" and equal to a tuple of values if
        # clamping is to be enabled
        self.clamp = None
        self.discretize = False

        self._compile()

    def _compile(self):
        """

        :return:
        """
        try:
            self.type = Distribution[self.config['preset']]
        except KeyError:
            self.type = None
            return
        self.discretize = self.config.get("do_discretize")
        if self.config.get("do_clamp"):
            self.clamp = tuple(self.config["clamping_factors"])

        self.params = self.config.get("parameters")


    @property
    def dimension(self) -> int:
        return self.dim

    def sample(self) -> List[float]:
        """

        :return:
        """
        if self.type is None or self.type == Distribution.NONE:
            return [0]*self.dim
        sampler = PresetSampler._get_sampler(self.type)
        values =  sampler(dim=self.dim, params=self.params)
        if self.discretize:
            for i in range(len(values)):
                values[i] = int(values[i])
        if self.clamp is not None:
            for i in range(len(values)):
                values[i] = min(self.clamp[1], max(values[i], self.clamp[0]))
        return values

class SelectorSampler(CompiledSampler):
    """Select one of multiple samplers with given weights"""

    def __init__(self, samplers: List[CompiledSampler], weights: List[float]):
        self.samplers = samplers
        self.weights = weights

        # Validate all have same dimension
        dims = set(s.dimension for s in samplers)
        if len(dims) != 1:
            raise ValueError(f"All samplers must have same dimension, got {dims}")
        self._dimension = samplers[0].dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def sample(self) -> List[float]:
        sampler = random.choices(self.samplers, weights=self.weights, k=1)[0]
        return sampler.sample()


class VectorSampler(CompiledSampler):
    """Combine scalar samplers into a vector"""

    def __init__(self, samplers: List[CompiledSampler]):
        # Each sampler must be 1D
        if any(s.dimension != 1 for s in samplers):
            raise ValueError("VectorSampler requires all inputs to be 1D")
        self.samplers = samplers

    @property
    def dimension(self) -> int:
        return len(self.samplers)

    def sample(self) -> List[float]:
        result = []
        for sampler in self.samplers:
            result.extend(sampler.sample())
        return result


class SamplerCompiler:
    """Compile JSON config to executable Sampler"""

    @staticmethod
    def compile(config: Dict[str, Any], dim) -> CompiledSampler:
        """Compile either simple or node-graph config"""
        use_tree = config['use_tree']
        if use_tree in config:
            # Node-graph format
            return SamplerCompiler._compile_node_config(config, dim)
        else:
            # Simple format (direct distribution with given dimension)
            return SamplerCompiler._compile_simple_config(config, dim)

    @staticmethod
    def make_distribution(op_type: str, dim: int, **kwargs):
        """ Generate a distribution given its type and its parameters. This is to be
         used to access the capabilities offered by the distribution interface in
         other sections of the code. The distribution type must be one recognized.

        :param dim: The dimension of the distribution
        :param op_type: the type of operation to perform
        :param kwargs: additional arguments
        :return: a Sampler object for the distribution.
        """
        return PresetSampler({
            'preset': op_type,
            "parameters": dict(**kwargs),
        }, dim)

    @staticmethod
    def _compile_simple_config(config: Dict[str, Any], dim: int = 1) -> CompiledSampler:
        """Compile simple preset distribution"""
        return PresetSampler(config, dim = dim)

    @staticmethod
    def _compile_node_config(config: Dict[str, Any], dim: int = 1) -> CompiledSampler:
        """Compile node-graph format"""

        # Extract the relevant node from bpy.data node tree for the
        # given distribution name
        name = config['distribution']
        tree = next(
            (ng for ng in bpy.data.node_groups
             if ng.bl_idname == DISTRO_EDITOR_NAME and ng.name == name),
            None
        )
        root_config = NodeDistributionSerializer.serialize(tree)
        compiled_nodes = {}  # node_id -> Sampler

        # First pass: topological sort by traversing backwards from root
        visit_order = []
        visited = set()

        def visit(cfg):
            n_id = id(cfg)
            if n_id in visited:
                return
            visited.add(n_id)

            # Visit inputs first
            if 'inputs' in cfg:
                for input_config in cfg['inputs']:
                    visit(input_config)

            visit_order.append(cfg)

        visit(root_config)

        # Second pass: compile in dependency order
        for config in visit_order:
            node_type = config.get('type')
            node_id = id(config)

            if node_type == 'constant':
                compiled_nodes[node_id] = ConstantSampler(config['value'])

            elif node_type == 'preset':
                dist_name = config['preset']
                dimension = 1
                compiled_nodes[node_id] = SamplerCompiler._compile_simple_config(dist_name, dimension)

            elif node_type == 'selector':
                # Inputs already compiled
                input_samplers = [
                    compiled_nodes[id(input_cfg)]
                    for input_cfg in config['inputs']
                ]
                weights = config['weights']
                compiled_nodes[node_id] = SelectorSampler(input_samplers, weights)

            elif node_type == 'vector_assemble':
                # Inputs already compiled
                input_samplers = [
                    compiled_nodes[id(input_cfg)]
                    for input_cfg in config['inputs']
                ]
                compiled_nodes[node_id] = VectorSampler(input_samplers)

            else:
                raise ValueError(f"Unknown node type: {node_type}")

        return compiled_nodes[id(root_config)]
