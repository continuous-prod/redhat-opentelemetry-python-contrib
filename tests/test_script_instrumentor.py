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
"""Tests for script_instrumentor.py"""
import json
from pathlib import Path
from subprocess import run

import pytest


@pytest.fixture
def console_exporters_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure all exportes are the to 'console' by default"""
    monkeypatch.delenv("TRACECONTEXT", raising=False)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "console")
    monkeypatch.setenv("OTEL_METRICS_EXPORTER", "console")
    monkeypatch.setenv("OTEL_LOGS_EXPORTER", "console")


@pytest.fixture
def tmp_traces_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Direct traces to file so we can inspect them"""
    traces_log = tmp_path / "_otel_traces.log"
    monkeypatch.setenv("OTEL_FILE_SPAN_EXPORTER_NAME", str(traces_log))
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "file")
    return traces_log


@pytest.mark.usefixtures("console_exporters_env")
def test_script_instrumentor_traces_script_invocation(
    tmp_traces_log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that we get a logged span when running a script"""
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "file")

    run(["opentelemetry-instrument", "python", __file__], check=True)

    assert tmp_traces_log.exists()
    trace_json = {}
    with tmp_traces_log.open("r") as tmp_traces_f:
        trace_json = json.load(tmp_traces_f)
    assert trace_json["name"] == Path(__file__).name
    assert trace_json["kind"] == "SpanKind.INTERNAL"
    assert trace_json["attributes"]["script_file"] == __file__
    assert trace_json["attributes"]["script_args"] == [__file__]
    assert trace_json["attributes"]["script_exit_code"] == 0


if __name__ == "__main__":
    # Allow this file to be used as a stand-alone script fur testing purposes
    print("Hi there")
