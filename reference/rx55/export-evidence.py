from hashlib import sha256
import json
from pathlib import Path
import re
import shutil

original=Path(__file__).resolve().parent
windows=Path('/mnt/e/RealmeX2Pro edk2')
dest=windows/'reference/rx55'
dest.mkdir(exist_ok=True)
names=['EudRxAudit.cs','EudSerialPerf.cs','eud-terminal-rx-perf.ps1',
       'prepare-diagnostic.py','check-diagnostic.ps1','capture-windows.ps1',
       'capture-final-state.ps1','analyze-windows-perf.py','diagnostic-abi.json',
       'before-state.json','final-state.json','windows-perf-01.raw',
       'windows-perf-01.txt','windows-perf-01.events.txt','windows-perf-01.rx-audit.jsonl',
       'windows-perf-summary.json','windows-tx-journal.bin','export-evidence.py']
rows=[]
for name in names:
    path=original/name; data=path.read_bytes(); exact=path.suffix in ('.cs','.ps1','.py','.raw','.bin')
    exported=data if exact else re.sub(r'\r+\n','\n',data.decode('utf-8-sig')).encode('utf-8')
    (dest/name).write_bytes(exported)
    rows.append(dict(name=name,original_path=str(path),original_sha256=sha256(data).hexdigest(),
                     exported_sha256=sha256(exported).hexdigest(),byte_identical=exact))
(dest/'exports.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
deps=['../rx54/restored-native.raw','../rx54/installed-driver-identity.json',
      '../rx54/perf-received-type.json','../rx54/SerialGetStats.asm.txt',
      '../rx54/rx50-vPutToReadBuffer.asm.txt','../rx53/source-epoch.json']
(dest/'dependencies.json').write_text(json.dumps({p:sha256((dest/p).read_bytes()).hexdigest() for p in deps},indent=2)+'\n',encoding='utf-8')
paths=sorted(p for p in dest.iterdir() if p.is_file() and p.name!='SHA256SUMS')
(dest/'SHA256SUMS').write_text(''.join(f'{sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in paths),encoding='utf-8')
repo=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
docs=['HANDOVER-NEXT.md','RX-CONSOLE.md','FLYWHEEL.md','DOCS-INDEX.md',
      'linux-port/docs/EUD-TERMINAL.md','sessions/55-windows-perf-counter-and-reproduced-tx-gap.md']
for name in docs:
    path=repo/name; path.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(windows/name,path)
repo_dest=repo/'reference/rx55'
repo_dest.mkdir(exist_ok=True)
for path in dest.iterdir():
    if path.is_file(): shutil.copyfile(path,repo_dest/path.name)
expected={p.relative_to(windows).as_posix():sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file()}
expected.update({p:sha256((windows/p).read_bytes()).hexdigest() for p in docs})
(original/'reviewed-manifest.json').write_text(json.dumps(expected,indent=2)+'\n',encoding='utf-8')
print(f'Exported {len(paths)+1} reference files; copied six reviewed docs; no automatic stage/commit/push.')
