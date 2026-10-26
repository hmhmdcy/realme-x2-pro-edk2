# Actual vendor-only extraction supplement

This is the later result of the single authorized extraction. The original
4639 source delivery, README and eight frozen files remain byte-for-byte
unchanged and still describe their earlier source-review state.

Original exec91865 returned0. Python223208 completed the frozen extractor with
passed=true; its original Node212548 was actually waited to return0. No
timeout, kill, retry or replay occurred. The private output remains unique.

The new raw host image is
`E:/edk2-samurai-out/charging-oem-audit-20261023/gauge-2719-vendor-extract-private-01/vendor.img`,
1711276032 bytes, SHA256
`905a0f0477b1edcd686fa059bfedc9aea79b6cc2107c472190d62f125abd7f0c`.

The ZIP member was read to EOF:699830594 bytes, CRC43496d61, SHA256
`c4e6c9808451f180dce0ea94a80bb34870df1f94996d99ce0ccaab0531c29246`.
Node's upstream count and Brotli engine bytesWritten both equal699830594.
Output was exactly1613049856 bytes with SHA256
`6238599745f01afc1fa3df5a20ff57bacbc852d681ff288e9f81ff46f7c9a29e`.
The converter consumed precisely that stream in sequence, checked EOF and the
same SHA, and covered the complete validated0..417792 destination range.
zero/erase affected only unwritten zero ranges in the new host image.

The source ZIP stat and fixed metadata/transfer hashes were unchanged. Plan,
tools and frozen source hashes were unchanged. This does not establish a
whole-OTA hash, signature or exact2719 pack identity. No system payload, other
OTA content, device, mount, SDK, storage helper/volume, Git or firmware was
changed. No debugfs/indexer ran in this step; filesystem interpretation and
descriptor lookup remain the root's separate readonly operation.

All original extracted files, plan copy, Node stdout/stderr and full result
remain private. actual-result.json and actual-delivery.json expose only the
necessary artifact/terminal bindings. freeze-actual.py verifies the saved small
receipts and frozen source snapshot and rechecks artifact sizes; it does not
redecode the payload or reread new.dat to duplicate its original SHA pass.
