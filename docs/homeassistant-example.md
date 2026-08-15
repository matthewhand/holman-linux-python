# Home Assistant / Lovelace example (generic)

Sprinkler = tap 0. Hose = tap 1. One outlet at a time. No site IPs or MACs.

f006 start bytes used by this SDK:

| Tap | Name | Start | Hex |
| --- | --- | --- | --- |
| 0 | Sprinkler | `[0x01, 0x00, 0x00, minutes]` | `010000NN` |
| 1 | Hose | `[0x01, 0x01, 0x00, minutes]` | `010100NN` |
| — | Stop | `[0x00, 0x00, 0x00, 0x00]` | `00000000` |

## Package snippet

```yaml
holman_bt:
  - mac: AA:BB:CC:DD:EE:FF
    name: Holman BX2
    default_runtime: 5
```

## Lovelace cards

Entities are named from the device name plus the tap
(`switch.holman_bx2_sprinkler`, `switch.holman_bx2_hose`).

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Holman BX2
    entities:
      - entity: number.holman_bx2_runtime
        name: Minutes
      - entity: switch.holman_bx2_sprinkler
        name: Sprinkler
        icon: mdi:sprinkler
      - entity: switch.holman_bx2_hose
        name: Hose
        icon: mdi:hose
  - type: horizontal-stack
    cards:
      - type: button
        name: Start Sprinkler
        icon: mdi:sprinkler
        tap_action:
          action: call-service
          service: holman_bt.start
          data:
            zone: 1
            minutes: 5
      - type: button
        name: Start Hose
        icon: mdi:hose
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
