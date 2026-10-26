from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel392/cancel-client.c').read_text().replace('int main(int argc,char **argv)','int inherited392_main(int argc,char **argv)')+'\n'+(HERE/'colour-client-tail.c').read_text()
file=HERE/'colour-client.c';file.write_text(source);out=P/'colour-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(out)],capture_output=True);(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
d=dict(stage=397,aarch64_static_v4l2_client=True,fixed_matrix_modes=4,bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),private_path=str(out),passed=True);(HERE/'client-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
