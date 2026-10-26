"""Preserve the first failed probe and add ioctl-level diagnostics for a new run."""
from pathlib import Path
import hashlib,json,subprocess
import host
root=Path(__file__).resolve().parent
for name in ['wb-params-capture-validation.json','wb-params-tool-validation.json','samurai-wb-params.c']:
 p=root/name;copy=root/('r1-'+name);assert not copy.exists();copy.write_bytes(p.read_bytes())
p=root/'samurai-wb-params.c';s=p.read_text();old=' while(result<0&&errno==EINTR&&!interrupted);return result;'
assert old in s
s=s.replace(old,' while(result<0&&errno==EINTR&&!interrupted);if(result<0)fprintf(stderr,"IOCTL_FAILURE fd=%d request=%#lx errno=%d\\n",fd,request,errno);return result;')
s=s.replace(' struct v4l2_requestbuffers request={.count=3,',' phase="capture-reqbufs";\n struct v4l2_requestbuffers request={.count=3,')
s=s.replace(' for(unsigned n=0;n<buffers;n++){\n  struct v4l2_plane',' phase="capture-map-queue";\n for(unsigned n=0;n<buffers;n++){\n  struct v4l2_plane',1)
p.write_text(s);binary=host.PRIVATE/'wb-params-r2-aarch64-private';assert not binary.exists()
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-wb-r2'],capture_output=True,timeout=10).returncode==3
proof=json.loads((root/'wb-params-tool-validation.json').read_text());proof.update(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,revision=2)
(root/'wb-params-tool-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
for name in ['native-wb-params.py','launch-wb-params.py','poll-wb-params.py','analyze-wb-params.py']:
 s=(root/name).read_text().replace('k292-wb-params-r1','k292-wb-params-r2').replace('k292-tools/wb-params','k292-tools/wb-params-r2').replace('k292-tools/native-wb-params.py','k292-tools/native-wb-params-r2.py').replace('wb-params-launch-private','wb-params-r2-launch-private').replace('wb-params-worker-private','wb-params-r2-worker-private').replace("/'wb-params'","/'wb-params-r2'")
 if name.startswith('launch'):s=s.replace("/'wb-params-aarch64-private'","/'wb-params-r2-aarch64-private'")
 (root/name.replace('.py','-r2.py')).write_text(s)
print(json.dumps(proof,indent=2))
