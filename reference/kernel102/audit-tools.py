from pathlib import Path
import json,subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel102')
py=list(ref.glob('*.py'));shell=list(ref.glob('*.sh'))
for p in py:compile(p.read_text(),str(p),'exec')
for p in shell:subprocess.run(['bash' if p.read_text().startswith('#!/bin/bash') else 'sh','-n',str(p)],check=True)
report=dict(python_syntax_pass=True,python_files=len(py),shell_syntax_pass=True,shell_files=len(shell),bytecode_generated=False)
Path('/mnt/e/edk2-samurai-out/kernel102/tools-syntax-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('AUDIO_TOOLS_SYNTAX_PASS')
