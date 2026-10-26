"""Exercise owned observations and the actual aggregate-completion function."""
from pathlib import Path
import json,re,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tree=storage.candidate()/'src/libcamera-v0.7.2';source=(tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_text()
a=source.index('void CamssVfeData::tryComplete(');b=source.index('\nvoid CamssVfeData::paramsReady',a)
actual=source[a:b];(P/'aggregate-model.cpp').write_text((HERE/'aggregate-provider.h').read_text()+actual+(HERE/'aggregate-cases.cpp').read_text())
rows=[]
for name,file in [('history',HERE/'history-model.cpp'),('aggregate',P/'aggregate-model.cpp')]:
 binary=P/(name+'-model');args=['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie','-I'+str(HERE),str(file),'-o',str(binary)]
 q=subprocess.run(args,capture_output=True);(P/(name+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 q=subprocess.run([str(binary)],capture_output=True);(P/(name+'-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
 m=re.search(r'cases=(\d+) passed=1',q.stdout.decode());assert m;rows.append(dict(name=name,cases=int(m[1]),asan_ubsan=True))
r=dict(stage=421,models=rows,actual_pipeline_aggregate_function=True,raw_pair_failure_timeout_stop_and_no_ipe_discard=True,
 owned_histogram_copy_and_bounded_epoch_tokens=True,out_of_order_success_never_reverses_history=True,
 observations_only_not_tmc_numerical_state=True,provider_not_hardware_concurrency_proof=True,passed=True)
(HERE/'history-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
