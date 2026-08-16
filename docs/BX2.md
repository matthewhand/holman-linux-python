# Holman BX2 notes

Protocol notes for a Holman **BX2** (dual outlet, advertised name `BX2`) with this SDK. No device addresses or credentials belong in this tree.

`AE 8E` is a shared session unlock also used by public BX1 ESPHome configs, not a per-device secret.

## Identity

- Advertised alias is exactly `BX2` (bluetoothctl Name/Alias and Bleak `local_name`). Not `Holman BX2` or `BTX2`. Discovery matches exact names `Tap Timer` (BX1) and `BX2`.
- This BX2 advertises vendor service `c521f000-0d70-4d4f-8e43-40d84c50ab38` (already labelled BTX1 / CO3011). Discovery can pass `service_uuids=TapTimer.SERVICE_UUIDS` again because that list includes the on-air UUID. Another BTX2 UUID (`aacaebbb-...`) stays in the list for other units.
- Manufacturer company id `0x0374`. BLE address type is **random**.

## GATT (safe)

| UUID | Role |
| --- | --- |
| `c521f000-...` | Vendor service |
| `0000c001-...` | Write. Session unlock `AE 8E`. |
| `0000f006-...` | Write. Manual start/stop. |
| `0000f004-...` | Read. 12-byte state. Last byte `01` means running **when the official app started the valve**. |

`start()` / `stop()` send the unlock when `c001` is present.

## Manual payload

4 bytes on `f006`:

    [0x01, tap, 0x00, minutes]

| Tap | Name | Start write | Hex |
| --- | --- | --- | --- |
| 0 | Sprinkler | `[0x01, 0x00, 0x00, minutes]` | `010000NN` |
| 1 | Hose | `[0x01, 0x01, 0x00, minutes]` | `010100NN` |
| — | Stop | `[0x00, 0x00, 0x00, 0x00]` | `00000000` |

- Byte 0 is on/off (`0x01` start, `0x00` stop).
- Byte 1 is the outlet: tap `0x00` = Sprinkler, tap `0x01` = Hose.
- `minutes` is `1...255`.
- Stop is all-off (both outlets).
- Sprinkler matches the original single-outlet SDK ON payload `01 00 00 <mins>`. BX1 stays compatible if callers leave the default tap 0.

A 10-byte ESPHome-style pad (`01 00 00 mins` + six zeros) is accepted if written **without** response. A 10-byte write **with** response returned ATT `0x0e` and dropped the link. Prefer the 4-byte form.

If a 4-byte write **with** response fails (ATT `0x0e`), retry **without** response. That is common while a run is already active.

## Dual outlet behaviour

- The timer can run **one outlet at a time**. Starting Hose while Sprinkler is open is not a second concurrent valve.
- To switch outlets: write stop (`00 00 00 00`), then start the other tap. A start-while-running write with response often errors; stop first.
- There is no extra reset characteristic required after a manual run. Stop is the all-zero `f006` write.

## What not to do

- **Do not read `0000e002-...`.** That drops the connection.
- Reading `f004` without a prior `c001` unlock can also return ATT `0x0e` and drop the link.
- First LE connect often fails with `le-connection-abort-by-local` / "failed to discover services, device disconnected". Retry. Two clients racing the same adapter makes this worse.
- `f004` last byte is **not a reliable water-is-flowing flag** after an SDK write. The official app sets it to `01`. A 4-byte start can open the valve while last byte stays `00`. Treat a successful write as optimistic; confirm physically if it matters.
- A successful GATT write can still look dry if that outlet is blocked. Confirm water, not only BLE ACKs.

## Other characteristics

Seen on the same service, not required for manual run:

- `f003` — identity blob (MAC bytes reversed), readable without unlock.
- `f005`, `e001`, `c002` — read/write. Unlock may be required. Not needed for start/stop.
- `46a60001-ca26-425a-9bc6-d917829d2906` — write + notify. Untouched.

## App pairing vs session unlock

BlueZ `Paired`/`Bonded` can stay **no**. The Holman app still talks to the timer. Multiple phones can start a **manual** run at the same time. `AE 8E` is a session unlock, not exclusive SMP pairing.

The printed manual's "one smartphone" line is about **scheduling ownership**, not a hard lock on manual GATT writes. The physical dial can still disable onboard schedules; that does not block these manual `f006` writes.

## Suggested PR surface

1. Accept exact aliases `Tap Timer` and `BX2` (optional `HOLMAN_ACCEPTED_ALIASES` adds more exact names).
2. Discover with `service_uuids=TapTimer.SERVICE_UUIDS` (includes the on-air BX2 UUID).
3. Unlock `c001` with `AE 8E` when the characteristic exists.
4. `start(runtime, zone=1)` writes `[0x01, tap, 0, mins]` (tap `0x00` Sprinkler / `0x01` Hose); `stop()` writes zeros.
5. CLI `--start` / `--stop` / `--minutes` / `--zone`.
6. README mention of BTX2 / BX2 and a link here.

Leave Home Assistant bindings, retries, and site addresses out of the SDK.

## CLI

```
holmanctl --discover
holmanctl --start AA:BB:CC:DD:EE:FF --minutes 2 --zone 1
holmanctl --stop  AA:BB:CC:DD:EE:FF
```
