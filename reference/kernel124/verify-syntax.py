from pathlib import Path
import subprocess,ast,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel124')
scripts=list(ref.glob('*.sh'));python=list(ref.glob('*.py'))
for p in scripts:subprocess.run(['bash','-n',str(p)],check=True)
for p in python:ast.parse(p.read_text(),filename=p.name)
report=dict(shell_files_checked=len(scripts),python_files_checked=len(python),syntax_pass=True)
(ref/'syntax-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
