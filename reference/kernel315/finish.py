"""Record the verified candidate and actual restored device state."""
from pathlib import Path
import json,re,shlex
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
reports=[json.loads((HERE/('raw-'+run+'-validation.json')).read_text()) for run in ['r1','r2','r3']]
assert all(d['passed'] for d in reports)
pids=set()
for run in ['r1','r2','r3']:
 d=json.loads((host.PRIVATE/('raw-'+run+'-results.json')).read_text());pids.add(d['state']['pid'])
 pids.add(d['state']['child_pid'])
 for name,text in d['logs'].items():
  if not name.startswith('capture-'):continue
  pids.update(map(int,re.findall(r'(?:APPLICATION_PROCESS pid=|IPA stats pid=)(\d+)',text)))
  pids.update(map(int,re.findall(r'\[[^\]]+\]\s+\[(\d+)\]',text)))
code='''
from pathlib import Path
import hashlib,json,os
live=[]
for pid in PIDS:
 p=Path('/proc',str(pid),'stat')
 if p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z':live.append(pid)
consumers={};stage_processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber']:consumers.setdefault(name,[]).append(int(p.name))
  cmd=(p/'cmdline').read_bytes()
  if int(p.name)!=os.getpid() and b'/var/lib/samurai/k315-raw-' in cmd and b'python3 -c' not in cmd:stage_processes.append(int(p.name))
 except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps({'live_stage_processes':live,'stage_path_processes':stage_processes,
 'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
 'loaded_camss_note_sha256':hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
 'taint':int(Path('/proc/sys/kernel/tainted').read_text()),'consumers':consumers,
 'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 'rails':{(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}}))
'''.replace('PIDS',repr(sorted(pids)))
health=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
faults={k:sum(d['capture']['fault_delta'][k] for d in reports) for k in reports[0]['capture']['fault_delta']}
health.update(stage=315,fault_delta=faults,candidate_module_installed=False,whole_system_healthy=False)
health['passed']=not health['live_stage_processes'] and not health['stage_path_processes'] and health['same_boot'] and not health['taint'] and not any(faults.values()) and health['loaded_camss_note_sha256']=='19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113' and set(health['consumers'])=={'pipewire','wireplumber'} and all(len(p)==1 for p in health['consumers'].values()) and all(s=='suspended' for s in health['platforms'].values()) and len(health['rails'])==9 and all(s=={'state':'disabled','users':0} for s in health['rails'].values())
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n');assert health['passed'],health
selections={name:s for d in reports for name,s in d['selections'].items()}
summary=dict(stage=315,requests=sum(s['frames'] for s in selections.values()),application_buffers=sum(s['images'] for s in selections.values()),
 correlated_requests=sum(s['paired_requests'] for s in selections.values()),max_pair_delta_ns=max(s['max_pair_delta_ns'] or 0 for s in selections.values()),
 selections=selections,health_evidence='final-health-validation.json',passed=True,system_installed=False,goal_complete=False)
(HERE/'coverage-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),('linux-port/camera/deployment-lock.json','../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());e=lambda name:prefix+'reference/kernel315/'+name
 d.update(stage=315,current_camera_evidence=e('README.md'),final_health_evidence=e('final-health-validation.json'),
  current_boot_evidence=e('final-health-validation.json'),candidate_pipeline_source_stage=315,
  inline_userspace_candidate_source=e('pipeline/camss_vfe.cpp'),inline_candidate_build_evidence=e('build-validation.json'),
  experimental_ipa_source_evidence=e('source-state.json'),inline_userspace_candidate_installed=False,
  candidate_hardware_raw_compatibility=True,candidate_hardware_raw_evidence=e('coverage-validation.json'),
  candidate_hardware_raw_scope='Six advertised modes dual RAW10+640x480NV12; four base modes RAW-only with internal PIX; software FRAME_SYNC correlation, no hardware frame-ID or exposure-time claim.',
  candidate_hardware_raw_requests=summary['correlated_requests'],candidate_hardware_raw_copy=False,
  candidate_hardware_raw_only_internal_pix=True,candidate_hardware_raw_same_request_verified=True,
  candidate_hardware_raw_af_verified=True,candidate_hardware_raw_af_evidence=e('raw-r3-validation.json'),
  candidate_hardware_raw_pair_max_delta_ns=summary['max_pair_delta_ns'],
  candidate_hardware_module_stage=314,candidate_hardware_automatic_pipeline_with_raw_verified=True,
  default_product_hardware_isp_selected=False,
  spectra_hardware_image_processing_supported_scope='315 candidate: six-mode RAW+NV12 default AE/AWB; four base RAW-only modes; main dual/RAW-only AF and cancel. Product remains RAW+CPU ISP; formal IQ incomplete.',
  full_automatic_hardware_pipeline_ipa_incomplete_scope='315 libcamera RAW-only and RAW+processed requests verified with314 kernel,313 IPA/AE/AWB/AF. Product packages/consumers, exposure timestamps, deliberate line desync/event-loss, extra modes and formal calibration remain incomplete.',
  goal_complete=False,current_adaptation_goal_status='active',whole_system_healthy=False)
 p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:summary[k] for k in ['stage','requests','application_buffers','correlated_requests','max_pair_delta_ns','goal_complete']}))
