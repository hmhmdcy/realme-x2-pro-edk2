from pathlib import Path
import hashlib

r=Path(__file__).resolve().parent
lines=[]
for p in sorted(r.iterdir()):
    if p.is_file() and p.name not in ('SHA256SUMS','verification-report.json'):
        lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(r/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
print(f'Sealed {len(lines)} public evidence/source files.')
