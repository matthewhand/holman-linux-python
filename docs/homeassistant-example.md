# Home Assistant / Lovelace example (generic)

Zone 1 = tap 0. Zone 2 = tap 1. One outlet at a time. No site IPs or MACs.

f006 start bytes used by this SDK:

| Zone | Tap | Start | Hex |
| --- | --- | --- | --- |
| 1 | 0 | `[0x01, 0x00, 0x00, minutes]` | `010000NN` |
| 2 | 1 | `[0x01, 0x01, 0x00, minutes]` | `010100NN` |
| — | — | Stop `[0x00, 0x00, 0x00, 0x00]` | `00000000` |

## Package snippet

```yaml
holman_bt:
  - mac: AA:BB:CC:DD:EE:FF
    name: Holman BX2
    default_runtime: 5
```

## Lovelace cards

Entities are named from the device name plus zone
(`switch.holman_bx2_zone_1`, `switch.holman_bx2_zone_2`).

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Holman BX2
    entities:
      - entity: number.holman_bx2_runtime
        name: Minutes
      - entity: switch.holman_bx2_zone_1
        name: Zone 1
        icon: mdi:sprinkler
      - entity: switch.holman_bx2_zone_2
        name: Zone 2
        icon: mdi:sprinkler
  - type: horizontal-stack
    cards:
      - type: button
        name: Start Zone 1
        icon: mdi:sprinkler
        tap_action:
          action: call-service
          service: holman_bt.start
          data:
            zone: 1
            minutes: 5
      - type: button
        name: Start Zone 2
        icon: mdi:sprinkler
        tap_action:
          action: call-service
          service: holman_bt.start
          data:
            zone: 2
            minutes: 5
      - type: button
        name: Stop
        icon: mdi:water-off
        tap_action:
          action: call-service
          service: holman_bt.stop
```
