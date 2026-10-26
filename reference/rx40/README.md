# RX40 source audit and baseline check

See [session 40](../../sessions/40-rx-register-map-and-stock-firmware-audit.md).
Native multi-byte RX remains unfixed; no flash or new multi-byte trial this session.

- `source-manifest.json`: pinned full-source URLs, sizes and verified Git/SHA-256 hashes.
- `source-audit.txt`: minimal older register index and stock SM8150 static findings/limits.
- `baseline-check.raw` / `.txt`: fresh Windows Ctrl-U receipt, 7 frames, 0 stray.
- `device-check.json`: exact bounded check and closed-port state, with evidence limits.
- `evidence-manifest.json`: hashes of the five evidence files above.

Full generated register table and firmware binaries remain outside the repository in
`E:\edk2-samurai-out\rx40-sources\`. They were not executed or transplanted into the build.
The older register map lacks read-side-effect documentation; it does not authorize new SM8150 writes.
