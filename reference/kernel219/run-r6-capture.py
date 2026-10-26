"""Use the graph-restoring capture harness with full r6 or installed libraries."""
from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==8
phase,kind,pattern,width,height,cell,configuration=sys.argv[1:]
assert phase in ['isolated-r6','installed-r6'] and configuration in ['default','full']
assert kind in ['raw','rgb'] and pattern in ['0','2']
assert (width,height,cell) in [('2304','1728','1'),('2296','1728','1'),('4608','3456','2')]
assert configuration=='default' or width=='4608'
tag=f'{phase}-{width}x{height}-{kind}-pattern{pattern}-{configuration}'
code=(here/'native-mode-runner.py').read_text().replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'",'tag='+repr(tag))
if phase=='isolated-r6':
 code=code.replace("prefix=Path('/run/samurai-camera219-cpu')","prefix=Path('/run/samurai-camera219-r6')")
 code=code.replace("prefix/'config-enabled'", "prefix/"+repr('config-'+configuration))
 code=code.replace("LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera',LIBCAMERA_IPA_CONFIG_PATH='/usr/share/libcamera/ipa'", "LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa')")
 library='candidate'
else:
 library='system'
 if configuration=='full':
  needle='def demote():'
  assert code.count(needle)==1;code=code.replace(needle,"env['XDG_CONFIG_HOME']='/run/samurai-camera219-r6/config-full'\n"+needle)
code=code.replace('report=dict(stage=219,',"report=dict(stage=219,test_pattern_not_colour_calibration=pattern==2,package_test_phase="+repr(phase)+",configuration_test="+repr(configuration)+",")
compile(code,'r6-capture','exec')
p=host.ssh('python3 - '+' '.join([kind,pattern,width,height,cell,library]),input=code.encode(),timeout=100)
(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(tag+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='frames'}))
assert report['program_exit']==0 and len(report['frames'])==6 and report['stream_geometry']['width']==int(width) and report['stream_geometry']['height']==int(height)
assert report['all_formats_restored'] and report['media_graph_restored'] and report['sensor_controls_restored'] and not report['restore_errors']
assert report['camera_devices_suspended'] and report['taint']==0 and not any(report['fault_delta'].values())
if kind=='rgb':assert 'system' in report['dma_exporters_observed']
if kind=='raw' or pattern!='0':assert all(not f['all_zero'] for f in report['frames'])
if kind=='raw' and pattern=='0':assert all(f['stddev']>0 and f['changed_fraction']>0 for f in report['frames'][1:])
