"""Wilson score interval (95%, percent). Pre-registered for destruction/asymmetry rates. Tested in tests/test_wilson.py."""

from math import sqrt


def wilson(k, n, z=1.96):  # Wilson score 95% CI in percent (pre-registered for destruction/asymmetry)
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    # clamp: at p=0 the lower bound is exactly 0 analytically, but floating point gives e.g. -6.9e-16 -> printed as "-0.0" (2026-09-19 review). z stays 1.96.
    return (max(0.0, 100 * (c - h)), min(100.0, 100 * (c + h)))
