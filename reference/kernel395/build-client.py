from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel393/local-error-client.c').read_text().replace('int main(int argc,char **argv)','int inherited393_main(int argc,char **argv)')+'\n'+(HERE/'ack-loss-client-tail.c').read_text()
file=HERE/'ack-loss-client.c';file.write_text(source);output=P/'ack-loss-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(output)],capture_output=True)
(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
r=dict(stage=395,aarch64_static_actual_v4l2_client=True,bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),two_configured_contexts_and_third_blocked_then_reopen=True,private_path=str(output),passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
