"""




"""

from ..constants import DISTRO_EDITOR_NAME

from bpy.types import Node, NodeTree, NodeSocket
from bpy.props import StringProperty, EnumProperty, FloatProperty, IntProperty, BoolProperty
from nodeitems_utils import NodeCategory
from typing import Optional


# CONSTANTS declarations for this module, e.g. stuff that is used for the
# various categorical attributes and to define which node types are vailable.

MATH_OPS = [
    ('NEG', 'Neg', ''), ('ABS', 'Abs', ''), ('EXP', 'Exp', ''), ('LOG', 'Log', ''),
    ('ADD', 'Add', ''), ('SUB', 'Sub', ''), ('MUL', 'Mul', ''), ('DIV', 'Div', ''),
    ('POW', 'Pow', '')
]

_UNARY_OPS = {'NEG', 'ABS', 'EXP', 'LOG'}


VECTORIZE_MODES = [
    ('1_1',   '1D + 1D > 2D',        ''),
    ('1_1_1', '1D + 1D + 1D > 3D',   ''),
    ('2_1',   '2D + 1D > 3D',         ''),
    ('1_2',   '1D + 2D > 3D',         ''),
]

_VECTORIZE_INPUTS = {
    '1_1':   [(1, 'X'), (1, 'Y')],
    '1_1_1': [(1, 'X'), (1, 'Y'), (1, 'Z')],
    '2_1':   [(2, 'XY'), (1, 'Z')],
    '1_2':   [(1, 'X'), (2, 'YZ')],
}

_VECTORIZE_OUT_DIM = {'1_1': 2, '1_1_1': 3, '2_1': 3, '1_2': 3}

CONTINUOUS_TYPES = [
    ('NORMAL',      'Normal',      ''),
    ('UNIFORM',     'Uniform',     ''),
    ('EXPONENTIAL', 'Exponential', ''),
    ('BETA',        'Beta',        ''),
    ('GAMMA',       'Gamma',       ''),
]

DISCRETE_TYPES = [
    ('UNIFORM_DISC', 'Uniform Discrete', ''),
    ('POISSON',      'Poisson',          ''),
    ('BINOMIAL',     'Binomial',         ''),
    ('CATEGORICAL',  'Categorical',      ''),
]

# Covariance structure for a multivariate Normal.
NORMAL_COV_TYPES = [
    ('ISOTROPIC', 'Isotropic',
     'Single shared sigma; spherical Gaussian (covariance = sigma^2 * I)'),
    ('DIAGONAL',  'Diagonal',
     'Independent sigma per axis; axis-aligned Gaussian (diagonal covariance, N d.o.f.)'),
]



class DistributionSocket(NodeSocket):
    """A random-variable channel of a fixed dimensionality (1D / 2D / 3D)."""
    bl_idname = 'DistributionSocket'
    bl_label = 'Distribution'

    dimension: IntProperty(default=1, min=1, max=3)  # type: ignore

    def draw_color(self, _context, _node):
        # Colors are for 1,2,3 d respectively yellow, green, azure (pastel)
        colors = {1: (1.0, 0.8, 0.0, 1.0), 2: (0.8, 1.0, 0.5, 1.0), 3: (0.5, 1.0, 0.8, 1.0)}
        return colors[self.dimension]

    def draw(self, _context, layout, _node, text):
        layout.label(text=f"{text} ({self.dimension}D)")


class ScalarSocket(NodeSocket):
    """A single deterministic 1D value. When unconnected it can be typed in directly."""
    bl_idname = 'ScalarSocket'
    bl_label = 'Value (1D)'

    # Inline editable value used whenever the socket is an unconnected input.
    default_value: FloatProperty(name='Value', default=0.0)  # type: ignore

    def draw_color(self, _context, _node):
        # Distinct blue-grey so it reads clearly as "scalar value", not a distribution
        # dimensional link
        return 0.40, 0.55, 0.90, 1.0

    def draw(self, _context, layout, _node, text):
        # Outputs and linked inputs are driven externally -> just label them.
        if self.is_output or self.is_linked:
            layout.label(text=f"{text}")
        else:
            layout.prop(self, 'default_value', text=text)


# IMPORTANT: Link compatibility / dimension propagation
#
# Blender does not gate socket connections for us: any output can be dragged onto any input link for
# the sockets. Compatibility is enforced here, in NodeTree.update(), which
# Blender calls whenever the graph topology changes. We first let every node refresh
# its dynamic output dimensions, then drop any link whose endpoints
# are incompatible (type mismatch, or DistributionSocket dimension mismatch).

