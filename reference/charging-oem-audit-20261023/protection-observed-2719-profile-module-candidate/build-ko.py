"""One private in-tree protection ko against actual Image502; never installs."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,stat,struct,subprocess,sys,time
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('Non-optimized Python required')
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
AUTHOR=HERE.parent/'protection-observed-2719-profile-candidate'
IMAGE=REF/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
REUSE=REF/'charging-ui-audit-20261023/usb-input-irq-board-candidate'
BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
OUT=Path('/home/cy122/charging-management-20261023/protection-observed-2719-profile-module-01')
EXPORT=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/protection-observed-2719-profile-module-private-01')
NAMES={'samurai-gauge-protection.c':'3078c62fdb7ef9f2aefbce3bac64be508b66fb0734fbcac7edcbd95bebbe1015',
 'gauge-i2c.h':'a47a031b66bea9c10d00a0dec271a2d21cb0497ef8e28285642f3115bb48803d',
 'gauge-protocol.h':'080f1d621886c3772f5b0b83ec4e5b4150c0e37007dd8fce707594882ff83e02'}
def sha(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def save(path,obj):
 with Path(path).open('w') as stream:
  json.dump(obj,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
def run_output(argv):return subprocess.check_output(argv,text=True)
def note(raw):
 assert raw[:6]==b'\x7fELF\x02\x01' and int.from_bytes(raw[18:20],'little')==183
 off=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
 assert stride>=64 and strings<count and off+stride*count<=len(raw)
 rows=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
 def data(r):assert r[4]+r[5]<=len(raw);return raw[r[4]:r[4]+r[5]]
 names=data(rows[strings]);found=[data(r) for r in rows if names[r[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id']
 assert len(found)==1;result=found[0];n,d,t=struct.unpack_from('<III',result)
 assert result[12:12+n]==b'GNU\0' and t==3 and d==20
 start=12+((n+3)//4)*4;assert start+d<=len(result)
 return result,result[start:start+d].hex()

def main():
 assert sys.argv[1:]==['--execute'] and os.geteuid()==0
 assert not OUT.exists() and not EXPORT.exists() and not (HERE/'ko-result.json').exists(),'unique output exists; inspect same original handle, never replay'
 assert sha(AUTHOR/'delivery.json')=='45467c6084d04e2149614477595781fe0a329d10fd9cb9d0b61d44ec84d2a509'
 author=json.loads((AUTHOR/'delivery.json').read_bytes())
 for name,row in author['files'].items():assert sha(AUTHOR/name)==row['sha256']
 for name,digest in NAMES.items():assert sha(AUTHOR/name)==digest
 assert sha(AUTHOR/'test-result.json')=='6a9a7ec194b67158af16e04a5c12a7ea6aa0ca4a0da098d03afca568018f39fc'
 assert sha(REUSE/'build-ko.py')=='7b69accb526573ad0419ec115f747844e8ac1da3941b9dc7c4ec68bad2656574'
 previous=json.loads((REUSE/'ko-result.json').read_bytes());assert previous['passed'] and previous['actual_config_values_exact_Image502']
 assert sha(IMAGE/'build-result.json')=='feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6'
 image=json.loads((IMAGE/'build-result.json').read_bytes());assert image['passed'] and image['build']['compatibility']['builtin_export_rows_exact_501']
 assert sha(BASE/'result.json')==sha(IMAGE/'build-result.json')
 for name,row in image['build']['outputs'].items():assert sha(BASE/'build'/name)==row['sha256'],name
 helper=REF/'kernel284/storage.py';assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
 backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
 assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
 spec=importlib.util.spec_from_file_location('protection_profile_original_storage284',helper)
 storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
 shared=storage.mounted_build();assert shared==Path('/mnt/samurai-full282/build')
 assert sha(BASE/'build/.config')=='23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
 assert sha(BASE/'build/vmlinux.symvers')=='84f5fc338ea72a6d71b23da50562f89c7963af50675956d3e0aff30540df4d47'
 assert sha(BASE/'source354/drivers/power/supply/Makefile')=='5d6a64153d6475ee5eb45ec69aceaa8f31b35a3a8b5b0dd40afc33b6a727c00f'
 # Shared caches and all selected Image502 link/config inputs are read-only.
 tracked=[helper]
 tracked += [shared/name for name in ['.config','Module.symvers','vmlinux.o','vmlinux','arch/arm64/boot/Image','include/generated/autoconf.h','include/generated/utsrelease.h']]
 tracked += [shared.parent/'source354'/name for name in ['Makefile','drivers/power/supply/Makefile','include/linux/power_supply.h']]
 tracked += [BASE/'build'/name for name in ['.config','Module.symvers','vmlinux.symvers','vmlinux.o','vmlinux','arch/arm64/boot/Image','include/generated/autoconf.h','include/generated/utsrelease.h']]
 tracked += [BASE/'source354'/name for name in ['Makefile','drivers/power/supply/Makefile','drivers/power/supply/bq27xxx_battery.c','include/linux/power_supply.h']]
 old=Path('/home/cy122/charging-management-20261023')
 tracked += [old/'source-view/drivers/power/supply'/name for name in NAMES]
 tracked += [old/'kbuild-integrated'/name for name in ['.config','Module.symvers','drivers/power/supply/samurai-gauge-protection.ko','drivers/power/supply/.samurai-gauge-protection.o.cmd']]
 tracked += [AUTHOR/name for name in NAMES]
 before={str(path):sha(path) for path in tracked}
 OUT.mkdir(mode=0o700);source,build=OUT/'source-view',OUT/'kbuild';commands=[];phases=[]
 result={'passed':False,'private_output':str(OUT),'sources':NAMES,'source_delivery_sha256':sha(AUTHOR/'delivery.json'),
  'old21_and_codec149_reused_not_rerun':True,'profile11_and_parser18_reused_not_rerun':True,
  'default_observed_2719_diagnostic':False,'ordinary_Health_policy_unchanged':True,'new_query_or_attempt_created':False,'original284_helper_sha256':sha(helper),'Image502_build_receipt_sha256':sha(IMAGE/'build-result.json'),
  'reused_USB_IRQ_builder_sha256':sha(REUSE/'build-ko.py'),'before':before,'device_SSH_USB_SDK_Git':False,
  'installed_or_loaded':False,'new_Image_built':False,'new_anchor_or_unmount':False,'builder_sha256':sha(Path(__file__))}
 try:
  source.mkdir()
  def branch(src,dst,branches):
   for p in src.iterdir():
    if p.name=='.git':continue
    q=dst/p.name
    if p.name in branches:q.mkdir();branch(p,q,branches[p.name])
    else:q.symlink_to(p,target_is_directory=p.is_dir())
  branch(BASE/'source354',source,{'drivers':{'power':{'supply':{}}}})
  supply=source/'drivers/power/supply';makefile=supply/'Makefile';assert makefile.is_symlink();makefile.unlink()
  makefile.write_bytes((BASE/'source354/drivers/power/supply/Makefile').read_bytes()+b'\nobj-m += samurai-gauge-protection.o\n')
  for name in NAMES:
   dest=supply/name;assert not dest.exists() and not dest.is_symlink();shutil.copy2(AUTHOR/name,dest)
  build.mkdir()
  for name in ['.config','Module.symvers','vmlinux.symvers']:shutil.copy2(BASE/'build'/name,build/name)
  (build/'vmlinux.o').symlink_to(BASE/'build/vmlinux.o');(OUT/'tmp').mkdir()
  env=dict(os.environ)
  for name in ['KBUILD_EXTMOD','KBUILD_OUTPUT','KCONFIG_CONFIG','SOURCE_DATE_EPOCH','KBUILD_EXTRA_SYMBOLS','KCFLAGS','CFLAGS_KERNEL','CFLAGS_MODULE','LDFLAGS','MAKEFLAGS','MFLAGS','LOCALVERSION']:env.pop(name,None)
  env.update(PATH='/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:'+env['PATH'],
   RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_USER='builder',KBUILD_BUILD_HOST='samurai',KBUILD_BUILD_VERSION='502',
   KBUILD_BUILD_TIMESTAMP='Tue Oct 20 03:03:47 UTC 2026',TMPDIR=str(OUT/'tmp'))
  argv=['make','-C',str(source),'O='+str(build),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LOCALVERSION=+','W=1','KCFLAGS=-Werror','-j4']
  for target in ['modules_prepare','drivers/power/supply/samurai-gauge-protection.ko']:
   log=OUT/('prepare.log' if target=='modules_prepare' else 'module.log');command=argv+[target];started=time.monotonic()
   with log.open('xb') as stream:
    child=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
    try:
     save(OUT/'process.json',{'pid':child.pid,'argv':command,'terminal':False})
     print(json.dumps({'phase':target,'pid':child.pid,'started':True}),flush=True)
    finally:rc=child.wait()
    stream.flush();os.fsync(stream.fileno())
   terminal={'pid':child.pid,'argv':command,'terminal':True,'returncode':rc};save(OUT/'process.json',terminal);commands.append(terminal)
   phases.append({'target':target,'seconds':round(time.monotonic()-started,3),'returncode':rc,'log_sha256':sha(log)})
   print(json.dumps({'phase':target,'returncode':rc,'seconds':phases[-1]['seconds']}),flush=True);assert rc==0,(target,rc)
  diagnostics=[{'log':log.name,'line':line} for log in [OUT/'prepare.log',OUT/'module.log'] for line in log.read_text(errors='replace').splitlines() if re.search(r'\b(?:warning|error):|undefined!',line,re.I)]
  assert not diagnostics,diagnostics
  ko=build/'drivers/power/supply/samurai-gauge-protection.ko';modinfo=run_output(['modinfo',str(ko)])
  release=(BASE/'build/include/config/kernel.release').read_text().strip();assert release=='7.3.0-rc6-rmx1931-samurai-k363+'
  vermagic=run_output(['modinfo','-F','vermagic',str(ko)]).strip()
  assert vermagic.split()[0]==release and run_output(['modinfo','-F','intree',str(ko)]).strip()=='Y'
  assert run_output(['modinfo','-F','name',str(ko)]).strip()=='samurai_gauge_protection'
  assert not run_output(['modinfo','-F','depends',str(ko)]).strip()
  assert 'observed_2719_diagnostic:bool' in run_output(['modinfo','-F','parmtype',str(ko)]).splitlines()
  assert 'AArch64' in run_output(['aarch64-linux-gnu-readelf','-h',str(ko)])
  config=lambda p:{l.split('=',1)[0]:l.split('=',1)[1] for l in p.read_text().splitlines() if l.startswith('CONFIG_')}
  assert config(build/'.config')==config(BASE/'build/.config') and sha(build/'.config')==sha(BASE/'build/.config')
  assert sha(build/'include/generated/autoconf.h')==sha(BASE/'build/include/generated/autoconf.h')
  exported={}
  for line in (BASE/'build/vmlinux.symvers').read_text().splitlines():
   row=line.split();assert row[2]=='vmlinux' and row[1] not in exported;exported[row[1]]=row
  assert len(exported)==15097
  strong=set();weak=set()
  for line in run_output(['aarch64-linux-gnu-nm','-u',str(ko)]).splitlines():
   row=line.split();assert len(row)==2 and row[0] in ['U','w','W','v','V'];(strong if row[0]=='U' else weak).add(row[1])
  assert not strong-exported.keys(),sorted(strong-exported.keys())
  imports={name:exported[name] for name in sorted(strong)};save(OUT/'Image502-import-map.json',imports)
  module_note,build_id=note(ko.read_bytes());(OUT/'note.gnu.build-id').write_bytes(module_note)
  EXPORT.mkdir(mode=0o700);private_ko=EXPORT/'samurai-gauge-protection-observed-2719-private.ko';shutil.copy2(ko,private_ko)
  assert sha(private_ko)==sha(ko)
  shutil.copy2(OUT/'note.gnu.build-id',EXPORT/'note.gnu.build-id')
  for name,digest in NAMES.items():assert sha(supply/name)==digest
  generated={name:sha(build/'drivers/power/supply'/name) for name in ['samurai-gauge-protection.o','samurai-gauge-protection.mod.c','samurai-gauge-protection.mod.o','.samurai-gauge-protection.o.cmd','.samurai-gauge-protection.ko.cmd']}
  result.update(passed=True,module_path=str(ko),exported_private_module_path=str(private_ko),module_sha256=sha(ko),module_bytes=ko.stat().st_size,
   module_note_sha256=hashlib.sha256(module_note).hexdigest(),module_note_bytes=len(module_note),GNU_build_id=build_id,
   modinfo=modinfo,intree='Y',ELF_machine='AArch64',vermagic=vermagic,release=release,generated_files=generated,
   actual_config_values_exact_Image502=True,generated_autoconf_exact_Image502=True,config_sha256=sha(build/'.config'),
   Image502_exports_sha256=sha(BASE/'build/vmlinux.symvers'),Image502_export_count=len(exported),strong_import_count=len(strong),weak_imports=sorted(weak),
   unresolved_strong_imports=[],imports_all_from_Image502_builtin=True,import_map_sha256=sha(OUT/'Image502-import-map.json'),
   no_module_provider_fallback=True,diagnostics=[],type_ABI_or_runtime_loading_attested=False,
   compiler_path=shutil.which('aarch64-linux-gnu-gcc'),compiler_sha256=sha(Path(shutil.which('aarch64-linux-gnu-gcc')).resolve()))
 except BaseException as error:result['error']=repr(error);raise
 finally:
  after={str(path):sha(path) for path in tracked};result.update(after=after,tracked_inputs_unchanged=before==after,commands=commands,phases=phases)
  result['passed']=result['passed'] and before==after;save(OUT/'ko-result.json',result);save(HERE/'ko-result.json',result)
  print(json.dumps({k:result.get(k) for k in ['passed','module_sha256','module_bytes','module_note_sha256','strong_import_count','tracked_inputs_unchanged','error']}),flush=True)
 return 0 if result['passed'] else 1
if __name__=='__main__':
 if sys.argv[1:]==['--execute']:raise SystemExit(main())
 assert not sys.argv[1:],'only explicit --execute; default source check'
 assert sha(AUTHOR/'delivery.json')=='45467c6084d04e2149614477595781fe0a329d10fd9cb9d0b61d44ec84d2a509'
 author=json.loads((AUTHOR/'delivery.json').read_bytes())
 for name,row in author['files'].items():assert sha(AUTHOR/name)==row['sha256']
 for name,digest in NAMES.items():assert sha(AUTHOR/name)==digest
 source=(AUTHOR/'samurai-gauge-protection.c').read_text()
 assert 'static bool observed_2719_diagnostic;' in source and 'module_param(observed_2719_diagnostic, bool, 0444);' in source
 print(json.dumps({'passed':True,'source_only':True,'default_profile':False,'storage_or_build_accessed':False,'device_accessed':False,'actual_output_created':False}))

