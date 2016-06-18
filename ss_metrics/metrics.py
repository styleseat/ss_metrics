from __future__ import absolute_import

import logging
import threading
from functools import wraps

from appmetrics import metrics
from appmetrics.exceptions import InvalidMetricError

from . import logger
from .utils import get_function_name


class DeltaTracker(object):
    """A class that tracks the change between two measurements of a metric."""

    def __init__(self):
        self.name_to_count = {}
        self.lock = threading.Lock()

    def peek_delta(self, name, count):
        """Calculate the delta without updating the current count."""
        previous = self.name_to_count.get(name, 0)
        return self.calculate_delta(name, previous, count)

    def get_delta(self, name, count):
        """Retrive the delta and update the current count."""
        with self.lock:
            previous = self.name_to_count.get(name, 0)
            self.name_to_count[name] = count
        return self.calculate_delta(name, previous, count)

    def calculate_delta(self, name, previous, count):
        """Calculate the delta, ensuring the values are increasing."""
        if count < previous:
            logger.error(
                "Saw a non-monotonically increasing value for "
                "metric {name}".format(name=name))
            return 0
        return count - previous


def _get_metric(name):
    """Get the named metric or return None."""
    try:
        return metrics.metric(name)
    except InvalidMetricError:
        return None


def gauge(name, value):
    """Record the current value of a gauge metric."""
    metric = _get_metric(name) or metrics.new_gauge(name)
    metric.notify(value)


def inc_meter(name, by=1):
    """Increment the value of a meter."""
    logging.info('Incrementing meter %s', name)
    counter = _get_metric(name) or metrics.new_meter(name)
    counter.notify(by)


def update_histogram(name, sample, reservoir_type='uniform'):
    histogram = metrics.get_or_create_histogram(name, reservoir_type)
    histogram.notify(sample)


# Use indirection to appmetrics to keep implementation details of our
# metrics library solely in this module
def timed(fn):
    """Time function calls and report metrics based on timings.

    Automatically generares metric names based on the decorated function's
    fully qualified name.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        name = '.'.join((get_function_name(fn), 'timer'))
        return metrics.with_histogram(name)(fn)(*args, **kwargs)
    return wrapper


def with_meter(fn):
    """Count function calls and report metrics based on count and rates.

    Automatically generares metric names based on the decorated function's
    fully qualified name.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        name = '.'.join((get_function_name(fn), 'rate'))
        return metrics.with_meter(name)(fn)(*args, **kwargs)
    return wrapper
