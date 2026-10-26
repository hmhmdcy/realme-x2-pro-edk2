from pathlib import Path
import host,json,statistics
here=Path(__file__).resolve().parent
tests={name:json.loads((here/('system-gain-raw-'+name+'-validation.json')).read_text()) for name in ['0-a','800-a','960-a','0-b']}
for result in tests.values():assert result['program_exit']==0 and len(result['frames'])==6 and result['taint']==0 and not any(result['fault_delta'].values()) and result['camera_devices_suspended'] and result['test_patterns_and_sensor_controls_restored'] and result['media_graph_restored_byte_exact']
noise={name:statistics.median(frame['stddev'] for frame in result['frames'][2:]) for name,result in tests.items()}
assert noise['800-a']>1.8*noise['0-a'] and noise['960-a']>2*noise['800-a'] and noise['0-b']<1.3*noise['0-a']
assert all(60<frame['mean']<70 and not frame['all_zero'] for result in tests.values() for frame in result['frames'])
clients=json.loads((here/'default-clients-validation.json').read_text());assert all(result['exit']==0 and result['frames']==6 for result in clients['clients'].values())
report=dict(stage=216,kernel_gain_max_extended_to_own_factory_limit=True,register_codes=[0,800,960],nominal_factory_gains=[1.0,1024/224,16.0],gain_raw_noise_response_verified=True,settled_raw_stddev_medians=noise,first_two_frames_excluded_from_noise_comparison_but_retained_in_evidence=True,first_frame_can_retain_previous_gain_response=True,return_to_low_gain_noise_verified=True,actual_photo_sensitivity_ratio_not_calibrated=True,controls_and_media_graph_restored=True,no_flash_or_external_illumination=True,standard_manual_gain_api_not_accepted=True,full_image_quality_and_rear_cameras_not_accepted=True)
(here/'gain-acceptance-validation.json').write_text(json.dumps(report,indent=2)+'\n')
original=(here.parent/'kernel214/final-health.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("out=root/'k214-final-health'","out=root/'k216-final-health'").replace("base=root/'k214-baseline'","base=root/'k216-baseline'")
code=code.replace("original=json.loads((base/'products-before-private.json').read_text())","original=json.loads((root/'k214-baseline/products-before-private.json').read_text())")
code=code.replace("if name.lstrip('/') not in paths:","if name.lstrip('/') not in paths and not name.endswith('/kernel/drivers/media/i2c/imx471.ko'):")
old="wp=Path('/proc',str(policy['new_pid']));assert (wp/'comm').read_text().strip()=='wireplumber' and 'libcamera.so' in (wp/'maps').read_text()"
new="""wp=[p for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'comm').exists() and (p/'comm').read_text().strip()=='wireplumber'];assert len(wp)==1;wp=wp[0]
assert 'libcamera.so' in (wp/'maps').read_text()
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()==__MODULE_HASH__
assert json.loads((root/'k216-driver-test-r2/transition-state-private.json').read_text())['state']=='verified'"""
assert old in code;code=code.replace(old,new)
code=code.replace('stage=214,same_boot_after_package_upgrade=True,','stage=216,same_boot_after_sensor_hot_reload=True,only_sensor_module_changed=True,kernel_gain_max=960,')
code=code.replace('__MODULE_HASH__',repr(json.loads((here/'imx471-module-build-validation.json').read_text())['module_sha256']))
compile(code,'native-final-health216','exec');p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
result=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(report));print(json.dumps(result))
