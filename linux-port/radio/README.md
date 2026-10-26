# Samurai modem TFTP work files

The modem requests temporary files such as `/readwrite/mcfg.tmp`. The previous server allowed only `server_check.txt`, causing these requests to fail with EACCES. This implementation keeps work files on a private 32MiB tmpfs, retains read-only firmware access, and leaves the NV COW service unchanged.

`source-lock.json` pins the public tqftpserv/qrtr inputs and local source hashes. With Python 3, `patch`, and an AArch64 GNU toolchain installed, run from the repository root:

```sh
python3 linux-port/radio/build-tftp.py --work-dir /tmp/samurai-tftp-build
```

The output directory must be new. The script verifies every downloaded file, applies the patch without fuzz, and builds a static `samurai-tqftpserv` with warnings treated as errors. The two upstream LICENSE files remain in the build directory. `samurai-wifi.sh` is the matching startup source; deployment and rollback require the current handset state and service environment.

For a previously downloaded source set, add `--source-cache /path/to/cache`. Each cached input must still match its pinned hash; the build directory must still be new.

The stage207 server keeps absolute block counters internally and truncates only the on-wire block number to 16 bits. Native QRTR tests reproduced failures in the previous reader and writer, then verified a 1,048,603-byte write/read across two counter rollovers. Duplicate packets and window acknowledgments are also covered by the bounded regression set.

`samurai-modem-configs.py` stages the handset's own `image/modem_pr/mcfg` subtree from the read-only stock modem partition into the private RAM firmware directory. The startup script calls it before unmounting the stock source. It requires private tmpfs destinations, checks every copied file, and records the per-file manifest privately. The MCFG firmware subtree is separate from the temporary `mcfg.tmp` work file. No proprietary MCFG files or device manifests are included here; installing the script requires Python 3 and the matching startup helper.

See [stage206](../../reference/kernel206/README.md) and [stage207](../../reference/kernel207/README.md) for native QRTR tests, runtime evidence, and remaining GNSS work. Passing file-service tests does not establish a real satellite fix or complete TFTP conformance.
