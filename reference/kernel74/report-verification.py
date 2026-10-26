from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parent
report = subprocess.check_output([sys.executable,str(root/'verify-evidence.py')],text=True)
result = json.loads(report)
(root/'evidence-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(report)
