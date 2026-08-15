'''
f006 manual payloads. No BLE imports.

Byte 0 is on/off. Byte 1 is the outlet. Grass is the original SDK
start [0x01, 0x00, 0x00, minutes]. Hose is [0x01, 0x01, 0x00, minutes]
(hex 010100NN). 0x02 is not Hose: both [0x02, 0x00, 0x00, mins] and
[0x01, 0x02, 0x00, mins] ACK and stay dry.
'''

CMD_ON = 0x01
CMD_OFF = 0x00
PAD_BYTE = 0x00
TAP_GRASS = 0x00
TAP_HOSE = 0x01
TAP_BY_ZONE = {1: TAP_GRASS, 2: TAP_HOSE}
ZONE_NAMES = {1: 'Grass', 2: 'Hose'}
ZONES = (1, 2)
DEFAULT_ZONE = 1
RUNTIME_MIN = 1
RUNTIME_MAX = 255


def clamp_runtime(minutes):
    return max(RUNTIME_MIN, min(int(minutes), RUNTIME_MAX))


def tap_for_zone(zone):
    '''
    Map zone 1/2 to the f006 tap byte. Unknown zones fail closed.
    '''
    try:
        key = int(zone)
    except (TypeError, ValueError) as err:
        raise ValueError(
            'unknown Holman zone %r; expected %s' % (zone, ZONES)
        ) from err
    try:
        return TAP_BY_ZONE[key]
    except KeyError as err:
        raise ValueError(
            'unknown Holman zone %r; expected %s' % (zone, ZONES)
        ) from err


def tap_name(zone):
    try:
        return ZONE_NAMES[int(zone)]
    except (KeyError, TypeError, ValueError):
        return 'zone %s' % zone


def manual_payload(on, minutes=5, zone=DEFAULT_ZONE):
    '''
    4-byte f006 write: stop is all-zero; start is [CMD_ON, tap, PAD, mins].
    '''
    if not on:
        return bytes([CMD_OFF, CMD_OFF, CMD_OFF, CMD_OFF])
    tap = tap_for_zone(zone)
    mins = clamp_runtime(minutes)
    return bytes([CMD_ON, tap, PAD_BYTE, mins])
