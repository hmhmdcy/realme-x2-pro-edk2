from pathlib import Path
import ast,hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel237')
p=P/'current-work-private.json';s=json.loads(p.read_text());s.update(next='Read readonly agent results; add minimal IMX319 gain helper (1024/(1024-code), no copied calibration), retain r13 full features and validate explicit RAW exposure/gain capture metadata/response before CPU RGB. Current236 guard and CAMSSff9.');p.write_text(json.dumps(s,indent=2)+'\n')
for p in R.glob('*.py'):ast.parse(p.read_text())
lock={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in R.rglob('*') if p.is_file() and p.suffix in ['.py','.cpp','.c','.h','.patch','.md']}
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
p=R/'source-final-validation.json';s=json.loads(p.read_text());s['python_syntax_files']=len(list(R.glob('*.py')));s['gain_helper_gap_documented']=True;p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(dict(stage=237,source_files_locked=len(lock),python_syntax_files=s['python_syntax_files'],gain_helper_gap_documented=True)))
