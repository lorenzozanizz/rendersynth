""" Utility math functions involving sampling and mathematic functions.
Functions:
    geometric: Samples a random variable from the geometric distribution, using the random module

Example:
    >>> from ext.utils.math_funcs import geometric
    >>> n = geometric(0.5) # random var from Geometric(p)
"""

import random

from .logger import UniqueLogger


def geometric(p: float) -> int:
    """ Sample from geometric distribution (number of trials until first success).

    :param p: probability of success on each trial [0, 1]
    :return: number of trials (>=1)
    """
    # Cheap safeguard against possible infinite lock mode.
    if p < 1e-4:
        return 10000
    trials = 1
    while random.random() >= p:
        trials += 1
    return trials

def pick_k_from_n(n: int, k: int) -> list[int]:
    """ Pick k items from the range 0, ... n-1, e.g. the range of indexes
    for a list of length n.

    :param n: Number of items
    :param k: Number of items selected
    :return: list of sampled items
    """
    result = random.sample(range(n), k)
    UniqueLogger.quick_log(f"pick_k_from_n({n}, {k}) = {result}")
    return result