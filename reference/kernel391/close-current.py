"""Verify the changed userspace and its released resources; reuse390 boot proof."""
from pathlib import Path
import importlib.util,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'install-r2-validation.json').read_text())['passed']
source=storage.mount.mounted_build().parent/'source354'
candidate=json.loads((HERE.parent/'kernel389/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==candidate['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
proof=json.loads((P/'install-proof-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json
proof=PROOF;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==proof['camss_note_sha256']
assert all(sha('/'+n)==h for n,h in proof['installed_files'].items())
assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in proof['private_defaults'].items())
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
workers=[]
for attempt in ['r1','r2']:
 root=Path('/var/lib/samurai/k391-install-'+attempt);s=json.loads((root/'state.json').read_text());live=[]
 for key,needle in [('pid','worker.py'),('client_pid','camera-client.py'),('collector_pid','dump-collector.py')]:
  p=Path('/proc',str(s.get(key,-1)))
  try:active=(p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and str(root/needle).encode() in (p/'cmdline').read_bytes()
  except OSError:active=False
  if active:live.append(key)
 workers.append(dict(attempt=attempt,terminal=s['terminal'],live=live))
clocks={}
for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 f=line.split()
 if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[f[0]]=int(f[1])
dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(packages=versions,installed_payload_matches=True,private_defaults_unchanged=True,same390_boot_guard=True,loaded_camss_note_unchanged=True,
 services=services,workers=workers,clocks=clocks,taint=int(Path('/proc/sys/kernel/tainted').read_text()),icp_driver=(dev/'driver').resolve().name,
 icp_state=json.loads((dev/'state').read_text()),m2m=json.loads((dev/'m2m_status').read_text()),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 camera_repository_current=Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text()=='ndx file:///var/lib/samurai/k391-install-r2/repository/forward/packages.adb\n')))
'''.replace('PROOF',repr(proof))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
assert not d['taint'] and d['icp_driver']=='qcom-sm8150-icp' and d['camera_repository_current']
assert all(r['terminal'] and not r['live'] for r in d['workers'])
assert all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
assert len(d['clocks'])==17 and not any(d['clocks'].values()) and all(v=='suspended' for v in d['camera_pm'].values())
assert len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert not any(d['icp_state'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','first_error'])
report=dict(stage=391,driver_source_commit=candidate['commit'],source_clean=True,kernel_and_board_unchanged_from390=True,kernel_evidence_reused='../kernel390/current-state-validation.json',**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
r1=json.loads((HERE/'install-r1-validation.json').read_text());r2=json.loads((HERE/'install-r2-validation.json').read_text());suite=json.loads((P/'install-collected-r1/suite.json').read_text())
frames=sum(r['ipe_completed'] for r in suite['captures'].values())
assert frames==r1['ipe_after_suite']['completed']-r1['ipe_before']['completed']==82
assert r2['ipe_after']['completed']-r2['ipe_before']['completed']==r2['pipewire']['ipe_completed']==12
hardware=dict(stage=391,camera_suite=suite,camera_suite_reused_without_rerun_in_r2=True,r1_camera_suite_completed=frames,r2_pipewire_frames=12,total_new_ipe_completed=94,direct_only=True,failed=0,cancelled=0,installed=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(hardware,indent=2)+'\n')
print(json.dumps(dict(current_state_passed=True,total_new_ipe_completed=94,installed_packages=d['packages'],m2m=d['m2m'],services=d['services'])))
