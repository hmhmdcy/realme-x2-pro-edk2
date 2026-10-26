#!/usr/bin/env python3
"""Copy reviewed RX50 evidence only; keep original raw/bin/executed source bytes."""
from hashlib import sha256
import json
from pathlib import Path

original = Path(__file__).resolve().parent
target = Path('/mnt/e/RealmeX2Pro edk2/reference/rx50')
target.mkdir(parents=True, exist_ok=True)
names = [
    'inspect-qcusbser.py', 'inspect-pdb-types.py', 'EudRxAudit.cs',
    'eud-terminal-rx-audit.ps1', 'audit-runtime.ps1', 'analyze-window.py',
    'windows-audit.raw', 'windows-audit.txt', 'windows-audit.events.txt',
    'windows-audit.rx-audit.jsonl', 'windows-window-summary.json',
    'windows-journal-1.bin', 'windows-journal-1.json',
    'qcusbser-identity.json', 'qcusbser-selected-types.json',
    'installed-managed-runtime.json', 'final-state.json', 'capture-state.ps1',
    'source-manifest.json', 'export-evidence.py',
]
manifest = []
for name in names:
    data = (original / name).read_bytes()
    if Path(name).suffix in ('.raw', '.bin', '.py', '.ps1', '.cs'):
        exported = data
    else:
        text = data.decode('utf-8-sig').replace('\r\n', '\n')
        exported = ('\n'.join(line.rstrip() for line in text.splitlines()) + '\n').encode()
    (target / name).write_bytes(exported)
    manifest.append(dict(name=name, original_sha256=sha256(data).hexdigest(),
                         exported_sha256=sha256(exported).hexdigest(), byte_identical=data == exported))
(target / 'exports.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(f'Exported {len(manifest)} reviewed files; no driver/PDB/third-party source binary copied.')
