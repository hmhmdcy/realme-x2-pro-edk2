"""Build one coherent candidate Image and modules; write live/results only privately."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import time
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD=Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
COMMIT='18b48939788bc7f95fb2999ea986846a67f0c62c'
git=lambda *args:subprocess.check_output(['git','-C',str(TREE),*args],text=True).strip()
assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
assert not sys.argv[1:] or sys.argv[1:] in [['r2'],['r3']]
suffix='-'+sys.argv[1] if sys.argv[1:] else ''
if suffix=='-r3':
    backing=host.PRIVATE/'full-kernel-build282.ext4'
    mount=Path('/mnt/samurai-full282')
    assert backing.is_file() and not backing.is_symlink() and backing.stat().st_size==32*1024**3
    assert mount.is_dir() and not mount.is_symlink()
    exact=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(mount)]
    if not exact:
        assert not any(mount.iterdir()), 'Refuse to hide unrelated files with a mount'
        subprocess.run(['mount','-o','loop,noatime',str(backing),str(mount)],check=True,capture_output=True)
    mounted=subprocess.check_output(['findmnt','-n','-o','FSTYPE,SOURCE,TARGET','--target',str(mount)],text=True).split()
    assert len(mounted)==3 and mounted[0]=='ext4' and mounted[1].startswith('/dev/loop') and mounted[2]==str(mount)
    loop=Path(mounted[1]).name
    assert Path(Path('/sys/class/block',loop,'loop/backing_file').read_text().strip()).resolve()==backing.resolve()
    BUILD=mount/'build'
    assert (BUILD/'.config').is_file() and (mount/'tmp').is_dir()
config=(BUILD/'.config').read_text()
required=['I2C_QCOM_CCI','MFD_QCOM_PM8008','REGULATOR_QCOM_PM8008','VIDEO_QCOM_CAMSS',
          'VIDEO_IMX319','VIDEO_IMX471','VIDEO_LC898219XI','VIDEO_S5KGW1','VIDEO_S5K3M5']
assert all('CONFIG_'+name+'=m' in config.splitlines() for name in required), 'Incomplete multi-camera configuration'
marker=host.PRIVATE/('full-kernel'+suffix+'-build-state-private.json')
log=(host.PRIVATE if suffix=='-r3' else BUILD)/('full282'+suffix+'-w1-private.log')
assert not marker.exists() and not log.exists(), 'Inspect the original handle before any retry'
epoch=int(git('show','-s','--format=%ct',COMMIT))
stamp=datetime.fromtimestamp(epoch,timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y')
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],
    RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='282',KBUILD_BUILD_USER='builder',
    KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_TIMESTAMP=stamp)
if suffix=='-r3':
    env['TMPDIR']=str(BUILD.parent/'tmp')
command=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
         '-j3','W=1','Image','modules','qcom/sm8150-samurai.dtb']
state=dict(stage=282,commit=COMMIT,pid=os.getpid(),terminal=False,command=command,
    started_utc=datetime.now(timezone.utc).isoformat(),config_sha256=hashlib.sha256((BUILD/'.config').read_bytes()).hexdigest())
start=time.monotonic()
with log.open('xb') as output:
    child=subprocess.Popen(command,env=env,stdout=output,stderr=subprocess.STDOUT)
    state['child_pid']=child.pid
    marker.write_text(json.dumps(state,indent=2)+'\n')
    receipt={k:v for k,v in state.items() if k not in ['pid','child_pid']}
    receipt.update(started_not_completed=True,no_phone_changes=True,not_deployed=True,
                   progress_and_result_retained_privately=True)
    receipt['all_nine_camera_configs_enabled_as_modules']=True
    (ROOT/('full'+suffix+'-build-start-validation.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(started=True,source=COMMIT,pid=os.getpid(),child_pid=child.pid,
                         private_marker=str(marker)),indent=2),flush=True)
    code=child.wait()
state.update(terminal=True,exit=code,seconds=round(time.monotonic()-start,2),
             finished_utc=datetime.now(timezone.utc).isoformat())
marker.write_text(json.dumps(state,indent=2)+'\n')
text=log.read_text(errors='replace')
diagnostics=[line for line in text.splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()]
report={k:v for k,v in state.items() if k not in ['pid','child_pid']}
report.update(diagnostic_count=len(diagnostics),
    camss_diagnostics=[line for line in diagnostics if 'drivers/media/platform/qcom/camss/' in line],
    source_commit_still_matches=git('rev-parse','HEAD')==COMMIT,
    source_still_clean=not git('status','--porcelain'),not_deployed=True,
    complete_hardware_isp_not_implemented=True)
if code==0:
    assert report['source_commit_still_matches'] and report['source_still_clean']
    artifacts=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
               'vmlinux','Module.symvers','modules.order']
    report['artifacts']={name:dict(bytes=(BUILD/name).stat().st_size,
        sha256=hashlib.sha256((BUILD/name).read_bytes()).hexdigest()) for name in artifacts}
    modules=[name for name in (BUILD/'modules.order').read_text().splitlines() if name]
    report['module_count']=len(modules)
    report['all_ordered_modules_present']=all((BUILD/name).is_file() for name in modules)
    assert report['all_ordered_modules_present'] and not report['camss_diagnostics']
(host.PRIVATE/('full-kernel'+suffix+'-build-result-private.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
assert code==0, 'Full build is terminal with failure; inspect its original log, do not blindly restart'
