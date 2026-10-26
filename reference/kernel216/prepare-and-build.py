from pathlib import Path
import hashlib,host,json,os,shutil,struct,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=host.PRIVATE;kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
shutil.copyfile(private.parent/'kernel215/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
binary=private.parent/'kernel115/vendor-camera-modules/com.qti.sensor.imx471.so';data=binary.read_bytes()
for address,opcode in [(0x102c,0x1e261000),(0x1058,0x52807809),(0x1078,0x710f011f)]:assert struct.unpack_from('<I',data,address)[0]==opcode
p=subprocess.run(['aarch64-linux-gnu-objdump','-d',str(binary)],capture_output=True,text=True,timeout=30);assert p.returncode==0;(private/'factory-imx471-disassembly-private.txt').write_text(p.stdout)
assert 'fmov\ts0, #1.600000000000000000e+01' in p.stdout and 'mov\tw9, #0x3c0' in p.stdout and 'cmp\tw8, #0x3c0' in p.stdout
factory=dict(stage=216,own_factory_imx471_code_rechecked=True,gain_min=1.0,gain_max=16.0,register_gain_max=960,gain_formula='1024/(1024-code)',instructions_checked=['0x102c: float16 ceiling','0x1058: code960 ceiling','0x1078: compare code960'],factory_binary_unmodified=True,no_calibration_or_nv_access=True)
(here/'factory-gain-contract-validation.json').write_text(json.dumps(factory,indent=2)+'\n');print(json.dumps(factory),flush=True)
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k216-baseline';assert not base.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k215-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
assert json.loads((root/'k215-driver-test-r2/transition-state-private.json').read_text())['state']=='verified'
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='6b2bb0b47b93c6bf12eb8e137592c203f12fa96fcf9551553c48cc35ccad9d9c'
base.mkdir(mode=0o700);(base/'boot-id-private.txt').write_bytes(boot);shutil.copyfile(module,base/'imx471-original.ko')
db=Path('/lib/apk/db/installed').read_bytes();assert db==(root/'k215-baseline/installed-before-private.txt').read_bytes();(base/'installed-before-private.txt').write_bytes(db)
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
p=subprocess.run(['v4l2-ctl','-d','/dev/'+nodes[0].name,'--list-ctrls'],capture_output=True,text=True,timeout=10);assert p.returncode==0;(base/'controls-before-private.txt').write_text(p.stdout)
assert 'analogue_gain' in p.stdout and 'max=800' in next(line for line in p.stdout.splitlines() if 'analogue_gain' in line)
report=dict(stage=216,fresh_same215_boot_verified=True,current_r5_database_unchanged=True,original215_module_backed_up=True,existing_analogue_gain_max=800,camera_suspended=True,taint=0)
(base/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45);(private/'baseline-host-private.log').write_bytes(p.stdout+p.stderr);result=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
path=kernel/'drivers/media/i2c/imx471.c';old=path.read_text();assert sha(path)=='8b0bf56725ae200c2e55ee5c231192f1c3fccf17a62cecf61b3a65f371beb1ce';(private/'imx471-before.c').write_text(old)
fragment='#define IMX471_ANA_GAIN_MAX\t\t\t800';assert old.count(fragment)==1;new=old.replace(fragment,fragment.replace('800','960'))
upstream=private.parent/'kernel215/related-upstream/kernel/patches/0003-media-i2c-imx471-Raise-the-analogue-gain-limit-to-th.patch';patch=upstream.read_text();assert '-'+fragment in patch and '+'+fragment.replace('800','960') in patch
shutil.copyfile(upstream,repo/'linux-port/camera/kernel/0002-imx471-analogue-gain-limit.patch');path.write_text(new)
source=dict(stage=216,source_before_sha256=hashlib.sha256(old.encode()).hexdigest(),source_after_sha256=sha(path),only_analogue_gain_max_changed=True,old_register_max=800,new_register_max=960,old_gain_max=1024/(1024-800),new_gain_max=16.0,own_factory_contract_verified=True,exposure_test_pattern_mode_power_and_gpio_unchanged=True,upstream_patch_commit='5cf84f3eda244f0a30684c2b323a5489edd9cb1b',upstream_repository_commit='533d995b7acbd6965e5b0b85c97f8bafab9fed4e',runtime_validation_pending=True)
(here/'gain-source-validation.json').write_text(json.dumps(source,indent=2)+'\n')
original=(here.parent/'kernel215/fix-and-build.py').read_text();body="out=private/'modules'"+original.split("out=private/'modules'",1)[1];body=body.replace('stage=215','stage=216');exec(compile(body,'kernel216-module-build','exec'))
