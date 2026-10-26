from pathlib import Path
import hashlib,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;build=storage.mount.mounted_build();tree=storage.candidate()/'src/libcamera-v0.7.2'
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='01a71e6fd9ac33b0f91539354f540b39213eafc3'
for row in json.loads((HERE.parent/'kernel439/source-state.json').read_text())['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
assert not set(subprocess.check_output(['ps','-eo','comm='],text=True).split())&{'make','ninja','cc1','cc1plus','clang','gcc','rustc','ld.lld'}
code=r'''from pathlib import Path
import hashlib,json,subprocess,os
dev=Path('/sys/bus/platform/devices/ac10000.icp');names={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'};versions={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if f.get('P') in names:versions[f['P']]=f['V']
assert len(versions)==7
modules={}
for name in ['qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_m2m']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip());owner=subprocess.run(['apk','info','--who-owns',str(p)],capture_output=True,text=True)
 modules[name]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),note_sha256=hashlib.sha256(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()).hexdigest(),apk_owner_rc=owner.returncode,apk_owner=owner.stdout.strip())
print(json.dumps(dict(packages=versions,uname=os.uname().release,modules=modules,m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),private_defaults={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/etc/libcamera/ipa/camss-vfe').glob('*.yaml')})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);q.check_returncode();d=json.loads(q.stdout);(P/'initial-device-private.json').write_bytes(q.stdout)
assert d['taint']==0 and all(v==('99990.7.2-r31' if n.startswith('libcamera') else '0.1.0-r26') for n,v in d['packages'].items())
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
r={'stage':440,'passed':True,'current439_sources_match':True,'formal_r31_r26_confirmed':True,'three_module_targets_and_ownership_observed':True,'phone_idle':True,'taint':0,'previous_goal_turn_classification':'progress:439 stock front IPE CCM83 delivered images79 successful math plus5 deterministic hardware replays;formal restored','new_source_clone_needed':False,'free_build_bytes':__import__('shutil').disk_usage(build).free}
(HERE/'initial-state-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
print(json.dumps({'module_apk_owners':{n:x['apk_owner'] for n,x in d['modules'].items()}}))
