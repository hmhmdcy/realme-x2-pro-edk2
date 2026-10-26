"""Read back the installed cohort and audit preserved default-path captures."""
from pathlib import Path
import json,shlex
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
installed=json.loads((HERE/'install-r3-validation.json').read_text());assert installed['passed'] and installed['installed'] and not installed['worker_live'] and not installed['client_live']
code='from pathlib import Path\nimport json,hashlib,os,re,subprocess,stat\n'+(HERE/'installed-frame-audit.py').read_text()+r'''
root=Path('/var/lib/samurai/k440-install-r3');proof=json.loads((root/'proof.json').read_text());transaction=json.loads((root/'state.json').read_text());suite=json.loads((root/'suite.json').read_text())
assert transaction['terminal'] and transaction['passed'] and transaction['installed'] and not transaction['rollback'] and not transaction['new_faults']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==proof['boot_id'] and os.uname().release==proof['uname']
versions={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if f.get('P') in proof['packages']:versions[f['P']]=f['V']
assert versions==proof['packages']
for name,digest in proof['installed_files'].items():assert sha('/'+name)==digest,name
modules={}
for row in proof['modules']:
 assert sha(row['path'])==row['new_sha256'] and sha('/sys/module/'+row['module']+'/notes/.note.gnu.build-id')==row['new_note_sha256']
 assert Path(subprocess.check_output(['modinfo','-n',row['module']],text=True).strip()).resolve()==Path(row['path']).resolve()
 assert subprocess.check_output(['modinfo','-F','intree',row['path']],text=True).strip()=='Y'
 assert 'test_' not in subprocess.check_output(['modinfo','-F','parm',row['path']],text=True)
 modules[row['module']]=dict(sha256=row['new_sha256'],bytes=Path(row['path']).stat().st_size,loaded=True,loaded_note_matches_disk=True,intree='Y',parameters={},source_stage=434,targeted_validation_stage=440)
for row in proof['profiles']:
 p=Path(row['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and sha(p)==row['new_sha256'] and stat.S_IMODE(s.st_mode)==row['mode'] and s.st_uid==row['uid'] and s.st_gid==row['gid']
assert Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text()=='ndx file://'+str(root/'repository/forward/packages.adb')+'\n'
assert all(Path(root/'repository/rollback',n+'-'+v+'.apk').is_file() for n,v in proof['old_packages'].items())
rows=[]
for model,case,log in [('s5kgw1',Path('/var/lib/samurai/k440-install-r2/auto-s5kgw1'),Path('/var/lib/samurai/k440-install-r2/auto-s5kgw1.log')),('imx471',root/'auto-imx471',root/'auto-imx471.log')]:
 result=audit_auto(log.read_text(),model,case);result['model']=model;result['case_root']=str(case);rows.append(result)
services={}
for name in ['pipewire','wireplumber']:
 processes=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':processes.append(p)
  except (FileNotFoundError,ProcessLookupError):pass
 assert len(processes)==1
 services[name]=dict(pid=int(processes[0].name),uid=processes[0].stat().st_uid)
maps=Path('/proc',str(services['wireplumber']['pid']),'maps').read_text();assert any('/usr/lib/libcamera.so.0.7.2' in line and '(deleted)' not in line for line in maps.splitlines())
dev=Path('/sys/bus/platform/devices/ac10000.icp');m=json.loads((dev/'m2m_status').read_text());c=json.loads((dev/'state').read_text())
assert m['completed']==m['jobs']==m['direct_completed']==transaction['ipe_after']['completed']
assert not any(m[k] for k in ['failed','cancelled','first_error','users','running','fatal','pinned','orphans'])
assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','watchdogs','protocol_errors','cleanup_error','pc_error'])
pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']};assert all(x=='suspended' for x in pm.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(stage=440,packages=versions,modules=modules,installed_runtime_files_verified=len(proof['installed_files']),private_profiles={row['model']:row['new_sha256'] for row in proof['profiles']},services=services,pm=pm,m2m=m,core=c,default_automatic_audit=rows,default_suite=suite,pipewire=transaction['pipewire'],kernel_image_and_board_unchanged=True,boot_revalidation_performed=False,offline_rollback_present=True,current_boot_guard_matches=True,taint=0,new_faults=0,installed=True,full_goal_complete=False,passed=True)))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=50);q.check_returncode();raw=json.loads(q.stdout);(P/'current-device-private.json').write_bytes(q.stdout)
report=dict(raw)
for row in report['default_automatic_audit']:row.pop('case_root',None)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['default_suite','core','private_profiles']},indent=2))
