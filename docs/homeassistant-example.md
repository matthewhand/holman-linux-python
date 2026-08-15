# Home Assistant / Lovelace example (generic)

Zone 1 = Grass. Zone 2 = Hose. One outlet at a time. No site IPs or MACs.

f006 start bytes used by this SDK (and by a `holman_bt` custom component that
speaks the same GATT):

| Zone | Name | Start | Hex |
| --- | --- | --- | --- |
| 1 | Grass | `[0x01, 0x00, 0x00, minutes]` | `010000NN` |
| 2 | Hose | `[0x01, 0x01, 0x00, minutes]` | `010100NN` |
| — | Stop | `[0x00, 0x00, 0x00, 0x00]` | `00000000` |

Do not send `0x02` as Hose. `[0x02, 0x00, 0x00, mins]` and
`[0x01, 0x02, 0x00, mins]` both ACK and stay dry.

## Package snippet

```yaml
holman_bt:
  - mac: AA:BB:CC:DD:EE:FF
    name: Holman BX2
    default_runtime: 5
```

## Lovelace cards

Entities are named from the device name plus Grass / Hose
(`switch.holman_bx2_grass`, `switch.holman_bx2_hose`).

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Holman BX2
    entities:
      - entity: number.holman_bx2_runtime
        name: Minutes
      - entity: switch.holman_bx2_grass
        name: Grass
        icon: mdi:grass
      - entity: switch.holman_bx2_hose
        name: Hose
        icon: mdi:hose
  - type: horizontal-stack
    cards:
      - type: button
        name: Start Grass
        icon: mdi:grass
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
