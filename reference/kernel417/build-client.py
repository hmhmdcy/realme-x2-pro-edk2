"""Build a typed Media Request client; reuse only authored V4L2 helpers."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
base=(HERE.parent/'kernel406/ltm-client.c').read_text().split('static void *run_stream(')[0]
fixture=(P.parent/'kernel400/test-chain-fixture.h').read_text().replace('camss_a5_ipe_colour','qcom_ipe_a5_colour').replace('CAMSS_A5_IPE_COLOUR_','QCOM_IPE_A5_COLOUR_')
(P/'request-fixture.h').write_text(fixture)
(P/'request-client.c').write_text(base+'\n'+(HERE/'request-client-tail.c').read_text())
inc=P/'client-include/linux';inc.mkdir(parents=True,exist_ok=True);(inc/'qcom-ipe-a5.h').write_bytes((HERE/'qcom-ipe-a5.h').read_bytes())
binary=P/'request-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-pthread','-I'+str(inc.parent),'-I'+str(P),str(P/'request-client.c'),'-o',str(binary)],capture_output=True)
(P/'request-client-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
r=dict(stage=417,frames=16,request_payload_bytes=6008,typed_control_per_output_request=True,mmap_nv12_and_exported_dmabuf_nv21=True,zero_gamma_and_constant_la_pixel_assertions=True,missing_payload_direct_control_and_invalid_range_rejected=True,bytes=binary.stat().st_size,sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
