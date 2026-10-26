# F.10 vendor-only extraction source plan

This candidate is ready for source review before a single real extraction. It
does not execute automatically. No actual vendor payload has been extracted or
decoded. The source ZIP path and unique output are supplied by a private plan;
the public source does not contain the source archive's random basename.

The default `extract-vendor.py --plan <private-plan>` authenticates the existing
ZIP central directory,340-byte metadata,8084-byte transfer and tool/source pins.
It checks the complete destination coverage but does not open the vendor data
member or create OUT. Only adding `--execute` can create that exclusive directory.
Existing OUT always refuses execution; failures retain partial artifacts and
logs. The private plan is not a deployment request or device identity.

The prepared private plan is
`E:/edk2-samurai-out/charging-oem-audit-20261023/gauge-2719-vendor-extract-plan-01/plan-private.json`.
Its SHA is recorded in plan-summary.json. It was created separately from the
still-absent extraction OUT. A real default check in original child181092
returned0, proving the actual F.10 transfer's complete0..417792 coverage without
opening vendor data or running Node. Only after source review would the same
public script with this plan and `--execute` perform the one extraction.

The fixed sequence is:

1. Read only `vendor.new.dat.br` from the existing ZIP into a new `xb` file,
   streaming at most1MiB per read. Require STORED/699830594 bytes/CRC43496d61,
   consume EOF and validate both ZipExtFile CRC and independent CRC32; record SHA.
2. Run the pinned Windows Node24.22.1 builtin Brotli pipeline into a new `wx`
   file. Input hashing/counting and decoder `bytesWritten` must both cover the
   exact compressed stream. Output is capped at and must equal1613049856 bytes,
   with SHA. Errors, including truncated/overflow/trailing input, make the same
   Node child return nonzero. Input and output streams are closed by pipeline;
   successful output is flushed to disk. The original Popen is always waited;
   stdin is DEVNULL and logs are ordinary private files. No timeout/kill/replay.
3. Parse only version4/new/zero/erase with zero stash fields. Validate every
   destination range first, requiring no overlaps or gaps and complete coverage
   of0..417792. Header401193 equals new393811+zero7382, not image extent.
   A new `xb` raw file is truncated to1711276032 bytes; only new commands copy
   sequential data. zero/erase leave zeros in this new host file. No device
   erase, partition command, mount or sparse-image conversion occurs. All
   new.dat bytes are consumed exactly once in order, its SHA is rechecked during
   that consumption and EOF is required. The resulting host image gets a SHA.

Source ZIP opens are readonly. Pre/post file stat plus the same small-member
hashes are checked; the entire3.67GB ZIP is not reread for a global hash or
claimed signature/integrity proof. Tool/source/private-plan hashes are rechecked.
All extracted originals and raw logs remain in private OUT. The extractor calls
neither debugfs nor any indexer; any later filesystem listing is a separate
root-owned operation.

`tools-and-engine.json` records the actual existing Node/Brotli versions and
local builtin decoder accounting. In the tiny trailing fixture,54 upstream
bytes versus46 decoder-consumed bytes correctly fail. Ubuntu debugfs1.47.2 is
available for a later readonly filesystem read, but is not part of this script.
No dependencies were installed. new.dat reconstructs a raw image, so simg2img
is not needed.

The small fixture runner uses only generated ZIP/Brotli/data files. It executes
the real extraction/converter functions and Node source for valid/CRC damage,
exclusive output, short/extra new stream, digest failure, complete range
coverage, overlap/gap/out-of-bounds/unsupported transfer, and Brotli
valid/truncated/overflow/trailing cases. The first private fixture run passed;
its gap input was then tightened from an empty range to a true gap, and the
small suite was rerun in another exclusive private fixture directory. Both raw
receipt sets remain private. No old codec/index/protection matrix was rerun.

F.10 metadata lacks an exact build fingerprint and says generic pre-device
`device`; its version_name F.10 and ota_id C.10 are preserved as observed. This
plan cannot establish the precise2719 pack model, new MAC semantics or query
permission. It changes no current501 phone state, prepared502 transaction,
Image, rootfs, firmware, SDK, storage volume, Git or frozen source leaf.
