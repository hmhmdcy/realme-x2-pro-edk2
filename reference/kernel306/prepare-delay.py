"""Reuse the measured 301 application and 300 IPA to measure telephoto timing."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel301';P=host.PRIVATE
assert json.loads((HERE/'tele-bls-export-validation.json').read_text())['independent_reader_and_direct_decoder_agree']
oldproof=json.loads((OLD/'delay-bundle-validation.json').read_text())
for name,digest in oldproof['source_sha256'].items():
 assert hashlib.sha256((OLD/name).read_bytes()).hexdigest()==digest
stepper=(OLD/'control-stepper.c').read_text().replace('"imx319 "','CHOSEN_SENSOR').replace('CHOSEN_SENSOR','"s5k3m5 "')
for before,after in [('3000','1200'),('1500','800'),('768','128'),('512','64')]:stepper=stepper.replace(before,after)
capture=(OLD/'delay-capture.cpp').read_text().replace('2.22f','1.0f').replace('1.90f','1.0f')
(HERE/'control-stepper.c').write_text(stepper);(HERE/'delay-capture.cpp').write_text(capture)
profile='''%YAML 1.1
---
# Explicit OEM IFE BLS reference. No unit-specific dark calibration or AWB.
version: 1
sensor_model: s5k3m5
residual_black_subtraction: 3840
range_normalization: 1.06201171875
...
'''
(HERE/'s5k3m5-reference.yaml').write_text(profile)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss306-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'delay-capture.cpp',stage/'delay-capture.cpp')
commands=[
 ['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror','-I/candidate278-r24/usr/include/libcamera',
 '/private/camss306-runtime/delay-capture.cpp','-L/candidate278-r24/usr/lib','-Wl,-rpath-link,/candidate278-r24/usr/lib',
 '-lcamera','-lcamera-base','-pthread','-o','/private/camss306-runtime/delay-capture'],
 ['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
 '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'control-stepper.c'),'-o',str(P/'control-stepper-aarch64-private')]]
for i,command in enumerate(commands):
 q=subprocess.run(command,capture_output=True,timeout=100)
 (P/f'delay-compile-{i}-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
shutil.copyfile(stage/'delay-capture',P/'delay-capture-aarch64-private')
q=subprocess.run(['qemu-aarch64',str(P/'control-stepper-aarch64-private'),'3'],capture_output=True,timeout=10)
assert q.returncode==3
archive=P.parent/'kernel301'/oldproof['archive_file']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==oldproof['archive_sha256']
files={}
with tarfile.open(archive,'r:gz') as tar:
 assert set(tar.getnames())==set(oldproof['files'])
 for name in tar.getnames():
  data=tar.extractfile(name).read();assert hashlib.sha256(data).hexdigest()==oldproof['files'][name]['sha256'];files[name]=data
fixture=P.parent/'kernel305/pipeline-fixture305-aarch64-private'
assert hashlib.sha256(fixture.read_bytes()).hexdigest()==json.loads((HERE.parent/'kernel305/interrupt-restoration-validation.json').read_text())['fixture_binary_sha256']
files.update({'bin/pipeline-smoke':(P/'delay-capture-aarch64-private').read_bytes(),
 'bin/control-stepper':(P/'control-stepper-aarch64-private').read_bytes(),
 'bin/pipeline-fixture':fixture.read_bytes(),'profile/manual.yaml':profile.encode()})
target=P/'tele-delay-bundle-r1-private.tar.gz';assert not target.exists()
with tarfile.open(target,'w:gz') as tar:
 for name,data in files.items():
  item=tarfile.TarInfo(name);item.size=len(data);item.mode=0o600 if name.startswith('profile/') or name.endswith('.sign') else 0o700
  tar.addfile(item,io.BytesIO(data))
report=dict(stage=306,archive_file=target.name,archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
 archive_bytes=target.stat().st_size,compile_werror_pass=True,wrong_kernel_guard_exit=q.returncode,
 tested300_libraries_module_signature_proxy_reused=True,fixture305_explicit_restore_result=True,
 no_sdk_kernel_or_product_package_changes=True,unity_wb_is_not_awb=True,
 exposure_test_lines=[500,1200,800],gain_test_codes=[64,128],no_delay_assumed=True,
 files={n:dict(bytes=len(d),sha256=hashlib.sha256(d).hexdigest()) for n,d in files.items()},
 source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['control-stepper.c','delay-capture.cpp']})
(HERE/'delay-bundle-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
