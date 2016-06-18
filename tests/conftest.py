from __future__ import absolute_import

import uuid

import appmetrics.metrics as _metrics
import mock
import pytest


@pytest.yield_fixture
def mock_metrics_registry(metric_count=0):
    with mock.patch.dict(
            _metrics.REGISTRY, {}, clear=True):
        for _ in range(metric_count):
            _metrics.new_metric(
                str(uuid.uuid4()), mock.Mock, spec=['get'])
        yield _metrics.REGISTRY.copy()
