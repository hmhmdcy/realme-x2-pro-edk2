from pathlib import Path
import runpy,json
r=Path('/mnt/e/RealmeX2Pro edk2');code=(r/'reference/kernel126/verify-rootfs-stage.py').read_text();code=code[:code.index("assert before==after")]
scope={};exec(compile(code,'manifest-diag126','exec'),scope)
before,after=scope['before'],scope['after'];different=[dict(path=n,expected=before.get(n),actual=after.get(n)) for n in sorted(before.keys()|after.keys()) if before.get(n)!=after.get(n)]
Path('/mnt/e/edk2-samurai-out/kernel126/stage-manifest-differences-private.json').write_text(json.dumps(different,indent=2)+'\n');print('DIFFERENT_PATHS',*[d['path'] for d in different[:30]],'COUNT',len(different))
