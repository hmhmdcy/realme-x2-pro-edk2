#!/usr/bin/env python3
"""Offline state tests for the Plasma Mobile power-key bridge."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import types


REPO = pathlib.Path(__file__).resolve().parents[2]
PATH = REPO / "linux-port/packages/samurai-desktop/samurai-powerkey"

loader = importlib.machinery.SourceFileLoader("samurai_powerkey", str(PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Session:
    runtime_dir = "/run/user/10000"

    def refresh(self) -> bool:
        return True


class Display:
    def __init__(self) -> None:
        self.bl = 0
        self.dpms = "on"
        self.dpms_calls: list[str] = []
        self.mode_calls: list[str] = []

    def bl_power(self) -> int | None:
        return self.bl

    def dpms_state(self) -> str | None:
        return self.dpms

    def set_dpms(self, target: str) -> bool:
        self.dpms_calls.append(target)
        self.dpms = target
        if target == "on":
            self.bl = 0
        return True

    def modeset_plan(self) -> tuple[str, str, str] | None:
        return "DSI-1", "1080x2400@90", "1080x2400@60"

    def _run(self, arguments: list[str], timeout: float = 5.0):
        self.mode_calls.append(" ".join(arguments))
        return types.SimpleNamespace(returncode=0)

    def lock(self) -> None:
        pass


clock = Clock()
module.time.monotonic = clock.monotonic
module.time.sleep = clock.sleep


def new_bridge() -> tuple[object, Display]:
    bridge = module.PowerKeyBridge(Session())
    display = Display()
    bridge.display = display
    bridge.last_bl_power = display.bl
    return bridge, display


def test_external_wake_modeset() -> None:
    bridge, display = new_bridge()
    bridge.last_bl_power = 4
    display.bl = 0
    bridge.monitor()
    clock.advance(0.40)
    bridge.monitor()
    assert display.dpms_calls == ["on"], display.dpms_calls
    assert display.mode_calls == [], display.mode_calls


def test_wake_modesets_only_when_panel_stays_gated() -> None:
    bridge, display = new_bridge()
    display.dpms = "off"
    display.bl = 4

    def slow_panel(target: str) -> bool:
        display.dpms_calls.append(target)
        display.dpms = target
        if target == "on":
            display.bl = 4
        return True

    display.set_dpms = slow_panel

    def mode_run(arguments: list[str], timeout: float = 5.0):
        display.mode_calls.append(" ".join(arguments))
        if arguments[0].endswith("@90"):
            display.bl = 0
        return types.SimpleNamespace(returncode=0)

    display._run = mode_run
    assert bridge.wake("test")
    assert display.dpms_calls == ["on"], display.dpms_calls
    assert display.mode_calls == [
        "output.DSI-1.mode.1080x2400@60",
        "output.DSI-1.mode.1080x2400@90",
    ], display.mode_calls


def test_touch_wake_race_restores_once() -> None:
    bridge, display = new_bridge()
    bridge.last_bl_power = 4
    display.bl = 0
    display.dpms = "off"
    bridge.monitor()
    clock.advance(0.40)
    bridge.monitor()
    assert display.dpms_calls == ["on"], display.dpms_calls

    calls = len(display.dpms_calls)
    display.dpms = "off"
    display.bl = 4
    clock.advance(module.WAKE_RECOVERY_POLL_SECONDS + 0.01)
    bridge.monitor()
    assert len(display.dpms_calls) == calls + 1, display.dpms_calls

    calls = len(display.dpms_calls)
    display.dpms = "off"
    display.bl = 4
    clock.advance(module.WAKE_RECOVERY_POLL_SECONDS + 0.01)
    bridge.monitor()
    assert len(display.dpms_calls) == calls + 1, display.dpms_calls

    calls = len(display.dpms_calls)
    display.dpms = "off"
    display.bl = 4
    clock.advance(module.WAKE_RECOVERY_POLL_SECONDS + 0.01)
    bridge.monitor()
    assert len(display.dpms_calls) == calls, display.dpms_calls


def test_deliberate_sleep_cancels_recovery() -> None:
    bridge, display = new_bridge()
    bridge._note_wake_requested()
    assert bridge.wake_recovery_until > clock.now
    display.dpms = "on"
    display.bl = 0
    assert bridge.sleep()
    assert bridge.wake_recovery_until == 0.0
    assert bridge.wake_recovery_retries == 0


def test_power_toggle_uses_real_dpms_not_bl_power() -> None:
    bridge, display = new_bridge()
    display.dpms = "off"
    display.bl = 4
    bridge.toggle()
    assert display.dpms_calls[:1] == ["on"], display.dpms_calls

    bridge, display = new_bridge()
    display.dpms = "on"
    display.bl = 0
    bridge.toggle()
    assert display.dpms_calls == ["off"], display.dpms_calls


def main() -> None:
    test_external_wake_modeset()
    test_wake_modesets_only_when_panel_stays_gated()
    test_touch_wake_race_restores_once()
    test_deliberate_sleep_cancels_recovery()
    test_power_toggle_uses_real_dpms_not_bl_power()
    print("samurai-powerkey state tests passed")


if __name__ == "__main__":
    main()
