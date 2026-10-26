"""Build an independent release with coherent embedded BT modules and the VFE175 standard parameter queue and capability guards."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,stat,subprocess,sys,tarfile,time
import host

ROOT=Path(__file__).resolve().parent;PRIVATE=host.PRIVATE
TREE=Path('/mnt/samurai-full282/source354')
sys.path.insert(0,str(ROOT.parent/'kernel284'))
from storage import mounted_build
BUILD=mounted_build()
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
COMMIT='ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert 'CONFIG_LOCALVERSION="-rmx1931-samurai-k363"' in (BUILD/'.config').read_text()
marker=PRIVATE/'boot-build-state-private.json'
backup=PRIVATE/'previous-build-artifacts'
assert backup.is_dir()

def snapshot(root):
 rows={}
 for p in root.rglob('*'):
  i=p.lstat();r=dict(mode=stat.S_IMODE(i.st_mode),uid=i.st_uid,gid=i.st_gid)
  if p.is_symlink():r.update(kind='symlink',target=os.readlink(p))
  elif p.is_file():r.update(kind='file',sha256=sha(p))
  elif p.is_dir():r.update(kind='directory')
  else:r.update(kind='special',rdev=i.st_rdev)
  rows[str(p.relative_to(root))]=r
 return rows

original=BUILD.parent/'input-initramfs293';payload=BUILD.parent/'input-initramfs363'
assert original.is_dir() and not original.is_symlink() and payload.is_dir()
initial=snapshot(original);assert len(initial)==396
existing_input=snapshot(payload)
assert {n for n in initial if initial[n]!=existing_input[n]}=={'lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']}
before=(backup/'.config').read_text()

epoch=int(git('show','-s','--format=%ct',COMMIT))
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
 KBUILD_BUILD_VERSION='363',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',
 KBUILD_BUILD_TIMESTAMP=datetime.fromtimestamp(epoch,timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'),TMPDIR=str(BUILD.parent/'tmp'))
base=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j8','W=1']
module_root=BUILD.parent/'modules363';assert not module_root.exists()
phases=json.loads((PRIVATE/'boot-before-resume-private.json').read_text())['phases'][:3];start_all=time.monotonic();state=dict(stage=363,commit=COMMIT,terminal=False,worker=os.getpid())
def phase(name,args):
 start=time.monotonic();log=PRIVATE/('boot-'+name+'-resume1-private.log')
 with log.open('xb') as out:
  child=subprocess.Popen(base+args,env=env,stdout=out,stderr=subprocess.STDOUT)
  state.update(phase=name,child_pid=child.pid);marker.write_text(json.dumps(state,indent=2)+'\n')
  print(json.dumps(dict(phase=name,worker=os.getpid(),child=child.pid,started=True)),flush=True);ret=child.wait()
 diagnostics=[l for l in log.read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
 phases.append(dict(name=name,exit=ret,seconds=round(time.monotonic()-start,2),diagnostic_count=len(diagnostics),
  camss_diagnostics=[l for l in diagnostics if 'drivers/media/platform/qcom/camss/' in l]))
 state['phases']=phases;marker.write_text(json.dumps(state,indent=2)+'\n');assert ret==0,(name,ret)
 if name=='camss-werror':assert not diagnostics,diagnostics
try:
 release=(BUILD/'include/config/kernel.release').read_text().strip()
 assert release=='7.3.0-rc6-rmx1931-samurai-k363+'
 changed=['lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']]
 final_input=snapshot(payload)
 phase('image-modules',['Image','modules','qcom/sm8150-samurai.dtb'])
 phase('install-modules',['INSTALL_MOD_PATH='+str(module_root),'INSTALL_MOD_STRIP=1','modules_install'])
 assert snapshot(original)==initial and snapshot(payload)==final_input
 stage=module_root/'lib/modules'/release;assert stage.is_dir()
 for name in ['build','source']:
  p=stage/name
  if p.is_symlink():p.unlink()
 modules=list(stage.rglob('*.ko'));assert len(modules)==778
 for p in modules:assert subprocess.check_output(['modinfo','-F','vermagic',str(p)],text=True).split()[0]==release
 for target in payload.rglob('*.ko'):
  matches=list(stage.rglob(target.name));assert len(matches)==1 and matches[0].read_bytes()==target.read_bytes()
 depmod=subprocess.run(['depmod','-e','-F',str(BUILD/'System.map'),'-b',str(module_root),release],capture_output=True)
 (PRIVATE/'boot-depmod-private.log').write_bytes(depmod.stdout+depmod.stderr);assert depmod.returncode==0 and not depmod.stdout and not depmod.stderr
 config_map=lambda t:{l.split('=',1)[0]:l for l in t.splitlines() if l.startswith('CONFIG_') or l.startswith('# CONFIG_')}
 a=config_map(before);b=config_map((BUILD/'.config').read_text())
 changes={k:dict(before=a.get(k),after=b.get(k)) for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
 assert {'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'} <= set(changes) and all(k in {'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'} or 'VIDEO_QCOM_CAMSS_ICP_A5' in k for k in changes),changes
 assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
 names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','vmlinux','Module.symvers','modules.order','.config']
 artifacts={n:dict(bytes=(BUILD/n).stat().st_size,sha256=sha(BUILD/n)) for n in names}
 assert artifacts['arch/arm64/boot/Image']['bytes']<64*1024*1024-1024*1024
 assert artifacts['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']['sha256']=='dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
 inventory={str(p.relative_to(stage)):sha(p) for p in modules};(PRIVATE/'installed-module-inventory-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
 archive=PRIVATE/'modules-k363-private.tar.gz';assert not archive.exists()
 with tarfile.open(archive,'w:gz') as tar:tar.add(stage,arcname='usr/lib/modules/'+release)
 report=dict(stage=363,commit=COMMIT,terminal=True,phases=phases,seconds=round(time.monotonic()-start_all,2),release=release,
  artifacts=artifacts,module_count=778,all_installed_vermagic_match=True,depmod_unresolved_symbols=0,
  embedded_input_entries=len(final_input),embedded_modules_rebuilt=sorted(changed),all_three_embedded_modules_match_installed_tree=True,
  old_initramfs293_preserved=True,changed_config_keys=sorted(changes),camss_component_count=len((BUILD/'drivers/media/platform/qcom/camss/qcom-camss.mod').read_text().splitlines()),
  module_archive=dict(bytes=archive.stat().st_size,sha256=sha(archive)),not_deployed=True,boot_not_yet_verified=True)
 assert report['camss_component_count']>=40
 report.update(intentional_parallelism_resume=True,parallel_jobs=8,previous_attempt_seconds=json.loads((PRIVATE/'boot-before-resume-private.json').read_text())['seconds'])
 (ROOT/'boot-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (PRIVATE/'boot-candidate-result-private.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(terminal=True,phase='finished',exit_code=0,seconds=report['seconds']);marker.write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)
except BaseException:
 state.update(terminal=True,phase='failed',exit_code=1,seconds=round(time.monotonic()-start_all,2));marker.write_text(json.dumps(state,indent=2)+'\n');raise
