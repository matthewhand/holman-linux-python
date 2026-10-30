"""Offline regression tests for the existing fork PR #1 BLE callback semantics.

No actual gatt, Bluetooth adapter, Home Assistant, network or third-party test
package is imported. The fake write_value records a request; only explicit
callback simulation completes it, just as the DBus-backed API does.
"""
import sys
import types
import unittest
from unittest.mock import patch

class FakeManager:
    def __init__(self, adapter_name="hci0"):
        self.adapter_name = adapter_name
        self.aliases = {}
        self.listener = None
        self.known_devices = []
        self.discovery_uuids = None
        self.discovered_tap_timers = {}
        self.stopped = False
    def devices(self):
        return self.known_devices
    def start_discovery(self, service_uuids=None):
        self.discovery_uuids = service_uuids
    def device_discovered(self, device):
        pass
    def stop(self):
        self.stopped = True
    def run(self):
        pass

class FakeDevice:
    def __init__(self, mac_address, manager, managed=True):
        self.mac_address = mac_address
        self.manager = manager
        self.services = []
    def alias(self):
        return self.manager.aliases.get(self.mac_address, "")
    def connect(self):
        pass
    def connect_failed(self, error):
        pass
    def disconnect(self):
        pass
    def disconnect_succeeded(self):
        pass
    def services_resolved(self):
        pass

class FakeCharacteristic:
    def __init__(self, uuid, value=b"\x00"):
        self.uuid = uuid
        self.value = value
        self.written = []
        self.raise_on_write = None
    def write_value(self, value):
        if self.raise_on_write:
            raise self.raise_on_write
        self.written.append(bytes(value))
    def read_value(self):
        return self.value

class FakeService:
    def __init__(self, uuid, characteristics):
        self.uuid = uuid
        self.characteristics = characteristics

fake_gatt = types.ModuleType("gatt")
fake_gatt.Device = FakeDevice
fake_gatt.DeviceManager = FakeManager
sys.modules["gatt"] = fake_gatt

import holman
import holmanctl

class Events(holman.TapTimerListener):
    def __init__(self):
        self.events = []
    def timer_written(self):
        self.events.append("written")
    def timer_write_failed(self, error):
        self.events.append(("failed", str(error)))
    def connect_failed(self, error):
        self.events.append(("connect_failed", str(error)))
    def disconnect_succeeded(self):
        self.events.append("disconnected")

