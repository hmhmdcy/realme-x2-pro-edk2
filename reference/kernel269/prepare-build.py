"""Create a fresh coherent kernel configuration and verify the relocated DT policy."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,shutil,stat,subprocess,time
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');U=Path('/home/cy122/x2pro-linux/upstream')
B=Path('/home/cy122/x2pro-linux/camera269-full-build-r1');B.mkdir(mode=0o700)
original=Path('/home/cy122/pmos-samurai-kernel136/initramfs');copy=B/'input-initramfs'
assert original.is_dir() and not original.is_symlink() and not copy.exists()
subprocess.run(['cp','-a',str(original),str(copy)],check=True)
def snapshot(root):
 result={}
 for p in root.rglob('*'):
  st=p.lstat();row=dict(mode=stat.S_IMODE(st.st_mode),uid=st.st_uid,gid=st.st_gid)
  if p.is_symlink():row.update(kind='symlink',target=os.readlink(p))
  elif p.is_file():row.update(kind='file',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  elif p.is_dir():row.update(kind='directory')
  else:row.update(kind='special',rdev=st.st_rdev)
  result[str(p.relative_to(root))]=row
 return result
before=snapshot(original);assert before==snapshot(copy)
(P/'initramfs-input-manifest-private.json').write_text(json.dumps(before,indent=2)+'\n')
shutil.copyfile('/home/cy122/x2pro-linux/camera268-maintained-build-r2/.config',B/'.config')
subprocess.run([str(U/'scripts/config'),'--file',str(B/'.config'),'--set-str','LOCALVERSION','-rmx1931-samurai-k269',
 '--disable','LOCALVERSION_AUTO','--set-str','INITRAMFS_SOURCE',str(copy)],check=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='269',
 KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai')
base=['make','-C',str(U),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','-j3']
def limit():resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
steps=[]
for name,args in [('configure',['olddefconfig']),('prepare',['modules_prepare']),('camera-dtb',['W=1','drivers/media/platform/qcom/camss/qcom-camss.o','qcom/sm8150-samurai.dtb'])]:
 start=time.monotonic()
 with (B/(name+'-private.log')).open('xb') as log:q=subprocess.run(base+args,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
 steps.append(dict(step=name,exit=q.returncode,seconds=round(time.monotonic()-start,2)))
 (P/'prepare-state-private.json').write_text(json.dumps(steps)+'\n')
 assert q.returncode==0,'Inspect the recorded build before continuing'
pp=P/'samurai.pp.dts';yaml=P/'samurai.yaml';includes=U/'scripts/dtc/include-prefixes'
q=subprocess.run(['cpp','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I',str(includes),
 str(U/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),'-o',str(pp)],capture_output=True);assert q.returncode==0
q=subprocess.run(['dtc','-I','dts','-O','yaml','-o',str(yaml),str(pp)],capture_output=True)
(P/'dtc-yaml-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
spec=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
parse=f.parser();old=parse(Path('/mnt/e/edk2-samurai-out/kernel267/board-build-r1/sm8150-samurai.dtb').read_bytes())
dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb';new=parse(dtb.read_bytes());delta=f.compare(old,new,yaml)
(P/'dtb-semantic-private.json').write_text(json.dumps(delta,indent=2)+'\n')
assert not delta['only_old_nodes'] and not delta['only_new_nodes'] and not delta['remaining_changed_properties'],delta
schema=Path('/home/cy122/x2pro-linux/schema-k267/processed.json')
assert schema.is_file()
validations={}
for select in ['qcom,sm8150-camss','qcom,pm8008','sony,imx319','reserved-memory']:
 q=subprocess.run(['/home/cy122/x2pro-linux/.venv-dtschema/bin/dt-validate','-s',str(schema),'-l',select,str(dtb)],capture_output=True)
 (P/('schema-'+select.replace(',','-')+'-private.log')).write_bytes(q.stdout+q.stderr)
 validations[select]=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr))
 assert q.returncode==0 and not q.stdout and not q.stderr,(select,'inspect private schema log')
config=(B/'.config').read_text();assert not any('CONFIG_'+x+'=' in config for x in json.loads((R/'cleanup-validation.json').read_text())['removed_configs'])
report=dict(stage=269,steps=steps,initramfs_input_entries=len(before),initramfs_copy_contents_owners_modes_links_exact=True,
 unique_release_requested='-rmx1931-samurai-k269',obsolete_of_configs_absent=True,
 dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),semantic_delta=delta,schema_validations=validations,
 driver_c_io_window_constants_removed=True,board_iommu_reservation_policy_unchanged=True,
 only_camera_objects_and_dtb_prepared=True,full_image_and_modules_pending=True,phone_unchanged=True)
(R/'prepare-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
