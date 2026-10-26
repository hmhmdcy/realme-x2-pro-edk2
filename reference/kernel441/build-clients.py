"""Bounded optical capture and variable-size fixed-input PD10 replay."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel437/capture.cpp').read_text()
def replace_once(text,a,b):assert text.count(a)==1,(a,text.count(a));return text.replace(a,b)
source=replace_once(source,'if(argc!=5)return 2;','if(argc!=5 && argc!=6)return 2;\n unsigned ow=640,oh=480;if(argc==6 && std::sscanf(argv[5],"%ux%u",&ow,&oh)!=2)return 2;\n const Size requestedOutput(ow,oh);')
source=replace_once(source,'config->at(0).size=Size(640,480);','config->at(0).size=requestedOutput;')
source=replace_once(source,'format.size!=Size(640,480)','format.size!=requestedOutput')
(HERE/'capture.cpp').write_text(source)
replay=(HERE.parent/'kernel430/pd10-ipe.c').read_text();replay=replace_once(replay,'static const unsigned cap_type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;','static const unsigned cap_type=V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE;\nstatic unsigned width,height,full_bytes,coarse_width,coarse_height,coarse_stride,coarse_bytes,scratch_bytes;')
replay=replay.replace('f.fmt.pix_mp.width=640;f.fmt.pix_mp.height=480;','f.fmt.pix_mp.width=width;f.fmt.pix_mp.height=height;').replace('f.fmt.pix_mp.plane_fmt[0].bytesperline=640;','f.fmt.pix_mp.plane_fmt[0].bytesperline=width;').replace('f.fmt.pix_mp.width==640 && f.fmt.pix_mp.height==480','f.fmt.pix_mp.width==width && f.fmt.pix_mp.height==height').replace('f.fmt.pix_mp.plane_fmt[1].bytesperline==768','f.fmt.pix_mp.plane_fmt[1].bytesperline==coarse_stride')
replay=replay.replace('460800','full_bytes').replace('46080','coarse_bytes').replace('46128','scratch_bytes')
replay=replace_once(replay,'assert(argc==4);','assert(argc==7);\n width=strtoul(argv[4],NULL,10);height=strtoul(argv[5],NULL,10);scratch_bytes=strtoul(argv[6],NULL,10);\n assert(width>=128 && width<=1920 && height>=128 && height<=1080 && !((width|height)&1) && scratch_bytes<=0x40000);\n full_bytes=width*height*3/2;coarse_width=((width+7)/4)&~1U;coarse_height=((height+7)/4)&~1U;\n coarse_stride=((coarse_width*4+191)/192)*192;coarse_bytes=coarse_stride*((coarse_height+7)/8)*4;')
replay=replace_once(replay,'row<60','row<coarse_height/2');replay=replace_once(replay,'group<80','group<coarse_width/2');replay=replace_once(replay,'row*768+group*8','row*coarse_stride+group*8')
(HERE/'pd10-ipe.c').write_text(replay)
work=storage.SDK/'private/camss441-clients';work.mkdir(exist_ok=True)
for name in ['capture.cpp','pd10-ipe.c']:shutil.copyfile(HERE/name,work/name)
T='/work/libcamera/src/libcamera-v0.7.2';rows=[]
includes=work/'include/linux';includes.mkdir(parents=True,exist_ok=True)
uapi=storage.mount.mounted_build().parent/'source354/include/uapi/linux/qcom-ipe-a5.h'
shutil.copyfile(uapi,includes/'qcom-ipe-a5.h')
with storage.sdk_candidate():
 for name,cmd in [('capture',['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+T+'/include','-I'+T+'/output/include','/private/camss441-clients/capture.cpp','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss441-clients/capture']),('pd10-ipe',['gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-I/private/camss441-clients/include','/private/camss441-clients/pd10-ipe.c','-o','/private/camss441-clients/pd10-ipe'])]:
  q=subprocess.run(['chroot',str(storage.SDK),*cmd],capture_output=True);(P/(name+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:];shutil.copyfile(work/name,P/name);rows.append(dict(name=name,bytes=(P/name).stat().st_size,sha256=hashlib.sha256((P/name).read_bytes()).hexdigest(),source_sha256=hashlib.sha256((HERE/('capture.cpp' if name=='capture' else 'pd10-ipe.c')).read_bytes()).hexdigest()))
r=dict(stage=441,aarch64_werror=True,clients=rows,capture_explicit_output_size=True,capture_stop_after_8_locked_max240_or20seconds=True,replay_real_black_white_real_pd10_four_jobs=True,replay_dynamic_full_and_coarse_layout=True,replay_original_known_safe_scratch_attribute_only=True,phone_accessed=False,passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
