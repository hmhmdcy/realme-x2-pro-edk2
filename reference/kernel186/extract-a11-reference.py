"""Extract only SLPI files from the CRC-verified A.11 FAT image."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel186')
download = json.loads((private / 'a11-package-range-validation.json').read_text())
assert download['selected_entry_zip_crc_verified'] and download['version'] == 'RMX1931_11.A.11'
(ref / 'a11-package-range-validation.json').write_text(json.dumps(download, indent=2) + '\n')
source = (ref.parent / 'kernel113/inspect-c28-reference.py').read_text()
source = source.replace("Path('/mnt/e/edk2-samurai-out/kernel113')", "Path('/mnt/e/edk2-samurai-out/kernel186')")
source = source.replace("ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')", "ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel186')")
path = private / 'inspect-a11-reference-private.py'
assert not path.exists()
path.write_text(source)
subprocess.run([sys.executable, str(path), 'a11'], check=True)
print(json.dumps({'stage': 186, 'slpi_extracted_offline': True, 'original_firmware_kept': True,
    'no_modem_image_flashed': True, 'no_package_scripts_executed': True}))
