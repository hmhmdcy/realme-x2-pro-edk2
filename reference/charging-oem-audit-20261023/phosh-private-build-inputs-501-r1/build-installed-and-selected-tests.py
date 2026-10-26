"""After confirmed owned Ninja SIGINT/join, build all installed outputs and two GTK tests incrementally."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import time

HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
BUILD=ROOT/'work/build/phosh-external-power'
sha=lambda b:hashlib.sha256(b).hexdigest()
stopped=json.loads((BASE/'phosh-build-state-private.json').read_bytes())
assert stopped['terminal'] and stopped['returncode']==254
interrupt=json.loads((BASE/'default-all-sigint-private.json').read_bytes())
observed=[]
for original in interrupt['descendants_before']:
    p=Path('/proc',str(original['pid']))
    if not p.exists():observed.append({'pid':original['pid'],'status':'absent'});continue
    try:f=(p/'stat').read_text().rsplit(')',1)[1].split()
    except FileNotFoundError:observed.append({'pid':original['pid'],'status':'absent'});continue
    assert int(f[19])!=original['startticks'],(original,f[0])
    observed.append({'pid':original['pid'],'status':'old_owned_process_gone_PID_reused'})
targets=json.loads((BUILD/'meson-info/intro-targets.json').read_bytes())
selected=set()
for target in targets:
    if target['installed']:
        for filename in target['filename']:
            selected.add(str(PurePosixPath(filename).relative_to('/work/build/phosh-external-power')))
for name in ['test-status-icon','test-status-icons-box']:
    found=[t for t in targets if t['name']==name]
    assert len(found)==1
    for filename in found[0]['filename']:
        selected.add(str(PurePosixPath(filename).relative_to('/work/build/phosh-external-power')))
options_raw=(BUILD/'meson-info/intro-buildoptions.json').read_bytes()
options={p['name']:p['value'] for p in json.loads(options_raw)}
for name,value in [('b_lto',True),('phoc_tests','disabled'),('man',True),('bindings-lib',True),('wrap_mode','nodownload')]:assert options[name]==value
command=['chroot',str(ROOT),'ninja','-C','/work/build/phosh-external-power','-j4',*sorted(selected)]
env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
state={'phase':'installed-targets-and-selected-GTK-tests','terminal':False,'targets':sorted(selected),
       'all_actual_Meson_installed_target_outputs_included':True,
       'selected_tests':['status-icon','status-icons-box'],'old_processes':observed,
       'original_Meson_options_unchanged_sha256':sha(options_raw),'source_sha256':sha(Path(__file__).read_bytes())}
marker=BASE/'installed-target-build-state-private.json'
assert not marker.exists()
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
save();start=time.monotonic()
with (BASE/'phosh-installed-targets-build-private.log').open('xb') as log:
    p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env)
    state.update(pid=p.pid,argv=command);save();rc=p.wait()
assert options_raw==(BUILD/'meson-info/intro-buildoptions.json').read_bytes()
state.update(phase='installed-target-build-passed' if rc==0 else 'installed-target-build-failed',terminal=True,returncode=rc,
             seconds=round(time.monotonic()-start,3),log_sha256=sha((BASE/'phosh-installed-targets-build-private.log').read_bytes()))
save();(HERE/'installed-target-build-result.json').write_text(json.dumps(state,indent=2)+'\n')
print((BASE/'phosh-installed-targets-build-private.log').read_text(errors='replace')[-7000:])
print(json.dumps({'returncode':rc,'seconds':state['seconds'],'target_count':len(selected),
                  'result_sha256':sha((HERE/'installed-target-build-result.json').read_bytes())}))
raise SystemExit(rc)