def _socket_dim(sock) -> Optional[int]:
    """ Returns the dimension of a socket type as an integer. Scalar sockets are interpreted
    as 1-dimensional sockets

    :param sock: The socket object
    :return: an integer
    """
    # A scalar value is treated as 1-dimensional for compatibility purposes.
    if isinstance(sock, ScalarSocket):
        return 1
    if isinstance(sock, DistributionSocket):
        return sock.dimension
    return None


def _link_compatible(link) -> bool:
    """ Returns true if a link is dimensionally compatible, i.e. it joins
    sockets of equal dimension.

    :param link: A link (so two sockets being connected)
    :return: True if the link is dimensionally valid
    """
    a = _socket_dim(link.from_socket)
    b = _socket_dim(link.to_socket)
    # Compatible when both ends are known and share a dimension. A blue scalar
    # (1D) therefore connects freely to a 1D distribution socket, and vice versa.
    return a is not None and a == b


def _propagate_and_validate(tree) -> None:
    """ Propagate along all the nodes in the three the dimensions of
    each link, dropping those links for which there is a dimensional mismatch which
    is nonsensical or can't be resolved.

    :param tree:  A distribution tree
    """
    if tree is None:
        return
    nodes = list(tree.nodes)
    # Several passes so dimensions can propagate down a chain (e.g. Swap -> Swap).
    for _ in range(max(1, len(nodes))):
        for node in nodes:
            # Get the function used to propagate dimenisons inside the tree. This is
            # required because of the selector nodes, in substance.
            fn = getattr(node, 'propagate_dims', None)
            if fn:
                fn()
    # Remove links that are no longer valid after propagation.
    for link in list(tree.links):
        if not _link_compatible(link):
            tree.links.remove(link)


def _first_input_dim(node) -> int:
    """ Get the dimension of the first socket of the node, just by reading
    the available sockets and reading its dimension attribute.

    :param node: a node object
    :return: an integer, the dimension of the socket
    """
    for inp in node.inputs:
        if isinstance(inp, DistributionSocket) and inp.is_linked:
            from_sock = inp.links[0].from_socket
            if isinstance(from_sock, DistributionSocket):
                return from_sock.dimension
            elif isinstance(from_sock, ScalarSocket):
                return 1
    return 1


# IMPORTANT:  Weight / probability string validation
#
# The Selector weights and the Categorical probabilities are entered as a comma-separated list.
# We parse them with _parse_weight_list and expose the
# backing StringProperty through get/set accessors: the setter only commits a value
# that parses, so malformed text is rejected and the field reverts to the last valid entry.
# In this way, the user cannot enter an invalid string which cannot be interpreted.
# (The compiler checks for correctness anyway as a sanity check, rejecting wrong nodes)

def _parse_weight_list(text):
    """ Return a list of non-negative floats, or None if text is malformed.

    Valid format: one or more comma-separated numbers, all >= 0, with a
    positive sum (so the list can be normalised into a probability vector).
    """
    parts = [p.strip() for p in text.split(',') if p.strip() != '']
    if not parts:
        return None
    values = []
    for p in parts:
        try:
            v = float(p)
        except ValueError:
            return None
        if v < 0.0:
            return None
        values.append(v)
    if sum(values) <= 0.0:
        return None
    return values


def _weight_string_prop(key, default):
    """ Build (getter, setter) for a validated comma-separated weight string.
    :param key: The weight string
    :param default: The default weight string

    :return a tuple with the getter, setter functions
    """

    # Its a bit bad to declare this inside another function, but i dont want
    # to clutter the global namespace with "getter" and "setter" which are very common
    def getter(self):
        return self.get(key, default)

    def setter(self, value):
        if _parse_weight_list(value) is not None:
            self[key] = value
        # Malformed input is ignored, leaving the previous valid value in place
        # so the input is scratched if its not valid

    return getter, setter


class DistributionNodeTree(NodeTree):
    bl_idname = 'DistributionNodeTree'
    bl_label = 'Distribution Editor'
    bl_icon = 'NODETREE'

    def update(self):
        # Called by Blender on any topology change: enforce socket compatibility.
        _propagate_and_validate(self)


class DistNode:

    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'DistributionNodeTree'

    def propagate_dims(self):
        """ Override to refresh dynamic output socket dimensions. Must be idempotent. """
        pass

    def _on_dim_change(self):
        """ Call from property update callbacks that change dimensionality. """
        _propagate_and_validate(self.id_data)


