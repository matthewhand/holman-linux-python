# Fork Review: holman-linux-python (skeptical)

## Executive Summary

This fork (matthewhand/holman-linux-python) adds BX2 MK1 dual-outlet support on top of upstream (scottmckenzie/holman-linux-python v0.1.0). The fork has three open PRs that progressively build on each other. House-specific tap names appear in shipped code, tests, docs, and commit messages. The README claims BTX2 support without testing. Upstream PR #9 is still open; the fork PRs are not the upstream story. Several house references must be scrubbed before upstreaming.

## Context Verification

### Upstream and Fork PRs

- **Upstream issue #8** ([link](https://github.com/scottmckenzie/holman-linux-python/issues/8)): Requests BX2 exact alias and two-outlet start. Confirms testing only on BX2 Dual Outlet MK1 SKU CO3112.
- **Upstream PR #9** ([link](https://github.com/scottmckenzie/holman-linux-python/pull/9)): Open PR targeting upstream master. Adds alias filter, zone parameter, unlock, and README note. Status: OPEN, not merged.
- **Fork PR #1** (pr1/bx2-hose-byte1): 8 commits. Implements BX2 basics plus house names in docs. The basis for upstream PR #9 but diverged.
- **Fork PR #2** (pr2/quality-guards-tdd): 14 commits. Adds tests, payload helpers, fail-closed guards, debug hex logging. Merges PR1.
- **Fork PR #3** (cursor/docs-bx2-notes-f6a3): Docs only.

**Fork PR #1 should NOT be the linked Implements for upstream PR #9.** The upstream PR is a separate artifact targeting scottmckenzie/holman-linux-python and is still open. Fork PR #1 has house names that upstream does not want.

### Device Identity

Confirmed: **BX2 Dual Outlet MK1 SKU CO3112**, not BTX2.

