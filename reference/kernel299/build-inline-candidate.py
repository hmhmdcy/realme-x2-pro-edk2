"""Create an isolated libcamera candidate; never replace the retained r24 tree."""
from pathlib import Path
import difflib,hashlib,json,os,shutil,signal,subprocess,sys
import host
HERE=Path(__file__).resolve().parent
def put(path,text):
 if not path.exists() or path.read_text()!=text:path.write_text(text)
def copy(source,dest):
 if not dest.exists() or dest.read_bytes()!=source.read_bytes():shutil.copyfile(source,dest)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
original=SDK/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2'
candidate=SDK/'work/libcamera299-inline'
retry='--retry' in sys.argv
if not retry:
 assert not candidate.exists()
 shutil.copytree(original,candidate,ignore=shutil.ignore_patterns('output','.git','__pycache__'))
else:assert candidate.is_dir()
pipeline=candidate/'src/libcamera/pipeline/camss-vfe';pipeline.mkdir(exist_ok=True)
for p in (HERE/'pipeline').glob('*'):copy(p,pipeline/p.name)
for name in ['parameter_encoder.cpp','parameter_encoder.h']:copy(HERE/'ipa'/name,pipeline/name)
p=pipeline/'params.h';put(p,(HERE/'ipa/params.h').read_text().replace('#include "v4l2_params.h"','#include "../../../ipa/libipa/v4l2_params.h"'))
kernel=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
for name in ['qcom-camss-config.h','media/v4l2-isp.h']:
 p=candidate/'include/linux'/name;p.parent.mkdir(exist_ok=True,parents=True);copy(kernel/'include/uapi/linux'/name,p)
patches={}
name='include/libcamera/internal/framebuffer.h';p=candidate/name;t=(original/name).read_text();old=t
t=t.replace('\tbool timestampMonotonic() const', '\tuint32_t kernelSequence() const { return kernelSequence_; }\n\tvoid setKernelSequence(uint32_t sequence) { kernelSequence_ = sequence; }\n\tbool timestampMonotonic() const',1)
t=t.replace('\tbool timestampMonotonic_ = false;','\tuint32_t kernelSequence_ = 0;\n\tbool timestampMonotonic_ = false;',1);assert t!=old;put(p,t);patches[name]=(old,t)
name='src/libcamera/v4l2_videodevice.cpp';p=candidate/name;t=(original/name).read_text();old=t
needle='\tmetadata.sequence = buf.sequence;';assert t.count(needle)==1
t=t.replace(needle,needle+'\n\t/* Keep the shared kernel frame identity across independently started queues. */\n\tbuffer->_d()->setKernelSequence(buf.sequence);');put(p,t);patches[name]=(old,t)
name='meson.build';p=candidate/name;t=(original/name).read_text();old=t
t=t.replace("    'imx8-isi':     arch_arm,","    'camss-vfe':    arch_arm,\n    'imx8-isi':     arch_arm,");assert t!=old;put(p,t);patches[name]=(old,t)
name='meson_options.txt';p=candidate/name;t=(original/name).read_text();old=t
needle="            'imx8-isi',";assert t.count(needle)==1
t=t.replace(needle,"            'camss-vfe',\n"+needle);put(p,t);patches[name]=(old,t)
name='include/linux/videodev2.h';p=candidate/name;t=(original/name).read_text();old=t
lines=(kernel/'include/uapi/linux/videodev2.h').read_text().splitlines()
definitions=[line for line in lines if line.startswith('#define V4L2_META_FMT_QCOM_ISP_')]
assert len(definitions)==2 and all(line.split()[1] not in t for line in definitions)
n=t.index('#define V4L2_META_FMT_');t=t[:n]+'/* Qualcomm ISP metadata, synchronized from the deployed kernel UAPI. */\n'+'\n'.join(definitions)+'\n'+t[n:]
put(p,t);patches[name]=(old,t)
(HERE/'libcamera-inline-integration.patch').write_text(''.join(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name,(a,b) in patches.items()))
args=['chroot',str(SDK),'/usr/bin/meson','setup']
if (candidate/'output/meson-private/coredata.dat').exists():args+=['--reconfigure']
args+=['/work/libcamera299-inline/output','/work/libcamera299-inline','--prefix=/usr','--buildtype=plain','-Doptimization=0','-Ddebug=false',
 '-Dpipelines=camss-vfe,simple','-Dipas=simple','-Dcam=enabled','-Dcam-output-kms=disabled','-Dcam-output-sdl2=disabled',
 '-Dqcam=disabled','-Dgstreamer=disabled','-Dv4l2=disabled','-Ddocumentation=disabled','-Dtest=false','-Dpycamera=disabled','-Dtracing=disabled','-Dwerror=true']
attempt=1
while (host.PRIVATE/f'inline-meson-r{attempt}-private.log').exists():attempt+=1
q=subprocess.run(args,capture_output=True,timeout=180)
(host.PRIVATE/f'inline-meson-r{attempt}-private.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print((q.stdout+q.stderr).decode()[-7000:]);sys.exit(q.returncode)
process=subprocess.Popen(['chroot',str(SDK),'/usr/bin/ninja','-C','/work/libcamera299-inline/output','-j8'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
try:stdout,stderr=process.communicate(timeout=1200)
except subprocess.TimeoutExpired:
 os.killpg(process.pid,signal.SIGTERM)
 try:stdout,stderr=process.communicate(timeout=15)
 except subprocess.TimeoutExpired:
  os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
q=subprocess.CompletedProcess(process.args,process.returncode,stdout,stderr)
(host.PRIVATE/f'inline-build-r{attempt}-private.log').write_bytes(q.stdout+q.stderr)
print((q.stdout+q.stderr).decode()[-6500:])
out=dict(stage=299,attempt=attempt,isolated_source=str(candidate),retained_r24_unchanged=True,kernel_unchanged=True,installed=False,
 build_exit=q.returncode,actual_pipeline_handler=True,inline_nv12_params_stats_queues=True,automatic_algorithms_not_implemented=True,
 ipa_ipc_not_yet_integrated=True,physical_pipeline_acceptance_pending=True,
 source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pipeline.glob('*')})
(HERE/'inline-build-validation.json').write_text(json.dumps(out,indent=2)+'\n');sys.exit(q.returncode)
