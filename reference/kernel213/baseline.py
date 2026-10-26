from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k213-baseline';out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k212-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
(out/'boot-id-private.txt').write_bytes(boot)
db=Path('/lib/apk/db/installed').read_bytes();(out/'apk-installed-before-private.txt').write_bytes(db)
paths=[Path('/usr/bin/cam'),Path('/usr/lib/libcamera.so.0.7.2'),Path('/usr/lib/libcamera-base.so.0.7.2'),Path('/usr/lib/libcamera/ipa/ipa_soft_simple.so'),Path('/usr/lib/libcamera/ipa/ipa_soft_simple.so.sign'),Path('/etc/libcamera/configuration.yaml')]
ipa=list(Path('/usr/lib/libcamera/ipa').glob('*'));(out/'ipa-files-private.json').write_text(json.dumps([str(p) for p in ipa]))
paths=[p for p in paths if p.is_file()];products={}
for p in paths:
    data=p.read_bytes();products[str(p)]=hashlib.sha256(data).hexdigest();shutil.copyfile(p,out/p.name)
(out/'products-before-private.json').write_text(json.dumps(products,indent=2)+'\n')
sdk=root/'k190-mm-sdk';envpath=root/'k190-mm-build/build-environment-private.json';env=json.loads(envpath.read_text());(out/'sdk-environment-private.json').write_text(json.dumps(env,indent=2)+'\n')
tools={n:(sdk/'usr/bin'/n).is_file() for n in ['gcc','g++','cc','c++','meson','ninja','pkg-config','python3']}
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
controls=subprocess.run(['v4l2-ctl','-d','/dev/'+nodes[0].name,'--list-ctrls'],capture_output=True,text=True,timeout=10);assert controls.returncode==0;(out/'sensor-controls-private.txt').write_text(controls.stdout+controls.stderr)
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(faults.values())
report=dict(stage=213,same_current212_boot_verified=True,taint=0,camera_devices_suspended=True,installed_camera_products_backed_up=list(products),isolated_native_sdk_tools=tools,isolated_sdk_has_cpp_headers=any((sdk/'usr/include/c++').glob('*')),isolated_sdk_pc_names=sorted(p.name for p in (sdk/'usr/lib/pkgconfig').glob('*.pc')),sensor_controls=controls.stdout,package_database_backed_up=True,remoteprocs={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},fault_counts=faults,no_product_change_or_transition=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
