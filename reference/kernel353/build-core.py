"""Build only the new external A5 core module against the prepared kernel."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();work=build.parent/'icp353-core';work.mkdir(exist_ok=True)
for path in (HERE/'kernel').iterdir():
 if path.is_file():shutil.copyfile(path,work/path.name)
release=(build/'include/config/kernel.release').read_text().strip();attempt=1
while (P/('kernel-build-r'+str(attempt)+'.log')).exists():attempt+=1
log=P/('kernel-build-r'+str(attempt)+'.log');state=P/'kernel-build-state.json'
env=dict(os.environ,TMPDIR=str(build.parent/'tmp'),KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='298',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
command=['make','-C',str(build),'M='+str(work),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1','KCFLAGS=-Werror','KERNELRELEASE='+release,'modules'];start=time.monotonic()
with log.open('xb') as stream:
 child=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
 state.write_text(json.dumps(dict(pid=child.pid,terminal=False,attempt=attempt))+'\n');code=child.wait()
report=dict(stage=353,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),kernel_release=release,external_module_only=True,
 diagnostics=[l for l in log.read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()],installed=False,passed=not code)
if not code:
 module=work/'qcom-camss-icp-a5-core.ko';out=P/('qcom-camss-icp-a5-core-r'+str(attempt)+'.ko');shutil.copyfile(module,out)
 report.update(module_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(out)],text=True).strip(),module_bytes=out.stat().st_size)
state.write_text(json.dumps(dict(pid=child.pid,terminal=True,**report),indent=2)+'\n')
(HERE/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(code)
