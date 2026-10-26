from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1] in ['sensor-raw','sensor-rgb','dark-raw']
assert json.loads((here/'module-reload-r2-validation.json').read_text())['new_module_unload_reload_and_static_bind_verified']
test=sys.argv[1];mode='system';tag=mode+'-'+test
original=(here.parent/'kernel214/run-camera-probe.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("base=Path('/var/lib/samurai/k214-baseline')","base=Path('/var/lib/samurai/k215-baseline')")
code=code.replace("out=Path('/var/lib/samurai/k214-'+tag)","out=Path('/var/lib/samurai/k215-'+tag)")
code=code.replace("kind=test.split('-')[1];white=test.startswith('white');tag=mode+'-'+test","kind=test.split('-')[1];white=False;sensor_pattern=2 if test.startswith('sensor') else 0;tag=mode+'-'+test")
code=code.replace("kind,'4' if white else '0'","kind,'4' if white else str(sensor_pattern)")
code=code.replace('stage=214,mode=mode,test=test,','stage=215,mode=mode,test=test,requested_sensor_pattern=sensor_pattern,')
code=code.replace('__MODE__',repr(mode)).replace('__TEST__',repr(test))
compile(code,'native-sensor-probe215','exec')
p=host.ssh('python3 -',input=code.encode(),timeout=110);(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(tag+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
