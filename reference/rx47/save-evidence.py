#!/usr/bin/env python3
"""Copy raw evidence unchanged; record original hashes of normalized text."""
from hashlib import sha256
from pathlib import Path
import json

SOURCE = Path('/mnt/e/edk2-samurai-out/rx47')
DEST = Path(__file__).resolve().parent
rows = []
sources = sorted(SOURCE.glob('*.raw')) + sorted(SOURCE.glob('*.txt'))
sources += [SOURCE / 'eud-open-session.ps1', SOURCE / 'eud-terminal-before-rx47.ps1',
            SOURCE / 'final-state.json',
            Path('/mnt/e/edk2-samurai-out/rx46/inspect-etl-payload.py')]
sources += [DEST.parents[1] / 'linux-port/scripts/eud-terminal.ps1']
for src in sources:
    original = src.read_bytes()
    name = 'eud-terminal-native.ps1' if src.name == 'eud-terminal.ps1' else src.name
    if src.suffix == '.raw' or 'eud-terminal' in name:
        exported = original
    else:
        decoded = original.decode('utf-8-sig')
        exported = ('\n'.join(line.rstrip() for line in decoded.splitlines()) + '\n').encode()
    (DEST / name).write_bytes(exported)
    rows.append({'name': name, 'original_path': str(src),
                 'original_sha256': sha256(original).hexdigest(),
                 'exported_sha256': sha256(exported).hexdigest(),
                 'byte_identical': exported == original})
(DEST / 'exports.json').write_text(json.dumps(rows, indent=2) + '\n')
protected = sorted(p for p in DEST.iterdir()
                   if p.is_file() and p.name not in ('SHA256SUMS', 'verify.py', 'README.md',
                                                     'source-audit.md', 'save-evidence.py',
                                                     'export-etw-controls.py'))
(DEST / 'SHA256SUMS').write_text(''.join(f'{sha256(p.read_bytes()).hexdigest()}  {p.name}\n'
                                      for p in protected))
print(f'Exported {len(rows)} files; raw sets={len(list(DEST.glob("*.raw")))}')
