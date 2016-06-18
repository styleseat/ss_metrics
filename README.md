# ss\_metrics: Metric collection and reporting

This library extends [AppMetrics] (http://avalente.github.io/appmetrics/),
providing additional reporters and metric collection interfaces.

# Sample Usage

```python
import appmetrics.reporter
from appmetrics.reporter import fixed_interval_scheduler
from ss_metrics import ConsoleReporter, LibratoReporter, logger, metrics

# Create a reporter that logs metrics to the console
console_reporter = ConsoleReporter()
appmetrics.reporter.register(console_reporter, fixed_interval_scheduler(5))

# Create a reporter that sends metrics to librato
librato_reporter = LibratoReporter(librato_email, librato_token)
appmetrics.reporter.register(librato_reporter, fixed_interval_scheduler(5))
```
