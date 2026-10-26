"""Build a matching standard RDI reference capture, without any image processing."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent
s=(ROOT/'samurai-physical-pix.c').read_text()
for a,b in [('msm_vfe0_pix','msm_vfe0_rdi0'),('msm_vfe0_video3','msm_vfe0_video0'),('l.source.index==4','l.source.index==1')]:
 assert a in s;s=s.replace(a,b)
save=' for(unsigned n=0;n<2;n++){if(call(vfe,VIDIOC_SUBDEV_G_SELECTION,&selections[n]))goto cleanup;selections_saved++;}'
assert save in s;s=s.replace(save,' /* RDI has no compose/crop selection. */')
start=s.index(' struct v4l2_subdev_selection compose=');end=s.index(' struct v4l2_control setting=',start);s=s[:start]+s[end:]
s=s.replace('output=320x240','output=1632x1224-RAW10')
s=s.replace('format.fmt.pix_mp.width=320;format.fmt.pix_mp.height=240;format.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_NV12',
 'format.fmt.pix_mp.width=1632;format.fmt.pix_mp.height=1224;format.fmt.pix_mp.pixelformat=V4L2_PIX_FMT_SRGGB10P')
s=s.replace('f->width!=320||f->height!=240||f->pixelformat!=V4L2_PIX_FMT_NV12','f->width!=1632||f->height!=1224||f->pixelformat!=V4L2_PIX_FMT_SRGGB10P')
s=s.replace('f->plane_fmt[0].bytesperline<320','f->plane_fmt[0].bytesperline<2040')
s=s.replace('f->plane_fmt[0].bytesperline*360','f->plane_fmt[0].bytesperline*1224')
s=s.replace('sizeimage>1024*1024','sizeimage>8*1024*1024').replace('plane[0].length>2*1024*1024','plane[0].length>8*1024*1024')
s=s.replace('for(unsigned y=0;y<360;y++)for(unsigned x=0;x<320;x++)','for(unsigned y=0;y<1224;y++)for(unsigned x=0;x<2040;x++)')
s=s.replace('size_t luma=(size_t)f->plane_fmt[0].bytesperline*240','size_t luma=plane[0].bytesused')
s=s.replace('active_bytes=115200','active_bytes=2496960').replace('active_changed<103680','active_changed<2247264')
s=s.replace('%s-%u.nv12','%s-%u.raw')
needle='  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill(fills[buffer.index],n);'
assert needle in s
s=s.replace(needle,r'''
  uint64_t total=0;unsigned raw_min=1023,raw_max=0;uint32_t count=0,above100=0,above200=0;
  for(unsigned row=0;row<1224;row++)for(unsigned group=0;group<408;group++){
   const unsigned char *b=data+(size_t)row*f->plane_fmt[0].bytesperline+group*5;
   for(unsigned k=0;k<4;k++){unsigned value=((unsigned)b[k]<<2)|((b[4]>>(2*k))&3);
    total+=value;count++;above100+=value>100;above200+=value>200;if(value<raw_min)raw_min=value;if(value>raw_max)raw_max=value;
   }
  }
  printf("RAW_STATS frame=%u min=%u max=%u mean=%.8f above100=%u above200=%u pixels=%u\n",frame,raw_min,raw_max,(double)total/count,above100,above200,count);
'''+needle)
source=ROOT/'samurai-physical-raw.c';assert not source.exists();source.write_text(s)
binary=host.PRIVATE/'physical-raw-aarch64-private';assert not binary.exists()
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(source),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'physical-raw-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--capture','/tmp/wrong-kernel-raw'],capture_output=True,timeout=10).returncode==3
report=dict(stage=291,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
 source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),standard_mc_v4l2_only=True,no_isp_processing=True,
 qemu_self_test_pass=True,wrong_kernel_guard_passed=True,physical_imx319=True,planned_frames=18,exposure_codes=[500,3000,500],gain_code=512)
(ROOT/'raw-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n')
worker=(ROOT/'native-physical.py').read_text().replace('k291-physical-r1','k291-raw-r1').replace('k291-tools/physical-pix','k291-tools/physical-raw')
worker=worker.replace("for frame in root.glob('*.nv12'):","for frame in root.glob('*.raw'):")
worker=worker.replace("b=frame.read_bytes();assert len(b)==115200;y=b[:76800];uv=b[76800:]\n  images[frame.name]=dict(bytes=len(b),y_min=min(y),y_max=max(y),y_mean=sum(y)/len(y),uv_min=min(uv),uv_max=max(uv),uv_mean=sum(uv)/len(uv))",
 "b=frame.read_bytes();assert len(b)==2048*1224\n  images[frame.name]=dict(bytes=len(b))")
worker=worker.replace('no_cpu_isp=True,tool_exit=ret','no_cpu_isp=True,raw_reference=True,tool_exit=ret')
(ROOT/'native-raw.py').write_text(worker)
launcher=(ROOT/'launch-physical.py').read_text().replace('physical-tool-validation','raw-tool-validation').replace('physical-pix-aarch64-private','physical-raw-aarch64-private').replace('physical-pix','physical-raw').replace('native-physical.py','native-raw.py').replace('k291-physical-r1','k291-raw-r1').replace('physical-worker','raw-worker').replace('physical-launch','raw-launch')
launcher=launcher.replace("p=Path('/var/lib/samurai/k291-tools');assert not p.exists();p.mkdir(mode=0o700);(p/'physical-raw.part').write_bytes(b'')",
 "p=Path('/var/lib/samurai/k291-tools/physical-raw.part');assert not p.exists();p.write_bytes(b'')")
(ROOT/'launch-raw.py').write_text(launcher)
poll=(ROOT/'poll-physical.py').read_text().replace('physical-launch','raw-launch').replace('k291-physical-r1','k291-raw-r1').replace('physical-poll','raw-poll').replace('physical-capture-validation','raw-capture-validation')
(ROOT/'poll-raw.py').write_text(poll)
print(json.dumps(report,indent=2))
