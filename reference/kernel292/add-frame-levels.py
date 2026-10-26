"""Record per-frame color-bar responses to measure parameter sequence correspondence."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;p=ROOT/'samurai-wb-params.c';s=p.read_text()
report=ROOT/'wb-params-tool-validation.json';proof=json.loads(report.read_text());assert proof['not_run_on_phone']
assert hashlib.sha256(p.read_bytes()).hexdigest()==proof['source_sha256']
needle='  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill(fills[buffer.index],n);';assert s.count(needle)==1
s=s.replace(needle,r'''
  double levels[4]={0};const unsigned int xs[4]={20,220,140,260};
  for(unsigned int patch=0;patch<4;patch++)for(unsigned int yy=112;yy<128;yy++)for(unsigned int xx=xs[patch]-8;xx<xs[patch]+8;xx++)levels[patch]+=data[(size_t)yy*f->plane_fmt[0].bytesperline+xx];
  printf("PIX_LEVEL phase=%u frame=%u sequence=%u white_y=%.6f red_y=%.6f green_y=%.6f blue_y=%.6f\n",wb_phase,frame,buffer.sequence,levels[0]/256,levels[1]/256,levels[2]/256,levels[3]/256);
'''+needle)
p.write_text(s);binary=host.PRIVATE/'wb-params-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'wb-params-frame-levels-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-wb-frames'],capture_output=True,timeout=10).returncode==3
proof.update(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),per_frame_color_levels_logged=True)
report.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
