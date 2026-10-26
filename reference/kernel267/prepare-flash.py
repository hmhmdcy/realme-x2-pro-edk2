"""Adapt the existing fresh-fastboot identity gate to only this locked boot image."""
from pathlib import Path
import hashlib
import json

R=Path(__file__).resolve().parent
s=(R.parent/'kernel236/flash-boot.py').read_text().replace('stage=236','stage=267').replace("['boot232_rollback']","['boot235_rollback']")
compile(s,'flash-boot.py','exec');(R/'flash-boot.py').write_text(s)
print(json.dumps(dict(stage=267,flash_source_sha256=hashlib.sha256(s.encode()).hexdigest(),
 fresh_original_identity_and_boot_geometry_gate=True,only_boot_partition=True)))
