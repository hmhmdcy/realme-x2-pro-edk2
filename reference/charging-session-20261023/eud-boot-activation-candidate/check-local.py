"""Default read-only syntax/hash check; never imports workers or transport."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
receipt=json.loads((HERE/'generation-result.json').read_text())
for name,entry in receipt['files'].items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==entry['candidate_sha256']
assert hashlib.sha256((HERE/'guard-fragment.py').read_bytes()).hexdigest()==receipt['guard_sha256']
print(json.dumps({'checked':True,'device_access':False,'workers_imported':False,'files_written':False,'workers':receipt['files']}))
