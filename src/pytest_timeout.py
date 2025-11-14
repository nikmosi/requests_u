from __future__ import annotations

import time
from dataclasses import dataclass

import pytest

from core import BaseAppError


@dataclass(frozen=True, slots=True, kw_only=True)
class TimeoutExceededError(BaseAppError):
    node_id: str
    timeout: float
    duration: float

    @property
    def message(self) -> str:
        return (
            f"Test {self.node_id!r} exceeded the configured timeout "
            f"of {self.timeout:.2f}s (took {self.duration:.2f}s)."
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("timeout")
    group.addoption(
        "--timeout",
        dest="timeout",
        type=float,
        default=None,
        help="Maximum amount of seconds a single test is allowed to run.",
    )


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_call(item: pytest.Item):
    timeout = item.config.getoption("timeout")
    if timeout is None:
        yield
        return

    start = time.perf_counter()
    outcome = yield
    duration = time.perf_counter() - start

    if outcome.excinfo is None and duration > timeout:
        raise TimeoutExceededError(
            node_id=item.nodeid, timeout=timeout, duration=duration
        )
