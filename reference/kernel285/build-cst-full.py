"""Build the committed CST candidate in the verified existing E-drive volume."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel285')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
sys.path.insert(0,str(ROOT.parent/'kernel284'))
from storage import mounted_build
BUILD=mounted_build()
COMMIT='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
assert hashlib.sha256((BUILD/'.config').read_bytes()).hexdigest()=='0c26bd9147ac31b92d824b8dbd529384772be3c8ae819314240cdd6cbde3a6ca'
marker=PRIVATE/'cst-full-build-state-private.json';assert not marker.exists()
# Save the preceding complete Demosaic candidate's essential artifacts first.
old=json.loads((ROOT.parent/'kernel284/demosaic-full-build-validation.json').read_text())
backup=PRIVATE/'completed-demosaic284';assert not backup.exists();backup.mkdir()
for name,info in old['artifacts'].items():
    data=(BUILD/name).read_bytes();assert hashlib.sha256(data).hexdigest()==info['sha256']
    (backup/Path(name).name).write_bytes(data)
epoch=int(git('show','-s','--format=%ct',COMMIT))
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
         KBUILD_BUILD_VERSION='285',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',
         KBUILD_BUILD_TIMESTAMP=datetime.fromtimestamp(epoch,timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'),
         TMPDIR=str(BUILD.parent/'tmp'))
base=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1']
state=dict(stage=285,commit=COMMIT,worker=os.getpid(),terminal=False,started_utc=datetime.now(timezone.utc).isoformat())
phases=[];begin=time.monotonic()
for name,extra in [('camss-werror',['KCFLAGS=-Werror','drivers/media/platform/qcom/camss/qcom-camss.o','qcom/sm8150-samurai.dtb']),
                   ('full',['Image','modules','qcom/sm8150-samurai.dtb'])]:
    log=PRIVATE/('cst-'+name+'-build-private.log');command=base+extra;start=time.monotonic()
    with log.open('xb') as output:
        child=subprocess.Popen(command,env=env,stdout=output,stderr=subprocess.STDOUT)
        state.update(phase=name,child_pid=child.pid,command=command)
        marker.write_text(json.dumps(state,indent=2)+'\n')
        print(json.dumps(dict(phase=name,worker=os.getpid(),child=child.pid,started=True)),flush=True)
        code=child.wait()
    diagnostics=[l for l in log.read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
    phases.append(dict(name=name,exit=code,seconds=round(time.monotonic()-start,2),diagnostic_count=len(diagnostics),
                       camss_diagnostics=[l for l in diagnostics if 'drivers/media/platform/qcom/camss/' in l]))
    if code or name=='camss-werror' and diagnostics:break
state.update(terminal=True,seconds=round(time.monotonic()-begin,2),phases=phases,finished_utc=datetime.now(timezone.utc).isoformat())
marker.write_text(json.dumps(state,indent=2)+'\n')
report={k:v for k,v in state.items() if k not in ['worker','child_pid','command']}
report.update(not_deployed=True,no_complete_hardware_isp_claim=True,source_still_matches=git('rev-parse','HEAD')==COMMIT,
              source_clean=not git('status','--porcelain'))
if len(phases)==2 and all(p['exit']==0 for p in phases):
    names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','vmlinux','Module.symvers','modules.order','.config']
    report['artifacts']={n:dict(bytes=(BUILD/n).stat().st_size,sha256=hashlib.sha256((BUILD/n).read_bytes()).hexdigest()) for n in names}
    order=(BUILD/'modules.order').read_text().splitlines();assert all(n.endswith('.o') for n in order)
    modules=[str(Path(n).with_suffix('.ko')) for n in order]
    hashes={n:hashlib.sha256((BUILD/n).read_bytes()).hexdigest() for n in modules}
    (PRIVATE/'cst-full-module-hashes-private.json').write_text(json.dumps(hashes,indent=2)+'\n')
    report.update(actual_ko_count=len(hashes),actual_ko_files_all_hashed=True)
    components=(BUILD/'drivers/media/platform/qcom/camss/qcom-camss.mod').read_text().splitlines()
    assert any(n.endswith('/camss-vfe-175-cst.o') for n in components)
    report['camss_component_count']=len(components)
    assert len(hashes)==778 and report['source_still_matches'] and report['source_clean']
    assert report['artifacts']['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']['sha256']=='dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
(PRIVATE/'cst-full-build-result-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
assert len(phases)==2 and all(p['exit']==0 and not p['camss_diagnostics'] for p in phases)
(ROOT/'cst-full-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
