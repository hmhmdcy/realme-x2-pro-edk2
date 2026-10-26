"""Run the actual wrapper with reordered requests, faults and callback reentry."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
inc=P/'model-include/linux';inc.mkdir(parents=True,exist_ok=True);(inc/'qcom-ipe-a5.h').write_bytes((HERE.parent/'kernel417/qcom-ipe-a5.h').read_bytes())
def clean(p):return '\n'.join(l for l in p.read_text().splitlines() if not l.startswith(('#include','#pragma')))+'\n'
source=(HERE/'ipe-model-provider.h').read_text()+'\n#include <array>\n#define private public\n'+clean(HERE/'camss_ipe.h')+'\n#undef private\n'+clean(HERE/'camss_ipe.cpp')+(HERE/'ipe-model-cases.cpp').read_text()
(P/'ipe-model.cpp').write_text(source)
q=subprocess.run(['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-I'+str(inc.parent),str(P/'ipe-model.cpp'),'-o',str(P/'ipe-model')],capture_output=True)
(P/'ipe-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'ipe-model')],capture_output=True);(P/'ipe-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4000:]
m=re.fullmatch(r'IPE_REQUEST_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert m
r=dict(stage=418,cases=int(m[1]),actual_wrapper_source=True,asan_ubsan=True,three_completion_orders=6,request_callback_unwinds_before_pool_destruction=True,
    partial_qbuf_control_queue_reinit_and_streamoff_failures=True,stale_queued_completion_serial_checked=True,
    plane_wrapper_request_fd_and_scheduler_ownership_balanced=True,legacy_explicit_iq_rejected=True,provider_not_kernel_concurrency_proof=True,
    source_sha256=hashlib.sha256((HERE/'camss_ipe.cpp').read_bytes()).hexdigest(),passed=True)
(HERE/'ipe-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
