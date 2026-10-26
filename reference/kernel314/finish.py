"""Record the native dual-stream result without promoting product capabilities."""
from pathlib import Path
import hashlib,json,re,shlex
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
dual=json.loads((HERE/'dual-r5-validation.json').read_text())
assert dual['passed'] and set(dual['sensors'])=={'s5kgw1','imx471','imx319','s5k3m5'}
pids=set()
for run in ['r1','r2','r3','r4','r5']:
 d=json.loads((host.PRIVATE/('dual-'+run+'-results.json')).read_text());pids.add(d['state']['pid'])
 for text in d['logs'].values():pids.update(map(int,re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)))
code='''
from pathlib import Path
import hashlib,json
live=[]
for pid in PIDS:
 p=Path('/proc',str(pid),'stat')
 if p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z':live.append(pid)
consumers={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber']:consumers.setdefault(name,[]).append(int(p.name))
 except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps({'live_stage_processes':live,'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
 'loaded_camss_note_sha256':hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
 'taint':int(Path('/proc/sys/kernel/tainted').read_text()),'consumers':consumers,
 'platforms':{n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 'rails':{(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}}))
'''.replace('PIDS',repr(sorted(pids)))
health=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
health.update(stage=314,fault_delta=dual['capture']['fault_delta'],candidate_module_installed=False,whole_system_healthy=False)
health['passed']=not health['live_stage_processes'] and health['same_boot'] and not health['taint'] and health['loaded_camss_note_sha256']=='19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113' and set(health['consumers'])=={'pipewire','wireplumber'} and all(len(p)==1 for p in health['consumers'].values()) and all(s=='suspended' for s in health['platforms'].values()) and len(health['rails'])==9 and all(s=={'state':'disabled','users':0} for s in health['rails'].values())
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n');assert health['passed']
source=json.loads((HERE/'source-state.json').read_text())
frames=sum(s['frames'] for s in dual['sensors'].values())
for rel,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),('linux-port/camera/deployment-lock.json','../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());e=lambda name:prefix+'reference/kernel314/'+name
 d.update(stage=314,current_camera_evidence=e('README.md'),final_health_evidence=e('final-health-validation.json'),
  candidate_camss_streams_source_stage=314,candidate_camss_streams_source_tree=source['tree'],
  candidate_camss_streams_branch=source['branch'],candidate_camss_streams_commit=source['head'],
  candidate_camss_streams_source_evidence=e('source-state.json'),candidate_camss_streams_build_evidence=e('kernel-build-validation.json'),
  candidate_camss_streams_evidence=e('dual-r5-validation.json'),candidate_camss_streams_installed=False,
  native_raw_pix_parallel_verified=True,native_raw_pix_parallel_buffers=frames,
  native_raw_pix_parallel_scope='Per-camera RAW10 RDI plus640x480NV12 PIX on four current board modes; independent stop/restart and serial cross-camera reuse. Not four physical cameras streaming concurrently; not libcamera same-request RAW integration.',
  candidate_hardware_raw_compatibility=False,default_product_hardware_isp_selected=False,
  full_automatic_hardware_pipeline_ipa_incomplete_scope='312 six-mode default AE/AWB and313 main AF candidates preserved;314 native dual RDI/PIX lifecycle verified. libcamera RAW/multistream request pairing, metadata compatibility with314 module, product integration, extra modes and formal IQ remain incomplete.',
  goal_complete=False,current_adaptation_goal_status='active',whole_system_healthy=False)
 p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'stage':314,'native_dual_buffers':frames,'health_passed':health['passed'],'candidate_commit':source['head'],'userspace_source_stage':313,'goal_complete':False}))
