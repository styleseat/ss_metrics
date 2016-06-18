from __future__ import absolute_import

import functools
import random
import string
import uuid

import appmetrics.metrics as _metrics
import appmetrics.reporter as _reporter
import librato
import mock
import pytest

import ss_metrics.reporter
from ss_metrics.metrics import DeltaTracker
from ss_metrics.reporter import ConsoleReporter, LibratoReporter, _get_hostname


@pytest.fixture
def hostname():
    return str(uuid.uuid4())


@pytest.yield_fixture
def mock_hostname(hostname):
    with mock.patch.object(
            ss_metrics.reporter, '_get_hostname', return_value=hostname):
        yield hostname


@pytest.yield_fixture
def mock_logger():
    with mock.patch.object(ss_metrics.reporter, 'logger') as logger:
        yield logger


@pytest.yield_fixture
def mock_librato():
    with mock.patch.object(ss_metrics.reporter, 'librato') as librato:
        yield librato


@pytest.fixture
def librato_email():
    return 'mailbox@example.com'


@pytest.fixture
def librato_token():
    return 'secretlibratotoken'


@pytest.fixture
def metric_prefix():
    return None


@pytest.fixture
def librato_reporter_factory(librato_email, librato_token, metric_prefix):
    return functools.partial(
        LibratoReporter,
        librato_email, librato_token, metric_prefix=metric_prefix)


@pytest.fixture
def librato_reporter(librato_reporter_factory):
    return librato_reporter_factory()


def test_get_hostname():
    hostname = _get_hostname()
    assert len(hostname) > 0
    assert hostname == _get_hostname()


def test_console_reporter(mock_logger):
    reporter = ConsoleReporter()
    metrics = mock.MagicMock()
    reporter(metrics)
    mock_logger.info.assert_called_once_with(metrics)


@pytest.mark.usefixtures('mock_metrics_registry')
class TestLibratoReporter(object):
    @pytest.mark.parametrize('metric_prefix', [None, 'namespace'])
    def test_init(
            self, librato_email, librato_token, metric_prefix,
            librato_reporter_factory):
        reporter = librato_reporter_factory()
        assert isinstance(reporter.delta_tracker, DeltaTracker)
        assert isinstance(reporter.librato_api, librato.LibratoConnection)
        assert reporter.librato_api.username.decode() == librato_email
        assert reporter.librato_api.api_key.decode() == librato_token
        assert reporter.metric_prefix == metric_prefix

    @pytest.mark.parametrize('metric_prefix,metric_name', [
        (None, 'x' * 256),
        ('ns', 'x' * (256 - len('ns'))),
    ])
    def test_metric_name_is_too_long(
            self, mock_logger, mock_librato, librato_reporter, metric,
            metric_name, full_metric_name):
        gauge = _metrics.new_gauge(metric_name)
        gauge.notify('value')
        self.metric_submission_test(librato_reporter, [])
        assert mock_logger.error.call_count == 1
        args, kwargs = mock_logger.error.call_args
        assert full_metric_name in args

    @pytest.mark.parametrize('metric_prefix', [None, 'namespace'])
    def test_gauge(
            self, mock_librato, librato_reporter, metric,
            metric_name, full_metric_name):
        value = 'healthy'
        gauge = _metrics.new_gauge(metric_name)
        gauge.notify(value)
        self.metric_submission_test(librato_reporter, [
            metric(full_metric_name, value)
        ])

    @pytest.mark.parametrize('metric_prefix', [None, 'namespace'])
    @pytest.mark.parametrize('value,delta', [
        tuple(random.randint(-2**31, 2**31-1) for _ in range(2))])
    def test_meter(
            self, mock_librato, librato_reporter, metric,
            metric_name, full_metric_name, value, delta):
        delta_tracker = mock.Mock(spec=DeltaTracker)
        delta_tracker.get_delta.return_value = delta
        librato_reporter.delta_tracker = delta_tracker
        meter = _metrics.new_meter(metric_name)
        meter.notify(value)
        self.metric_submission_test(librato_reporter, [
            metric('.'.join((full_metric_name, 'count')), delta),
            metric('.'.join((full_metric_name, '1m')), meter.m1.rate),
            metric('.'.join((full_metric_name, '5m')), meter.m5.rate),
        ])
        delta_tracker.get_delta.assert_called_once_with(metric_name, value)

    @pytest.mark.parametrize('metric_prefix', [None, 'namespace'])
    @pytest.mark.parametrize('value', [random.random()])
    def test_histogram(
            self, mock_librato, librato_reporter, metric,
            metric_name, full_metric_name, value):
        histogram = _metrics.new_histogram(metric_name)
        histogram.notify(value)
        percentiles = histogram.get()['percentile']
        self.metric_submission_test(librato_reporter, [
            metric(
                full_metric_name, None,
                count=1, sum=value, min=value, max=value)
        ] + [
            metric('.'.join((full_metric_name, str(p))), value)
            for p, _ in percentiles
        ])

    def test_histogram_zero_samples(
            self, mock_librato, librato_reporter, metric_name):
        _metrics.new_histogram(metric_name)
        self.metric_submission_test(librato_reporter, [])

    def test_unsupported_metric_type(
            self, mock_librato, librato_reporter, metric_name):
        self.metric_submission_test(
            librato_reporter,
            [],
            input_metrics={metric_name: dict(kind='unknown')})

    def test_multiple_metrics(
            self, mock_librato, librato_reporter, metric, metric_prefix):
        names = ['A', 'B']
        values = [random.random(), random.random()]
        gauges = []
        for i, name in enumerate(names):
            gauge = _metrics.new_gauge(name)
            gauge.notify(values[i])
            gauges.append(gauge)
        self.metric_submission_test(librato_reporter, [
            metric(self.full_metric_name(metric_prefix, names[i]), values[i])
            for i in range(len(names))
        ])

    def metric_submission_test(
            self, librato_reporter, submitted_metrics, input_metrics=None):
        new_queue = librato_reporter.librato_api.new_queue
        queue = new_queue.return_value
        queue.__enter__.return_value = queue
        queue.__exit__.side_effect = lambda *args: queue.submit()
        if input_metrics is None:
            input_metrics = _reporter.get_metrics(None)
        librato_reporter(input_metrics)
        new_queue.assert_called_once_with()
        print("Calls: %s" % (queue.method_calls,))
        queue.assert_has_calls([
            mock.call.add(*args, **kwargs)
            for args, kwargs in submitted_metrics
        ],
            any_order=True)
        assert queue.method_calls[-1] == mock.call.submit()
        assert len(queue.method_calls) == len(submitted_metrics) + 1

    @pytest.fixture
    def metric_name(self):
        return random.choice(string.ascii_letters)

    @pytest.fixture
    def full_metric_name(self, metric_prefix, metric_name):
        return (
            metric_name if metric_prefix is None else
            '.'.join((metric_prefix, metric_name)))

    @pytest.fixture
    def metric(self, mock_hostname):
        def make_metric(name, value, **properties):
            properties.setdefault('type', 'gauge')
            properties.setdefault('source', mock_hostname)
            return ((name, value), properties)

        return make_metric
