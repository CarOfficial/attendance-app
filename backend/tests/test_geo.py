import pytest

from app.geo import haversine_m


def test_zero_distance_for_same_point():
    assert haversine_m(35.7, 51.4, 35.7, 51.4) == pytest.approx(0.0, abs=1e-6)


def test_one_degree_latitude_is_about_111km():
    d = haversine_m(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111_195, rel=0.001)


def test_symmetry():
    a = haversine_m(35.6892, 51.3890, 35.7000, 51.4000)
    b = haversine_m(35.7000, 51.4000, 35.6892, 51.3890)
    assert a == pytest.approx(b)
