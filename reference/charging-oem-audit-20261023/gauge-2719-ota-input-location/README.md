# Existing F.10 OTA input located

A useful new input exists: `E:/c09efbe9-4161-4f8e-b94b-01d3861d335f_3.zip`,
3666753073 bytes. Its PK ZIP central directory is directly readable and contains
72 members, including `vendor.new.dat.br` (699830594 bytes, ZIP_STORED),
`vendor.transfer.list` (8084 bytes), and an empty vendor patch member. There is
no member with `odm` in its name. This is the OTA container membership, not a
vendor filesystem path index or a guarantee that every payload passes CRC.

Only the archive header, existing central directory,340-byte metadata,
8084-byte transfer list and64-byte vendor data header were read. The metadata
matches the existing decrypted metadata bytes exactly
(SHA256 `3e005ffe…953c0`): Android11, F.10, OTA id
`RMX1931_11.C.10_11001510_202104251602`. Its pre-device is the generic `device`;
there is no build/fingerprint field to project into an exact pack identity.
The64-byte vendor header is readable and ZIP encryption flag is not set, but no
Brotli decode or complete vendor CRC verification has run. No payload was
extracted and no index was generated. Original external download/signature provenance and
the complete3.67GB file hash have not been established in this narrow step.

The existing `E:/RMX1931_11_OTA_1340_all_2QCxQYdkxpql.ozip` is a different
3.345GB OPPOENCRYPT container. Its saved top-level index/report and320-byte
metadata identify Android10/C.34; the old extraction report includes encrypted
or decompression failures. Its vendor member is a different size. The two OTAs
must not be conflated because their directories share RMX1931 names.

The actual vendor transfer list exactly matches the existing decrypted copy,
SHA256 `fedaa479…82830f`. Its header is4/401193/0/0. The394 commands comprise
1erase,385new and8zero commands. Standard4096-byte range accounting requires
393811 new blocks (1613049856 bytes). The header401193 is new+zero block count,
not the partition extent: maximum target ends are417792(new),417791(zero) and
413972(erase), so the image must cover at least1711276032 bytes. The initial
partition label was corrected before this leaf was frozen; no image was created
or truncated. These are decoded input size expectations, not evidence the stream
has already been decoded or applied.

Root has confirmed the existing F.10 ZIP as the next vendor-only input; execution
remains separate. Python `zipfile.ZipFile(...).infolist()`
is enough to list its existing central directory without extracting payloads.
Session's separate decoder/tool check can evaluate a vendor-only read/decode;
this leaf neither performs that operation nor supplies a decoder.

Bounded root-level listings of the two RMX extraction directories, the named
backup directory and the kernel85-named original device-artifact directory did
not show standalone vendor/odm images there. The six nominated historical
producer sources point to selected GPU/Wi-Fi/MPSS/MCFG archives, fixed OEM kernel
sources and live DT snapshots. Those selected archives do not become full
vendor backups. Exact locations, sizes, small-source hashes and limitations are
in result.json.

The old six-index search was not repeated; its README was read only to preserve
its stated scope. No new OTA search for battery/gauge/bq files or the2719
fingerprint has run. Nothing here maps2719 to a precise chip or pack, establishes
new-MAC semantics, or permits a new real-device query. There was no full-drive
scan, payload extraction, download, firmware build, phone/USB/SSH/SDK/storage/Git
action, or change to any frozen leaf. This input-location step ends here.
