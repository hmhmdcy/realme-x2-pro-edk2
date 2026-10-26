"""Build a coherent Image and every configured module from one clean commit."""
from pathlib import Path
import hashlib,json,os,resource,stat,subprocess,time,traceback
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');U=Path('/home/cy122/x2pro-linux/upstream')
B=Path('/home/cy122/x2pro-linux/camera269-full-build-r1');os.umask(0o077)
G=['git','-c','safe.directory='+str(U),'-C',str(U)]
def git(*args):return subprocess.check_output(G+list(args),text=True).strip()
commit=json.loads((R/'kernel-commit-validation.json').read_text())['commit'];assert git('rev-parse','HEAD')==commit and not git('status','--porcelain')
assert json.loads((R/'prepare-build-validation.json').read_text())['board_iommu_reservation_policy_unchanged']
marker=P/'full-build-state-private.json';assert not marker.exists()
def verify_initramfs():
 manifest=json.loads((P/'initramfs-input-manifest-private.json').read_text());root=B/'input-initramfs'
 for name,row in manifest.items():
  p=root/name;st=p.lstat();assert stat.S_IMODE(st.st_mode)==row['mode'] and st.st_uid==row['uid'] and st.st_gid==row['gid']
  if row['kind']=='file':assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
  elif row['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==row['target']
 return len(manifest)
verify_initramfs();epoch=git('show','-s','--format=%ct','HEAD')
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='269',
 KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',SOURCE_DATE_EPOCH=epoch,
 KBUILD_BUILD_TIMESTAMP=time.strftime('%a %b %d %H:%M:%S UTC %Y',time.gmtime(int(epoch))))
base=['make','-C',str(U),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','-j3']
state=dict(stage=269,state='starting',terminal=False,source_commit=commit,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],steps=[])
def save():
 p=P/'full-build-next-private.json';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(marker)
def limit():resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
save()
try:
 for name,args in [('image-modules',['W=1','Image','modules','qcom/sm8150-samurai.dtb']),
                   ('install-modules',['INSTALL_MOD_PATH='+str(B/'module-stage'),'INSTALL_MOD_STRIP=1','modules_install'])]:
  if name=='install-modules':assert not (B/'module-stage').exists()
  start=time.monotonic()
  with (B/(name+'-private.log')).open('xb') as log:
   child=subprocess.Popen(base+args,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
   state.update(state='running',step=name,child_pid=child.pid,child_start_ticks=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()[19]);save()
   ret=child.wait()
  state['steps'].append(dict(step=name,exit=ret,seconds=round(time.monotonic()-start,2)));save()
  assert ret==0,'Inspect this build log; candidate was not deployed'
 assert git('rev-parse','HEAD')==commit and not git('status','--porcelain');verify_initramfs()
 release=(B/'include/config/kernel.release').read_text().strip();assert release.startswith('7.3.0-rc6-rmx1931-samurai-k269')
 stage=B/'module-stage/lib/modules'/release;modules=list(stage.rglob('*.ko'));assert len(modules)>700
 targets={}
 for name in ['qcom-pm8008','qcom-pm8008-regulator','imx319','imx471','qcom-camss']:
  found=list(stage.rglob(name+'.ko'));assert len(found)==1;p=found[0]
  info=lambda k:subprocess.check_output(['modinfo','-F',k,str(p)],text=True).strip()
  assert info('intree')=='Y' and info('vermagic').split()[0]==release
  targets[name]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,intree=True,vermagic=info('vermagic'))
 assert not list(stage.rglob('*imx319-lab*')) and not list(stage.rglob('*rmx1931-pm8008*'))
 image=B/'arch/arm64/boot/Image';dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
 log=(B/'image-modules-private.log').read_text(errors='replace');diagnostics=[l for l in log.splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()]
 camera=[l for l in diagnostics if any(n in l for n in ['drivers/media/platform/qcom/camss','drivers/media/i2c/imx319','drivers/media/i2c/imx471','drivers/mfd/qcom-pm8008','drivers/regulator/qcom-pm8008'])]
 assert not camera,camera
 assert hashlib.sha256(dtb.read_bytes()).hexdigest()==json.loads((R/'prepare-build-validation.json').read_text())['dtb_sha256']
 report=dict(stage=269,source_commit=commit,branch=git('branch','--show-current'),kernel_release=release,
  source_date_epoch=int(epoch),steps=state['steps'],image_bytes=image.stat().st_size,image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
  dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),configured_modules_built_and_installed=len(modules),camera_modules=targets,
  full_w1_diagnostic_count=len(diagnostics),camera_w1_diagnostic_count=0,no_old_symbol_file_or_vmlinux_copied=True,
  all_image_modules_and_dtb_from_same_commit_and_config=True,original_initramfs_input_preserved=True,
  obsolete_camera_helpers_and_lab_modules_absent=True,phone_not_modified=True)
 (R/'full-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report,indent=2),flush=True)
except BaseException:
 (P/'full-build-failure-private.txt').write_text(traceback.format_exc());state.update(state='failed',terminal=True,exit_code=1);save();raise