class DistributionRootNode(DistNode, Node):
    bl_idname = 'DistributionRootNode'
    bl_label = 'Root'
    bl_icon = 'NODETREE'

    dimension: IntProperty(name='Dimension', default=1, min=1, max=3,  # type: ignore
                           update=lambda self, ctx: self._on_dim_change())

    def init(self, _context):
        s = self.inputs.new('DistributionSocket', 'In')
        s.dimension = self.dimension

    def propagate_dims(self):
        if self.inputs:
            self.inputs[0].dimension = self.dimension

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'dimension', text='Dim')

class DistributionContinuousNode(DistNode, Node):
    bl_idname = 'DistributionContinuousNode'
    bl_label = 'Continuous'

    dist_type: EnumProperty(items=CONTINUOUS_TYPES,  # type: ignore
                            update=lambda self, ctx: self._on_dim_change())

    # --- Normal (now multivariate) ---
    dimension: IntProperty(name='Dimension', default=1, min=1, max=3,  # type: ignore
                           update=lambda self, ctx: self._on_dim_change())
    normal_cov: EnumProperty(name='Covariance', items=NORMAL_COV_TYPES)  # type: ignore
    mean:   FloatProperty(name='Mean',   default=0.0)  # type: ignore  (X)
    mean_y: FloatProperty(name='Mean Y', default=0.0)  # type: ignore
    mean_z: FloatProperty(name='Mean Z', default=0.0)  # type: ignore
    sigma:   FloatProperty(name='Sigma',   default=1.0, min=1e-6)  # type: ignore  (X / isotropic)
    sigma_y: FloatProperty(name='Sigma Y', default=1.0, min=1e-6)  # type: ignore
    sigma_z: FloatProperty(name='Sigma Z', default=1.0, min=1e-6)  # type: ignore

    # Uniform
    low:  FloatProperty(name='Low',  default=0.0)  # type: ignore
    high: FloatProperty(name='High', default=1.0)  # type: ignore
    # Exponential
    lam: FloatProperty(name='Lambda', default=1.0, min=1e-6)  # type: ignore
    # Beta / Gamma share alpha/beta
    alpha: FloatProperty(name='Alpha', default=1.0, min=1e-6)  # type: ignore
    beta:  FloatProperty(name='Beta',  default=1.0, min=1e-6)  # type: ignore
    # Truncation (1D only)
    truncate: BoolProperty(name='Truncate', default=False)  # type: ignore
    trunc_lo: FloatProperty(name='Lo', default=0.0)  # type: ignore
    trunc_hi: FloatProperty(name='Hi', default=1.0)  # type: ignore

    def init(self, _context):
        self.outputs.new('DistributionSocket', 'Out')
        self.propagate_dims()

    def propagate_dims(self):
        if not self.outputs:
            return
        # Only the Normal is multivariate; every other primitive here is scalar 1D.
        self.outputs[0].dimension = self.dimension if self.dist_type == 'NORMAL' else 1

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'dist_type', text='')
        t = self.dist_type
        if t == 'NORMAL':
            layout.prop(self, 'dimension', text='Dim')
            multi = self.dimension > 1
            if multi:
                layout.prop(self, 'normal_cov', text='')

            col = layout.column(align=True)
            col.prop(self, 'mean', text='Mean X' if multi else 'Mean')
            if self.dimension >= 2:
                col.prop(self, 'mean_y')
            if self.dimension == 3:
                col.prop(self, 'mean_z')

            sig = layout.column(align=True)
            if not multi or self.normal_cov == 'ISOTROPIC':
                # One sigma -> a circle / sphere of radius sigma in N dimensions.
                sig.prop(self, 'sigma', text='Sigma')
            else:
                sig.prop(self, 'sigma', text='Sigma X')
                if self.dimension >= 2:
                    sig.prop(self, 'sigma_y')
                if self.dimension == 3:
                    sig.prop(self, 'sigma_z')
        elif t == 'UNIFORM':
            layout.prop(self, 'low')
            layout.prop(self, 'high')
        elif t == 'EXPONENTIAL':
            layout.prop(self, 'lam')
        elif t in ('BETA', 'GAMMA'):
            layout.prop(self, 'alpha')
            layout.prop(self, 'beta')

        # Truncation only makes sense for the scalar variants.
        if t != 'NORMAL' or self.dimension == 1:
            layout.prop(self, 'truncate')
            if self.truncate:
                row = layout.row(align=True)
                row.prop(self, 'trunc_lo')
                row.prop(self, 'trunc_hi')


