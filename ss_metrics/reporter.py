from __future__ import absolute_import, print_function

import socket

import librato

from . import logger
from .metrics import DeltaTracker

_hostname = None


# Hostname is done this way to avoid socket operations as a side
# effect of importing this module
def _get_hostname():
    """Get the current machine's hostname."""
    global _hostname
    if _hostname is None:
        _hostname = socket.getfqdn()
    return _hostname


class ConsoleReporter(object):
    def __call__(self, metrics):
        logger.info(metrics)


class LibratoReporter(object):
    def __init__(self, librato_email, librato_token, metric_prefix=None):
        self.delta_tracker = DeltaTracker()
        self.librato_api = librato.connect(librato_email, librato_token)
        self.metric_prefix = metric_prefix

    def __call__(self, metrics):
        # No point in caching the LibratoConnection instance, as initialization
        # does not involve any socket operations and each call to `submit`
        # creates a new socket connection.
        with self.librato_api.new_queue() as q:
            hostname = _get_hostname()
            for name, info in metrics.items():
                # Add a prefix for separate environments
                # Workaround unless/until we have separate Librato buckets
                # for each environment
                # (lily|2015-07-28)
                if self.metric_prefix is not None:
                    full_name = '.'.join((self.metric_prefix, name))
                else:
                    full_name = name
                if len(full_name) > 255:
                    logger.error(
                        'Metric name "%s" exceeds maximum allowed length',
                        full_name)
                    continue
                kind = info['kind']
                if kind == 'gauge':
                    value = info['value']
                    q.add(full_name, value, type='gauge', source=hostname)
                elif kind == 'meter':
                    q.add('.'.join((full_name, 'count')),
                          self.delta_tracker.get_delta(name, info['count']),
                          type='gauge',
                          source=hostname)

                    # pairs of appmetrics metrics names with their
                    # counterparts on librato
                    meter_names = (('one', '1m'), ('five', '5m'))
                    for meter_name in meter_names:
                        appmetrics_name, librato_name = meter_name
                        q.add('.'.join((full_name, librato_name)),
                              info[appmetrics_name],
                              type='gauge',
                              source=hostname)
                elif kind == 'histogram':
                    # Librato will reject if n is not > 0
                    if info['n'] > 0:
                        q.add(full_name,
                              None,
                              type='gauge',
                              count=info['n'],
                              sum=(info['n'] * info['arithmetic_mean']),
                              max=info['max'],
                              min=info['min'],
                              source=hostname)
                        for percentile_name, value in info['percentile']:
                            q.add('.'.join((full_name, str(percentile_name))),
                                  value,
                                  type='gauge',
                                  source=hostname)
