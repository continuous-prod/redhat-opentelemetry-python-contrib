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
"""Automated instrumentation for Python scripts

This create an OpenTelemetry span that wraps an entire script and includes
information about the command line arguments its got and the exceptions raised
"""
import atexit
import os
import sys
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Any, Collection, NoReturn, Optional, Protocol, Type
from warnings import warn

from opentelemetry import trace
from opentelemetry.instrumentation.instrumentor import (  # type: ignore[attr-defined]
    BaseInstrumentor,
)
from opentelemetry.propagate import extract, inject
from opentelemetry.propagators.textmap import CarrierValT, Getter, Setter
from opentelemetry.trace.span import Span
from opentelemetry.trace.status import StatusCode

from .__version__ import __version__


class UndoingEnvironGetterSetter(Setter[os._Environ], Getter[os._Environ]):
    # pylint: disable=protected-access
    """OTel getter/setter for propagating value via environment variables. It
    also includes an undo buffer so changes can be undone"""

    # Since carrier is passed in as a parameter to the calls we must
    # differentiate undo buffers by carrier as well as keep references to the
    # carriers to enable undo
    _undo_buffer: dict[int, tuple[os._Environ, dict[str, Optional[list[str]]]]]

    def __init__(self):
        self._undo_buffer = {}

    def set(self, carrier: os._Environ, key: str, value: CarrierValT) -> None:
        """Write on OTel context propagation value into the environment"""
        if not isinstance(value, str):
            warn("Propagation of non-string values to environment is not supported")
            return
        ukey = key.upper()
        carrier_ub = self._undo_buffer.setdefault(id(carrier), (carrier, {}))[1]
        carrier_ub.setdefault(ukey, self.get(carrier, ukey))
        carrier[ukey] = value

    def get(self, carrier: os._Environ, key: str) -> Optional[list[str]]:
        """Read an OTel context propagation value from the environment"""
        if key.upper() not in carrier:
            return None
        return [carrier[key.upper()]]

    def keys(self, carrier: os._Environ) -> list[str]:
        """Return the list of OTel context propagation keys"""
        return [k.lower() for k in carrier]

    def undo(self) -> None:
        """Undo all changes made to all carriers since this object was created
        or the last undo invocation"""
        for carrier, unb in self._undo_buffer.values():
            for key, vlist in unb.items():
                if vlist is None:
                    del carrier[key]
                else:
                    carrier[key] = vlist[0]
        self._undo_buffer = {}


class ExceptionHook(Protocol):
    # pylint: disable=too-few-public-methods
    """Represent the signature for a sys.excepthook function"""

    def __call__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: Optional[TracebackType],
        /,
    ) -> Any:
        pass


class ExitFunc(Protocol):
    # pylint: disable=too-few-public-methods
    """Represent the signature for the sys.exit function"""

    def __call__(self, exit_code: object = 0, /) -> NoReturn:
        pass


class ScriptInstrumentor(BaseInstrumentor):
    """Open telemetry instrumentor for scripts"""

    _old_excepthook: ExceptionHook
    _old_exit: ExitFunc
    _span: Optional[Span]
    _span_ctx: Optional[AbstractContextManager[Span]]
    _exit_code: int
    _exc_info: tuple[
        Optional[type[BaseException]], Optional[BaseException], Optional[TracebackType]
    ]
    _env_setter_getter: UndoingEnvironGetterSetter

    def __init__(self):
        self._old_excepthook = sys.excepthook
        self._old_exit = sys.exit
        self._span = None
        self._span_ctx = None
        self._exit_code = 0
        self._exc_info = None, None, None
        self._env_setter_getter = UndoingEnvironGetterSetter()

    def instrumentation_dependencies(self) -> Collection[str]:
        return tuple()

    def _start_span(
        self, tracer: trace.Tracer, script_file: str, script_args: list[str]
    ) -> None:
        context = extract(os.environ, getter=self._env_setter_getter)
        self._span = tracer.start_span(os.path.basename(script_file), context=context)
        self._span.set_attributes(
            dict(script_file=script_file, script_args=script_args)
        )
        self._span_ctx = trace.use_span(self._span, end_on_exit=True)
        # Since MyPy is actually letting the line below pass just fine,
        # disabling pylint that fails on it since it does not trace types
        # properly
        self._span_ctx.__enter__()  # pylint: disable=no-member,unnecessary-dunder-call
        # Inject span context back into the environment so that if we run
        # Python sub processes they become child spans of this process
        inject(os.environ, setter=self._env_setter_getter)

    def _end_span(self) -> None:
        assert self._span
        assert self._span_ctx
        self._span.set_status(
            StatusCode.OK if self._exit_code == 0 else StatusCode.ERROR
        )
        self._span.set_attribute("script_exit_code", self._exit_code)
        self._env_setter_getter.undo()
        # Since MyPy is actually letting the line below pass just fine,
        # disabling pylint that fails on it since it does not trace types
        # properly
        self._span_ctx.__exit__(*self._exc_info)  # pylint: disable=no-member

    def _instrumented_exit(self, code: object = 0, /) -> NoReturn:
        """Figure out what the process exist code is going to be by imitating
        sys.exit's behaviour where it either uses the int passed to it, treats
        None like 0 or any other object like 1. Store that so we can report it
        on the span"""
        if code is None:
            self._exit_code = 0
        elif isinstance(code, int):
            self._exit_code = code
        else:
            self._exit_code = 1
        self._old_exit(code)

    def _excepthook(
        self,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        traceback: Optional[TracebackType],
    ) -> None:
        self._exc_info = exc_type, exc_value, traceback
        if self._exit_code == 0:
            # We don't get a proper exit code when the interpreter is exiting
            # via an exception so fix that here
            self._exit_code = 1
        self._old_excepthook(exc_type, exc_value, traceback)

    def _instrument(self, **kwargs: Any) -> None:
        script_file = sys.argv and sys.argv[0]
        if not script_file or script_file == "-c":
            # Don't instrument something that isn't a script if `argv[0]` is
            # "-c" it means this is a `python -c` command rather then a full
            # script and we don't want to trace that
            return

        tracer_provider = kwargs.get("tracer_provider")
        tracer = trace.get_tracer(__name__, __version__, tracer_provider)

        sys.excepthook = self._excepthook
        sys.exit = self._instrumented_exit
        atexit.register(self._end_span)

        self._start_span(tracer, script_file, sys.argv)

    def _uninstrument(self, **_: Any) -> None:
        atexit.unregister(self._end_span)
        sys.exit = self._old_exit
        sys.excepthook = self._old_excepthook
