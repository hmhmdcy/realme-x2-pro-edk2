"""Stage the new unloaded lens module and signed packages with matched actual273 rollback."""
from pathlib import Path
import ast,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'complete-host-qa-validation.json').read_text())['all_13_package_signatures_and_features_checked']
module=json.loads((R/'current-module-build-validation.json').read_text());binary=P/'current-module-build-r1/lc898219xi.ko';assert hashlib.sha256(binary.read_bytes()).hexdigest()==module['module_sha256']
runtime=json.loads((R/'runtime-repo-validation.json').read_text());archive=P/'r22-seven-package-repo-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==runtime['sha256']
baseline=json.loads((P/'deployment-baseline-private.json').read_text());stage='/var/lib/samurai/k275-main-candidates';response=P/'stage-response-private.log';assert not response.exists()
q=host.ssh('python3 -c '+shlex.quote("from pathlib import Path;import os;os.umask(0o077);Path(%r).mkdir(mode=0o700)"%stage),timeout=15)
for name,path in [('runtime.tar.gz',archive),('lc898219xi.ko',binary)]:
 data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();remote=stage+'/'+name
 code="from pathlib import Path;import hashlib,os,sys;os.umask(0o077);p=Path(%r);assert not p.exists();b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b);print(len(b))"%(remote,digest)
 q=host.ssh('python3 -c '+shlex.quote(code),input=data,timeout=35);assert int(q.stdout)==len(data)
args=dict(boot_id=baseline['boot_id'],old_boot_sha256=baseline['boot_partition_sha256'],package_db_sha256=baseline['package_db_sha256'],module_sha256=module['module_sha256'],vermagic=module['vermagic'],old_repo=baseline['old_repo'])
tree=ast.parse((R.parent/'kernel273/stage-main.py').read_text());n=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets));code=ast.literal_eval(n.value)
changes=[('k273','k275'),('stage=273','stage=275'),('s5kgw1','lc898219xi'),("'0.1.0-r15'","'__OLD_CONFIG__'"),('0.1.0-r16','0.1.0-r17'),('__OLD_CONFIG__','0.1.0-r16'),('99990.7.2-r20','99990.7.2-r21'),('boot270-rollback','boot273-rollback'),('assert len(inventory)==774','assert len(inventory)==775'),('existing_774_modules_byte_exact','existing_775_modules_byte_exact'),('old_module_count=774,new_module_count=775','old_module_count=775,new_module_count=776')]
for a,b in changes:assert a in code,a;code=code.replace(a,b)
response.write_bytes(b'SUBMISSION INTENT: inspect /var/lib/samurai/k275-main-transaction if response is lost.\n')
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=110,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the submitted staging transaction before any retry'
d=json.loads(q.stdout);(R/'module-stage-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2),flush=True)
# This is read-only after a terminal staging transaction. A failed transfer must
# resume this archive, never rerun the staging worker.
q=host.ssh('cat /var/lib/samurai/k275-main-transaction/rollback-private.tar.gz',timeout=60)
assert len(q.stdout)==d['rollback_bytes'] and hashlib.sha256(q.stdout).hexdigest()==d['rollback_sha256'];(P/'main-rollback-private.tar.gz').write_bytes(q.stdout)
report=dict(stage=275,phone_and_pc_rollback_verified=True,bytes=len(q.stdout),sha256=d['rollback_sha256'],contains_old_signed_r21_r16_packages=True,contains_current_boot273_and_depfiles=True,rollback_boot_sha256=d['rollback_boot_sha256'])
(R/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
