"""Build a static V4L2 client with two actual geometry configurations."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
base=(HERE.parent/'kernel402/gamma-client.c').read_text();base=base[:base.index('\nstatic int test_nv21;')]
extra=(HERE.parent/'kernel392/cancel-client.c').read_text();extra=extra[extra.index('struct test_context {'):extra.index('static void verify_frame(')]
extra=extra.replace('.width=640,.height=480,.stride=640,.frames=2','.width=test_width,.height=480,.stride=test_width,.frames=2,.nv21=test_nv21')
source=base+'\nstatic int test_nv21;\nstatic unsigned test_width=640;\n'+extra+'\n'+(HERE/'ltm-client-tail.c').read_text();assert len(re.findall(r'\bint main\(',source))==1
file=HERE/'ltm-client.c';file.write_text(source);binary=P/'colour-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(binary)],capture_output=True);(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
report=dict(stage=406,aarch64_static_v4l2_client=True,widths=[640,650],height=480,formats=['NV12','NV21'],fixed_modes=13,frames=52,input_unchanged_output_tail_sequence_timestamp_crc_checked=True,pixel_correctness_analyzed_separately_on_host=True,bytes=binary.stat().st_size,sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),private_path=str(binary),passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
