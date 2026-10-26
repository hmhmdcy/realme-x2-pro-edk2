"""Advertise required delivery semantics from the common SPA source itself."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
base=SDK/'work/pipewire263-busy';W=SDK/'work/pipewire263-automatic';assert not W.exists();shutil.copytree(base,W)
p=W/'source/libcamera-source.cpp';s=p.read_text();needle='{ SPA_KEY_NODE_DRIVER, "true" },';assert s.count(needle)==1
s=s.replace(needle,needle+'\n\t\t{ "node.reliable", "true" },');p.write_text(s)
common=['g++','-std=c++20','-fPIC','-O2','-Wall','-Wextra','-Wno-unused-parameter','-Wno-missing-field-initializers','-I/work/pipewire263-automatic/source','-I/work/pipewire262/sdk/usr/include/spa-0.2','-I/candidate238-r14/usr/include/libcamera']
def inside(args):return subprocess.run(['chroot',str(SDK),*args],capture_output=True)
q=inside([*common,'-c','/work/pipewire263-automatic/source/libcamera-source.cpp','-o','/work/pipewire263-automatic/libcamera-source.cpp.o']);(P/'automatic-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=inside(['g++','-shared',*['/'+str(p.relative_to(SDK)) for p in sorted(W.glob('*.o'))],'-L/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-pthread','-o','/work/pipewire263-automatic/libspa-libcamera.so']);assert q.returncode==0
shutil.copyfile(W/'libspa-libcamera.so',P/'libspa-libcamera-automatic-candidate.so')
original=(SDK/'work/pipewire262/pipewire-1.6.9/spa/plugins/libcamera/libcamera-source.cpp').read_text()
(R/'libcamera-automatic-ownership-candidate.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/spa/plugins/libcamera/libcamera-source.cpp',tofile='b/spa/plugins/libcamera/libcamera-source.cpp')))
report=dict(stage=263,compiled=True,source_sha256=hashlib.sha256(s.encode()).hexdigest(),plugin_sha256=hashlib.sha256((W/'libspa-libcamera.so').read_bytes()).hexdigest(),requires_no_application_copy_flag=True,no_system_deployment=True)
(R/'automatic-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
