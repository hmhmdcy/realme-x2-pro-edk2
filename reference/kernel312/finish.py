"""Save scoped six-mode coverage, current source identity and final resource state."""
from pathlib import Path
import difflib,hashlib,json,re,shlex,yaml
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
base=json.loads((HERE/'default-r2-validation.json').read_text())
front=json.loads((HERE/'default-r3-validation.json').read_text())
recovery=json.loads((HERE/'default-r7-validation.json').read_text())
if not front['passed'] or not recovery['passed']:raise RuntimeError('Inspect incomplete results')
modes={label:{'run':'r2',**s} for label,s in base['sensors'].items() if label!='imx471-1928x1088'}
modes['imx471-1928x1088']={'run':'r3',**front['sensors']['imx471-1928x1088']}
coverage={'stage':312,'modes':modes,'normal_default_frames':sum(s['frames'] for s in modes.values()),
          'camera_start_without_controls':True,'standard_sensor_config_and_ipa_config_path':True,
          'normal_scope':'Five modes fromr2 plus targeted front correction fromr3; unrelated passing modes reused',
          'recovery_evidence':'default-r7-validation.json','product_userspace_installed':False}
coverage['passed']=len(modes)==6 and all(not s['errors'] and all(e['final8_within_0_01_of_target'] and e['final8_sensor_controls_stable'] and e['locked_frames']>=8 for e in s['epochs']) for s in modes.values())
(HERE/'mode-coverage-validation.json').write_text(json.dumps(coverage,indent=2)+'\n')
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
changed={'camss.mojom':'include/libcamera/ipa/camss.mojom','ipa/camss.cpp':'src/ipa/camss-vfe/camss.cpp','pipeline/camss_vfe.cpp':'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'}
digests={};patch=[]
for local,target in changed.items():
    raw=(HERE/local).read_bytes()
    if raw!=(SDK/target).read_bytes():raise RuntimeError('SDK differs: '+target)
    digests[target]=hashlib.sha256(raw).hexdigest()
    patch.extend(difflib.unified_diff((HERE.parent/'kernel311'/local).read_text().splitlines(True),raw.decode().splitlines(True),fromfile='a/'+target,tofile='b/'+target))
(HERE/'mode-default-recovery.patch').write_text(''.join(patch))
artifacts=['output/src/libcamera/libcamera.so.0.7.2','output/src/ipa/camss-vfe/ipa_camss_vfe.so','output/src/libcamera/proxy/worker/camss_ipa_proxy']
source={'stage':312,'sdk_tree':str(SDK),'changed_source_sha256':digests,
        'candidate_sha256':{p:hashlib.sha256((SDK/p).read_bytes()).hexdigest() for p in artifacts},
        'profiles_sha256':{m:hashlib.sha256((HERE/(m+'.yaml')).read_bytes()).hexdigest() for m in ['s5kgw1','imx471','imx319','s5k3m5']},
        'kernel_source_and_module_stage':309,'system_install':False,'profile_catalog_version':2,
        'primary_sensor_config_reference':'https://docs.libcamera.org/master/public-api/classlibcamera_1_1CameraConfiguration.html',
        'kernel_dt_sensor_sources_changed':False}
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
pids=set()
for filename in ['delay-r1-results.json']+['joint-r'+str(n)+'-results.json' for n in range(1,8)]:
    data=json.loads((host.PRIVATE/filename).read_text());pids.add(data['state']['pid']);pids.add(data['state'].get('child_pid',-1))
    for text in data['logs'].values():pids.update(map(int,re.findall(r'(?:APPLICATION_PROCESS pid=|IPA init pid=|STEPPER_READY pid=)(\d+)',text)))
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
health.update(stage=312,health=recovery['capture']['health'],fault_delta=recovery['capture']['fault_delta'],
              consumers_unchanged=recovery['capture']['consumers_unchanged'],whole_system_healthy=False)
