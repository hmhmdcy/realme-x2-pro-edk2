from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==3 and sys.argv[1] in ['0','800','960'] and sys.argv[2] in ['a','b']
gain_code=int(sys.argv[1]);mode='system';test='gain-raw-'+sys.argv[1]+'-'+sys.argv[2];tag=mode+'-'+test
assert json.loads((here/'module-reload-validation.json').read_text())['new_module_unload_reload_and_static_bind_verified']
original=(here.parent/'kernel214/run-camera-probe.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("base=Path('/var/lib/samurai/k214-baseline')","base=Path('/var/lib/samurai/k216-baseline')")
code=code.replace("out=Path('/var/lib/samurai/k214-'+tag)","out=Path('/var/lib/samurai/k216-'+tag)")
code=code.replace("else 'raw-dark-sync-probe'","else 'raw-gain-sync-probe'")
code=code.replace("probes=Path('/run/samurai-camera214-probes')","probes=Path('/run/samurai-camera216-probes')")
code=code.replace("source=stage/'probes'/probe_name;probe=probes/probe_name","source=base/probe_name;probe=probes/probe_name")
code=code.replace("kind,'4' if white else '0']","kind,'4' if white else '0',str(__GAIN__)]")
code=code.replace('stage=214,mode=mode,test=test,','stage=216,mode=mode,test=test,analogue_gain_code=__GAIN__,nominal_factory_gain=1024/(1024-__GAIN__),sensitivity_calibration_not_claimed=True,')
code=code.replace('__GAIN__',str(gain_code)).replace('__MODE__',repr(mode)).replace('__TEST__',repr(test));compile(code,'native-gain-probe216','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=110);(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(tag+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
assert report['program_exit']==0 and not report['timed_out'] and report['camera_devices_suspended'] and report['taint']==0 and not any(report['fault_delta'].values())
print(json.dumps(dict(gain_code=gain_code,frames=len(report['frames']),means=[f['mean'] for f in report['frames']],stddevs=[f['stddev'] for f in report['frames']],controls_and_graph_restored=report['test_patterns_and_sensor_controls_restored'] and report['media_graph_restored_byte_exact'],taint=report['taint'],fault_delta=report['fault_delta'])))