class DistributionDiscreteNode(DistNode, Node):
    bl_idname = 'DistributionDiscreteNode'
    bl_label = 'Discrete'

    dist_type: EnumProperty(items=DISCRETE_TYPES)  # type: ignore
    # Uniform discrete
    d_low:  IntProperty(name='Low',  default=0)  # type: ignore
    d_high: IntProperty(name='High', default=9)  # type: ignore
    # Poisson
    lam: FloatProperty(name='Lambda', default=1.0, min=1e-6)  # type: ignore
    # Binomial
    n_trials: IntProperty(name='n',   default=10, min=1)  # type: ignore
    p_success: FloatProperty(name='p', default=0.5, min=0.0, max=1.0)  # type: ignore
    # Categorical
    _cat_get, _cat_set = _weight_string_prop('_cat_probs', '0.2, 0.5, 0.3')
    cat_probs: StringProperty(name='Probs', default='0.2, 0.5, 0.3',  # type: ignore
                              get=_cat_get, set=_cat_set)

    def init(self, _context):
        s = self.outputs.new('DistributionSocket', 'Out')
        s.dimension = 1

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'dist_type', text='')
        t = self.dist_type
        if t == 'UNIFORM_DISC':
            layout.prop(self, 'd_low')
            layout.prop(self, 'd_high')
        elif t == 'POISSON':
            layout.prop(self, 'lam')
        elif t == 'BINOMIAL':
            layout.prop(self, 'n_trials')
            layout.prop(self, 'p_success')
        elif t == 'CATEGORICAL':
            layout.prop(self, 'cat_probs')


class DistributionConstantNode(DistNode, Node):
    bl_idname = 'DistributionConstantNode'
    bl_label = 'Constant'

    mode: EnumProperty(                                                     # type: ignore
        items=[('SCALAR', 'Scalar', ''), ('VECTOR', 'Vector', '')],
        update=lambda self, ctx: self._rebuild_outputs()
    )
    scalar_val: FloatProperty(name='Value', default=0.0)  # type: ignore
    vec2: FloatProperty(name='Y', default=0.0)            # type: ignore — paired with scalar_val as X
    vec3: FloatProperty(name='Z', default=0.0)            # type: ignore
    vec_dim: EnumProperty(                                 # type: ignore
        items=[('2', '2D', ''), ('3', '3D', '')],
        update=lambda self, ctx: self._rebuild_outputs()
    )

    def init(self, _context):
        self.outputs.new('ScalarSocket', 'Value')

    def _rebuild_outputs(self):
        self.outputs.clear()
        if self.mode == 'SCALAR':
            self.outputs.new('ScalarSocket', 'Value')
        else:
            s = self.outputs.new('DistributionSocket', 'Value')
            s.dimension = int(self.vec_dim)
        self._on_dim_change()

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'mode', expand=True)
        if self.mode == 'SCALAR':
            layout.prop(self, 'scalar_val', text='Value')
        else:
            layout.prop(self, 'vec_dim', text='Dim')
            layout.prop(self, 'scalar_val', text='X')
            if int(self.vec_dim) >= 2:
                layout.prop(self, 'vec2', text='Y')
            if int(self.vec_dim) == 3:
                layout.prop(self, 'vec3', text='Z')


class DistributionVectorizeNode(DistNode, Node):
    bl_idname = 'DistributionVectorizeNode'
    bl_label = 'Vectorize'

    mode: EnumProperty(items=VECTORIZE_MODES, update=lambda self, ctx: self._rebuild())  # type: ignore

    def init(self, _context):
        self._rebuild()

    def _rebuild(self):
        self.inputs.clear()
        self.outputs.clear()
        for dim, name in _VECTORIZE_INPUTS[self.mode]:
            s = self.inputs.new('DistributionSocket', name)
            s.dimension = dim
        out = self.outputs.new('DistributionSocket', 'Out')
        out.dimension = _VECTORIZE_OUT_DIM[self.mode]
        self._on_dim_change()

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'mode', text='')



