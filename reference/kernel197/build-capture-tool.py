from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel197');headers=Path('/home/cy122/pmos-samurai-kernel136/kernel/usr/include');assert (headers/'linux/videodev2.h').exists();source=ref/'samurai-front-capture.c';flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I'+str(headers)];records=[]
for compiler,name in [('gcc','front-capture-host-private'),('aarch64-linux-gnu-gcc','front-capture-aarch64-private')]:
 p=out/name;result=subprocess.run([compiler,*flags,'-static',str(source),'-o',str(p)],capture_output=True,text=True);(out/(name+'-compile-private.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,result.stderr;records.append(dict(name=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
for args in [[str(out/'front-capture-host-private'),'--self-test'],['qemu-aarch64',str(out/'front-capture-aarch64-private'),'--self-test']]:
 p=subprocess.run(args,capture_output=True,text=True,timeout=10);assert p.returncode==0 and 'FRONT_CAPTURE_HASH_SELF_TEST_PASS' in p.stdout
p=subprocess.run([str(out/'front-capture-host-private'),'--capture',str(out/'should-not-exist.raw')],capture_output=True,text=True);assert p.returncode==3 and not (out/'should-not-exist.raw').exists()
r=dict(stage=197,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),static_binaries=records,host_and_qemu_self_tests_passed=True,wrong_kernel_guard_passed=True,kernel_uapi_headers_used=True,hardware_executed=False);(ref/'capture-tool-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
