"Shipped f006 payload builder — import the real function, not a copy."

import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'holman'


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


payload = _load('holman.payload', 'payload.py')
aliases = _load('holman.aliases', 'aliases.py')
manual_payload = payload.manual_payload
tap_for_zone = payload.tap_for_zone
tap_name = payload.tap_name
clamp_runtime = payload.clamp_runtime
get_default_aliases = aliases.get_default_aliases
alias_accepted = aliases.alias_accepted
get_default_service_uuids = aliases.get_default_service_uuids
DEFAULT_SERVICE_UUIDS = aliases.DEFAULT_SERVICE_UUIDS
HOLMAN_CO3015_SERVICE_UUID = aliases.HOLMAN_CO3015_SERVICE_UUID
HOLMAN_CO3012_SERVICE_UUID = aliases.HOLMAN_CO3012_SERVICE_UUID
HOLMAN_CO3011_SERVICE_UUID = aliases.HOLMAN_CO3011_SERVICE_UUID
UNKNOWN_SERVICE_UUID = '00000000-0000-0000-0000-000000000000'


class TestManualPayload(unittest.TestCase):
    def test_start_sprinkler(self):
        self.assertEqual(list(manual_payload(True, 3, 1)), [0x01, 0x00, 0x00, 3])

    def test_start_hose(self):
        self.assertEqual(list(manual_payload(True, 1, 2)), [0x01, 0x01, 0x00, 1])

    def test_hose_payload_bytes(self):
        self.assertEqual(list(manual_payload(True, 5, 2)), [0x01, 0x01, 0x00, 5])

    def test_stop_all_zero(self):
        self.assertEqual(list(manual_payload(False, 10, 2)), [0x00, 0x00, 0x00, 0x00])
        self.assertEqual(list(manual_payload(False, 0, 0)), [0x00, 0x00, 0x00, 0x00])

    def test_minutes_clamped(self):
        self.assertEqual(list(manual_payload(True, 0, 2))[3], 1)
        self.assertEqual(list(manual_payload(True, 999, 1))[3], 255)
        self.assertEqual(clamp_runtime(0), 1)
        self.assertEqual(clamp_runtime(999), 255)

    def test_invalid_zone_fails_closed(self):
        with self.assertRaises(ValueError):
            manual_payload(True, 5, 3)
        with self.assertRaises(ValueError):
            manual_payload(True, 5, 0)
        with self.assertRaises(ValueError):
            tap_for_zone(9)
        with self.assertRaises(ValueError):
            tap_for_zone('hose')

    def test_tap_helpers(self):
        self.assertEqual(tap_for_zone(1), 0x00)
        self.assertEqual(tap_for_zone(2), 0x01)
        self.assertEqual(tap_name(1), 'Sprinkler')
        self.assertEqual(tap_name(2), 'Hose')


class TestAcceptedAliases(unittest.TestCase):
    def _clear_alias_env(self):
        return os.environ.pop('HOLMAN_ACCEPTED_ALIASES', None)

    def _restore_alias_env(self, aliases):
        if aliases is not None:
            os.environ['HOLMAN_ACCEPTED_ALIASES'] = aliases

    def test_default_exact_tap_timer_and_bx2(self):
        old_aliases = self._clear_alias_env()
        try:
            self.assertEqual(get_default_aliases(), ('Tap Timer', 'BX2'))
        finally:
            self._restore_alias_env(old_aliases)

    def test_env_adds_exact_alias(self):
        old_aliases = self._clear_alias_env()
        os.environ['HOLMAN_ACCEPTED_ALIASES'] = 'BX3'
        try:
            self.assertEqual(get_default_aliases(), ('Tap Timer', 'BX2', 'BX3'))
        finally:
            os.environ.pop('HOLMAN_ACCEPTED_ALIASES', None)
            self._restore_alias_env(old_aliases)

    def test_unknown_names_fail_closed(self):
        old_aliases = self._clear_alias_env()
        try:
            accepted = get_default_aliases()
            self.assertTrue(alias_accepted('Tap Timer', accepted))
            self.assertTrue(alias_accepted('BX2', accepted))
            for name in ('', 'Tap', 'BX', 'Holman BX2', 'BTX2', 'BX21', 'Tap Timer '):
                self.assertFalse(alias_accepted(name, accepted))
            self.assertNotIn('Tap', accepted)
            self.assertNotIn('BX', accepted)
            self.assertNotIn('', accepted)
        finally:
            self._restore_alias_env(old_aliases)


class TestServiceUuids(unittest.TestCase):
    def _clear_uuid_env(self):
        return os.environ.pop('HOLMAN_SERVICE_UUIDS', None)

    def _restore_uuid_env(self, value):
        if value is not None:
            os.environ['HOLMAN_SERVICE_UUIDS'] = value

    def test_default_includes_co3011(self):
        old = self._clear_uuid_env()
        try:
            uuids = get_default_service_uuids()
            self.assertEqual(uuids, DEFAULT_SERVICE_UUIDS)
            self.assertIn(HOLMAN_CO3011_SERVICE_UUID, uuids)
            self.assertIn(HOLMAN_CO3015_SERVICE_UUID, uuids)
            self.assertIn(HOLMAN_CO3012_SERVICE_UUID, uuids)
        finally:
            self._restore_uuid_env(old)

    def test_env_replaces_list(self):
        old = self._clear_uuid_env()
        os.environ['HOLMAN_SERVICE_UUIDS'] = (
            UNKNOWN_SERVICE_UUID + ', ' + HOLMAN_CO3011_SERVICE_UUID)
        try:
            uuids = get_default_service_uuids()
            self.assertEqual(
                uuids, (UNKNOWN_SERVICE_UUID, HOLMAN_CO3011_SERVICE_UUID))
            self.assertNotIn(HOLMAN_CO3015_SERVICE_UUID, uuids)
            self.assertNotIn(HOLMAN_CO3012_SERVICE_UUID, uuids)
        finally:
            os.environ.pop('HOLMAN_SERVICE_UUIDS', None)
            self._restore_uuid_env(old)

    def test_unknown_uuid_not_in_default_unless_env_set(self):
        old = self._clear_uuid_env()
        try:
            self.assertNotIn(UNKNOWN_SERVICE_UUID, get_default_service_uuids())
            os.environ['HOLMAN_SERVICE_UUIDS'] = UNKNOWN_SERVICE_UUID
            self.assertEqual(get_default_service_uuids(), (UNKNOWN_SERVICE_UUID,))
            self.assertNotIn(HOLMAN_CO3011_SERVICE_UUID, get_default_service_uuids())
        finally:
            os.environ.pop('HOLMAN_SERVICE_UUIDS', None)
            self._restore_uuid_env(old)


if __name__ == '__main__':
    unittest.main()
