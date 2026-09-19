"""wilson(): bounds stay inside [0, 100] (a -0.0 lower bound was printed on 2026-09-19); z stays 1.96."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from stats_ci import wilson  # noqa: E402


def test_zero_successes_lower_bound_is_not_negative():
    lo, hi = wilson(0, 60)
    assert lo == 0.0
    assert abs(hi - 6.017) < 0.01


def test_all_successes_upper_bound_is_not_above_100():
    lo, hi = wilson(60, 60)
    assert hi <= 100.0 and abs(hi - 100.0) < 1e-9  # analytically 100; float gives 99.999...
    assert 90 < lo < 100


def test_n_zero_is_nan():
    lo, hi = wilson(0, 0)
    assert lo != lo and hi != hi
