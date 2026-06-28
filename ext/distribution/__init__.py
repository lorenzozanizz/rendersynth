from .nodes import *
from nodeitems_utils import NodeItem


PRIMITIVE_CAT_NAME = 'DIST_PRIMITIVES'
COMBINATORS_CAT_NAME = 'DIST_COMBINATORS'
MATH_CAT_NAME = 'DIST_MATH'
SINK_CAT_NAME = 'DIST_SINK'

node_categories = [
    # We use the __name__ dunder method to avoid writing strings which would break down
    # on class name change
    DistributionNodeCategory(PRIMITIVE_CAT_NAME, 'Primitives', items=[ # type: ignore
        NodeItem(DistributionContinuousNode.__name__),
        NodeItem(DistributionDiscreteNode.__name__),
        NodeItem(DistributionConstantNode.__name__),
    ]),
    DistributionNodeCategory(COMBINATORS_CAT_NAME, 'Combinators', items=[ # type: ignore
        NodeItem(DistributionVectorizeNode.__name__),
        NodeItem(DistributionSwapNode.__name__),
        NodeItem(DistributionSelectorNode.__name__),
    ]),
    DistributionNodeCategory(MATH_CAT_NAME, 'Math', items=[ # type: ignore
        NodeItem(DistributionMathNode.__name__),
        NodeItem(DistributionScaleNode.__name__),
    ]),
    DistributionNodeCategory(SINK_CAT_NAME, 'Sink', items=[ # type: ignore
        NodeItem(DistributionRootNode.__name__),
    ]),
]

classes = (
    DistributionSocket, ScalarSocket,
    DistributionNodeTree, DistributionRootNode,
    DistributionContinuousNode, DistributionDiscreteNode,
    DistributionConstantNode, DistributionVectorizeNode,
    DistributionSwapNode, DistributionSelectorNode,
    DistributionMathNode, DistributionScaleNode,
)