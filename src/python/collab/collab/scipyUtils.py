# Copyright (c) Simon Parry.
# See LICENSE for details.

import numpy as np
from scipy import stats


def percentile(dist, per):
    arr = np.fromiter(dist.itervalues(), np.float32)
    return stats.scoreatpercentile(a=arr, per=per)
                
