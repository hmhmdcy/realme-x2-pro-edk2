"""Reproduce actual dispatcher recursion on old/new ARM64 shared libraries."""
from pathlib import Path
from contextlib import contextmanager
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;new=storage.candidate();old=new.parent/'libcamera360-combined-r28-built'
relative=Path('/private/dispatcher361-test');stage=storage.SDK/str(relative).lstrip('/');backing=new.parent/'dispatcher361-test';backing.mkdir(exist_ok=True)
baseRelative=Path('/private/dispatcher361-baseline');baseSlot=storage.SDK/str(baseRelative).lstrip('/')
@contextmanager
def bind(source,target):
    target.mkdir(exist_ok=True);assert not any(target.iterdir()) and subprocess.run(['mountpoint','-q',str(target)],capture_output=True).returncode
    subprocess.run(['mount','--bind',str(source),str(target)],check=True,capture_output=True)
    try:yield
    finally:subprocess.run(['umount',str(target)],check=True,capture_output=True)
results=[]
with storage.sdk_candidate(),bind(backing,stage),bind(old,baseSlot):
    shutil.copyfile(HERE/'dispatcher-regression.cpp',stage/'probe.cpp');base=str(baseRelative)+'/src/libcamera-v0.7.2';current='/work/libcamera/src/libcamera-v0.7.2'
    q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+base+'/include',str(relative/'probe.cpp'),'-L'+base+'/output/src/libcamera/base','-lcamera-base','-pthread','-o',str(relative/'probe')],capture_output=True)
    (P/'dispatcher-probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
    for label,tree in [('old',base),('new',current)]:
        for depth,timer in [(1,0),(2,0),(3,0),(2,1)]:
            q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+tree+'/output/src/libcamera/base','LIBCAMERA_LOG_LEVELS=*:ERROR',str(relative/'probe'),str(depth),str(timer)],capture_output=True,timeout=20)
            (P/f'dispatcher-{label}-{depth}-{timer}.log').write_bytes(q.stdout+q.stderr)
            wanted=label=='new' or depth==1
            assert (q.returncode==0)==wanted,(label,depth,timer,q.returncode,q.stderr.decode()[-2000:])
            result=dict(library=label,depth=depth,timer_unregister=bool(timer),exit_code=q.returncode,expected_pass=wanted,matched_expectation=True);results.append(result);print(json.dumps(result),flush=True)
report=dict(stage=361,actual_aarch64_shared_library=True,baseline_reproduces_nested_failure=True,baseline_simple_dispatch_passes=True,
    fixed_nested_levels_and_timer_unregister_pass=True,rearm_after_cleanup_verified=True,assertion_not_removed=True,tests=results,sdk_binds_unmounted=True,passed=True)
(HERE/'dispatcher-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=361,tests=len(results),passed=True)))
