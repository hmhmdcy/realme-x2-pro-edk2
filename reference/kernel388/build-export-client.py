from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;output=P/'export-lifetime-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(HERE/'export-lifetime-client.c'),'-o',str(output)],capture_output=True)
(P/'export-client-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
report=dict(stage=388,aarch64_static=True,private_path=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),export_fd_and_mmap_lifetimes_separate=True,passed=True)
(HERE/'export-client-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
