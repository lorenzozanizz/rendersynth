""" Serialization, de-serialization and compilation of a Distribution node tree.

This module is the bridge between the bpy node graph (defined in the node-editor
module) and the executable samplers (defined in the compilation module). It holds three independent pieces:

  * NodeDistributionSerializer  - bpy tree            -> plain dict / JSON
  * NodeDistributionDeserializer - plain dict / JSON  -> bpy tree   (rebuilds save files)
  * CompiledNodeTreeSampler     - plain dict          -> CompiledSampler

The serialized format is a graph (node list + link list, addressed by node
name) rather than a nested tree. That keeps it a true DAG (a node feeding two
consumers is stored once), and lets every traversal here be iterative:
- Kahn's algorithm for the compile order,
- a stack-based BFS for reachability,
- and two flat passes for rebuilding

To avoid a circular import with the compilation module (which imports this one),
CompiledNodeTreeSampler does not import the leaf sampler classes. Instead the
caller injects them as a small "kit", i.e. see SamplerCompiler._compile_node_config.
"""

from .sampler import CompiledSampler
from .tree_constants import *
from ..utils.logger import UniqueLogger
from ..utils.parsing import parse_floats

import math
from typing import Any, Optional, Callable

# Small combinator samplers used by the node graph.
#
# These are graph-shaping operations more than primitive distributions, so
# they live next to the compiler. Each conforms to the CompiledSampler interface by duck typing -
# so that no imports of the interface are required in the module

class ConcatSampler:
    """ Concatenate the samples of several child samplers into one vector. """

    def __init__(self, parts: List[Any]):
        self._parts = parts

    @property
    def dimension(self) -> int:
        return sum(p.dimension for p in self._parts)

    def sample(self) -> List[float]:
        out: List[float] = []
        # concatenate the sampled values. The loop really only
        # goes up to 3 values (1d to 3d)
        for p in self._parts:
            out.extend(p.sample())
        return out


class ScaleSampler:
    """ Multiply an N-D distribution by a scalar factor. """

    def __init__(self, factor: Any, vector: Any):
        self._factor = factor
        self._vector = vector

    @property
    def dimension(self) -> int:
        return self._vector.dimension

    def sample(self) -> List[float]:
        f = self._factor.sample()[0]
        return [f * x for x in self._vector.sample()]


class SwapSampler:
    """ Swap two channels of an N-D sample. """

    _PAIRS = {'XY': (0, 1), 'XZ': (0, 2), 'YZ': (1, 2)}

    def __init__(self, source: Any, permutation: str):
        self._source = source
        self._perm = permutation

    @property
    def dimension(self) -> int:
        return self._source.dimension

    def sample(self) -> List[float]:
        v = list(self._source.sample())
        a, b = self._PAIRS[self._perm]
        if a < len(v) and b < len(v):
            v[a], v[b] = v[b], v[a]
        return v


class MathSampler:
    """ Apply a unary or binary scalar op to its (1D) inputs, per sample. """

    # Just a small performance note: obviously doing raw computations like this in
    # python is not really efficient, however I reckon that the most expensive
    # part of processing is largely the rendering section, and that even with
    # hundreds of small operations required, sampling is limited to milliseconds compared
    # to the seconds required to render.
    _OPS: Dict[str, Callable[[float, float], float]] = {
        'NEG': lambda a, b: -a,
        'ABS': lambda a, b: abs(a),
        'EXP': lambda a, b: math.exp(a),
        'LOG': lambda a, b: math.log(a) if a > 0.0 else float('-inf'),
        'ADD': lambda a, b: a + b,
        'SUB': lambda a, b: a - b,
        'MUL': lambda a, b: a * b,
        'DIV': lambda a, b: a / b if b != 0.0 else 0.0,
        'POW': lambda a, b: a ** b,
    }

    def __init__(self, operation: str, a: Any, b: Optional[Any] = None):
        self._op = operation
        self._a = a
        self._b = b

    @property
    def dimension(self) -> int:
        return 1

    def sample(self) -> List[float]:
        av = self._a.sample()[0]
        bv = self._b.sample()[0] if self._b is not None else 0.0
        return [self._OPS[self._op](av, bv)]



