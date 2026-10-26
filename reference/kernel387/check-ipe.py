from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def clean(p):return '\n'.join(line for line in p.read_text().splitlines() if not line.startswith('#include') and not line.startswith('#pragma'))+'\n'
source=(HERE/'ipe-model-provider.h').read_text()+'\n#define private public\n'+clean(HERE/'camss_ipe.h')+'\n#undef private\n'+clean(HERE/'camss_ipe.cpp')+(HERE/'ipe-model-cases.cpp').read_text()
model=P/'ipe-model.cpp';model.write_text(source)
q=subprocess.run(['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',str(model),'-o',str(P/'ipe-model')],capture_output=True)
(P/'ipe-model-build.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-4000:]
q=subprocess.run([str(P/'ipe-model')],capture_output=True);(P/'ipe-model-run.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()[-4000:]
match=re.fullmatch(r'IPE_MODEL cases=(\d+) passed=1\n',q.stdout.decode());assert match
report=dict(stage=387,actual_wrapper_source=True,asan_ubsan=True,cases=int(match[1]),format_before_any_buffers=True,both_dq_orders=True,partial_qbuf_failure=True,streamoff_failures_wait_close=True,failed_streamoff_reopen_rejected=True,own_job_watchdog_armed_and_disarmed=True,timeout_and_reentrant_stop=True,provider_not_kernel_concurrency_proof=True,source_sha256=hashlib.sha256((HERE/'camss_ipe.cpp').read_bytes()).hexdigest(),passed=True)
(HERE/'ipe-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
