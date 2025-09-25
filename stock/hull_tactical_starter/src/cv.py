
import numpy as np
from typing import Iterator, Tuple

class PurgedWalkForwardSplit:
    """
    Time-series splitter with a *gap* (purge) between train and test to reduce leakage.
    - n_splits: number of evaluation folds
    - test_size: number of time steps in each test fold
    - gap: number of time steps purged between train and test
    """
    def __init__(self, n_splits: int = 5, test_size: int = 252, gap: int = 5):
        assert n_splits > 0 and test_size > 0
        self.n_splits = n_splits
        self.test_size = test_size
        self.gap = gap

    def split(self, n_samples: int):
        total_test = self.n_splits * self.test_size
        start = max(0, n_samples - total_test)
        for i in range(self.n_splits):
            test_start = start + i * self.test_size
            test_end = min(test_start + self.test_size, n_samples)
            train_end = max(0, test_start - self.gap)
            yield np.arange(0, train_end), np.arange(test_start, test_end)