health['passed']=not health['live_stage_processes'] and health['same_boot'] and recovery['capture']['passed'] and health['loaded_camss_note_sha256']=='19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113'
(HERE/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
if not health['passed'] or not coverage['passed']:raise RuntimeError('Inspect health/coverage before updating current records')
for rel,prefix in [('linux-port/camera/kernel/source-lock.json','../../../'),('linux-port/camera/deployment-lock.json','../../')]:
    p=ROOT/rel;d=json.loads(p.read_text());e=lambda name:prefix+'reference/kernel312/'+name
    d.update(stage=312,current_camera_evidence=e('README.md'),final_health_evidence=e('final-health-validation.json'),
        current_boot_evidence=e('mode-coverage-validation.json'),inline_userspace_candidate_source=e('pipeline/camss_vfe.cpp'),
        inline_candidate_build_evidence=e('build-validation.json'),experimental_ipa_source_evidence=e('source-state.json'),candidate_pipeline_source_stage=312,
        experimental_sensor_mode_catalog_version=2,experimental_advertised_sensor_modes_supported=6,
        standard_sensor_config_mode_selection=True,standard_ipa_profile_lookup=True,default_hardware_ae_awb_with_empty_start_controls=True,
        hardware_awb_scope='Six currently advertised board modes: default AE/AWB; normal r2/r3 coverage and targeted120ms front1928 buffer-hold recovery r7; formal IQ and other modes remain incomplete',
        hardware_awb_evidence=e('mode-coverage-validation.json'),experimental_hardware_ae_scope='Six currently advertised modes; default controls and mode-scoped timing. Extra OEM modes, dynamic frame duration and formal calibration pending.',
        normal_default_stage312_frames=209,buffer_starvation_recovery_evidence=e('default-r7-validation.json'),
        additional_sensor_mode_timing_evidence=e('delay-r1-validation.json'),
        image_request_mapping_resync_supported=True,same_sensor_context_replaces_fixed_ae_statistics_age_limit=True,
        missing_statistics_frame_controls_recovered_from_confirmed_history=True,
        runtime_wb_control_scope='Four modes verified in311.312 updates pending request mapping after image gaps; manual WB timing across a gap is not independently verified. SOF event loss and invalid contexts can still require restart.',
        candidate_hardware_ae_real_frames_total=2576,
        candidate_hardware_ae_frame_count_scope='Accepted through311r2 plus312 selected six-mode209frames and recoveryr6/r7 65frames; failed experiments excluded',
        current_boot_tele_hardware_frames=1624,current_boot_tele_ae_frames=866,
        full_automatic_hardware_pipeline_ipa_incomplete_scope='Six board modes have default AE/AWB and selected buffer-gap recovery; product integration, AF/RAW compatibility, extra modes and formal IQ incomplete',
        goal_complete=False,current_adaptation_goal_status='active',whole_system_healthy=False)
    d['experimental_hardware_ae_verified_frames_by_sensor'].update({'s5kgw1_stage312':70,'imx471_stage312':132,'imx319_stage312':36,'s5k3m5_stage312':36})
    for model in ['s5kgw1','imx471','imx319','s5k3m5']:
        catalog=yaml.safe_load((HERE/(model+'.yaml')).read_text())
        d['experimental_sensor_profiles'][model].update(profile=e(model+'.yaml'),version=2,
            modes=[m['match'] for m in catalog['modes']],joint=e('mode-coverage-validation.json'))
        if len(catalog['modes'])>1:d['experimental_sensor_profiles'][model]['additional_mode_timing_evidence']=e('delay-r1-validation.json')
    if 'spectra_hardware_image_processing_supported_scope' in d:
        d['spectra_hardware_image_processing_supported_scope']='Six advertised board modes with standard sensorConfig, mode catalog and default AE/AWB; front buffer-hold recovery verified. Product RAW plus CPU ISP unchanged; full IQ and product hardware integration incomplete.'
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'source_stage':312,'six_mode_coverage_passed':coverage['passed'],'normal_frames':coverage['normal_default_frames'],'recovery_frames':33,'health_passed':health['passed']}))
