"""Only affected saved W=1 object commands; original284 guard; no make/link."""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,stat,subprocess,sys
H=Path(__file__).resolve().parent;REF=H.parents[1]
BASE=REF/'charging-oem-audit-20261023/apsd-pd5v-client-bridge-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
HELPER_SHA='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
r=dict(passed=False,device_accessed=False,SDK_invoked=False,Git_invoked=False,Image_or_module_linked=False,shared_write=False,config_changed=False)
before={};paths=[]
try:
 t=json.loads((H/'test-result.json').read_bytes());assert t['passed'] and t['affected_groups']==9
 for n,v in t['tested_files'].items():assert sha(H/n)==v,n
 helper=REF/'kernel284/storage.py';assert sha(helper)==HELPER_SHA
 backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
 assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('original284_phy_lifetime',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 BUILD=m.mounted_build();SOURCE=(BUILD/'source').resolve();assert SOURCE==Path('/mnt/samurai-full282/source354')
 O=Path('/home/cy122/charging-management-20261023/apsd-phy-lifetime-objects-02');assert not O.exists(),'do not replay'
 commands_files=[BUILD/'drivers/usb/dwc3/.core.o.cmd',BUILD/'drivers/phy/qualcomm/.phy-qcom-snps-femto-v2.o.cmd']
 paths=[helper,BUILD/'.config',BUILD/'include/generated/autoconf.h',BUILD/'Module.symvers',*commands_files,
  SOURCE/'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c',SOURCE/'drivers/usb/dwc3/core.c',SOURCE/'drivers/usb/dwc3/core.h',SOURCE/'drivers/usb/dwc3/gadget.c']
 before={str(p):sha(p) for p in paths};r['shared_before']=before
 O.mkdir(parents=True);(O/'tmp').mkdir();inc=O/'include';inc.mkdir()
 headers={'linux/usb/samurai-apsd-backend.h':BASE/'samurai-apsd-backend.h','linux/usb/samurai-pd5v.h':BASE/'qcom_pmic_typec_5v.h',
  'eud-com-window.h':REF/'charging-session-20261023/eud-runtime-window-candidate-r2/eud-com-window.h',
  'phy-qcom-snps-femto-v2-window.h':H/'phy-qcom-snps-femto-v2-window.h',
  'core.h':BASE/'core.h','samurai-apsd-owner.h':H/'samurai-apsd-owner.h'}
 for n,p in headers.items():q=inc/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
 future=O/'future-builtin-only.h';future.write_text('#undef CONFIG_TYPEC_QCOM_PMIC_MODULE\n#define CONFIG_TYPEC_QCOM_PMIC 1\n')
 phases=[];commands=[]
 for name,rel,template,source,builtin in [
  ('phy-lifetime','drivers/phy/qualcomm','phy-qcom-snps-femto-v2',H/'phy-qcom-snps-femto-v2.c',False),
  ('owner-current-m','drivers/usb/dwc3','core',H/'samurai-apsd-owner.c',False),
  ('owner-future-builtin','drivers/usb/dwc3','core',H/'samurai-apsd-owner.c',True)]:
  saved=BUILD/rel/('.'+template+'.o.cmd');line=saved.read_text().splitlines()[0]
  assert line.startswith('savedcmd_'+rel+'/'+template+'.o := ')
  argv=shlex.split(line.split(' := ',1)[1]);assert argv[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in argv
  assert argv[-1]==str(SOURCE/rel/(template+'.c'))
  argv[-1]=str(source);argv[argv.index('-o')+1]=str(O/(name+'.o'))
  dep='-Wp,-MMD,'+rel+'/.'+template+'.o.d';assert argv.count(dep)==1;argv[argv.index(dep)]='-Wp,-MMD,'+str(O/(name+'.d'))
  argv[1:1]=['-Werror','-DCONFIG_USB_DWC3_SAMURAI_APSD_OWNER=1','-DCONFIG_USB_DWC3_SAMURAI_APSD_PD5V_CLIENT=1',
   '-I'+str(inc),'-I'+str(H),'-I'+str(BASE),'-I'+str(SOURCE/rel)]
  if builtin:
   i=argv.index('-c');argv[i:i]=['-include',str(future)]
  commands.append(argv)
  p=subprocess.run(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(O/'tmp')},capture_output=True)
  (O/(name+'.stdout')).write_bytes(p.stdout);(O/(name+'.stderr')).write_bytes(p.stderr)
  phases.append(dict(name=name,returncode=p.returncode,diagnostic_bytes=len(p.stderr),stderr=p.stderr.decode()))
  if p.returncode:break
 r.update(private_output=str(O),phases=phases,commands=commands,
  original_helper_sha256=HELPER_SHA,backing_bytes=backing.stat().st_size,
  actual_TYPEC='m',future_TYPEC='private command-only builtin view; no config mutation or link',
  sources={n:sha(H/n) for n in ['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h','phy-lifetime.inc','samurai-apsd-owner.c','samurai-apsd-owner.h']},
  component_headers={n:sha(p) for n,p in headers.items()},objects={p.name:sha(p) for p in O.glob('*.o')},test_receipt_sha256=sha(H/'test-result.json'))
 after={str(p):sha(p) for p in paths};r.update(shared_after=after,shared_unchanged=before==after)
 r['passed']=len(phases)==3 and all(p['returncode']==0 and p['diagnostic_bytes']==0 for p in phases) and before==after
except Exception as e:r.update(error=type(e).__name__,message=str(e))
finally:
 if before:
  final={str(p):sha(p) for p in paths};r['shared_final']=final;r['shared_final_unchanged']=before==final
  r['passed']=r['passed'] and r['shared_final_unchanged']
(H/'build-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r.get(k) for k in ['passed','error','message','phases','objects','shared_unchanged']},indent=2))
raise SystemExit(0 if r['passed'] else 1)