class DistributionSwapNode(DistNode, Node):
    bl_idname = 'DistributionSwapNode'
    bl_label = 'Swap'

    def _perm_items(self, _context):
        dim = _first_input_dim(self) # type: ignore (Node has .inputs)
        if dim == 2:
            return [('XY', 'X ↔ Y', '')]
        return [('XY', 'X exchange Y', ''), ('XZ', 'X exchange Z', ''), ('YZ', 'Y exchange Z', '')]

    permutation: EnumProperty(items=_perm_items)  # type: ignore

    def init(self, _context):
        self.inputs.new('DistributionSocket', 'In')
        self.outputs.new('DistributionSocket', 'Out')

    def propagate_dims(self):
        dim = _first_input_dim(self) # type: ignore
        # Keep the input socket's declared dimension in step so links read clearly.
        if self.inputs:
            self.inputs[0].dimension = dim
        if self.outputs:
            self.outputs[0].dimension = dim

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'permutation', text='')


class DistributionSelectorNode(DistNode, Node):
    bl_idname = 'DistributionSelectorNode'
    bl_label = 'Selector'

    dimension: IntProperty(name='Dimension', default=1, min=1, max=3,  # type: ignore
                           update=lambda self, ctx: self._on_dim_change())
    num_inputs: IntProperty(default=2, min=2, max=8,  # type: ignore
                            update=lambda self, ctx: self._on_dim_change())
    _w_get, _w_set = _weight_string_prop('_weights', '0.5, 0.5')
    weights: StringProperty(name='Weights', default='0.5, 0.5',  # type: ignore
                            get=_w_get, set=_w_set)

    def init(self, _context):
        out = self.outputs.new('DistributionSocket', 'Out')
        out.dimension = self.dimension
        for i in range(self.num_inputs):
            s = self.inputs.new('DistributionSocket', f'In {i + 1}')
            s.dimension = self.dimension

    def _sync_inputs(self):
        while len(self.inputs) < self.num_inputs:
            self.inputs.new('DistributionSocket', f'In {len(self.inputs) + 1}')
        while len(self.inputs) > self.num_inputs:
            self.inputs.remove(self.inputs[-1])

    def propagate_dims(self):
        self._sync_inputs()
        # A mixture mixes same-dimension components: pin every input and the
        # output to the chosen dimension so incompatible attempts are rejected.
        for inp in self.inputs:
            if isinstance(inp, DistributionSocket):
                inp.dimension = self.dimension
        if self.outputs:
            self.outputs[0].dimension = self.dimension

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'dimension', text='Dim')
        layout.prop(self, 'num_inputs', text='Inputs')
        layout.prop(self, 'weights', text='Weights')
        values = _parse_weight_list(self.weights)
        if values is not None and len(values) != self.num_inputs:
            layout.label(text=f"{len(values)} weight(s) for {self.num_inputs} input(s)",
                         icon='ERROR')


class DistributionMathNode(DistNode, Node):
    """Operates on 1D scalar values. Inputs are typed-in unless a value is plugged in."""
    bl_idname = 'DistributionMathNode'
    bl_label = 'Math'

    operation: EnumProperty(items=MATH_OPS, update=lambda self, ctx: self._rebuild())  # type: ignore

    def init(self, _context):
        self._rebuild()

    def _rebuild(self):
        self.inputs.clear()
        self.outputs.clear()
        self.inputs.new('ScalarSocket', 'A')
        if self.operation not in _UNARY_OPS:
            self.inputs.new('ScalarSocket', 'B')
        self.outputs.new('ScalarSocket', 'Out')

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'operation', text='')


class DistributionScaleNode(DistNode, Node):
    """Scale an N-D distribution by a scalar factor. Dimension is chosen explicitly."""
    bl_idname = 'DistributionScaleNode'
    bl_label = 'Scale'

    dimension: IntProperty(name='Dimension', default=1, min=1, max=3,  # type: ignore
                           update=lambda self, ctx: self._on_dim_change())

    def init(self, _context):
        # Factor is an explicit 1D scalar (typeable when unconnected).
        self.inputs.new('ScalarSocket', 'Factor')
        v = self.inputs.new('DistributionSocket', 'Vector')
        v.dimension = self.dimension
        out = self.outputs.new('DistributionSocket', 'Out')
        out.dimension = self.dimension

    def propagate_dims(self):
        vec = self.inputs.get('Vector')
        if vec is not None:
            vec.dimension = self.dimension
        if self.outputs:
            self.outputs[0].dimension = self.dimension

    def draw_buttons(self, _context, layout):
        layout.prop(self, 'dimension', text='Dim')


class DistributionNodeCategory(NodeCategory):

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == DISTRO_EDITOR_NAME

def get_tree_dimensionality(tree) -> int:
    """ Dimensionality demanded by the tree's Root node (defaults to 1 if absent). """
    for node in tree.nodes:
        if isinstance(node, DistributionRootNode):
            return node.dimension
    return 1