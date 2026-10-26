"""Save source identity, scoped health and current experiment records."""
from pathlib import Path
import difflib,hashlib,json,re,shlex
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
changed={'camss.mojom':'include/libcamera/ipa/camss.mojom','ipa/camss.cpp':'src/ipa/camss-vfe/camss.cpp','pipeline/camss_vfe.cpp':'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'}
digests={};patch=[]
for local,target in changed.items():
    raw=(HERE/local).read_bytes()
    if raw!=(SDK/target).read_bytes():raise RuntimeError('SDK source differs: '+target)
    digests[target]=hashlib.sha256(raw).hexdigest()
    patch.extend(difflib.unified_diff((HERE.parent/'kernel308'/local).read_text().splitlines(True),raw.decode().splitlines(True),fromfile='a/'+target,tofile='b/'+target))
(HERE/'runtime-controls.patch').write_text(''.join(patch))
artifacts=['output/src/libcamera/libcamera.so.0.7.2','output/src/ipa/camss-vfe/ipa_camss_vfe.so','output/src/libcamera/proxy/worker/camss_ipa_proxy']
source={'stage':311,'sdk_tree':str(SDK),'changed_source_sha256':digests,
        'candidate_sha256':{p:hashlib.sha256((SDK/p).read_bytes()).hexdigest() for p in artifacts},
        'kernel_source_and_module_stage':309,'system_install':False,'profile_base_stage':310,
        'primary_control_semantics':'https://docs.libcamera.org/master/internal-api/namespacelibcamera_1_1controls.html',
        'kernel_dt_sensor_sources_changed':False}
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
pids=set()
for run in ['r1','r2']:
    data=json.loads((host.PRIVATE/('runtime-'+run+'-results.json')).read_text());pids.add(data['state']['pid'])
    for text in data['logs'].values():pids.update(map(int,re.findall(r'(?:APPLICATION_PROCESS pid=|IPA init pid=)(\d+)',text)))
code=r'''
from pathlib import Path
import hashlib,json
live=[]
for pid in PIDS:
    p=Path('/proc',str(pid))
    try:
        if (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':live.append(pid)
    except FileNotFoundError:pass
print(json.dumps({'live_stage_processes':live,'same_boot':Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),
 'loaded_camss_note_sha256':hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()}))
'''.replace('PIDS',repr(sorted(pids)))
health=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
result=json.loads((HERE/'runtime-r2-validation.json').read_text())
health.update(stage=311,health=result['capture']['health'],fault_delta=result['capture']['fault_delta'],
              consumers_unchanged=result['capture']['consumers_unchanged'],whole_system_healthy=False)
health['passed']=not health['live_stage_processes'] and health['same_boot'] and result['capture']['passed'] and health['loaded_camss_note_sha256']=='19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113'
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
if not health['passed'] or not result['passed']:raise RuntimeError('Inspect results before updating current records')
for rel,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),('linux-port/camera/deployment-lock.json','../../')]:
    p=ROOT/rel;d=json.loads(p.read_text());e=lambda name:prefix+'reference/kernel311/'+name
    d.update(stage=311,current_camera_evidence=e('README.md'),final_health_evidence=e('final-health-validation.json'),
        current_boot_evidence=e('runtime-r2-validation.json'),inline_userspace_candidate_source=e('pipeline/camss_vfe.cpp'),
        inline_candidate_build_evidence=e('build-validation.json'),experimental_ipa_source_evidence=e('source-state.json'),
        candidate_pipeline_source_stage=311,runtime_awb_enable_and_manual_colour_gains_implemented=True,
        runtime_wb_control_evidence=e('runtime-r2-validation.json'),runtime_wb_stage311_accepted_frames=394,
        runtime_wb_requested_image_sof_matched_controls=12,runtime_wb_physical_domains_aligned=64,
        runtime_wb_unique_quantization_frames=390,runtime_wb_rounded_log_ambiguous_frames=4,
        runtime_wb_control_scope='Four current modes with continuous image/request mapping and timely parameter service; image mapping change rejects further ISP requests until restart; backlog/starvation recovery and other modes pending',
        runtime_wb_initial_early_application_failure=e('runtime-r1-validation.json'),
        current_boot_tele_hardware_frames=1588,current_boot_tele_ae_frames=830,
        candidate_hardware_ae_real_frames_total=2302,candidate_hardware_ae_frame_count_scope='Accepted AE experiments through311r2; rejected311r1 request-timing experiment retained separately',
        hardware_awb_evidence=e('runtime-r2-validation.json'),goal_complete=False,whole_system_healthy=False)
    d['experimental_hardware_ae_verified_frames_by_sensor'].update({
        's5kgw1_current_boot_runtime_stage311':97,'imx471_current_boot_runtime_stage311':103,
        'imx319_current_boot_runtime_stage311':99,'s5k3m5_current_boot_runtime_stage311':95})
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'source_stage':311,'deployed_camss_stage':309,'runtime_controls_passed':result['passed'],'health_passed':health['passed']}))
