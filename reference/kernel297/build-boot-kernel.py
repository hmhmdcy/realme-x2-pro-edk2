"""Build an independent release with coherent embedded BT modules and the VFE175 standard parameter queue and capability guards."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,stat,subprocess,sys,tarfile,time
import host

ROOT=Path(__file__).resolve().parent;PRIVATE=host.PRIVATE
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
sys.path.insert(0,str(ROOT.parent/'kernel284'))
from storage import mounted_build
BUILD=mounted_build()
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
COMMIT='ab709d9670f6dcaa71858fd4f3e189522f669913'
assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(BUILD/'.config')=='82e39f7ea2ad2507417290cfbcd5754dd3f4ee431bb3a73b31e8f880e5e04233'
marker=PRIVATE/'boot-build-state-private.json';assert not marker.exists()
old=json.loads((ROOT.parent/'kernel296/boot-candidate-build-validation.json').read_text())
backup=PRIVATE/'completed-boot296';assert not backup.exists();backup.mkdir()
for name,row in old['artifacts'].items():
 assert sha(BUILD/name)==row['sha256'];shutil.copyfile(BUILD/name,backup/Path(name).name)

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

original=BUILD.parent/'input-initramfs293';payload=BUILD.parent/'input-initramfs297'
assert original.is_dir() and not original.is_symlink() and not payload.exists()
initial=snapshot(original);assert len(initial)==396
subprocess.run(['cp','-a',str(original),str(payload)],check=True);assert snapshot(payload)==initial
before=(BUILD/'.config').read_text()
for key,value in [('LOCALVERSION','-rmx1931-samurai-k297'),('INITRAMFS_SOURCE',str(payload))]:
 subprocess.run([str(TREE/'scripts/config'),'--file',str(BUILD/'.config'),'--set-str',key,value],check=True)
epoch=int(git('show','-s','--format=%ct',COMMIT))
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',
 KBUILD_BUILD_VERSION='297',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',
 KBUILD_BUILD_TIMESTAMP=datetime.fromtimestamp(epoch,timezone.utc).strftime('%a %b %d %H:%M:%S UTC %Y'),TMPDIR=str(BUILD.parent/'tmp'))
base=['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1']
module_root=BUILD.parent/'modules297';assert not module_root.exists()
phases=[];start_all=time.monotonic();state=dict(stage=297,commit=COMMIT,terminal=False,worker=os.getpid())
def phase(name,args):
 start=time.monotonic();log=PRIVATE/('boot-'+name+'-private.log')
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
 phase('configure',['olddefconfig'])
 phase('camss-werror',['KCFLAGS=-Werror','drivers/media/platform/qcom/camss/qcom-camss.o','qcom/sm8150-samurai.dtb'])
 phase('modules',['modules'])
 release=(BUILD/'include/config/kernel.release').read_text().strip()
 assert release=='7.3.0-rc6-rmx1931-samurai-k297+' and release!='7.3.0-rc6-rmx1931-samurai-k290+'
 changed=[]
 for target in payload.rglob('*.ko'):
  matches=list(BUILD.rglob(target.name));assert len(matches)==1
  shutil.copyfile(matches[0],target);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(target)],check=True)
  assert subprocess.check_output(['modinfo','-F','vermagic',str(target)],text=True).split()[0]==release
  changed.append(str(target.relative_to(payload)))
 assert set(changed)=={'lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']}
 final_input=snapshot(payload);assert {n for n in initial if initial[n]!=final_input[n]}==set(changed)
 (PRIVATE/'boot-initramfs-manifest-private.json').write_text(json.dumps(final_input,indent=2)+'\n')
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
 assert set(changes)=={'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'},changes
 assert git('rev-parse','HEAD')==COMMIT and not git('status','--porcelain')
 names=['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','vmlinux','Module.symvers','modules.order','.config']
 artifacts={n:dict(bytes=(BUILD/n).stat().st_size,sha256=sha(BUILD/n)) for n in names}
 assert artifacts['arch/arm64/boot/Image']['bytes']<64*1024*1024-1024*1024
 assert artifacts['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']['sha256']=='dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
 inventory={str(p.relative_to(stage)):sha(p) for p in modules};(PRIVATE/'installed-module-inventory-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
 archive=PRIVATE/'modules-k297-private.tar.gz';assert not archive.exists()
 with tarfile.open(archive,'w:gz') as tar:tar.add(stage,arcname='usr/lib/modules/'+release)
 report=dict(stage=297,commit=COMMIT,terminal=True,phases=phases,seconds=round(time.monotonic()-start_all,2),release=release,
  artifacts=artifacts,module_count=778,all_installed_vermagic_match=True,depmod_unresolved_symbols=0,
  embedded_input_entries=len(final_input),embedded_modules_rebuilt=sorted(changed),all_three_embedded_modules_match_installed_tree=True,
  old_initramfs293_preserved=True,changed_config_keys=sorted(changes),camss_component_count=len((BUILD/'drivers/media/platform/qcom/camss/qcom-camss.mod').read_text().splitlines()),
  module_archive=dict(bytes=archive.stat().st_size,sha256=sha(archive)),not_deployed=True,boot_not_yet_verified=True)
 assert report['camss_component_count']==40
 (ROOT/'boot-candidate-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 (PRIVATE/'boot-candidate-result-private.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(terminal=True,phase='finished',exit_code=0,seconds=report['seconds']);marker.write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)
except BaseException:
 state.update(terminal=True,phase='failed',exit_code=1,seconds=round(time.monotonic()-start_all,2));marker.write_text(json.dumps(state,indent=2)+'\n');raise
