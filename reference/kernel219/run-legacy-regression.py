from pathlib import Path
import host,json,sys

here=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1] in ['dark-raw','white-rgb']
test=sys.argv[1]
assert json.loads((here/'module-reload-validation.json').read_text())['new_sensor_module_installed']
original=(here.parent/'kernel214/run-camera-probe.py').read_text()
code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("base=Path('/var/lib/samurai/k214-baseline')","base=Path('/var/lib/samurai/k219-baseline')")
code=code.replace("out=Path('/var/lib/samurai/k214-'+tag)","out=Path('/var/lib/samurai/k219-legacy-'+tag)")
code=code.replace('report=dict(stage=214,','report=dict(stage=219,new_driver_old_boot_frequencies=True,')
code=code.replace('__MODE__',repr('system')).replace('__TEST__',repr(test))
compile(code,'native-legacy-mode219','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=110)
(host.PRIVATE/('legacy-'+test+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
assert report['program_exit']==0 and report['taint']==0 and not any(report['fault_delta'].values()) and report['camera_devices_suspended']
if test=='white-rgb':assert len(report['frames'])==6 and all(f['byte_min']==f['byte_max']==254 for f in report['frames'])
else:assert len(report['frames'])==6 and all(not f['all_zero'] for f in report['frames']) and all(f['changed_fraction']>0 for f in report['frames'][1:])
(here/('legacy-'+test+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='frames'}))
