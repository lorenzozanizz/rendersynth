from typing import Dict, List

PRIMITIVE_CAT_NAME = 'DIST_PRIMITIVES'
COMBINATORS_CAT_NAME = 'DIST_COMBINATORS'
MATH_CAT_NAME = 'DIST_MATH'
SINK_CAT_NAME = 'DIST_SINK'

ROOT_IDNAME = 'DistributionRootNode'
SCALAR_IDNAME = 'ScalarSocket'

SERIALIZED_FORMAT = 'distribution_tree'
SERIALIZED_VERSION = 1

NODE_PROPERTIES: Dict[str, List[str]] = {
    'DistributionRootNode':       ['dimension'],
    'DistributionContinuousNode': ['dist_type', 'dimension', 'normal_cov',
                                   'mean', 'mean_y', 'mean_z',
                                   'sigma', 'sigma_y', 'sigma_z',
                                   'low', 'high', 'lam', 'alpha', 'beta',
                                   'truncate', 'trunc_lo', 'trunc_hi'],
    'DistributionDiscreteNode':   ['dist_type', 'd_low', 'd_high', 'lam',
                                   'n_trials', 'p_success', 'cat_probs'],
    'DistributionConstantNode':   ['mode', 'vec_dim', 'scalar_val', 'vec2', 'vec3'],
    'DistributionVectorizeNode':  ['mode'],
    'DistributionSwapNode':       ['permutation'],
    'DistributionSelectorNode':   ['dimension', 'num_inputs', 'weights'],
    'DistributionMathNode':       ['operation'],
    'DistributionScaleNode':      ['dimension'],
}