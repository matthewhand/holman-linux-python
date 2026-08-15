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
get_default_alias_prefixes = aliases.get_default_alias_prefixes


class TestManualPayload(unittest.TestCase):
    def test_start_zone_1_grass(self):
        self.assertEqual(list(manual_payload(True, 3, 1)), [0x01, 0x00, 0x00, 3])

    def test_start_zone_2_hose(self):
        self.assertEqual(list(manual_payload(True, 1, 2)), [0x01, 0x01, 0x00, 1])

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

    def test_never_emits_0x02_as_hose(self):
        grass = list(manual_payload(True, 5, 1))
        hose = list(manual_payload(True, 5, 2))
        self.assertNotIn(0x02, grass)
        self.assertNotIn(0x02, hose)
        self.assertEqual(hose, [0x01, 0x01, 0x00, 5])

    def test_tap_helpers(self):
        self.assertEqual(tap_for_zone(1), 0x00)
        self.assertEqual(tap_for_zone(2), 0x01)
        self.assertEqual(tap_name(1), 'Grass')
        self.assertEqual(tap_name(2), 'Hose')


class TestAliasPrefixes(unittest.TestCase):
    def test_default_accepts_tap_and_bx(self):
        old = os.environ.pop('HOLMAN_ACCEPTED_ALIAS_PREFIXES', None)
        try:
            self.assertEqual(get_default_alias_prefixes(), ('Tap', 'BX'))
        finally:
            if old is not None:
                os.environ['HOLMAN_ACCEPTED_ALIAS_PREFIXES'] = old

    def test_env_override_for_future_bx3(self):
        old = os.environ.get('HOLMAN_ACCEPTED_ALIAS_PREFIXES')
        os.environ['HOLMAN_ACCEPTED_ALIAS_PREFIXES'] = 'Tap,BX,BX3'
        try:
            self.assertEqual(get_default_alias_prefixes(), ('Tap', 'BX', 'BX3'))
        finally:
            if old is None:
                os.environ.pop('HOLMAN_ACCEPTED_ALIAS_PREFIXES', None)
            else:
                os.environ['HOLMAN_ACCEPTED_ALIAS_PREFIXES'] = old


if __name__ == '__main__':
    unittest.main()
