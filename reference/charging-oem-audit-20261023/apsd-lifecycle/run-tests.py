"""Small exact-OEM lifecycle fixture; host compiler, no phone/SDK."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
spec=importlib.util.spec_from_file_location('restore_local',HERE/'restore.py')
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)
manifest=json.loads((HERE/'source-manifest.json').read_bytes())
provenance=[]
for row in manifest['functions']:
    source=(HERE/'oem'/row['path'].replace('/','--')).read_text()
    body,line=restore.extract(source,row['function'])
    assert line==row['line'] and sha(body.encode())==row['sha256']
    assert body in (HERE/'oem-functions.inc').read_text()
    provenance.append(row['function'])
assert '-DVENDOR_EDIT' in (HERE/'oem/Makefile').read_text()
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
       '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g']
compile_run=subprocess.run(['gcc',*flags,str(HERE/'test-oem-lifecycle.c'),'-o',str(HERE/'test-oem-lifecycle')],capture_output=True)
run=subprocess.run([str(HERE/'test-oem-lifecycle')],capture_output=True) if compile_run.returncode==0 else None
result=dict(passed=compile_run.returncode==0 and run.returncode==0 if run else False,
    actual_oem_function_groups=7,full_function_provenance_checked=provenance,
    flags=flags,compile_returncode=compile_run.returncode,
    compile_stdout=compile_run.stdout.decode(),compile_stderr=compile_run.stderr.decode(),
    runtime_returncode=run.returncode if run else None,
    runtime_stdout=run.stdout.decode() if run else '',runtime_stderr=run.stderr.decode() if run else '',
    sha256={p.name:sha(p.read_bytes()) for p in [HERE/'test-oem-lifecycle.c',HERE/'tested-oem-smb.inc',
        HERE/'tested-oem-phy.inc',HERE/'oem-registers.inc',HERE/'oem-functions.inc',HERE/'source-manifest.json']},
    phone_accessed=False,ssh_executed=False,sdk_accessed=False,hardware_writes_performed=False,
    old_float_12768_and_14_tests_repeated=False,
    scope='exact complete OEM functions, fake register/regulator/PHY OS boundaries; no integration or hardware acceptance')
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
