"""Record the scoped AF change and carry forward unchanged camera baselines."""
from pathlib import Path
import difflib,hashlib,json,re,shlex
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
scan=json.loads((HERE/'af-scan-r3-validation.json').read_text())
cancel=json.loads((HERE/'af-cancel-r2-validation.json').read_text())
assert scan['passed'] and scan['optical_focused'] and cancel['passed']
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
assert json.loads((HERE/'ipa-contract-validation.json').read_text())['passed']
changed={'camss.mojom':'include/libcamera/ipa/camss.mojom',
 'ipa/camss.cpp':'src/ipa/camss-vfe/camss.cpp',
 'pipeline/camss_vfe.cpp':'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp',
 'pipeline/hardware_focus.h':'src/libcamera/pipeline/camss-vfe/hardware_focus.h'}
patch=[];digests={}
for local,target in changed.items():
 raw=(HERE/local).read_bytes();assert raw==(SDK/target).read_bytes(),target
 digests[target]=hashlib.sha256(raw).hexdigest()
 base=HERE.parent/'kernel312'/local
 patch.extend(difflib.unified_diff(base.read_text().splitlines(True) if base.exists() else [],raw.decode().splitlines(True),fromfile='a/'+target,tofile='b/'+target))
patch.extend(difflib.unified_diff((HERE.parent/'kernel312/s5kgw1.yaml').read_text().splitlines(True),(HERE/'s5kgw1.yaml').read_text().splitlines(True),fromfile='a/src/ipa/camss-vfe/data/s5kgw1.yaml',tofile='b/src/ipa/camss-vfe/data/s5kgw1.yaml'))
(HERE/'hardware-af.patch').write_text(''.join(patch))
source={'stage':313,'sdk_tree':str(SDK),'changed_source_sha256':digests,
 'scan_evidence_build_attempt':5,'final_build_attempt':json.loads((HERE/'build-validation.json').read_text())['attempt'],
 'post_scan_delta':'Skip AF processing and lens commands while stopped; optical search algorithm unchanged. Final build and targeted cancellation/stop rechecked.',
 'reused_contrast_af_sha256':hashlib.sha256((SDK/'src/ipa/libipa/contrast_af.h').read_bytes()).hexdigest(),
 'reused_contrast_af_origin':'linux-port/packages/libcamera/0028-simple-contrast-autofocus.patch',
 'main_af_profile_sha256':hashlib.sha256((HERE/'s5kgw1.yaml').read_bytes()).hexdigest(),
 'kernel_dt_sensor_sources_changed':False,'kernel_source_and_module_stage':309,
 'system_install':False,'raw_compatibility_in_hardware_handler':False,
 'optical_scope':'One scene; main4608x3456 to640x480NV12. Auto start/coarse/fine/verify/cancel. No continuous or dioptre map; no VFE BAF.'}
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
pids=set()
for kind,run in [('af-scan','r1'),('af-scan','r2'),('af-scan','r3'),('af-cancel','r1'),('af-cancel','r2')]:
 data=json.loads((host.PRIVATE/(kind+'-'+run+'-results.json')).read_text())
 pids.update([data['state']['pid'],data['state'].get('child_pid',-1)])
 for text in data['logs'].values():pids.update(map(int,re.findall(r'(?:APPLICATION_PROCESS pid=|IPA init pid=)(\d+)',text)))
code='''
from pathlib import Path
import json
live=[]
for pid in PIDS:
 p=Path('/proc',str(pid),'stat')
 if p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z':live.append(pid)
print(json.dumps({'live_stage_processes':live,'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()}))
'''.replace('PIDS',repr(sorted(pids)))
health=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
health.update(stage=313,health=cancel['capture']['health'],fault_delta=cancel['capture']['fault_delta'],
 consumers_unchanged=cancel['capture']['consumers_unchanged'],whole_system_healthy=False)
health['passed']=not health['live_stage_processes'] and health['same_boot'] and cancel['capture']['passed']
assert health['passed']
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
for rel,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),('linux-port/camera/deployment-lock.json','../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());e=lambda name:prefix+'reference/kernel313/'+name
 d.update(stage=313,current_camera_evidence=e('README.md'),final_health_evidence=e('final-health-validation.json'),
  current_boot_evidence=e('af-scan-r3-validation.json'),inline_userspace_candidate_source=e('pipeline/camss_vfe.cpp'),
  inline_candidate_build_evidence=e('build-validation.json'),experimental_ipa_source_evidence=e('source-state.json'),
  candidate_pipeline_source_stage=313,candidate_hardware_single_auto_af_verified=True,
  candidate_hardware_af_scope=source['optical_scope'],candidate_hardware_af_evidence=e('af-scan-r3-validation.json'),
  candidate_hardware_af_cancel_evidence=e('af-cancel-r2-validation.json'),candidate_hardware_af_verified_frames=scan['image_frames']+cancel['image_frames'],
  candidate_hardware_af_metric=scan['metric'],candidate_hardware_af_continuous=False,
  candidate_hardware_raw_compatibility=False,current_boot_auto_af_retest_pending=False,
  current_boot_auto_af_retest_scope='313 isolated hardware candidate only; installed RAW/CPU product AF not retested',
  current_boot_product_raw_cpu_auto_af_retest_pending=True,
  full_automatic_hardware_pipeline_ipa_incomplete_scope='Six board modes default AE/AWB inherited312; main hardware-NV12 single Auto AF/cancel313. RAW compatibility, product integration, extra modes and formal IQ incomplete.',
  goal_complete=False,current_adaptation_goal_status='active',whole_system_healthy=False)
 for model in ['s5kgw1','imx471','imx319','s5k3m5']:
  d['experimental_sensor_profiles'][model]['profile']=e(model+'.yaml')
 p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'stage':313,'scan_frames':scan['image_frames'],'cancel_frames':cancel['image_frames'],'focused_dac':scan['moves'][-1]['position'],'health_passed':health['passed'],'goal_complete':False}))
