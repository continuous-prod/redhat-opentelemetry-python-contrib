redhat-opentelemetry-python-contrib
===================================
OpenTelemetry Python extensions written at Red Hat

This repository includes:
* File exporters to export OpenTelemetry data to files when using auto-instrumentation
* Script instrumentor - Auto instrumentation plugin for wrapping an entire
  python script run in a tracing span

Installation
------------
```
pip install redhat-opentelemetry-python-contrib
```

Using the file exporters
------------------------
The file exporters can be used by setting the `OTEL_*_EXPORTER` environment
variables to `file`, or using the equivalent arguments to
`opentelemetry-instrument`.

For example to export span data to a file for a particular Python script:
```
opentelemetry-instrument --traces_exporter file python myscript.py
```

The file to which the data will be written to can be customized using the
environment variables listed below. Otherwise, the listed default value would
be used:

| Variable                         | Used for   | Default value      |
| -------------------------------- | ---------- | ------------------ |
| `OTEL_FILE_SPAN_EXPORTER_NAME`   | Trace data | `otel_traces.log`  |
| `OTEL_FILE_METRIC_EXPORTER_NAME` | Metrics    | `otel_metrics.log` |
| `OTEL_FILE_LOG_EXPORTER_NAME`    | Logs       | `otel_logs.log`    |

Using the script instrumentor
-----------------------------
Once installed, the script instrumentor will automatically wrap any Python
script invoked with auto instrumentation enabled in a span that would include
the script name, command-line arguments and exit status.

The script instrumentor attempts to propagate the tracing context from the
environment it was invoked in, by trying to read environment variables that are
capitalized versions of the HTTP headers defined by the [W3C Trace Context
specification][w3c]. This typically means that if the `TRACEPARENT` environment
variable is defined in the environment the script runs in, the script span will
become a child span of that trace. This is generally compatible with how other
tools and systems handle things such as the [Ansible OpenTelemetry callback
plugin][ans] and the [Jenkins OpenTelemetry plugin][jnk].

The script instrumentor can cause traces to look a bit strange for things that
are not meant to be stand-alone Python scripts such as Django and Flask server
processes. It can be disabled by setting the
`OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` environment variable:
```
export OTEL_PYTHON_DISABLED_INSTRUMENTATIONS="__main__"
```

[w3c]: https://www.w3.org/TR/trace-context/
[ans]: https://docs.ansible.com/ansible/latest/collections/community/general/opentelemetry_callback.html
[jnk]: https://github.com/jenkinsci/opentelemetry-plugin
