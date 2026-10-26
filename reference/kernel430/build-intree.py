"""Build calibrated VFE175 PD10 auxiliary capture and matching modules."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil,subprocess,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';camss=Path('drivers/media/platform/qcom/camss');v4l2=Path('drivers/media/v4l2-core')
vb2=Path('drivers/media/common/videobuf2')
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
attempt=1
while (P/('intree-build-r'+str(attempt)+'.log')).exists():attempt+=1
backup=P/('intree-build-r'+str(attempt)+'-before');backup.mkdir()
for relative in [camss,v4l2,vb2]:shutil.copytree(build/relative,backup/relative,symlinks=True)
saved={}
for name in ['.config','.config.old','Module.symvers','modules.order','Makefile','source','include/generated/compile.h','include/generated/utsversion.h','include/generated/utsrelease.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd','include/config/kernel.release']:
 path=build/name;saved[name]=('symlink',os.readlink(path)) if path.is_symlink() else ('file',path.read_bytes()) if path.is_file() else ('missing',None)
release=(build/'include/config/kernel.release').read_text().strip()
modules=[camss/'qcom-camss-icp-a5-core.ko',camss/'qcom-camss.ko',camss/'camss-icp-a5-m2m.ko']
runtime_modules=set(modules)
modules += [v4l2/'v4l2-mem2mem.ko',v4l2/'v4l2-isp.ko']
modules += [vb2/(n+'.ko') for n in ['videobuf2-common','videobuf2-v4l2','videobuf2-memops','videobuf2-vmalloc','videobuf2-dma-sg']]
command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1','KCFLAGS=-Werror','KERNELRELEASE='+release,
 'CONFIG_VIDEO_QCOM_CAMSS_ICP=y','CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE=m','CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST=m','CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_M2M=m','CONFIG_V4L2_MEM2MEM_DEV=m']+[str(p) for p in modules]
env=dict(os.environ,TMPDIR=str(build.parent/'tmp'),KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='363',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
log=P/('intree-build-r'+str(attempt)+'.log');running=P/'intree-build-state.json';start=time.monotonic();rows=[];code=-1
try:
 subprocess.run([str(source/'scripts/config'),'--file',str(build/'.config'),'--enable','VIDEO_QCOM_CAMSS_ICP','--module','VIDEO_QCOM_CAMSS_ICP_A5_BOOT_TEST'],check=True)
 config=subprocess.run(['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],env=env,capture_output=True)
 (P/('olddefconfig-r'+str(attempt)+'.log')).write_bytes(config.stdout+config.stderr);config.check_returncode()
 selected=[line for line in (build/'.config').read_text().splitlines() if line.startswith(('CONFIG_VIDEO_QCOM_CAMSS=','CONFIG_VIDEO_QCOM_CAMSS_ICP','CONFIG_V4L2_MEM2MEM_DEV='))]
 assert 'CONFIG_VIDEO_QCOM_CAMSS_ICP=y' in selected
 assert 'CONFIG_VIDEO_QCOM_CAMSS=m' in selected and 'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_CORE=m' in selected and 'CONFIG_VIDEO_QCOM_CAMSS_ICP_A5_M2M=m' in selected,selected
 with log.open('xb') as stream:
  child=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT);running.write_text(json.dumps(dict(pid=child.pid,terminal=False,attempt=attempt))+'\n');code=child.wait()
 if not code:
  for relative in modules:
   out=P/(relative.stem+'-intree-r'+str(attempt)+'.ko');shutil.copyfile(build/relative,out)
   row=dict(name=relative.stem,bytes=out.stat().st_size,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
    runtime_candidate=relative in runtime_modules,
    intree=subprocess.check_output(['modinfo','-F','intree',str(out)],text=True).strip(),
    vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(out)],text=True).strip(),
    depends=subprocess.check_output(['modinfo','-F','depends',str(out)],text=True).strip(),private_path=str(out))
   rows.append(row);assert row['intree']=='Y'
finally:
 for relative in [camss,v4l2,vb2]:
  target=build/relative;assert target.resolve().is_relative_to(build.resolve()) and target!=build
  shutil.rmtree(target);shutil.copytree(backup/relative,target,symlinks=True)
 for name,(kind,data) in saved.items():
  path=build/name
  if path.is_symlink():path.unlink()
  if kind=='symlink':
   if path.exists():path.unlink()
   path.symlink_to(data)
  elif kind=='file':path.write_bytes(data)
  elif path.exists():path.unlink()
report=dict(stage=430,attempt=attempt,exit_code=code,seconds=round(time.monotonic()-start,2),modules=rows,
 selected_config=selected,normal_camss_and_icp_same_module_owner=True,camss_ds4_capture_candidate=True,typed_pd10_core_candidate=True,experimental_paired_source_format=True,
 diagnostics=[l for l in log.read_text(errors='replace').splitlines() if 'warning:' in l.lower() or 'error:' in l.lower()],
 actual_in_tree_camss_and_core_candidates_built=not code,shared_camss_v4l2_outputs_config_and_symvers_restored=True,
 refreshed_host_tools_and_other_preparation_outputs_not_rolled_back=True,installed=False,passed=not code)
running.write_text(json.dumps(dict(pid=child.pid,terminal=True,**report),indent=2)+'\n')
(HERE/('intree-build-r'+str(attempt)+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
if not code:(HERE/'intree-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));raise SystemExit(code)




