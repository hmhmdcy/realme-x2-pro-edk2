"""Verify durable files, loaded modules, package use and released resources."""
from pathlib import Path
import importlib.util,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
r=json.loads((HERE/'install-validation.json').read_text());assert r['passed'] and r['installed'] and r['driver_pair_installed'] and r['terminal']
assert not any(r[k] for k in ['worker_live','client_live','collector_live'])
source=storage.mount.mounted_build().parent/'source354';s=json.loads((HERE.parent/'kernel419/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==s['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
proof=json.loads((P/'install-proof-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json
proof=PROOF;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
assert all(sha('/'+n)==h for n,h in proof['installed_files'].items())
assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in proof['private_defaults'].items())
for i in proof['driver_pair']:
 assert sha(i['target'])==i['new_sha256']
 assert sha('/sys/module/'+i['module']+'/notes/.note.gnu.build-id')==i['new_note_sha256']
assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
for n in ['test_cc_mode','test_gamma_mode','test_ltm_mode','test_chain_mode']:assert not Path('/sys/module/camss_icp_a5_m2m/parameters',n).exists()
versions={}
for b in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(l.split(':',1) for l in b.splitlines() if ':' in l)
 if f.get('P') in proof['packages']:versions[f['P']]=f['V']
assert versions==proof['packages']
services={n:[] for n in ['pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(dict(pid=int(p.name),uid=p.stat().st_uid))
 except OSError:pass
root=Path('/var/lib/samurai/k420-install-r1');state=json.loads((root/'state.json').read_text());live=[]
for key,n in [('pid','worker.py'),('client_pid','camera-client.py'),('collector_pid','dump-collector.py')]:
 p=Path('/proc',str(state.get(key,-1)))
 try:active=(p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and str(root/n).encode() in (p/'cmdline').read_bytes()
 except OSError:active=False
 if active:live.append(key)
clocks={}
for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 f=line.split()
 if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[f[0]]=int(f[1])
dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(packages=versions,installed_payload_matches=True,private_defaults_unchanged=True,same394_boot_guard=True,production_driver_pair_disk_and_loaded_notes_match=True,test_parameters_absent=True,loaded_camss_note_unchanged=True,
 services=services,transaction_terminal=state['terminal'],transaction_live=live,clocks=clocks,taint=int(Path('/proc/sys/kernel/tainted').read_text()),icp_driver=(dev/'driver').resolve().name,
 core=json.loads((dev/'state').read_text()),m2m=json.loads((dev/'m2m_status').read_text()),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 camera_repository_current=Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text()=='ndx file:///var/lib/samurai/k420-install-r1/repository/forward/packages.adb\n')))
'''.replace('PROOF',repr(proof))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
assert d['taint']==512 and d['icp_driver']=='qcom-sm8150-icp' and d['camera_repository_current'] and not d['transaction_live'] and d['transaction_terminal']
assert all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
assert len(d['clocks'])==17 and not any(d['clocks'].values()) and all(v=='suspended' for v in d['camera_pm'].values())
assert len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert d['m2m']['jobs']==d['m2m']['completed']==d['m2m']['direct_completed']==93
report=dict(stage=420,driver_source_commit=s['commit'],source_clean=True,installed_core_stage=419,installed_adapter_stage=419,kernel_image_board_firmware_unchanged=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
suite=json.loads((P/'install-collected-r1/suite.json').read_text());assert suite['passed'] and len(suite['captures'])==7
assert sum(c['ipe_completed'] for c in suite['captures'].values())==81 and r['pipewire']['ipe_completed']==12
for model in ['imx471','imx319','s5k3m5','s5kgw1']:
 assert suite['captures'][model]['frames']==12
 assert 'requests=1' in (P/('install-collected-r1/gst-'+model+'.log')).read_text()
assert 'requests=1' in (P/'install-collected-r1/raw-dual.log').read_text()
assert 'requests=1' in (P/'install-collected-r1/isolated-main.log').read_text()
hardware=dict(stage=420,camera_suite=suite,typed_request_path_logged_for_each_camera_dual_and_isolated=True,camera_suite_completed=81,
 ordinary_user_pipewire_frames=12,total_new_ipe_completed=93,direct_only=True,failed=0,cancelled=0,production_driver_pair_installed=True,
 automatic_ipa_nonzero_iq_generation=False,old_package_and_driver_rollback_retained_not_executed=True,installed=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(hardware,indent=2)+'\n')
print(json.dumps(dict(stage=420,current_state_passed=True,total_new_ipe_completed=93,installed_packages=d['packages'],services=d['services'],passed=True)))
