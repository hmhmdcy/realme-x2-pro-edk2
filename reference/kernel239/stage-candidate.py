"""Stage signed and host-verified runtime payload in RAM, keep installed r13."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'r15-host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
host.upload(P/'r15-runtime-candidate-private.tar.gz','/var/lib/samurai/k239-tools/r15-runtime-candidate-private.tar.gz')
host.upload(P/'candidate-runtime-lock-private.json','/var/lib/samurai/k239-tools/candidate-runtime-lock-private.json')
code=r'''
from pathlib import Path
import hashlib,json,os,stat,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((r/'k239-odm-source/state-private.json').read_text())['exit_code']==0
out=r/'k239-candidate-stage';assert not out.exists();out.mkdir(mode=0o700)
target=Path('/run/samurai-camera239-r15');assert not target.exists();target.mkdir(mode=0o755);target.chmod(0o755)
lock=json.loads((r/'k239-tools/candidate-runtime-lock-private.json').read_text());bundle=r/'k239-tools/r15-runtime-candidate-private.tar.gz'
assert bundle.stat().st_size==lock['bundle_bytes'] and hashlib.sha256(bundle.read_bytes()).hexdigest()==lock['bundle_sha256']
with tarfile.open(bundle,'r:gz') as archive:
 members=archive.getmembers();assert {m.name for m in members}==set(lock['files'])
 for m in members:
  assert not m.name.startswith('/') and '..' not in Path(m.name).parts and m.name.startswith(('usr/','etc/'))
  dest=target/m.name;dest.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
  for parent in [dest.parent,*dest.parent.parents]:
   if parent==target:break
   assert parent.is_relative_to(target);parent.chmod(0o755)
  expected=lock['files'][m.name]
  if m.issym():
   assert expected['kind']=='symlink' and '..' not in Path(m.linkname).parts and m.linkname==expected['target'];dest.symlink_to(m.linkname)
  else:
   assert m.isfile() and expected['kind']=='file';data=archive.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==expected['sha256'];dest.write_bytes(data);dest.chmod(expected['mode'])
config=target/'config-enabled/libcamera';config.mkdir(parents=True,mode=0o755);config.parent.chmod(0o755);config.chmod(0o755);(config/'configuration.yaml').write_bytes((target/'etc/libcamera/configuration.yaml').read_bytes());(config/'configuration.yaml').chmod(0o644)
assert b'mode: cpu' in (config/'configuration.yaml').read_bytes()
assert (target/'usr/lib/libcamera/ipa/ipa_soft_simple.so').is_file() and (target/'usr/lib/libcamera/ipa/ipa_soft_simple.so.sign').is_file()
report=dict(stage=239,ram_candidate_staged=True,payload_files=len(members),exact_verified_package_payload=True,cpu_config_explicit=True,installed_r13_unchanged=True,initial_parameters_fix_not_yet_physically_verified=True,no_camera_capture=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=25);(P/'stage-candidate-host-private.log').write_bytes(r.stdout+r.stderr);report=json.loads(r.stdout)
(R/'candidate-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
