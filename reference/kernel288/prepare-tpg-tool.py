"""Adapt the proven standard media/V4L2 TPG helper to the real FULL NV12 path."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
s=(ROOT.parent/'kernel126/samurai-tpg-capture.c').read_text()
replacements=[
 ('7.3.0-rc6-rmx1931-samurai-k126+','7.3.0-rc6-rmx1931-samurai-k279candidate+'),
 ('if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k279candidate+"))',
  'if(uname(&identity)||strcmp(identity.release,"7.3.0-rc6-rmx1931-samurai-k279candidate+")||strncmp(identity.version,"#288 ",5))'),
 ('msm_vfe0_rdi0','msm_vfe0_pix'),('msm_vfe0_video0','msm_vfe0_video3'),
 ('link.source.index==1','link.source.index==4'),
 ('subformat(csid,1,','subformat(csid,4,'),
 ('V4L2_PIX_FMT_SGRBG10P','V4L2_PIX_FMT_NV12'),
 ('bytesperline<400','bytesperline<320'),
 ('bytesperline*240','bytesperline*360'),
 ('for(unsigned y=0;y<240;y++)for(unsigned x=0;x<400;x++)','for(unsigned y=0;y<360;y++)for(unsigned x=0;x<320;x++)'),
 ('active_bytes=96000','active_bytes=115200'),('active_changed<86400','active_changed<103680'),
]
for before,after in replacements:
 assert before in s,before;s=s.replace(before,after)
# Inspect each DMA plane and the page-rounded tail independently of the content hash.
before='  int64_t timestamp=(int64_t)buffer.timestamp.tv_sec*1000000+buffer.timestamp.tv_usec;'
after='''  size_t luma=(size_t)f->plane_fmt[0].bytesperline*240,y_changed=0,uv_changed=0;
  for(size_t n=0;n<luma;n++)y_changed+=data[n]!=fills[buffer.index];
  for(size_t n=luma;n<plane[0].bytesused;n++)uv_changed+=data[n]!=fills[buffer.index];
  for(size_t n=plane[0].bytesused;n<sizes[buffer.index];n++)if(data[n]!=fills[buffer.index]){errno=EOVERFLOW;goto cleanup;}
  printf("PLANES y_changed=%zu uv_changed=%zu tail_unchanged=%zu\\n",y_changed,uv_changed,sizes[buffer.index]-plane[0].bytesused);
  if(y_changed<luma*3/4||uv_changed<(plane[0].bytesused-luma)*3/4){errno=EIO;goto cleanup;}
'''+before
assert before in s;s=s.replace(before,after)
source=ROOT/'samurai-pix-tpg-capture.c';assert not source.exists();source.write_text(s)
headers=PRIVATE/'host-uapi'
for n in ['media.h','media-bus-format.h']:
 subprocess.run(['sh',str(TREE/'scripts/headers_install.sh'),str(TREE/'include/uapi/linux'/n),str(headers/'include/linux'/n)],cwd=headers,check=True)
flags=['-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I'+str(headers/'include'),'-static','-s']
for compiler,name in [('gcc','pix-tpg-host-private'),('aarch64-linux-gnu-gcc','pix-tpg-aarch64-private')]:
 q=subprocess.run([compiler,*flags,str(source),'-o',str(PRIVATE/name)],capture_output=True)
 (PRIVATE/(name+'-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
for cmd in [[str(PRIVATE/'pix-tpg-host-private'),'--self-test'],['qemu-aarch64',str(PRIVATE/'pix-tpg-aarch64-private'),'--self-test']]:
 q=subprocess.run(cmd,capture_output=True,timeout=15);assert q.returncode==0
q=subprocess.run([str(PRIVATE/'pix-tpg-host-private'),'--capture',str(PRIVATE/'wrong-kernel-must-not-exist.raw')],capture_output=True)
assert q.returncode==3 and not (PRIVATE/'wrong-kernel-must-not-exist.raw').exists()
binary=PRIVATE/'pix-tpg-aarch64-private'
report=dict(stage=288,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
 native_and_qemu_self_tests_pass=True,wrong_release_or_build_rejected_before_device_open=True,
 csid_source_pad=4,vfe_entity='msm_vfe0_pix',capture_entity='msm_vfe0_video3',format='NV12',width=320,height=240,
 frames=3,per_frame_poll_timeout_ms=5000,per_plane_prefill_and_page_tail_checked=True,
 graph_controls_and_formats_restored_on_exit=True,standard_media_v4l2_only=True,not_run_on_phone=True)
(ROOT/'tpg-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
