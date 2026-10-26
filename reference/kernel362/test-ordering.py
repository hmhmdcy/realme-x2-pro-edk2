from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();old=storage.previous.candidate()
backing=new.parent/'ordering362-test';backing.mkdir(exist_ok=True);shutil.copyfile(HERE/'ordering-regression.cpp',backing/'probe.cpp')
results=[]
for label,tree in [('old',old),('new',new)]:
    text=(tree/'src/libcamera-v0.7.2/src/libcamera/pipeline_handler.cpp').read_text()
    start=text.index('void PipelineHandler::doQueueRequests(Camera *camera)');end=text.index('\n/**',start)
    (backing/'ordering-method.inc').write_text(text[start:end])
    q=subprocess.run(['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-D_GLIBCXX_ASSERTIONS','-fsanitize=address,undefined',str(backing/'probe.cpp'),'-o',str(backing/'probe')],capture_output=True)
    assert not q.returncode,q.stderr.decode()
    q=subprocess.run([str(backing/'probe')],capture_output=True,timeout=10)
    (host.PRIVATE/f'ordering-{label}.log').write_bytes(q.stdout+q.stderr)
    assert (q.returncode==0)==(label=='new'),(label,q.stderr.decode()[-2000:])
    results.append(dict(source=label,exit_code=q.returncode,expected_pass=label=='new',matched=True))
report=dict(stage=362,verbatim_common_method=True,same_camera_nested_order=True,other_camera_progress=True,prepared_and_capacity_resume=True,asan_ubsan=True,tests=results,passed=True)
(HERE/'ordering-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
