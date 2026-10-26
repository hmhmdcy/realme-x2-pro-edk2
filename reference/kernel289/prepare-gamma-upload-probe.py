"""Transfer the exact standard curve under the Gamma clock, verify it, then capture fresh frames."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent
s=(ROOT/'samurai-dmi-pattern.c').read_text()
# Retain the existing bounded MMIO primitives, not its unrelated readback entrypoint.
h=(ROOT/'dmi-readback.h').read_text().split('static int gamma_readback(void)')[0]
(ROOT/'mmio-primitives.h').write_text(h)
s=s.replace('#include "dmi-cgc.h"','#include "mmio-primitives.h"\n#include "gamma-upload-probe.h"')
s=s.replace('for(unsigned frame=0;frame<3;frame++)','for(unsigned frame=0;frame<9;frame++)')
s=s.replace('if(!frame){int output=open(argv[2],',
 '''if(!frame||frame==6){char corrected[1024];if(snprintf(corrected,sizeof(corrected),"%s.corrected",argv[2])>=(int)sizeof(corrected)){errno=EINVAL;goto cleanup;}int output=open(frame?corrected:argv[2],''')
needle='\n }\n if(gamma_readback())goto cleanup;'
assert s.count(needle)==1
s=s.replace(needle,'''
  if(frame==2){
   if(gamma_probe_upload())goto cleanup;
   for(unsigned n=0;n<buffers;n++){
    struct v4l2_plane qp[VIDEO_MAX_PLANES]={0};struct v4l2_buffer qb={.index=n,.type=type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=qp};
    for(size_t i=0;i<sizes[n];i++)((unsigned char *)maps[n])[i]=prefill(fills[n],i);
    if(call(video,VIDIOC_QBUF,&qb))goto cleanup;
   }
  }else if(frame>=3&&frame<6){
   for(size_t i=0;i<sizes[buffer.index];i++)data[i]=prefill(fills[buffer.index],i);
   if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;
  }
 }
 gamma_probe_restore();''')
s=s.replace('cleanup:\n if(result)','cleanup:\n gamma_probe_restore();\n if(result)')
source=ROOT/'samurai-gamma-upload-probe.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'gamma-upload-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'gamma-upload-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
report=dict(stage=289,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256((ROOT/'gamma-upload-probe.h').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 standard_srgb_curve_only=True,inactive_bank_upload_and_readback_words=192,three_post_switch_frames_discarded=True,
 register_restore_check_in_tool=True,previous_inactive_bank_restore_writes_issued=True,
 previous_inactive_bank_restore_readback_verified=False,not_run_on_phone=True)
(ROOT/'gamma-upload-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for src,dst in [('native-dmi-pattern.py','native-gamma-upload.py'),('launch-dmi-pattern.py','launch-gamma-upload.py')]:
 s=(ROOT/src).read_text().replace('k289-dmi-r5','k289-gamma-r1').replace('dmi-pattern','gamma-upload')
 (ROOT/dst).write_text(s)
s=(ROOT/'poll-dmi-readback.py').read_text().split('source=subprocess.check_output')[0]
s=s.replace('dmi-launch-private','gamma-upload-launch-private').replace('k289-dmi-r1','k289-gamma-r1').replace('dmi-poll-private','gamma-upload-poll-private').replace('dmi-capture-validation','gamma-upload-capture-validation')
s+='print(json.dumps(summary,indent=2))\n'
(ROOT/'poll-gamma-upload.py').write_text(s)
print(json.dumps(report,indent=2))
