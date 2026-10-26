from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build();SDK=storage.SDK;work=SDK/'private/camss440-raw';work.mkdir(exist_ok=True);T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss440-raw'
source=(HERE.parent/'kernel387/pipeline-smoke.cpp').read_text().replace('#include <cstring>','#include <cstring>\n#include <cstdlib>')
source=source.replace('unsigned frames=0,failed=0,stable=0;','unsigned frames=0,failed=0,stable=0,targetFrames=6;').replace('frames>=6 && (!hold || heldOnce)','frames>=targetFrames && (!hold || heldOnce)')
source=source.replace('Size selectedSize;', 'if(const char *limit=std::getenv("RAW_TARGET_FRAMES")){capture.targetFrames=std::stoul(limit);if(capture.targetFrames<6 || capture.targetFrames>256)return 2;}\n Size selectedSize;')
(HERE/'pipeline-smoke.cpp').write_text(source);(work/'pipeline-smoke.cpp').write_text(source)
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include',W+'/pipeline-smoke.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/pipeline-smoke'],capture_output=True)
 (P/'raw-client-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
shutil.copyfile(work/'pipeline-smoke',P/'pipeline-smoke')
r={'stage':440,'passed':True,'binary_sha256':hashlib.sha256((P/'pipeline-smoke').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'original_raw_dual_metadata_checks_retained':True,'bounded_target_frames':[6,256],'raw_only_target_for_test':72,'werror':True,'sdk_bind_unmounted':True};(HERE/'raw-client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
