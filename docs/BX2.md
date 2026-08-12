# Holman BX2 notes

Field notes from bringing a Holman **BX2** (dual outlet, advertised name `BX2`) up with this SDK. Useful before a PR or another integration.

## Identity

- Advertised alias starts with `BX`, not `Tap Timer`. Discovery must accept that prefix.
- The unit we tested advertised vendor service `c521f000-0d70-4d4f-8e43-40d84c50ab38` (this repo already labelled that UUID as BTX1 / CO3011). Another BTX2 UUID (`aacaebbb-…`) is listed here but was **not** seen on that BX2.
- Manufacturer company id `0x0374`. BLE address type is **random**.

## GATT (safe)

| UUID | Role |
| --- | --- |
| `c521f000-…` | Vendor service |
| `0000c001-…` | Write. Session unlock `AE 8E` (same 2-byte passcode used by BX1 ESPHome adapters). |
| `0000f006-…` | Write. Manual start/stop. |
| `0000f004-…` | Read. 12-byte state. Last byte `01` means running **when the official app started the valve**. |

`start()` / `stop()` now send the unlock when `c001` is present.

## Manual payload

4 bytes on `f006`:

```
[zone, 0x00, 0x00, minutes]
```

- `zone` is `1` or `2` (outlet).
- `minutes` is `1…255`.
- Stop is `00 00 00 00`.

This matches the original single-outlet SDK when `zone=1` (`01 00 00 <mins>`).

A 10-byte ESPHome-style pad (`01 00 00 mins` + six zeros) is accepted if written **without** response. A 10-byte write **with** response returned ATT `0x0e` and dropped the link.

## What not to do

- **Do not read `0000e002-…`.** That drops the connection.
- While a run is active, a 4-byte `f006` write **with response** often returns ATT `0x0e`. Stop first, or use write-without-response, then start the other zone.
- First LE connect often fails with `le-connection-abort-by-local` / “failed to discover services, device disconnected”. Retry. Two clients (e.g. Home Assistant Bluetooth + `bluetoothctl`) racing the same adapter makes this worse.
- `f004` last byte is **not a reliable “water is flowing” flag** after an SDK write. The official app sets it to `01`. Our 4-byte start can open the valve while last byte stays `00`. Treat a successful write as optimistic; confirm physically if it matters.

## Other characteristics

Seen on the same service, not required for manual run:

- `f003` — identity blob (MAC bytes reversed), readable without unlock.
- `f005`, `e001`, `c002` — read/write. Unlock may be required. Not needed for start/stop.
- `46a60001-ca26-425a-9bc6-d917829d2906` — write + notify. Untouched.

Reading `f004` without a prior `c001` unlock can return ATT `0x0e` and drop the link.

## App pairing

BlueZ `Paired`/`Bonded` can stay **no**. The Holman app still talks to the timer. Multiple phones can start a manual run. `AE 8E` is a session unlock, not exclusive SMP pairing. The printed manual’s “one smartphone” line is about scheduling ownership, not a hard lock on manual GATT writes.

## CLI

```
holmanctl --discover
holmanctl --start AA:BB:CC:DD:EE:FF --minutes 2 --zone 1
holmanctl --stop  AA:BB:CC:DD:EE:FF
```

No device addresses, credentials, or site-specific outlet names belong in this tree.
