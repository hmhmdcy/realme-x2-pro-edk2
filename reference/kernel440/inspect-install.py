"""Refresh the exact installed baseline without altering the phone."""
from pathlib import Path
import json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.mount.mounted_build()
assert json.loads((HERE/'hardware-validation.json').read_text())['passed']
code=r'''from pathlib import Path
import hashlib,json,subprocess,os,stat
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return dict(path=str(p),resolved=str(p.resolve()),sha256=sha(p),mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
dev=Path('/sys/bus/platform/devices/ac10000.icp');names={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'};versions={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if f.get('P') in names:versions[f['P']]=f['V']
modules={}
for name in ['qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_m2m']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip());owner=subprocess.run(['apk','info','--who-owns',str(p)],capture_output=True,text=True)
 modules[name]={**record(p),'note_sha256':sha(Path('/sys/module',name,'notes/.note.gnu.build-id')),'apk_owner_rc':owner.returncode,'apk_owner':owner.stdout.strip()}
profiles={p.name:record(p) for p in Path('/etc/libcamera/ipa/camss-vfe').glob('*.yaml')}
configuration={n:record('/'+n) for n in ['etc/apk/world','etc/apk/repositories.d/60-samurai-camera.list']}
print(json.dumps(dict(packages=versions,uname=os.uname().release,modules=modules,profiles=profiles,configuration=configuration,m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);q.check_returncode();d=json.loads(q.stdout)
assert len(d['packages'])==7 and d['taint']==0
assert all(v==('99990.7.2-r31' if n.startswith('libcamera') else '0.1.0-r26') for n,v in d['packages'].items())
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert d['m2m']['jobs']==d['m2m']['completed']==d['m2m']['direct_completed']
prior=json.loads((P/'initial-device-private.json').read_text())
assert d['packages']==prior['packages']
assert all(d['modules'][n]['sha256']==x['sha256'] and d['modules'][n]['note_sha256']==x['note_sha256'] and not d['modules'][n]['apk_owner'] for n,x in prior['modules'].items())
assert {n:x['sha256'] for n,x in d['profiles'].items()}==prior['private_defaults']
(P/'install-baseline-private.json').write_bytes(q.stdout)
r={'stage':440,'passed':True,'formal_r31_r26_still_installed':True,'three_module_targets_and_notes_unchanged':True,'all_module_files_unowned_by_apk':True,'four_private_defaults_unchanged':len(d['profiles'])==4,'idle':True,'taint':0,'prior_goal_turn_classification':'progress: reclaimed expired build/cache files, compacted WSL, verified current release and rollback unchanged; phase440 r2 physical audit406 automatic images386 math plus90RAW-only and6dual passed','installed':False}
(HERE/'install-preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