class CallbackSafetyTests(unittest.TestCase):
    def setUp(self):
        self.manager = holman.TapTimerManager()
        self.tap = holman.TapTimer("AA:BB:CC:DD:EE:FF", self.manager)
        self.listener = Events()
        self.tap.listener = self.listener
        self.manual = FakeCharacteristic(self.tap.MANUAL_CHARACTERISTIC_UUID)
        self.state = FakeCharacteristic(self.tap.STATE_CHARACTERISTIC_UUID)
        self.auth = FakeCharacteristic(self.tap.AUTH_CHARACTERISTIC_UUID)
    def resolve(self, auth=True):
        chars = [self.manual, self.state] + ([self.auth] if auth else [])
        self.tap.services = [FakeService(self.tap.HOLMAN_CO3011_SERVICE_UUID, chars)]
        self.tap.services_resolved()

    def test_01_pr1_zone2_start_waits_for_async_unlock(self):
        self.resolve()
        self.tap.start(runtime=1, zone=2)
        self.assertEqual(self.auth.written, [b"\xae\x8e"])
        self.assertEqual(self.manual.written, [])
        self.tap.characteristic_write_value_succeeded(self.auth)
        self.assertEqual(self.manual.written, [b"\x01\x01\x00\x01"])
        self.assertEqual(self.listener.events, [])
        self.tap.characteristic_write_value_succeeded(self.manual)
        self.assertEqual(self.listener.events, ["written"])

    def test_02_invalid_zone_fails_before_any_write(self):
        self.resolve()
        for zone in (0, 3, -1, "2", None, True):
            with self.subTest(zone=zone):
                with self.assertRaises(ValueError):
                    self.tap.start(runtime=1, zone=zone)
        self.assertEqual(self.auth.written, [])
        self.assertEqual(self.manual.written, [])

    def test_03_unlock_failure_blocks_start(self):
        self.resolve()
        self.tap.start(runtime=1, zone=1)
        self.tap.characteristic_write_value_failed(self.auth, RuntimeError("denied"))
        self.assertEqual(self.manual.written, [])
        self.assertEqual(self.listener.events, [("failed", "denied")])

    def test_04_stop_supersedes_queued_start(self):
        self.resolve()
        self.tap.start(runtime=1, zone=2)
        self.tap.stop()
        self.assertEqual(len(self.auth.written), 1)
        self.assertEqual(self.manual.written, [])
        self.tap.characteristic_write_value_succeeded(self.auth)
        self.assertEqual(self.manual.written, [bytes(4)])

    def test_05_stop_attempts_all_off_if_unlock_denied(self):
        self.resolve()
        self.tap.stop()
        self.assertEqual(self.manual.written, [])
        self.tap.characteristic_write_value_failed(self.auth, RuntimeError("denied"))
        self.assertEqual(self.manual.written, [bytes(4)])
        self.assertEqual(self.listener.events, [])

    def test_06_disconnection_cancels_pending_start(self):
        self.resolve()
        self.tap.start(runtime=1, zone=2)
        self.tap.disconnect_succeeded()
        self.tap.characteristic_write_value_succeeded(self.auth)
        self.assertEqual(self.manual.written, [])
        self.assertEqual(self.listener.events, ["disconnected"])

    def test_07_pending_start_refuses_another_start(self):
        self.resolve()
        self.tap.start(runtime=1, zone=1)
        with self.assertRaises(RuntimeError):
            self.tap.start(runtime=1, zone=2)
        self.tap.characteristic_write_value_succeeded(self.auth)
        self.assertEqual(self.manual.written, [b"\x01\x00\x00\x01"])

    def test_08_no_auth_legacy_co3015_direct_write(self):
        self.tap.services = [FakeService(self.tap.HOLMAN_CO3015_SERVICE_UUID, [self.manual, self.state])]
        self.tap.services_resolved()
        self.tap.start(runtime=1, zone=1)
        self.tap.stop()
        self.assertEqual(self.manual.written, [b"\x01\x00\x00\x01", bytes(4)])

    def test_09_start_sync_auth_exception_does_not_emit_manual(self):
        self.resolve()
        self.auth.raise_on_write = RuntimeError("c001 missing")
        self.tap.start(runtime=1, zone=2)
        self.assertEqual(self.manual.written, [])
        self.assertEqual(self.listener.events, [("failed", "c001 missing")])

    def test_10_sync_stop_auth_failure_still_attempts_all_off(self):
        self.resolve()
        self.auth.raise_on_write = RuntimeError("c001 missing")
        self.tap.stop()
        self.assertEqual(self.manual.written, [bytes(4)])

    def test_11_manual_write_success_and_failure_callbacks(self):
        self.resolve(auth=False)
        self.tap.start(runtime=1, zone=1)
        self.tap.characteristic_write_value_succeeded(self.manual)
        self.tap.characteristic_write_value_failed(self.manual, RuntimeError("ATT error"))
        self.assertEqual(self.listener.events, ["written", ("failed", "ATT error")])

    def test_12_exact_bx2_alias_and_legacy_alias(self):
        self.manager.aliases["AA:BB:CC:DD:EE:FF"] = "BX2"
        self.assertIsNotNone(self.manager.make_device("AA:BB:CC:DD:EE:FF"))
        self.manager.aliases["AA:BB:CC:DD:EE:FF"] = "Tap Timer"
        self.assertIsNotNone(self.manager.make_device("AA:BB:CC:DD:EE:FF"))
        self.manager.aliases["AA:BB:CC:DD:EE:FF"] = "Other"
        self.assertIsNone(self.manager.make_device("AA:BB:CC:DD:EE:FF"))


    def test_13_stop_sync_unlock_and_manual_failure_reports_error(self):
        self.resolve()
        self.auth.raise_on_write = RuntimeError("auth unavailable")
        self.manual.raise_on_write = RuntimeError("all-off rejected")
        self.tap.stop()
        self.assertEqual(self.listener.events, [("failed", "all-off rejected")])
        self.assertEqual(self.manual.written, [])

    def test_14_stop_async_unlock_and_manual_failure_reports_error(self):
        self.resolve()
        self.manual.raise_on_write = RuntimeError("all-off rejected")
        self.tap.stop()
        self.tap.characteristic_write_value_failed(self.auth, RuntimeError("auth rejected"))
        self.assertEqual(self.listener.events, [("failed", "all-off rejected")])

    def test_15_stop_success_ack_notifies_once(self):
        self.resolve()
        self.tap.stop()
        self.assertEqual(self.manual.written, [])
        self.assertEqual(self.listener.events, [])
        self.tap.characteristic_write_value_succeeded(self.auth)
        self.assertEqual(self.manual.written, [bytes(4)])
        self.assertEqual(self.listener.events, [])
        self.tap.characteristic_write_value_succeeded(self.manual)
        self.assertEqual(self.listener.events, ["written"])

