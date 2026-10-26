from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel392/cancel-client.c').read_text().replace('int main(int argc,char **argv)','int inherited392_main(int argc,char **argv)')+'\n'+(HERE/'local-error-client-tail.c').read_text()
file=HERE/'local-error-client.c';file.write_text(source);output=P/'local-error-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(output)],capture_output=True)
(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
r=dict(stage=393,aarch64_static_actual_v4l2_client=True,bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),private_path=str(output),isolated_input_error_plus_cancel_concurrency=True,passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
