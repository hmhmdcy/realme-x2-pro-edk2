"""Close only the tested source/core change and its two distinct runtime epochs."""
from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
normal=json.loads((HERE/'normal-install-validation.json').read_text());fault=json.loads((HERE/'fault-experiment-validation.json').read_text())
assert normal['state']['passed'] and normal['state']['installed'] and fault['experiment_passed']
assert not any(normal[k] for k in ['worker_live','client_live','collector_live'])
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';expected=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==expected['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
assert 'CAMSS_A5_TEST_DROP_FRAME_ACK' not in (source/'drivers/media/platform/qcom/camss/camss-icp-a5-boot.c').read_text()
meta=json.loads((P/'manifest-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json
meta=META;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
assert sha(meta['core_target'])==meta['new_core_sha256']
assert sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta['new_core_note_sha256']
assert all(sha(n)==h for n,h in meta['other_files'].items())
for n,h in meta['unchanged_notes'].items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h
assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
transactions={}
for name in ['k395-ack-loss-r1','k395-normal-install-r2']:
 root=Path('/var/lib/samurai',name);s=json.loads((root/'state.json').read_text());live=[]
 for k,names in [('pid',['worker.py']),('client_pid',['pipeline-fixture','ack-loss-client']),('collector_pid',['dump-collector.py'])]:
  p=Path('/proc',str(s.get(k,-1)))
  try:active=(p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and any(str(root/n).encode() in (p/'cmdline').read_bytes() for n in names)
  except OSError:active=False
  if active:live.append(k)
 assert sha(root/'backup/normal393-core.ko')==meta['old_core_sha256']
 transactions[name]=dict(terminal=s['terminal'],live=live,passed=s['passed'],old393_backup_matches=True)
services={n:[] for n in ['pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(dict(pid=int(p.name),uid=p.stat().st_uid))
 except OSError:pass
clocks={}
for l in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 f=l.split()
 if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[f[0]]=int(f[1])
versions={}
for b in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(l.split(':',1) for l in b.splitlines() if ':' in l)
 if f.get('P') in ['libcamera','libcamera-gstreamer','libcamera-ipa','libcamera-tools','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:versions[f['P']]=f['V']
dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(normal395_disk_and_loaded_note_match=True,adapter393_and_camss389_unchanged=True,private_profiles_unchanged=True,test_knobs_absent=True,transactions=transactions,services=services,packages=versions,clocks=clocks,m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))})))
'''.replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
assert d['m2m']['jobs']==d['m2m']['completed']==d['m2m']['direct_completed']==48 and d['m2m']['starts']==d['m2m']['stops']==4
assert not d['taint'] and not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert len(d['clocks'])==17 and not any(d['clocks'].values()) and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert all(v=='suspended' for v in d['camera_pm'].values()) and all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
assert all(v['terminal'] and not v['live'] for v in d['transactions'].values())
assert d['packages']==json.loads((HERE.parent/'kernel391/current-state-validation.json').read_text())['packages']
report=dict(stage=395,current_boot_guard_stage=394,normal_driver_source_commit=expected['commit'],source_clean=True,production_test_macro_absent=True,normal_camera_recovery_passed=True,ack_loss_complete_recovery_passed=True,prior394_failure_preserved=True,precise394_reboot_cause_still_unproven=True,only_production_core_replaced=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
expected['installed']=True;(HERE/'source-state.json').write_text(json.dumps(expected,indent=2)+'\n')
print(json.dumps(dict(current_normal_state_passed=True,ack_loss_recovery_passed=True,normal_camera_frames=48,services=d['services'],transactions=d['transactions'])))