class CompiledNodeTreeSampler(CompiledSampler):
    """ A compiled distribution graph. Conforms to the CompiledSampler interface.

    Construction compiles every node reachable from the Root into a leaf/combinator
    sampler and wires them together; sampling delegates to the Root's input.

    Leaf samplers are injected via a small kit (really a dictionary with keys 'constant',
     'preset', 'selector') so this module never imports the compilation module
    """

    # bl_idname -> builder method name. Extend by adding a method + entry.
    # For a note on performance, saw the note above in MathSampler
    _BUILDERS: Dict[str, str] = {
        'DistributionRootNode':       '_build_root',
        'DistributionConstantNode':   '_build_constant',
        'DistributionContinuousNode': '_build_continuous',
        'DistributionDiscreteNode':   '_build_discrete',
        'DistributionSelectorNode':   '_build_selector',
        'DistributionVectorizeNode':  '_build_vectorize',
        'DistributionSwapNode':       '_build_swap',
        'DistributionScaleNode':      '_build_scale',
        'DistributionMathNode':       '_build_math',
    }

    def __init__(self, data: Dict[str, Any], kit: Dict[str, Callable]):
        self._kit = kit
        self._root = self._compile(data)

    @property
    def dimension(self) -> int:
        return self._root.dimension

    def sample(self) -> List[float]:
        """ Sample from the full compile distributions, iterating in topological order """
        return self._root.sample()

    def _compile(self, data: Dict[str, Any]):
        """

        :param data:
        :return:
        """
        nodes_by_id = {nd['id']: nd for nd in data.get('nodes', [])}
        root_id = data.get('root')
        if root_id is None or root_id not in nodes_by_id:
            raise ValueError("Distribution graph has no Root node")

        # incoming[node_id][to_socket] = from_node_id
        incoming: Dict[str, Dict[int, str]] = {nid: {} for nid in nodes_by_id}
        for lk in data.get('links', []):
            tgt = lk['to_node']
            src = lk['from_node']
            if tgt in incoming and src in nodes_by_id:
                incoming[tgt][lk['to_socket']] = src

        deps = {nid: set(incoming[nid].values()) for nid in nodes_by_id}

        # Reachability from the root (iterative, stack-based), ignore orphans nodes
        # that can be created in the Blender editor
        reachable: set = set()
        stack = [root_id]
        while stack:
            nid = stack.pop()
            if nid in reachable:
                continue
            reachable.add(nid)
            stack.extend(deps[nid])

        # topological sort restricted to the reachable sub-graph
        in_deg = {nid: len(deps[nid] & reachable) for nid in reachable}
        dependents: Dict[str, List[str]] = {nid: [] for nid in reachable}
        for nid in reachable:
            for d in deps[nid] & reachable:
                dependents[d].append(nid)

        queue = [nid for nid, deg in in_deg.items() if deg == 0]
        order: List[str] = []
        while queue:
            nid = queue.pop()
            order.append(nid)
            for m in dependents[nid]:
                in_deg[m] -= 1
                if in_deg[m] == 0:
                    queue.append(m)

        if len(order) != len(reachable):
            # If a cycle is present, something is wrong with the distribution that
            # makes it impossible to sample from. Good distributions should be
            # trees.
            raise ValueError("Distribution graph has a cycle")

        compiled: Dict[str, Any] = {}
        for nid in order:
            nd = nodes_by_id[nid]
            inputs = self._ordered_inputs(nd, incoming[nid], compiled)
            compiled[nid] = self._dispatch(nd, inputs)
        return compiled[root_id]

    def _ordered_inputs(self, nd, incoming_map, compiled) -> List[Optional[Any]]:
        """ Resolve a node's inputs in socket order.

        A socket is, in priority: a linked upstream sampler; else a typed-in
        scalar default (wrapped in a constant sampler); else None (an
        unconnected distribution socket left for the builder to reject).
        """
        defaults = {int(k): v for k, v in nd.get('input_defaults', {}).items()}
        n = -1
        for k in incoming_map:
            n = max(n, k)
        for k in defaults:
            n = max(n, k)

        result: List[Optional[Any]] = []
        for i in range(n + 1):
            if i in incoming_map:
                result.append(compiled[incoming_map[i]])
            elif i in defaults:
                # For default nodes, we have to append a default node on the fly.
                # Blender has the possibility of specifying default values for every
                # input socket
                result.append(self._kit['constant'](defaults[i]))
            else:
                result.append(None)
        return result

    def _dispatch(self, nd, inputs):
        bl = nd['bl_idname']
        # Get the builder corresponding to the node name
        name = self._BUILDERS.get(bl)
        if name is None:
            raise ValueError(f"No compiler registered for node type '{bl}'")

        # call the build function with the inputs to the node, the topological ordering
        # forces the inputs to be already compiled at this call.
        return getattr(self, name)(nd.get('params', {}), inputs)

    def _build_root(self, _p, inputs):
        """ Builds the root node """
        # The root node is unique and requires a connection.
        # this reduces to just ignoring the root and returning its first and only
        # input, as the root makes no computation and only serves to induce an ordering.
        if not inputs or inputs[0] is None:
            raise ValueError("Root node has no connected distribution")
        return inputs[0]

    def _build_constant(self, p, _inputs):
        """ Build a constant node"""
        if p.get('mode', 'SCALAR') == 'SCALAR':
            return self._kit['constant'](p.get('scalar_val', 0.0))

        # If we're here, we have a vectorial constant
        dim = int(p.get('vec_dim', 2))
        comps = [p.get('scalar_val', 0.0), p.get('vec2', 0.0), p.get('vec3', 0.0)][:dim]
        # To handle vector constants, the concatenate the values to create a vector in the compiled
        # graph
        return ConcatSampler([self._kit['constant'](c) for c in comps])

    def _build_continuous(self, p, _inputs):
        """ Build a continuous node from a repository of present continuous distributions """
        # A small note on inputs:
        # Note that the standard deviations, means etc... are not inputs themselves, rather
        # they are parameters, this disallows models like the standard normal/normal where
        # a parameter to a distribution may be the output of a previous random distribution.
        # This is currently NOT implemented, but may be added in the future
        preset = self._kit['preset']
        dt = p['dist_type']
        if dt == 'NORMAL':
            dim = int(p.get('dimension', 1))
            means = [p.get('mean', 0.0), p.get('mean_y', 0.0), p.get('mean_z', 0.0)][:dim]
            if dim == 1:
                return preset({'preset': 'GAUSSIAN',
                               'parameters': {'mean': means[0], 'std': p.get('sigma', 1.0)}}, 1)
            if p.get('normal_cov', 'ISOTROPIC') == 'ISOTROPIC':
                sigmas = [p.get('sigma', 1.0)] * dim
            else:  # DIAGONAL: independent sigma per axis (diagonal covariance)
                sigmas = [p.get('sigma', 1.0), p.get('sigma_y', 1.0), p.get('sigma_z', 1.0)][:dim]
            axes = [preset({'preset': 'GAUSSIAN',
                            'parameters': {'mean': means[i], 'std': sigmas[i]}}, 1)
                    for i in range(dim)]
            return ConcatSampler(axes)
        if dt == 'UNIFORM':
            return preset({'preset': 'UNIFORM',
                           'parameters': {'min': p.get('low', 0.0), 'max': p.get('high', 1.0)}}, 1)
        if dt == 'BETA':
            return preset({'preset': 'BETA',
                           'parameters': {'alpha': p.get('alpha', 1.0), 'beta': p.get('beta', 1.0),
                                          'min': 0.0, 'max': 1.0}}, 1)
        raise NotImplementedError(
            f"Continuous '{dt}' is not compiled yet - add a branch in _build_continuous")

    def _build_discrete(self, p, inputs):
        preset = self._kit['preset']
        dt = p['dist_type']
        if dt == 'BINOMIAL':
            return preset({'preset': 'BINOMIAL',
                           'parameters': {'n': p.get('n_trials', 1), 'p': p.get('p_success', 0.5)}}, 1)
        raise NotImplementedError(
            f"Discrete '{dt}' is not compiled yet - add a branch in _build_discrete")

    def _build_selector(self, p, inputs):
        samplers = [s for s in inputs if s is not None]
        if not samplers:
            raise ValueError("Selector has no connected inputs")
        weights = parse_floats(p.get('weights', '')) or [1.0] * len(samplers)
        if len(weights) != len(samplers):
            UniqueLogger.quick_log(
                f"Selector weight count {len(weights)} != inputs {len(samplers)}; padding/trimming")
            weights = (weights + [0.0] * len(samplers))[:len(samplers)]
        return self._kit['selector'](samplers, weights)

    def _build_vectorize(self, _p, inputs):
        """ Build a vectorize node by just concatenating its components """
        parts = [s for s in inputs if s is not None]
        if not parts:
            raise ValueError("Vectorize has no connected inputs")
        return ConcatSampler(parts)

    def _build_swap(self, p, inputs):
        """ Build a swap node dependngin on the type of swap"""
        if not inputs or inputs[0] is None:
            raise ValueError("Swap has no connected input")
        # By default swap to XY, shouldn't ever happen in theory
        return SwapSampler(inputs[0], p.get('permutation', 'XY'))

    def _build_scale(self, p, inputs):
        """ Build a scale node to scale the magnitude of a vector """
        if len(inputs) < 2 or inputs[1] is None:
            raise ValueError("Scale needs a connected Vector input")
        factor = inputs[0] if inputs[0] is not None else self._kit['constant'](1.0)
        return ScaleSampler(factor, inputs[1])

    def _build_math(self, p, inputs):
        """ Build a math node performing an operation """
        a = inputs[0] if inputs else None
        if a is None:
            raise ValueError("Math node has no input A")
        b = inputs[1] if len(inputs) > 1 else None
        return MathSampler(p.get('operation', 'ADD'), a, b)

