# 0x2719: existing firmware fingerprint and exact identity boundary

The new result changes the next step: **do not repeat0002 on the phone**, and do
not query0050/0052/0056 to infer an unknown firmware's identity. Two existing full
FirmwareVersion frames are identical and suffice for a precise source request.
No exact catalog part, firmware word byte order or new status-bit compatibility
was established. No production patch or query permission is warranted.

`identity-fingerprint.py` adds only saved-text0002 parsing, absent from the existing
live six-command/protection-evidence parser. It accepts one complete historical
record, checks exact route/echo/11-byte payload/length15/checksum and contradictory
printed fields, and preserves a frame/payload fingerprint. There is no I2C,
network, control or deployment interface. Default execution prints source-only.

## Actual identity evidence

`result.json` pins the old raw files and exact source bytes. The paired historical
0001 capture is bound to its existing kernel80 audit; the kernel85 FirmwareVersion
file is also bound by its old `capture-manifest.json`. No old suite was rerun.

| Saved evidence | Confirmed result |
| --- | --- |
| kernel80 paired0001 | Full36-byte frame, echo0001, length6, payload`19 27`, DeviceTypeLE=`0x2719`; legacy`0xffa5` |
| kernel80 + kernel85 FirmwareVersion | Identical complete frame, echo0002, payload11, length15, checksum`29` |
| Exact firmware payload | `27 19 00 04 00 06 00 03 85 02 00` |

The0001 payload and the first two0002 payload bytes have opposite order. Applying
the ordinary `sm_le16` to the latter would produce`0x1927`; it would not identify
this pack. The parser therefore retains the firmware fields as raw byte slices,
without turning them into a catalog model or a numeric version.

The cached official [SLUUA65E](https://www.ti.com/lit/pdf/sluua65), §12.2.2,
printed page76, text3286–3298, gives the ordered token
`ddDDvvVVbbBBTTzzZZRREE`. It describes device, version, build, firmware type,
Impedance Track version and two reserved fields. Its firmware-type prose says
`ttTT` although the token allocates one byte. This does not resolve this custom
payload's semantic word order. The reported slices are consequently
`2719/0004/0006/00/0385/02/00`, explicitly unconfirmed. They are useful search and
descriptor-matching bytes, rather than guessed version/build meanings.

## What the fixed OEM sources establish

Repository `realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source`, fixed
commit`23172a1571bd91156032cc9fef16284a82b63d2c`:

- `drivers/power/oppo/gauge_ic/oplus_bq27541.c`, SHA`0c4640c8…b7a87`,
  `bq27541_hw_config`1545–1596 reads the legacy16-bit DeviceType and firmware word
  through register00. Lines1590–1592 recognize FFA5 only for the0C current mapping.
  This is not a decoder for the extended11-byte firmware identity.
- `arch/arm64/boot/dts/19781/sm8150-pmic-overlay.dtsi`, SHA`f2f12882…6f91e7`,
  lines422–429 select the family-compatible node and`qcom,batt_bq28z610`, with no
  extended model/firmware schema. The SHA1 key index is not a catalog model.
- The inspected gauge source has no`request_firmware` or`MODULE_FIRMWARE` loader.
  The fixed Makefile selects`oplus_bq27541.o`. No authenticated pack firmware blob
  or matching BQZ descriptor was found in these named inputs. This is not a claim
  that the entire vendor partition or repository contains none. A new fixed
  GitHub directory API lookup returned403 rate-limit; its failure is retained,
  and it was not treated as a successful directory inventory.

## New official compatibility constraint

The official [BQ28Z610-DEVICE-FW release
information](https://www.ti.com/tool/BQ28Z610-DEVICE-FW) says the R1B release
supports the R1/BQ78Z100 hardware path and excludes original BQ28Z610 hardware.
Thus the family name is insufficient to choose firmware or a descriptor. The
current2719 hardware class remains unknown; this source does **not** prove that
R1B is compatible or incompatible with this exact pack. It blocks treating that
download as a way to establish compatibility.

Only the official HTML page was cached privately (SHA`3f3cf15d…972fc`); no firmware
archive, installer or firmware write path was downloaded or executed.

## New MAC and TCA decision

The prior standard-family definitions remain unchanged:0050 SafetyAlert,
0052 PFAlert and0056 GaugingStatus each have4-byte payload/length8 in SLUUA65E;
0056 includes its reserved fourth byte. Those standard layouts and TCA's
SafetyAlert-or-TC relationship remain hypotheses for this exact firmware.
Neither the old six frames nor the0002 fingerprint establish the new command
formats or TCA cause on2719. No Health/Full/timer/mask/whitelist change was made.

The next useful source input is a TI/OEM command/bit description or device
configuration that explicitly matches **DeviceType2719 and the entire11-byte
fingerprint**. A family label, chemistry`LION`, zero SafetyStatus/PFStatus or a
passing checksum is insufficient. Pending that match, the existing once-observer
candidate remains unqueried and the conservative TCA stop policy remains.

## Local validation

`test-result.json`: two actual cached frames plus11 malformed saved-text cases;
all13 pass. It rejects duplicate/truncated-prefix records, command/route/echo,
short frames, size/checksum/validation errors and contradictory duplicate fields.
The old codec/149/observer suites were not run. `audit.py` only reads named caches
and creates this evidence result; it never queries a device or downloads data.
`local-checks.json` retains the real local default child and its waited return0.

All original source/frames remain private or in their existing frozen leaves.
No phone/USB/SSH/SDK/build/Git action or production-file modification occurred.
