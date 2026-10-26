"""Compile the actual before/after method and force nested IPC callbacks."""
from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent
current=storage.candidate();baseline=storage.previous.candidate()
backing=current.parent/'submit362-test';backing.mkdir(exist_ok=True)
shutil.copyfile(HERE/'submit-regression.cpp',backing/'probe.cpp')
relative='src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
scenarios=['recursive-control','retry-order','stop-during-call','restart-during-call','parameter-recursion','recursive-stats','stop-during-stats','error-unlocks']
results=[]
for label,tree in [('old',baseline),('new',current)]:
    s=(tree/relative).read_text();start=s.index('void CamssVfeData::submitStatistics()');end=s.index('\nvoid CamssVfeData::statsProcessed',start)
    (backing/'method.inc').write_text(s[start:end])
    args=['g++','-std=c++20','-g','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D_GLIBCXX_ASSERTIONS','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(backing/'probe.cpp'),'-o',str(backing/'probe')]
    q=subprocess.run(args,capture_output=True);assert not q.returncode,q.stderr.decode()
    for scenario in (['recursive-control','retry-order','restart-during-call','recursive-stats'] if label=='old' else scenarios):
        q=subprocess.run([str(backing/'probe'),scenario],capture_output=True,timeout=10)
        (host.PRIVATE/f'submit-{label}-{scenario}.log').write_bytes(q.stdout+q.stderr)
        expected=label=='new' or scenario=='recursive-stats'
        assert (q.returncode==0)==expected,(label,scenario,q.returncode,q.stderr.decode()[-1200:])
        results.append(dict(source=label,scenario=scenario,exit_code=q.returncode,expected_pass=expected,matched=True))
report=dict(stage=362,verbatim_production_method=True,asan_ubsan=True,tests=results,passed=True)
(HERE/'submit-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
