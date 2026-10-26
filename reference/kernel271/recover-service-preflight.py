"""Restore the stopped old provider after the verified pre-mutation failure."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,subprocess,time,shutil
o=Path('/var/lib/samurai/k271-gain-transaction');state=json.loads((o/'transaction-state-private.json').read_text())
assert not any(state[k] for k in ['module_unbound','module_replaced','packages_sent'])
assert not Path('/proc',str(state['pid'])).exists(),'Original transaction still exists'
assert Path('/lib/apk/db/installed').read_bytes()==(o/'backup/lib/apk/db/installed').read_bytes()
target=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/s5k3m5.ko'
assert hashlib.sha256(target.read_bytes()).hexdigest()=='22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72'
services={x['name']:x for x in json.loads((o/'services-before-private.json').read_text())}
def found(name):
 result=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':result.append(p)
  except OSError:pass
 return result
assert not found('wireplumber')
pw=services['pipewire'];assert Path('/proc',str(pw['pid']),'stat').read_text().rsplit(')',1)[1].split()[19]==pw['start_ticks']
u=pwd.getpwuid(10000)
def demote():os.initgroups(u.pw_name,u.pw_gid);os.setgid(u.pw_gid);os.setuid(u.pw_uid)
row=services['wireplumber']
with (o/'wireplumber-recovery-private.log').open('xb') as log:
 child=subprocess.Popen(['/usr/bin/wireplumber'],env=row['env'],cwd=row['cwd'],preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+12
while time.monotonic()<deadline:
 assert child.poll() is None
 p=Path('/proc',str(child.pid))
 if '/usr/lib/libcamera.so.0.7.2' in (p/'maps').read_text():break
 time.sleep(.2)
else:raise RuntimeError('Restored provider did not load libcamera')
assert len(found('wireplumber'))==1
row['pid']=child.pid;row['start_ticks']=(p/'stat').read_text().rsplit(')',1)[1].split()[19]
state.update(state='failed-before-update-old-service-restored',terminal=True,exit_code=1,restored_wireplumber_pid=child.pid)
(o/'transaction-state-private.json').write_text(json.dumps(state,indent=2)+'\n')
n=Path('/var/lib/samurai/k271-gain-transaction-r2');n.mkdir(mode=0o700)
shutil.copytree(o/'backup',n/'backup')
for name in ['old-manifest-private.json','new-manifest-private.json','module-inventory-before-private.json','candidate-repositories.list','rollback-repositories.list']:
 shutil.copyfile(o/name,n/name)
(n/'services-before-private.json').write_text(json.dumps(list(services.values())))
report=dict(stage=271,first_transaction_terminal_before_package_or_module_mutation=True,original_driver_and_database_verified=True,
 old_provider_restored=True,new_provider_pid=child.pid,pipewire_and_desktop_preserved=True,new_transaction_prepared=True)
(o/'recovery-summary.json').write_text(json.dumps(report));print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30,check=False)
(host.PRIVATE/'preflight-recovery-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect recovery before proceeding'
(R/'preflight-recovery-validation.json').write_text(json.dumps(json.loads(q.stdout),indent=2)+'\n');print(q.stdout.decode())
