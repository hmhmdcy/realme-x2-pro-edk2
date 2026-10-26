"""Make post-QBUF mutation retain a valid header so snapshotting is observable."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;p=ROOT/'samurai-wb-params.c';s=p.read_text()
proof=ROOT/'wb-params-tool-validation.json';data=json.loads(proof.read_text());assert data['not_run_on_phone']
assert hashlib.sha256(p.read_bytes()).hexdigest()==data['source_sha256']
old='if(corrupt_after)memset(params_map,0,params_size);';assert old in s
s=s.replace(old,'if(corrupt_after)memset((char*)params_map+sizeof(struct params_envelope)+sizeof(struct v4l2_isp_block_header),0,params_size-sizeof(struct params_envelope)-sizeof(struct v4l2_isp_block_header));')
p.write_text(s);binary=host.PRIVATE/'wb-params-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'wb-params-refined-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel-wb-refined'],capture_output=True,timeout=10).returncode==3
data.update(binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),post_qbuf_mutation_retains_header_and_zeros_gains=True)
proof.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
