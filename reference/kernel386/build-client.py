from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;output=P/'m2m-client-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(HERE/'m2m-client.c'),'-o',str(output)],capture_output=True)
(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
report=dict(stage=386,aarch64_static_v4l2_client=True,bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
 scope='MMAP6 frames; imported/exported DMABUF4 with source offset16 and padded stride672; concurrent MMAP contexts4+4; explicit STREAMOFF and close-streaming',
 private_path=str(output),passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
