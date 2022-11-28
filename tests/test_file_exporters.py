# -*- coding: utf-8 -*-
# Copyright 2022 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Tests for file_exporters.py"""
import json
from pathlib import Path
from subprocess import run
from typing import Final

import pytest
from opentelemetry import trace


@pytest.fixture
def console_exporters_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure all exportes are the to 'console' by default"""
    monkeypatch.delenv("TRACECONTEXT", raising=False)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    monkeypatch.setenv("OTEL_METRICS_EXPORTER", "console")
    monkeypatch.setenv("OTEL_LOGS_EXPORTER", "console")


@pytest.fixture
def tmp_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, Path]:
    """Create temporary log file paths and define env ars to amke the OTel exporeters use them"""
    traces_log = tmp_path / "_otel_traces.log"
    metrics_log = tmp_path / "_otel_metrics.log"
    otel_logs = tmp_path / "_otel_logs.log"

    monkeypatch.setenv("OTEL_FILE_SPAN_EXPORTER_NAME", str(traces_log))
    monkeypatch.setenv("OTEL_FILE_METRIC_EXPORTER_NAME", str(metrics_log))
    monkeypatch.setenv("OTEL_FILE_LOG_EXPORTER_NAME", str(otel_logs))

    return traces_log, metrics_log, otel_logs


@pytest.fixture
def tmp_traces_log(tmp_logs: tuple[Path, Path, Path]) -> Path:
    """Convenient ficture for getting just the traces log path"""
    return tmp_logs[0]


@pytest.fixture
def tmp_metrics_log(tmp_logs: tuple[Path, Path, Path]) -> Path:
    """Convenient ficture for getting just the metrics log path"""
    return tmp_logs[1]


@pytest.fixture
def tmp_otel_logs(tmp_logs: tuple[Path, Path, Path]) -> Path:
    """Convenient ficture for getting just the logs file path"""
    return tmp_logs[2]


TEST_SPAN_NAME: Final[str] = "Hello span"


@pytest.mark.usefixtures("console_exporters_env")
def test_file_span_exporter(
    tmp_traces_log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the FileSpanExporter with auto-instrumentation"""
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "file")

    run(["opentelemetry-instrument", "python", __file__], check=True)
    # tmp_traces_log.write_text('{"name": "Hello span", "kind": "SpanKind.INTERNAL"}')

    assert tmp_traces_log.exists()
    with tmp_traces_log.open("r") as tmp_traces_f:
        trace_json = json.load(tmp_traces_f)
        assert trace_json["name"] == TEST_SPAN_NAME
        assert trace_json["kind"] == "SpanKind.INTERNAL"


@pytest.mark.usefixtures("console_exporters_env")
def test_file_metrics_exporter(
    tmp_metrics_log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test the FileMetricsExporter with auto-instrumentation"""
    monkeypatch.setenv("OTEL_METRICS_EXPORTER", "file")

    run(["opentelemetry-instrument", "python", __file__], check=True)

    assert tmp_metrics_log.exists()
    with tmp_metrics_log.open("r") as tmp_metrics_f:
        metrics_json = json.load(tmp_metrics_f)
        assert (
            metrics_json["resource_metrics"][0]["resource"]["attributes"][
                "telemetry.sdk.name"
            ]
            == "opentelemetry"
        )


if __name__ == "__main__":
    # Creates a tracer from the global tracer provider, since we didn't setup
    # any processors or exporters, the auto-configured ones should be used
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span(TEST_SPAN_NAME):
        print("Hi there")
