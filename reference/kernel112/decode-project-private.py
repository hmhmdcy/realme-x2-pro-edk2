#!/usr/bin/env python3
"""Decode SMEM 135 using the official X2 Pro Android R OCDT structure.

ProjectInfoOCDT: Version (4), ProjectDataBCDT (52), SCDT (36), ECDT (8).
get_Modem_Version() returns SCDT.RF, not the old project header's byte 4.
Input and output remain in the private artifact directory.
"""
import json
import pathlib
import struct

root = pathlib.Path('/mnt/e/edk2-samurai-out/kernel112')
record = json.loads((root / 'project-v4-private.json').read_text())
raw = bytes.fromhex(record['raw_hex'])
assert record['memory_read_only'] and len(raw) == record['smem_record_bytes'] == 100
version, project, dtsi, audio = struct.unpack_from('<4I', raw)
boot_mode, rf, pcb = struct.unpack_from('<3I', raw, 56)
assert version == 2 and project == dtsi == audio == 19781
decoded = dict(schema='Realme X2 Pro Android R ProjectInfoOCDT',
               schema_version=version, project=project, dtsi=dtsi, audio=audio,
               modem_type=rf, pcb=pcb, boot_mode=boot_mode,
               smem_bytes=len(raw), memory_read_only=True,
               legacy_layout_valid=False,
               source='https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source')
(root / 'project-ocdt-private.json').write_text(json.dumps(decoded, indent=2) + '\n')
(root / 'modemType-private.txt').write_text(str(rf))
(root / 'project-metadata-summary.json').write_text(json.dumps(dict(
    project_initialized=True, legacy_layout_plausible=False,
    legacy_modem_type_invalid=True, correct_ocdt_layout_verified=True,
    modem_property_captured=True, probe_unloaded=True,
    expected_external_module_taint=4096), indent=2) + '\n')
print('OCDT_SCHEMA_VALIDATED; derived property saved privately')
