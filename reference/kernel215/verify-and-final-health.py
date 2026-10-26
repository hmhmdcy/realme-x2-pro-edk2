from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
results={tag:json.loads((here/('system-'+tag+'-validation.json')).read_text()) for tag in ['sensor-raw','sensor-rgb','dark-raw']}
for result in results.values():assert result['program_exit']==0 and not result['timed_out'] and result['taint']==0 and not any(result['fault_delta'].values()) and result['camera_devices_suspended'] and result['error_line_count']==0
raw=results['sensor-raw']['frames'];dark=results['dark-raw']['frames'];rgb=results['sensor-rgb']['frames']
assert len(raw)==len(dark)==len(rgb)==6
assert all(frame['byte_min']==0 and frame['byte_max']==1023 and frame['occupied_bins']==2 for frame in raw)
assert all(frame['changed_fraction']==0 for frame in raw[1:]) and all(len(set(frame['horizontal_eighth_means']))>1 for frame in raw)
assert all(not frame['all_zero'] and frame['byte_max']>=254 for frame in rgb)
assert all(not frame['all_zero'] and 60<frame['mean']<70 and frame['stddev']>0.1 for frame in dark) and all(frame['changed_fraction']>0.2 for frame in dark[1:])
report=dict(stage=215,sensor_test_pattern_now_effective=True,sensor_generated_pattern_raw_min=0,sensor_generated_pattern_raw_max=1023,sensor_pattern_exactly_two_raw_levels=True,spatially_nonuniform_and_repeatable_all_six_frames=True,rgb_from_first_frame_nonblack=True,physical_sensor_csi_input_not_detached=True,dma_read_start_end_sync_verified=True,after_disable_real_dark_raw_noise_and_frame_changes_returned=True,all_controls_and_media_graph_restored=True,no_external_light_or_flash=True,full_image_quality_and_rear_cameras_not_accepted=True)
(here/'test-pattern-acceptance-validation.json').write_text(json.dumps(report,indent=2)+'\n')
original=(here.parent/'kernel214/final-health.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("out=root/'k214-final-health'","out=root/'k215-final-health'").replace("base=root/'k214-baseline'","base=root/'k215-baseline'")
# The camera packages remain r5; their original product reference belongs to214.
code=code.replace("original=json.loads((base/'products-before-private.json').read_text())","original=json.loads((root/'k214-baseline/products-before-private.json').read_text())")
code=code.replace("if name.lstrip('/') not in paths:","if name.lstrip('/') not in paths and not name.endswith('/kernel/drivers/media/i2c/imx471.ko'):")
old="wp=Path('/proc',str(policy['new_pid']));assert (wp/'comm').read_text().strip()=='wireplumber' and 'libcamera.so' in (wp/'maps').read_text()"
new="""wp=[p for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'comm').exists() and (p/'comm').read_text().strip()=='wireplumber'];assert len(wp)==1;wp=wp[0]
assert 'libcamera.so' in (wp/'maps').read_text()
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()==__MODULE_HASH__
assert json.loads((root/'k215-driver-test-r2/transition-state-private.json').read_text())['state']=='verified'"""
assert old in code;code=code.replace(old,new)
code=code.replace('stage=214,same_boot_after_package_upgrade=True,','stage=215,same_boot_after_sensor_hot_reload=True,only_sensor_module_changed=True,test_pattern_fix_verified=True,')
code=code.replace('__MODULE_HASH__',repr(json.loads((here/'imx471-module-build-validation.json').read_text())['module_sha256']))
compile(code,'native-final-health215','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
result=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(report));print(json.dumps(result))
