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
"""File exporters for Open telemetry

Those classes act as exporters for the Open telemetry library, allowing to export the
trace, metrics and logs data to a file.
"""
import os
from typing import Optional

from opentelemetry.sdk._logs.export import (
    ConsoleLogExporter,  # type: ignore[attr-defined]
)
from opentelemetry.sdk.metrics._internal.export import (
    ConsoleMetricExporter,  # type: ignore[attr-defined]
)
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,  # type: ignore[attr-defined]
)


class EnvVars:
    # pylint: disable=too-few-public-methods
    """This class is meant to be registered as an
    `opentelemetry_environment_variables` entry point to expose our env vars to
    the OTel tooling
    """

    OTEL_FILE_SPAN_EXPORTER_NAME = "OTEL_FILE_SPAN_EXPORTER_NAME"
    OTEL_FILE_METRIC_EXPORTER_NAME = "OTEL_FILE_METRIC_EXPORTER_NAME"
    OTEL_FILE_LOG_EXPORTER_NAME = "OTEL_FILE_LOG_EXPORTER_NAME"


# All classes below need to open files and close them much later outside of
# neat block boundaries
# pylint: disable=consider-using-with


class FileSpanExporter(ConsoleSpanExporter):
    """Implementation of :class:`ConsoleSpanExporter` that writes spans to a
    file.

    This class can be used for diagnostic purposes. It writes the exported
    spans to a file.
    """

    def __init__(
        self,
        service_name: Optional[str] = None,
        file_path: str = os.environ.get(
            EnvVars.OTEL_FILE_SPAN_EXPORTER_NAME, "otel_traces.log"
        ),
    ) -> None:
        super().__init__(
            out=open(file_path, "a", encoding="utf-8"), service_name=service_name
        )
        self.file_path = file_path

    def __del__(self):
        self.out.close()


class FileMetricExporter(ConsoleMetricExporter):
    """Implementation of :class:`ConsoleMetricExporter` that writes metrics to
    a file.

    This class can be used for debugging purposes. It writes the exported
    metrics to a file.
    """

    def __init__(
        self,
        file_path: str = os.environ.get(
            EnvVars.OTEL_FILE_METRIC_EXPORTER_NAME, "otel_metrics.log"
        ),
    ) -> None:
        super().__init__(out=open(file_path, "a", encoding="utf-8"))
        self.file_path = file_path

    def __del__(self):
        self.out.close()


class FileLogExporter(ConsoleLogExporter):
    """Implementation of :class:`ConsoleLogExporter` that writes log records
    to a file.

    This class can be used for debugging purposes. It writes the exported
    log records to a file.
    """

    def __init__(
        self,
        file_path: str = os.environ.get(
            EnvVars.OTEL_FILE_LOG_EXPORTER_NAME, "otel_logs.log"
        ),
    ) -> None:
        super().__init__(out=open(file_path, "a", encoding="utf-8"))
        self.file_path = file_path

    def __del__(self):
        self.out.close()
