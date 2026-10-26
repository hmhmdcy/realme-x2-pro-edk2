"""Run actual statsProcessed/queueIspUpdate with nested event dispatch."""
from pathlib import Path
import json,re,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2'
s=(tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_text()
def function(name,next_name):
 a=s.index('void CamssVfeData::'+name+'(');b=s.index('\nvoid CamssVfeData::'+next_name,a);return s[a:b]
stats=function('statsProcessed','finish');update=function('queueIspUpdate','frameStart')
source=(HERE/'stats-provider.h').read_text()+stats+update+(HERE/'stats-cases.cpp').read_text();(P/'stats-model.cpp').write_text(source)
q=subprocess.run(['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',str(P/'stats-model.cpp'),'-o',str(P/'stats-model')],capture_output=True)
(P/'stats-model-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
q=subprocess.run([str(P/'stats-model')],capture_output=True);(P/'stats-model-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
m=re.search(r'cases=(\d+) passed=1',q.stdout.decode());assert m
# The real old ordering must reproduce the false missing-statistics decision.
old=stats.replace('/* Publish the same-SOF histogram before any synchronous IPA dispatch. */','if (!statistics.status && statistics.parametersKnown) queueIspUpdate(statistics.ispUpdate);',1)
old=old.replace('if (!running_ || epoch != epoch_) return;\n if (!statistics.status && statistics.parametersKnown) queueIspUpdate(statistics.ispUpdate);\n if (!running_ || epoch != epoch_) return;','',1)
counterexample=(HERE/'stats-provider.h').read_text()+old+update+'''int main(){CamssVfeData d;FrameBuffer b;d.pendingStats_[100]={1,&b,true};d.statsProcessed(1,1,100,{},{});assert(d.fallback==1 && d.paired==0);}\n'''
(P/'old-stats-counterexample.cpp').write_text(counterexample)
q=subprocess.run(['g++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',str(P/'old-stats-counterexample.cpp'),'-o',str(P/'old-stats-counterexample')],capture_output=True);assert not q.returncode,q.stderr.decode()[-1000:]
q=subprocess.run([str(P/'old-stats-counterexample')],capture_output=True);(P/'old-stats-counterexample.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-1000:]
r=dict(stage=421,cases=int(m[1]),actual_stats_processed_and_parameter_queue_functions=True,asan_ubsan=True,old_order_reproduces_premature_missing_statistics=True,
 fixed_order_pairs_before_parameter_dispatch=True,stop_during_focus_or_parameter_dispatch_does_not_reuse_freed_buffers=True,
 model_not_hardware_scheduling_proof=True,passed=True)
(HERE/'statistics-reentry-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
