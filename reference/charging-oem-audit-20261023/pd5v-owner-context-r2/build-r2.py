"""Explicitly authorized original-helper restoration; two final objects only.

No tests, Image/module link, anchor, unmount, SDK or device access.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,stat,subprocess,sys,time
HERE=Path(__file__).resolve().parent;CANDIDATE=HERE;REF=HERE.parents[1];R1=HERE.parent/'pd5v-owner-feasibility'
HELPER_SHA='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
DELIVERY_SHA='0c377f5776262a7622bf2e587ec78af369e21ebfab1259ff187339b535b9808a'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=dict(passed=False,scope='only R2 context-reference qcom two objects',
 tests_rerun=False,Image_or_module_linked=False,installed=False,phone_accessed=False,
 SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False,
 anchor_created=False,unmounted=False,helper_modified=False,lock_or_sysctl_modified=False)
try:
 assert sha(R1/'delivery.json')==DELIVERY_SHA
 delivery=json.loads((R1/'delivery.json').read_text())
 for n,v in delivery['files'].items():assert sha(R1/n)==v['sha256'],n
 t=json.loads((CANDIDATE/'test-result.json').read_text())
 assert t['passed'] and t['affected_groups']==8 and not t['original_7_groups_rerun']
 for n,h in t['tested_files'].items():assert sha(CANDIDATE/n)==h,n
 helper=REF/'kernel284/storage.py'
 assert sha(helper)==HELPER_SHA
 backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
 assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
 mount=Path('/mnt/samurai-full282')
 before_mount=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(mount)]
 r['preflight']=dict(helper_path=str(helper),helper_sha256=HELPER_SHA,
  backing=str(backing),backing_bytes=backing.stat().st_size,backing_regular=True,
  originally_mounted=bool(before_mount),original_mountinfo=before_mount,
  original_candidate_delivery_sha256=DELIVERY_SHA,test_receipt_sha256=sha(CANDIDATE/'test-result.json'))
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('original_storage284_final_pd5v',helper)
 storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
 shared=storage.mounted_build();original=shared.parent/'source354'
 assert sha(helper)==HELPER_SHA
 r['original_helper_called']=True
 r['mountinfo_after_helper']=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(mount)]
 relative='drivers/usb/typec/tcpm/qcom'
 assert sha(original/relative/'qcom_pmic_typec.c')=='02d6faab6ce98d69e267ea461df9ac87c604bcdccbd7af1793b361d36b4747cd'
 tracked=[shared/'.config',shared/'Module.symvers',*[original/relative/n for n in ['qcom_pmic_typec.c','qcom_pmic_typec.h','qcom_pmic_typec_pdphy.c','qcom_pmic_typec_port.c','qcom_pmic_typec_pdphy.h','qcom_pmic_typec_port.h','Makefile']]]
 before={str(p):sha(p) for p in tracked if p.exists()};r['shared_inputs_before']=before
 private=Path('/home/cy122/charging-management-20261023/pd5v-owner-context-r2')
 source=private/'source-view';build=private/'kbuild';source.mkdir(parents=True,exist_ok=True)
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
  shutil.copy2(CANDIDATE/n,target)
 build.mkdir(exist_ok=True)
 if not (build/'.config').exists():shutil.copy2(shared/'.config',build/'.config')
 env=dict(os.environ)
 for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG']:env.pop(name,None)
 command=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','-j4']
 targets=['modules_prepare',relative+'/qcom_pmic_typec_5v.o',relative+'/qcom_pmic_typec.o'];phases=[]
 with (private/'build.log').open('w') as log:
  for target in targets:
   started=time.monotonic();p=subprocess.run([*command,target],env=env,stdout=log,stderr=subprocess.STDOUT)
   phases.append(dict(target=target,returncode=p.returncode,seconds=time.monotonic()-started))
   if p.returncode:break
 text=(private/'build.log').read_text()
 diagnostics=[line for line in text.splitlines() if re.search(r'warning:|error:',line,re.I)]
 objects={n:build/relative/n for n in ['qcom_pmic_typec_5v.o','qcom_pmic_typec.o']}
 def config(p):return {line.split('=',1)[0]:line.split('=',1)[1] for line in p.read_text().splitlines() if line.startswith('CONFIG_')}
 def disabled(p):return {line[2:-11] for line in p.read_text().splitlines() if line.startswith('# CONFIG_') and line.endswith(' is not set')}
 shared_unchanged=all(sha(Path(p))==h for p,h in before.items())
 a,b=config(shared/'.config'),config(build/'.config')
 config_same=a==b
 config_diff={k:dict(shared=a.get(k),private=b.get(k)) for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)}
 r.update(phases=phases,diagnostics=diagnostics,objects={n:dict(path=str(p),sha256=sha(p) if p.exists() else None) for n,p in objects.items()},
  source_files={n:sha(CANDIDATE/n) for n in files},private_source=str(source),private_build=str(build),
  build_log_private=str(private/'build.log'),build_log_sha256=sha(private/'build.log'),
  shared_inputs_unchanged=shared_unchanged,original_helper_sha256_after=sha(helper),
  private_configuration_sha256=sha(build/'.config'),configuration_semantics_unchanged=config_same,
  command_prefix=command,configuration_differences=config_diff,
  private_disabled_comments_added=sorted(disabled(build/'.config')-disabled(shared/'.config')),
  private_disabled_comments_removed=sorted(disabled(shared/'.config')-disabled(build/'.config')))
 r['passed']=len(phases)==3 and all(p['returncode']==0 for p in phases) and not diagnostics and all(p.exists() for p in objects.values()) and shared_unchanged and config_same and sha(helper)==HELPER_SHA
except Exception as e:
 r.update(error=type(e).__name__,message=str(e))
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r.get(k) for k in ['passed','error','message','phases','diagnostics','objects','shared_inputs_unchanged']},indent=2))
raise SystemExit(0 if r['passed'] else 1)
