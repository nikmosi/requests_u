import asyncio

import pytest

import main
import main as main_module


class FakeContainer:
    instances: list["FakeContainer"] = []

    def __init__(self):
        self.init_completed = False
        self.shutdown_completed = False
        type(self).instances.append(self)

    def init_resources(self):
        async def _init():
            await asyncio.sleep(0)
            self.init_completed = True

        return _init()

    def wire(self, modules):  # pragma: no cover - simple test double hook
        self.modules = modules

    def shutdown_resources(self):
        async def _shutdown():
            await asyncio.sleep(0)
            self.shutdown_completed = True

        return _shutdown()


def test_middleware_shuts_down_resources(monkeypatch):
    FakeContainer.instances = []

    async def failing_main():
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "Container", FakeContainer)
    monkeypatch.setattr(main_module, "main", failing_main)

    with pytest.raises(RuntimeError):
        asyncio.run(main_module.middleware())

    assert FakeContainer.instances, "Container should have been instantiated"
    instance = FakeContainer.instances[-1]
    assert instance.init_completed
    assert instance.shutdown_completed


def test_entrypoint_suppresses_keyboard_interrupt(monkeypatch):
    async def raise_keyboard_interrupt():
        raise KeyboardInterrupt

    monkeypatch.setattr(main, "middleware", raise_keyboard_interrupt)

    main.entrypoint()
