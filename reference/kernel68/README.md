# Kernel68: actual firmware DTB and CPU7 OPP

The firmware DTB now contains the CPU7 2.9568 GHz OPP from session67. A boot-only
firmware update activates that node. Device-verified facts show policy7's available
table/max=2956800 kHz, a fresh boot_id and taint0. The complete 52842-byte boot
log passes device SHA256/gzip CRC and no longer reports the OPP/initial-frequency
failure. USB UDC and six UFS LUNs remain. High-frequency stress and actual USB
traffic remain untested.

Run `python3 verify.py` for capture, export, source-image audit, failure retention
and final-state checks. `manifest.json` covers the committed evidence bytes.
Session68 records scope and remaining priorities. No EUD changes or experiments.

The closed WSL captures include their complete target usbmon/raw; Windows raw
and event logs are separate. Windows close observations come from exec output,
with an independent PnP/process audit in finish-state.json. Failed exports and
partial commands remain unchanged; verified logs were independently received
from the same saved files using existing terminals, without reconstruction.

Large firmware volumes and boot images stay in E:/edk2-samurai-out/kernel68.
For the full independent packaging/module audit there, run
`python3 verify-firmware.py /mnt/e/edk2-samurai-out/kernel68`. It validates old/new
gzip/LZMA/headers/RAW DTBs and exact version-only differences in executable files.
The archived DTBs, reports, build log and source hashes identify that result;
the smaller archive verifier does not pretend to re-run missing large volumes.

Only boot was flashed; logdump/Image/config/init and Android data were preserved.
Original F1 boot image remains the immediate firmware rollback. Current COM14
is Windows Shared/unattached, three nodes OK, no known owner. Original EUD fixes,
driver, native/compatible terminals and RX48 rollback remain intact.
