from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';raw=(T/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_text()
start=raw.index('void CamssVfeData::coarseReady(');brace=raw.index('{',start);end=brace+1;depth=1
while depth:depth+=(raw[end]=='{')-(raw[end]=='}');end+=1
W=P/'retention-test';W.mkdir(exist_ok=True);(W/'coarse-ready-body-private.cpp').write_text(raw[start:end]+'\n');shutil.copyfile(HERE/'retention-test.cpp',W/'test.cpp')
q=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie','-I'+str(W),str(W/'test.cpp'),'-o',str(W/'test')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(W/'test')],capture_output=True);assert not q.returncode,q.stderr.decode();assert b'COARSE_RETENTION_PASS' in q.stdout
assert 'sequence!=images_.begin()->first)return;' in raw
r=dict(stage=435,actual_coarse_ready_body=True,waiting_full_pd10_not_evicted=True,unclaimed_sofs_bounded=True,stale_pd10_requeued=True,oldest_full_guard_present=True,full_finish_body_not_host_executed=True,host_asan_ubsan=True,passed=True)
(HERE/'retention-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
