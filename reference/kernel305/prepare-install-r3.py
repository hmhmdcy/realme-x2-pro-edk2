"""Prepare a new transaction only after the failed verifier rolled back completely."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
previous=json.loads((HERE/'geometry-install-validation.json').read_text())
assert previous['rollback_verified'] and previous['resources_restored'] and previous['taint']==0 and not previous['restart_failure']
code=r'''
from pathlib import Path
import hashlib,json,os,shutil
old=Path('/var/lib/samurai/k305-geometry-r2')
state=json.loads((old/'transaction-state-private.json').read_text());summary=json.loads((old/'summary-private.json').read_text())
assert state['terminal'] and summary['rollback_verified'] and summary['resources_restored'] and summary['taint']==0
pre=json.loads((old/'preflight-private.json').read_text())
for item in summary['new_services']:
 p=Path('/proc',str(item['pid']))
 fields=(p/'stat').read_text().rsplit(')',1)[1].split()
 assert fields[0]!='Z' and fields[19]==item['start_ticks']
 pre['services'][item['name']]=dict(item,env=dict(s.decode().split('=',1) for s in (p/'environ').read_bytes().split(b'\0') if b'=' in s),
  cwd=os.readlink(p/'cwd'),argv=[s.decode() for s in (p/'cmdline').read_bytes().split(b'\0') if s])
for name in ['phoc','phosh']:
 item=pre['services'][name];assert Path('/proc',str(item['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]==item['start_ticks']
target=Path(pre['module_path']);assert hashlib.sha256(target.read_bytes()).hexdigest()==pre['original_sha256']
assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()==pre['loaded_note_sha256']
root=Path('/var/lib/samurai/k305-geometry-r3');assert not root.exists();root.mkdir(mode=0o700)
for name in ['backup','payload']:shutil.copytree(old/name,root/name)
for name in ['boot-id-private.txt','module-inventory-before-private.json','payload-manifest-private.json']:
 shutil.copyfile(old/name,root/name)
(root/'preflight-private.json').write_text(json.dumps(pre,indent=2)+'\n')
print(json.dumps(dict(stage=305,previous_transaction_terminal=True,original_module_rollback_verified=True,
 refreshed_service_identities=True,new_transaction_prepared=True,no_module_mutation=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(HERE/'geometry-install-r2-validation.json').write_text(json.dumps(previous,indent=2)+'\n')
report=json.loads(q.stdout);(HERE/'r3-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
