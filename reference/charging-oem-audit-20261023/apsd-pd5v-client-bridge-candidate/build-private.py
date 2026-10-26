"""Original284 guard, private saved W=1 object commands only; no make/link."""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,stat,subprocess,sys
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
HELPER_SHA='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=dict(passed=False,Image_or_module_linked=False,SDK_invoked=False,device_accessed=False,
 shared_write=False,config_file_changed=False,Git_invoked=False,anchor_created=False)
try:
 t=json.loads((HERE/'test-result.json').read_bytes());assert t['passed'] and t['affected_groups']==14
 for n,h in t['tested_files'].items():assert sha(HERE/n)==h,n
 helper=REF/'kernel284/storage.py';assert sha(helper)==HELPER_SHA
 backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
 assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('original_storage284_pd_bridge',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 BUILD=m.mounted_build();SOURCE=(BUILD/'source').resolve();assert SOURCE==Path('/mnt/samurai-full282/source354')
 OUT=Path('/home/cy122/charging-management-20261023/apsd-pd5v-client-bridge-objects-04')
 assert not OUT.exists(),'private output already exists; do not replay'
 core_cmd=BUILD/'drivers/usb/dwc3/.core.o.cmd'
 pd_cmd=BUILD/'drivers/usb/typec/tcpm/qcom/.qcom_pmic_typec.o.cmd'
 paths=[helper,BUILD/'.config',BUILD/'include/generated/autoconf.h',BUILD/'Module.symvers',core_cmd,pd_cmd,
  SOURCE/'drivers/usb/dwc3/core.c',SOURCE/'drivers/usb/dwc3/core.h',SOURCE/'drivers/usb/dwc3/gadget.c',
  SOURCE/'drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c',SOURCE/'drivers/usb/typec/tcpm/qcom/Makefile']
 before={str(p):sha(p) for p in paths};r['shared_before']=before
 assert 'CONFIG_TYPEC_QCOM_PMIC=m' in (BUILD/'.config').read_text().splitlines()
 OUT.mkdir(parents=True);(OUT/'tmp').mkdir();include=OUT/'include';include.mkdir()
 headers={'linux/usb/samurai-apsd-backend.h':HERE/'samurai-apsd-backend.h',
  'linux/usb/samurai-pd5v.h':HERE/'qcom_pmic_typec_5v.h',
  'eud-com-window.h':REF/'charging-session-20261023/eud-runtime-window-candidate/eud-com-window.h',
  'phy-qcom-snps-femto-v2-window.h':REF/'charging-oem-audit-20261023/apsd-phy-window-candidate/phy-qcom-snps-femto-v2-window.h'}
 for n,p in headers.items():q=include/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
 future=OUT/'future-builtin-only.h';future.write_text('#undef CONFIG_TYPEC_QCOM_PMIC_MODULE\n#define CONFIG_TYPEC_QCOM_PMIC 1\n')
 phases=[];commands=[]
 previous=json.loads((HERE/'history/build-before-abort-gates.json').read_bytes())
 assert previous['passed'] and previous['sources']['qcom_pmic_typec_5v.c']==sha(HERE/'qcom_pmic_typec_5v.c')
 assert previous['sources']['qcom_pmic_typec_5v.h']==sha(HERE/'qcom_pmic_typec_5v.h')
 reused=Path(previous['private_output'])/'pd5v-metadata.o';assert sha(reused)==previous['objects']['pd5v-metadata.o']
 for name,template,rel,source,future_mode in [
  ('owner-current-m','core','drivers/usb/dwc3',HERE/'samurai-apsd-owner.c',False),
  ('owner-future-builtin','core','drivers/usb/dwc3',HERE/'samurai-apsd-owner.c',True)]:
  saved=BUILD/rel/('.'+template+'.o.cmd');line=saved.read_text().splitlines()[0]
  assert line.startswith('savedcmd_'+rel+'/'+template+'.o := ')
  argv=shlex.split(line.split(' := ',1)[1]);assert argv[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in argv
  assert argv[-1]==str(SOURCE/rel/(template+'.c'))
  argv[-1]=str(source);argv[argv.index('-o')+1]=str(OUT/(name+'.o'))
  dep='-Wp,-MMD,'+rel+'/.'+template+'.o.d';assert argv.count(dep)==1;argv[argv.index(dep)]='-Wp,-MMD,'+str(OUT/(name+'.d'))
  argv[1:1]=['-Werror','-DCONFIG_USB_DWC3_SAMURAI_APSD_OWNER=1','-DCONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT=1',
   '-I'+str(include),'-I'+str(HERE),'-I'+str(SOURCE/rel)]
  if future_mode:
   i=argv.index('-c');argv[i:i]=['-include',str(future)]
  commands.append(argv)
  p=subprocess.run(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},capture_output=True)
  (OUT/(name+'.stdout')).write_bytes(p.stdout);(OUT/(name+'.stderr')).write_bytes(p.stderr)
  phases.append(dict(name=name,returncode=p.returncode,diagnostic_bytes=len(p.stderr),stderr=p.stderr.decode()))
  if p.returncode:break
 after={str(p):sha(p) for p in paths}
 r.update(phases=phases,commands=commands,private_output=str(OUT),shared_after=after,shared_unchanged=before==after,
  original_helper_sha256=HELPER_SHA,backing=str(backing),backing_bytes=backing.stat().st_size,
  actual_shared_TYPEC='m',future_builtin_view='command-only private header; no .config mutation, not a link or deployed config',
  sources={n:sha(HERE/n) for n in ['samurai-apsd-owner.c','samurai-apsd-owner.h','qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','Kconfig.fragment']},
  component_headers={n:sha(p) for n,p in headers.items()},objects={p.name:sha(p) for p in OUT.glob('*.o')},
  unchanged_PD_object_reused=dict(path=str(reused),sha256=sha(reused),receipt_sha256=sha(HERE/'history/build-before-abort-gates.json')))
 r['passed']=len(phases)==2 and all(p['returncode']==0 and not p['diagnostic_bytes'] for p in phases) and before==after
except Exception as e:r.update(error=type(e).__name__,message=str(e))
(HERE/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r.get(k) for k in ['passed','error','message','phases','objects','shared_unchanged']},indent=2))
raise SystemExit(0 if r['passed'] else 1)
