from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'cpu-isp-tests-validation.json').read_text())['real_libcamera_cpu_isp_and_dma_heap_test']
builder=here.parent/'kernel216/verify-and-final-health.py';text=builder.read_text()
# Recreate only the native health block; avoid replaying old aggregation/writes.
original=(here.parent/'kernel214/final-health.py').read_text();code=original.split("code=r'''",1)[1].split("'''",1)[0]
code=code.replace("out=root/'k214-final-health'","out=root/'k218-final-health'").replace("base=root/'k214-baseline'","base=root/'k218-baseline'")
code=code.replace("original=json.loads((base/'products-before-private.json').read_text())","original=json.loads((root/'k214-baseline/products-before-private.json').read_text())")
code=code.replace("if name.lstrip('/') not in paths:","if name.lstrip('/') not in paths and not name.endswith('/kernel/drivers/media/i2c/imx471.ko'):")
old="wp=Path('/proc',str(policy['new_pid']));assert (wp/'comm').read_text().strip()=='wireplumber' and 'libcamera.so' in (wp/'maps').read_text()"
new="""wp=[p for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'comm').exists() and (p/'comm').read_text().strip()=='wireplumber'];assert len(wp)==1;wp=wp[0]
assert 'libcamera.so' in (wp/'maps').read_text()
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b'
assert json.loads((root/'k216-driver-test-r2/transition-state-private.json').read_text())['state']=='verified'
assert Path('/lib/apk/db/installed').read_bytes()==(base/'installed-before-private.txt').read_bytes()"""
assert old in code;code=code.replace(old,new)
code=code.replace('stage=214,same_boot_after_package_upgrade=True,','stage=218,same216_boot_and_sensor_module_preserved=True,candidate_full_resolution_mode_not_installed=True,')
compile(code,'native-final-health218','exec');p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
