"""Only affected qcom objects, private source/O, original configuration."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_text());assert t['passed'] and t['actual_function_count']==22
for n,h in t['tested_files'].items():assert sha(HERE/n)==h,n
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('pd5v_storage284',REF/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
# Root has ended its old anchor but not unmounted. Never remount/recreate an
# anchor here: require the original mount, then let the original helper verify
# its exact filesystem/backing/path under its original lock.
assert any(line.split()[4]=='/mnt/samurai-full282' for line in Path('/proc/self/mountinfo').read_text().splitlines()), 'original mount absent; no remount permitted'
shared=storage.mounted_build();original=shared.parent/'source354'
relative='drivers/usb/typec/tcpm/qcom'
assert sha(original/relative/'qcom_pmic_typec.c')=='02d6faab6ce98d69e267ea461df9ac87c604bcdccbd7af1793b361d36b4747cd'
tracked=[shared/'.config',shared/'Module.symvers',*[original/relative/n for n in ['qcom_pmic_typec.c','qcom_pmic_typec.h','qcom_pmic_typec_pdphy.c','qcom_pmic_typec_port.c','Makefile']]]
before={str(p):sha(p) for p in tracked if p.exists()}
private=Path('/home/cy122/charging-management-20261023/pd5v-owner-feasibility');source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
def branch(src,dst,selected):
 dst.mkdir(exist_ok=True)
 for p in src.iterdir():
  if p.name=='.git':continue
  q=dst/p.name
  if p.name in selected:branch(p,q,selected[p.name])
  elif not q.exists() and not q.is_symlink():q.symlink_to(p,target_is_directory=p.is_dir())
branch(original,source,{'drivers':{'usb':{'typec':{'tcpm':{'qcom':{}}}}}})
files=['qcom_pmic_typec.c','qcom_pmic_typec.h','qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','Makefile']
for n in files:
 target=source/relative/n
 if target.is_symlink():target.unlink()
 shutil.copy2(HERE/n,target)
build.mkdir(exist_ok=True)
if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
env=dict(os.environ)
for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(name,None)
command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
targets=['modules_prepare',relative+'/qcom_pmic_typec_5v.o',relative+'/qcom_pmic_typec.o']
phases=[]
with (private/'build.log').open('w') as log:
 for target in targets:
  started=time.monotonic();p=subprocess.run([*command,target],env=env,stdout=log,stderr=subprocess.STDOUT)
  phases.append(dict(target=target,returncode=p.returncode,seconds=time.monotonic()-started))
  if p.returncode:break
text=(private/'build.log').read_text();diagnostics=[line for line in text.splitlines() if re.search(r'warning:|error:',line,re.I)]
objects={n:build/relative/n for n in ['qcom_pmic_typec_5v.o','qcom_pmic_typec.o']}
def cfg(p):return dict(line.split('=',1) for line in p.read_text().splitlines() if line.startswith('CONFIG_'))
unchanged=all(sha(Path(p))==h for p,h in before.items())
passed=len(phases)==3 and all(p['returncode']==0 for p in phases) and not diagnostics and all(p.exists() for p in objects.values()) and unchanged and cfg(shared/'.config')==cfg(build/'.config')
r=dict(passed=passed,phases=phases,diagnostics=diagnostics,objects={n:dict(path=str(p),sha256=sha(p) if p.exists() else None) for n,p in objects.items()},source_files={n:sha(HERE/n) for n in files},test_receipt_sha256=sha(HERE/'test-result.json'),private_source=str(source),private_build=str(build),build_log_private=str(private/'build.log'),build_log_sha256=sha(private/'build.log'),shared_inputs_before=before,shared_inputs_unchanged=unchanged,existing_original_mount_required=True,original_helper='reference/kernel284/storage.py::mounted_build',remounted=False,anchor_created=False,configuration_differences={},Image_or_module_linked=False,installed=False,phone_accessed=False,SDK_invoked=False,Git_invoked=False)
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=passed,phases=phases,diagnostics=diagnostics,objects=r['objects']),indent=2))
if not passed:print(text[-8000:]);raise SystemExit(1)