class LegacyCliTests(unittest.TestCase):
    def test_old_cli_spellings_preserved(self):
        for flag in ("--start", "--stop", "--minutes", "--zone", "--connect", "--auto", "--disconnect", "--known", "--discover"):
            with self.subTest(flag=flag):
                self.assertIn(flag, __import__("inspect").getsource(holmanctl.main))

    def test_reject_bad_zone_before_constructing_manager(self):
        for zone in ("0", "3", "-1", "hose"):
            with self.subTest(zone=zone):
                with patch.object(sys, "argv", ["holmanctl", "--start", "AA:BB:CC:DD:EE:FF", "--zone", zone]), patch.object(holmanctl, "holman") as holman_module:
                    with self.assertRaises(SystemExit) as context:
                        holmanctl.main()
                    self.assertEqual(context.exception.code, 2)
                    holman_module.TapTimerManager.assert_not_called()

class CliCallbackIntegrationTests(unittest.TestCase):
    def invoke(self, *args):
        active = []
        def connect(tap):
            active.append(tap)
            m = FakeCharacteristic(tap.MANUAL_CHARACTERISTIC_UUID)
            s = FakeCharacteristic(tap.STATE_CHARACTERISTIC_UUID)
            a = FakeCharacteristic(tap.AUTH_CHARACTERISTIC_UUID)
            tap.services = [FakeService(tap.HOLMAN_CO3011_SERVICE_UUID, [m, s, a])]
            tap.services_resolved()
            tap.test_chars = (a, m)
        with patch.object(sys, "argv", ["holmanctl", *args]), patch.object(holman.TapTimer, "connect", connect):
            result = holmanctl.main()
        return result, active

    def test_legacy_start_completes_after_manual_ack(self):
        _, active = self.invoke("--start", "AA:BB:CC:DD:EE:FF", "--minutes", "1", "--zone", "2")
        self.assertEqual(len(active), 1)
        tap = active[0]
        auth, manual = tap.test_chars
        self.assertEqual(manual.written, [])
        tap.characteristic_write_value_succeeded(auth)
        self.assertEqual(manual.written, [b"\x01\x01\x00\x01"])
        disconnected = []
        with patch.object(holman.TapTimer, "disconnect", lambda this: disconnected.append(this)):
            tap.characteristic_write_value_succeeded(manual)
        self.assertEqual(disconnected, [tap])

    def test_legacy_stop_completes_after_manual_ack(self):
        _, active = self.invoke("--stop", "AA:BB:CC:DD:EE:FF")
        tap = active[0]
        auth, manual = tap.test_chars
        self.assertEqual(manual.written, [])
        tap.characteristic_write_value_succeeded(auth)
        self.assertEqual(manual.written, [bytes(4)])
        disconnected = []
        with patch.object(holman.TapTimer, "disconnect", lambda this: disconnected.append(this)):
            tap.characteristic_write_value_succeeded(manual)
        self.assertEqual(disconnected, [tap])

    def test_legacy_start_failure_exits_nonzero(self):
        _, active = self.invoke("--start", "AA:BB:CC:DD:EE:FF")
        tap = active[0]
        auth, manual = tap.test_chars
        with self.assertRaises(SystemExit) as cm:
            tap.characteristic_write_value_failed(auth, RuntimeError("unlock denied"))
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(manual.written, [])

    def test_legacy_cli_invalid_runtime_refused_before_device(self):
        for minutes in ("0", "-1", "256", "nope"):
            with self.subTest(minutes=minutes), patch.object(sys, "argv", ["holmanctl", "--start", "AA:BB:CC:DD:EE:FF", "--minutes", minutes]), patch.object(holmanctl, "holman") as stub:
                with self.assertRaises(SystemExit) as cm:
                    holmanctl.main()
                self.assertEqual(cm.exception.code, 2)
                stub.TapTimerManager.assert_not_called()

if __name__ == "__main__":
    unittest.main()
