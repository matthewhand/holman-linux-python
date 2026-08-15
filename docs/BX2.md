# Holman BX2 notes

Protocol notes for a Holman **BX2** (dual outlet, advertised name `BX2`) with this SDK. No device addresses, credentials, or site-specific outlet names belong in this tree.

`AE 8E` is a shared session unlock also used by public BX1 ESPHome configs, not a per-device secret.

## Identity

- Advertised alias starts with `BX`, not `Tap Timer`. Discovery must accept that prefix.
- A BX2 may advertise vendor service `c521f000-0d70-4d4f-8e43-40d84c50ab38` (this repo already labelled that UUID as BTX1 / CO3011). Another BTX2 UUID (`aacaebbb-…`) is listed here but is not required for discovery.
- Manufacturer company id `0x0374`. BLE address type is **random**.
- Scan advertisements often carry the name and company id only. Do **not** require the vendor service UUID in the advert packet; resolve GATT after connect. That is why `TapTimerManager.start_discovery()` no longer passes `service_uuids=`.

## GATT (safe)

| UUID | Role |
| --- | --- |
| `c521f000-…` | Vendor service |
| `0000c001-…` | Write. Session unlock `AE 8E`. |
| `0000f006-…` | Write. Manual start/stop. |
| `0000f004-…` | Read. 12-byte state. Last byte `01` means running **when the official app started the valve**. |

`start()` / `stop()` send the unlock when `c001` is present.

## Manual payload

4 bytes on `f006`:

    [0x01, tap, 0x00, minutes]

| Zone | Tap | Start write | Hex |
| --- | --- | --- | --- |
| 1 | 0 | `[0x01, 0x00, 0x00, minutes]` | `010000NN` |
| 2 | 1 | `[0x01, 0x01, 0x00, minutes]` | `010100NN` |
| — | — | Stop `[0x00, 0x00, 0x00, 0x00]` | `00000000` |

- Byte 0 is on/off (`0x01` start, `0x00` stop).
- Byte 1 is the outlet: tap `0x00` = zone 1, tap `0x01` = zone 2.
- `minutes` is `1…255`.
- Stop is all-off (both outlets).
- Zone 1 matches the original single-outlet SDK ON payload `01 00 00 <mins>`. BX1 stays compatible if callers leave `zone` at the default `1`.

A 10-byte ESPHome-style pad (`01 00 00 mins` + six zeros) is accepted if written **without** response. A 10-byte write **with** response returned ATT `0x0e` and dropped the link. Prefer the 4-byte form.

If a 4-byte write **with** response fails (ATT `0x0e`), retry **without** response. That is common while a run is already active.

## Dual outlet behaviour

- The tap can run **one outlet at a time**. Starting zone 2 while zone 1 is open is not a second concurrent valve.
- To switch outlets: write stop (`00 00 00 00`), then start the other zone. A start-while-running write with response often errors; stop first.
- There is no extra “reset” characteristic required after a manual run. Stop is the all-zero `f006` write.

## What not to do

- **Do not read `0000e002-…`.** That drops the connection.
- Reading `f004` without a prior `c001` unlock can also return ATT `0x0e` and drop the link.
- First LE connect often fails with `le-connection-abort-by-local` / “failed to discover services, device disconnected”. Retry. Two clients (Home Assistant Bluetooth + `bluetoothctl`, or two phones plus the SDK) racing the same adapter makes this worse.
- `f004` last byte is **not a reliable “water is flowing” flag** after an SDK write. The official app sets it to `01`. A 4-byte start can open the valve while last byte stays `00`. Treat a successful write as optimistic; confirm physically if it matters.
- A successful GATT write can still look dry if that outlet is blocked. Confirm water, not only BLE ACKs.

## Other characteristics

Seen on the same service, not required for manual run:

- `f003` — identity blob (MAC bytes reversed), readable without unlock.
- `f005`, `e001`, `c002` — read/write. Unlock may be required. Not needed for start/stop.
- `46a60001-ca26-425a-9bc6-d917829d2906` — write + notify. Untouched.

## App pairing vs session unlock

BlueZ `Paired`/`Bonded` can stay **no**. The Holman app still talks to the timer. Multiple phones can start a **manual** run at the same time. `AE 8E` is a session unlock, not exclusive SMP pairing.

The printed manual’s “one smartphone” line is about **scheduling ownership**, not a hard lock on manual GATT writes. The physical dial can still disable onboard schedules; that does not block these manual `f006` writes.

## Suggested PR surface

1. Accept `BX*` aliases (and optionally `HOLMAN_ACCEPTED_ALIAS_PREFIXES`).
2. Discover by alias, not advertised service UUID.
3. Unlock `c001` with `AE 8E` when the characteristic exists.
4. `start(runtime, zone=1)` writes `[0x01, tap, 0, mins]` (tap `0x00` zone 1 / `0x01` zone 2); `stop()` writes zeros.
5. CLI `--start` / `--stop` / `--minutes` / `--zone`.
6. README mention of BTX2 / BX2 and a link here.

Leave Home Assistant bindings, retries, outlet nicknames, and site addresses out of the SDK.

## CLI

```
holmanctl --discover
holmanctl --start AA:BB:CC:DD:EE:FF --minutes 2 --zone 1
holmanctl --stop  AA:BB:CC:DD:EE:FF
```