- Advertised name: exactly `BX2`
- Vendor service UUID: `c521f000-0d70-4d4f-8e43-40d84c50ab38` (CO3011, already in SDK as BTX1)
- NOT tested: newer BX2 (https://www.holmanindustries.com.au/product/bx2-dual-outlet-bluetooth-tap-timer/)
- NOT tested: BTX2 (advertises different UUID `aacaebbb-...` and name)

**README claims BTX2 support in line 4 without testing.** That link is to the commercial BTX2 product page. No BTX2 unit was tested. Only BX2 MK1 CO3112 is confirmed.

### Live HA Integration

User reports live Home Assistant uses **vendored holman_bt**, not a git checkout of this fork. The vendored version is deployed separately. This fork is the source but is not directly executed in production.

## Fork vs Upstream Drift

Fork master is **at the same commit as upstream master** (tag 0.1.0, commit 2b62c03). No drift. All BX2 work lives in feature branches:

- `bx2` (3 commits on top of master)
- `pr1/bx2-hose-byte1` (8 commits on top of master, includes bx2 plus more)
- `pr2/quality-guards-tdd` (14 commits on top of master, merges pr1 plus tests)

Upstream has not merged anything past 0.1.0 since Aug 2024 (hmoffatt BTX1 work). Upstream PR #9 is open but not merged. No upstream commits exist that the fork is missing.

## House Names in Code

House-specific tap names (`Sprinkler`, `Hose`) appear in **shipped code**:

### Production Code

**holman/payload.py**:
```
TAP_SPRINKLER = 0x00
TAP_HOSE = 0x01
ZONE_NAMES = {1: 'Sprinkler', 2: 'Hose'}
```

**holman/holman.py** (line 294-295):
```
Byte 1 is the outlet: tap 0x00 is Sprinkler, tap 0x01 is
Hose (hex ``010100NN``). Sprinkler matches the original SDK ON
```

**holmanctl.py** (line 104):
```
arg_parser.add_argument('--zone', type=int, default=1, help="1 Sprinkler (tap 0) or 2 Hose (tap 1). Default 1")
```

### Tests

**tests/test_payload.py**:
```
def test_start_sprinkler(self):
def test_start_hose(self):
def test_hose_payload_bytes(self):
self.assertEqual(tap_name(1), 'Sprinkler')
self.assertEqual(tap_name(2), 'Hose')
```

Test function names and assertions reference house taps.

### Documentation

**README.md** (line 157, 172):
```
zone=1` (Sprinkler, tap 0, `[0x01, 0x00, 0x00, mins]`) or `zone=2` (Hose, tap 1
Sprinkler / Hose; no site addresses
`--debug` logs the f006 write as hex (`01010005` for Hose, 5 minutes)
```

**docs/BX2.md** (6 references):
```
| 0 | Sprinkler | `[0x01, 0x00, 0x00, minutes]` | `010000NN` |
| 1 | Hose | `[0x01, 0x01, 0x00, minutes]` | `010100NN` |
tap `0x00` = Sprinkler, tap `0x01` = Hose
Starting Hose while Sprinkler is open is not a second concurrent valve
tap `0x00` Sprinkler / `0x01` Hose
```

**docs/homeassistant-example.md** (9 references):
```
Sprinkler = tap 0. Hose = tap 1
switch.holman_bx2_sprinkler
switch.holman_bx2_hose
name: Sprinkler / name: Hose (entities and buttons)
```

### Commit Messages

Two commits explicitly name house taps:

- `42d9d0a` "Name BX2 taps Sprinkler and Hose in docs and comments."
- `7f79124` "Name BX2 taps Sprinkler and Hose in payload helpers and docs."

Commit `7a7ad02` "Use generic zone 1 / zone 2 language" was an earlier attempt to remove house names, but `42d9d0a` reverted that decision and put them back.

## One-Commit vs 13-Commit History

Fork PR #2 has **14 commits** (not 13). PR #1 has **8 commits**. Both are multi-commit histories:

- `bx2` branch: 3 commits (the original exploratory work)
- `pr1/bx2-hose-byte1`: 8 commits (includes bx2, adds alias/UUID overrides, flips zone vs house naming back and forth)
- `pr2/quality-guards-tdd`: 14 commits (merges pr1, adds tests and guards)

**Upstream PR #9 is a squashed single-commit story.** It references issue #8 and proposes a clean implementation. The fork PRs are the **13-commit working tree** that led to that squashed story. The fork PRs are not the upstream PR.

If upstream merges PR #9, it will be a single commit or a few clean commits. The fork PRs are exploratory history and are not intended to be merged as-is.

## What is Actually Upstreamable

Upstreamable (after scrubbing):

1. **Exact alias allowlist** (`Tap Timer`, `BX2`). No prefix match. Empty alias rejected.
2. **Two-outlet start**: `zone` parameter (1 or 2), maps to tap byte `0x00` or `0x01`.
3. **Unlock `c001`** with `AE 8E` when present.
4. **CLI `--zone` flag**.
5. **Overrides**: `HOLMAN_ACCEPTED_ALIASES` (adds exact names), `HOLMAN_SERVICE_UUIDS` (replaces list).
6. **README** mention of BX2 MK1 SKU CO3112 support, link to docs.
7. **docs/BX2.md** protocol notes (GATT, unlock, payloads, what not to do).

Changes required for upstream:

1. **Remove house names from code**: Replace `TAP_SPRINKLER` / `TAP_HOSE` with `TAP_ZONE_1` / `TAP_ZONE_2`, or just inline `0x00` / `0x01`.
2. **Remove house names from `ZONE_NAMES`**: Use generic `{1: 'zone 1', 2: 'zone 2'}` or remove the dict entirely.
3. **Scrub docs**: Replace "Sprinkler" and "Hose" with "zone 1" and "zone 2" or "tap 0" and "tap 1".
4. **Scrub tests**: Rename `test_start_sprinkler` -> `test_start_zone_1`, etc.
5. **Scrub README**: Remove house names from examples.
6. **Fix BTX2 claim**: Change line 4 to reference BX2 MK1 only, or remove BTX2 until tested.
7. **Squash commits**: Upstream wants a clean story, not 8-14 commits with back-and-forth naming debates.

The **docs/homeassistant-example.md** file should stay in the fork (it is a generic example, but still references house names). Upstream probably does not want HA-specific docs.

## What Must Stay Private

Must stay private:

1. **House tap names** (`Sprinkler`, `Hose`) in any form. Upstream wants generic zone language.
2. **Commit history** showing the back-and-forth on house names (commits `7a7ad02`, `42d9d0a`, `7f79124`).
3. **HA example** with entity names like `switch.holman_bx2_sprinkler`. That is a site-specific deployment pattern.
4. **Site addresses, MACs, IPs**. (Already clean.)

The fork can keep these in its own branches. Upstream PR #9 is a separate artifact and is already clean of house names (based on the PR description, it uses "zone 1" and "zone 2" language).

## Device Claims vs Code

### Claimed Devices (README line 2-4)

- CO3015 (tested upstream)
- BTX1 (tested upstream, PR #2 by hmoffatt)
- **BTX2** (NOT TESTED, link to commercial page)

### Tested Devices

- BX2 Dual Outlet MK1 SKU CO3112 (this fork, confirmed)

**Discrepancy**: README line 4 links to BTX2 product page and claims support. No BTX2 unit was tested. The tested device is BX2 MK1 (older model, now superseded). Issue #8 explicitly says "I have not tested the newer model."

The README also does not mention the older BX2 MK1 SKU. It jumps straight to BTX2. This is misleading.

### Recommended Fix

Replace README line 4:

```
and [BTX2](https://www.holmanindustries.com.au/products/btx2-dual-outlet-bluetooth-tap-timer/) are Bluetooth tap timers
```

With:

```
and [BX2 MK1](https://www.holmanindustries.com.au/product/bx2-dual-outlet-bluetooth-tap-timer-mk1/) (SKU CO3112) are Bluetooth tap timers
```

Or add a note:

```
Tested on BX2 Dual Outlet MK1 (SKU CO3112). Newer BX2 and BTX2 models are not tested.
```

## Summary Table

| Item | Fork | Upstream | Upstreamable | Notes |
|------|------|----------|--------------|-------|
| Exact alias filter | Yes | No (PR #9 open) | Yes | Must scrub house names |
| Two-outlet start | Yes | No (PR #9 open) | Yes | `zone` param, byte 1 |
| Unlock `c001` | Yes | No (PR #9 open) | Yes | `AE 8E` session unlock |
| Overrides (aliases, UUIDs) | Yes | No (PR #9 open) | Yes | Env and constructor |
| CLI `--zone` | Yes | No (PR #9 open) | Yes | Works |
| Payload helpers (`payload.py`) | Yes | No | **Partial** | Remove house names first |
| Fail-closed guards | Yes | No | Yes | Good safety |
| Tests | Yes | No | **Partial** | Rename test functions |
| Debug hex logging | Yes | No | Yes | `--debug` flag |
| docs/BX2.md | Yes | No | **Partial** | Scrub house names |
| docs/homeassistant-example.md | Yes | No | **No** | Site-specific, house names |
| House names in code | **Yes** | No | **No** | Must remove |
| House names in tests | **Yes** | No | **No** | Must remove |
| House names in docs | **Yes** | No | **No** | Must remove |
| BTX2 claim in README | **Yes** | No | **No** | Not tested |
| BX2 MK1 mention in README | No | No | Yes | Tested device |

## Recommendations

1. **Do not merge fork PRs to upstream as-is.** They contain house names and exploratory history.
2. **Upstream PR #9 is the clean submission.** Let that stand or squash it further.
3. **Scrub house names from fork PRs** if you want to point upstream to them as a reference.
4. **Fix README BTX2 claim** to BX2 MK1 SKU CO3112.
5. **Keep docs/homeassistant-example.md in fork only.** It is a useful reference for the house deployment but is not generic enough for upstream.
6. **Keep payload helpers, tests, and guards in fork** until upstream wants them. They are good but need house name removal first.
7. **Update commit messages** if you rebase: remove house tap names.

## Conclusion

This fork does good work: BX2 MK1 support is solid, tests are thorough, guards are sensible. But house-specific names are baked into production code, tests, docs, and commit history. Upstream wants generic language. The fork is a working prototype; upstream PR #9 is the clean submission. Keep them separate. Do not claim BTX2 support without testing.
