"""Compare CST offset/clamp and FULL clamp responses with fixed synthetic configurations."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent;previous=ROOT.parent/'kernel289'
(ROOT/'mmio-primitives.h').write_bytes((previous/'mmio-primitives.h').read_bytes())
h=(previous/'gamma-upload-probe.h').read_text()
needle='printf("GAMMA_RESTORE registers=%d\\n",'
assert h.count(needle)==1
h=h.replace(needle,'''unsigned restored=0;
 for(unsigned ch=0;ch<3;ch++){
  if(gamma_restore_selectors[ch]<26||gamma_restore_selectors[ch]>31)continue;
  mmio_write(gamma_base,0x34,gamma_saved_cgc|8u);mmio_write(gamma_base,0xc24,(gamma_saved_dmi&~0xffu)|gamma_restore_selectors[ch]);
  for(unsigned i=0;i<64;i++){mmio_write(gamma_base,0xc28,i);restored+=mmio_read(gamma_base,0xc30)==gamma_old_words[ch][i];}
 }
 mmio_write(gamma_base,0xc24,gamma_saved_dmi);mmio_write(gamma_base,0xc28,gamma_saved_addr);mmio_write(gamma_base,0x34,gamma_saved_cgc);
 printf("GAMMA_RESTORE_LUT matching_words=%u expected=192\\n",restored);
 '''+needle)
(ROOT/'gamma-upload-probe.h').write_text(h)
s=(previous/'samurai-gamma-upload-probe.c').read_text().replace('#include "gamma-upload-probe.h"','#include "gamma-upload-probe.h"\n#include "cst-response-probe.h"')
s=s.replace('frame<9','frame<3+6*RESPONSE_PHASES')
s=s.replace('if(!frame||frame==6)','if(!frame)')
start=s.index('  if(frame==2){');end=s.index('\n }\n gamma_probe_restore();',start)
s=s[:start]+'''
  if(frame>=6&&(frame-6)%6==0)response_measure((frame-6)/6,data,f->plane_fmt[0].bytesperline);
  if(frame==2||(frame>=8&&(frame-8)%6==0&&frame<2+6*RESPONSE_PHASES)){
   if(frame==2&&gamma_probe_upload())goto cleanup;
   response_set((frame-2)/6);
   for(unsigned n=0;n<buffers;n++){
    struct v4l2_plane qp[VIDEO_MAX_PLANES]={0};struct v4l2_buffer qb={.index=n,.type=type,.memory=V4L2_MEMORY_MMAP,.length=1,.m.planes=qp};
    for(size_t i=0;i<sizes[n];i++)((unsigned char *)maps[n])[i]=prefill(fills[n],i);
    if(call(video,VIDIOC_QBUF,&qb))goto cleanup;
   }
  }else if(frame>=3&&(frame-3)%6<3){
   for(size_t i=0;i<sizes[buffer.index];i++)data[i]=prefill(fills[buffer.index],i);
   if(call(video,VIDIOC_QBUF,&buffer))goto cleanup;
  }
'''+s[end:]
s=s.replace(' gamma_probe_restore();',' response_restore();gamma_probe_restore();')
source=ROOT/'samurai-cst-response.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'cst-response-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'cst-response-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
report=dict(stage=290,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),header_sha256=hashlib.sha256((ROOT/'cst-response-probe.h').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),bytes=binary.stat().st_size,qemu_content_self_test=True,
 fixed_response_phases=15,frames_planned=93,no_persistent_writes=True,calibration_untouched=True,register_and_lut_restore_checks=True,not_run_on_phone=True)
(ROOT/'cst-response-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for src,dst in [('native-gamma-upload.py','native-cst-response.py'),('launch-gamma-upload.py','launch-cst-response.py'),('poll-gamma-upload.py','poll-cst-response.py')]:
 s=(previous/src).read_text().replace('stage=289','stage=290').replace('k289-gamma-r1','k290-response-r1').replace('gamma-upload','cst-response').replace('k289-tools','k290-tools')
 if dst.startswith('launch-'):s=s.replace('p.mkdir(mode=0o700,exist_ok=True)','p.mkdir(mode=0o700,exist_ok=True)')
 (ROOT/dst).write_text(s)
print(json.dumps(report,indent=2))
