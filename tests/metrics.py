from __future__ import absolute_import

import appmetrics.metrics as _metrics
import pytest

from ss_metrics import metrics


@pytest.fixture
def populated_delta_tracker():
    tracker = metrics.DeltaTracker()
    tracker.name_to_count = {
        'client_signups': 0,
        'impressions': 15
    }
    return tracker


class TestDeltaTracker(object):
    @pytest.mark.parametrize('key,expected', [
        ('client_signups', 20),
        ('impressions', 5),
        ('nonexistent', 20)
    ])
    def test_peek_delta(self, populated_delta_tracker, key, expected):
        actual = populated_delta_tracker.peek_delta(key, 20)
        assert expected == actual

    @pytest.mark.parametrize('key,expected', [
        ('client_signups', 20),
        ('impressions', 5),
        ('nonexistent', 20)
    ])
    def test_get_delta(self, populated_delta_tracker, key, expected):
        new_count = 20
        actual = populated_delta_tracker.get_delta(key, new_count)
        assert expected == actual
        assert populated_delta_tracker.name_to_count.get(key) == new_count

    @pytest.mark.parametrize('key,previous,count,expected', [
        ('equal', 20, 20, 0),
        ('decreasing', 20, 5, 0),
        ('increasing', 20, 30, 10)
    ])
    def test_calculate_delta(self, populated_delta_tracker, key, previous,
                             count, expected):
        actual = populated_delta_tracker.calculate_delta(key, previous, count)
        assert expected == actual


def test_gauge(mock_metrics_registry):
    name, value = 'speedometer', 'too slow'
    metrics.gauge(name, value)
    assert _metrics.get(name)['value'] == value


@pytest.mark.parametrize('value', range(-1, 1))
def test_inc_meter(mock_metrics_registry, value):
    name = 'balance'
    metrics.inc_meter(name, value)
    assert _metrics.get(name)['count'] == value


def test_update_histogram(mock_metrics_registry):
    name, value = 'duration', 1.0
    metrics.update_histogram(name, value)
    assert _metrics.get(name)['min'] == value


def test_timed(mock_metrics_registry):
    @metrics.timed
    def timed_fn():
        pass

    timed_fn()
    assert len(_metrics.REGISTRY) == 1
    name, metric = _metrics.REGISTRY.popitem()
    assert name.endswith('.timed_fn.timer')
    assert len(metric.raw_data()) == 1


def test_with_meter(mock_metrics_registry):
    @metrics.with_meter
    def metered_fn():
        pass

    metered_fn()
    assert len(_metrics.REGISTRY) == 1
    name, metric = _metrics.REGISTRY.popitem()
    assert name.endswith('.metered_fn.rate')
    assert metric.get()['count'] == 1
