from pathlib import Path
import subprocess,ast,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')
scripts=list(ref.glob('*.sh'));python=list(ref.glob('*.py'))
for path in scripts:subprocess.run(['sh','-n',str(path)],check=True)
for path in python:ast.parse(path.read_text(),filename=path.name)
report=dict(posix_shell_files_checked=len(scripts),python_files_checked=len(python),syntax_pass=True)
(ref/'syntax-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
