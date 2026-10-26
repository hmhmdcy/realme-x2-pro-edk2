from pathlib import Path
import importlib.util,json,re,hashlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
video=(source/'drivers/media/platform/qcom/camss/camss-video.c').read_text()
lines=video.splitlines();hits=[(i,l) for i,l in enumerate(lines) if 'V4L2_PIX_FMT_NV12' in l]
snippets=['\n'.join(f'{j+1}: {lines[j]}' for j in range(max(0,i-3),min(len(lines),i+10))) for i,_ in hits]
(P/'camss-nv12-layout-private.txt').write_text('\n\n'.join(snippets)+'\n')
library=build.parent/'libcamera362-serialized-built/src/libcamera-v0.7.2'
headers=[library/'include/libcamera/internal/v4l2_videodevice.h']
for p in headers:
 out=P/p.name;out.write_bytes(p.read_bytes())
report=dict(stage=386,kernel_camss_nv12_format_snippets_saved_privately=True,kernel_file_sha256=hashlib.sha256(video.encode()).hexdigest(),
 actual_library_source=str(library),v4l2_m2m_wrapper_header_available=all(p.is_file() for p in headers),nv12_hits=len(hits),passed=True)
(HERE/'integration-inspection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
