"""One private protection.o using original guarded k363 W1 command; no link."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shlex,shutil,stat,subprocess,sys,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PRIVATE=Path('/home/cy122/charging-management-20261023/protection-query-observer-object-r1')
BASE=Path('/home/cy122/charging-management-20261023')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'only_private_object':True,'module_Image_linked_or_installed':False,
 'phone_SSH_USB_SDK_Git_accessed':False,'shared_source_config_written':False,'new_anchor':False,'unmounted':False}
try:
 assert os.geteuid()==0
 helper=REF/'kernel284/storage.py'
 assert sha(helper)=='5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
 backing=Path('/mnt/e/edk2-samurai-out/kernel282/full-kernel-build282.ext4')
 assert not backing.is_symlink() and stat.S_ISREG(backing.stat().st_mode) and backing.stat().st_size==32*1024**3
 test=json.loads((HERE/'test-result.json').read_bytes());assert test['passed'] and test['actual']['actual_function_cases']==21
 for n,d in test['tested_files'].items():assert sha(HERE/n)==d,n
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location('original284_guard_for_protection',helper)
 storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
 shared=storage.mounted_build();original=shared.parent/'source354'
 oldbuild=BASE/'kbuild-integrated';oldsource=BASE/'source-view'
 assert (oldbuild/'include/config/kernel.release').read_text().strip()=='7.3.0-rc6-rmx1931-samurai-k363+'
 cmdfile=oldbuild/'drivers/power/supply/.samurai-gauge-protection.o.cmd'
 first=cmdfile.read_text().splitlines()[0]
 assert first.startswith('savedcmd_drivers/power/supply/samurai-gauge-protection.o := ')
 command=shlex.split(first.split(' := ',1)[1]);assert command[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in command
 assert not any(x in [';','&&','||'] for x in command)
 oldc=oldsource/'drivers/power/supply/samurai-gauge-protection.c'
 assert sha(oldc)=='5d77236d555f13fae56adf4a5fcbbb719a9fab9745ae04c02aa558edf39a45b6'
 assert command[-1]==str(oldc) and command[-4:-2]==['-c','-o']
 tracked=[helper,shared/'.config',oldbuild/'.config',cmdfile,oldc,oldbuild/'drivers/power/supply/samurai-gauge-protection.o',
  original/'drivers/power/supply/Makefile',oldsource/'drivers/power/supply/gauge-i2c.h',oldsource/'drivers/power/supply/gauge-protocol.h']
 before={str(p):sha(p) for p in tracked}
 PRIVATE.mkdir(exist_ok=False)
 for n in ['samurai-gauge-protection.c','gauge-i2c.h','gauge-protocol.h']:shutil.copy2(HERE/n,PRIVATE/n)
 obj=PRIVATE/'samurai-gauge-protection.o'
 command=[('-Wp,-MMD,'+str(PRIVATE/'.samurai-gauge-protection.o.d')) if x.startswith('-Wp,-MMD,') else x for x in command]
 command[-1]=str(PRIVATE/'samurai-gauge-protection.c');command[-2]=str(obj);command.insert(1,'-Werror')
 start=time.monotonic();log=PRIVATE/'build.log'
 with log.open('xb') as output:
  child=subprocess.Popen(command,cwd=oldbuild,stdout=output,stderr=subprocess.STDOUT);pid=child.pid;rc=child.wait()
 text=log.read_text();diagnostics=[line for line in text.splitlines() if re.search(r'warning:|error:',line,re.I)]
 unchanged=all(sha(Path(p))==h for p,h in before.items())
 report.update(returncode=rc,pid=pid,owned_child_waited=True,seconds=time.monotonic()-start,
  command=command,cwd=str(oldbuild),saved_command_sha256=sha(cmdfile),helper_sha256=sha(helper),backing=str(backing),
  log_path=str(log),log_sha256=sha(log),diagnostics=diagnostics,shared_original_inputs_before=before,shared_original_inputs_unchanged=unchanged)
 assert rc==0 and not diagnostics,text
 raw=obj.read_bytes();assert raw[:4]==b'\x7fELF' and int.from_bytes(raw[18:20],'little')==183
 assert unchanged
 report.update(passed=True,object_path=str(obj),object_sha256=sha(obj),ELF_machine='AArch64',
  source_sha256={n:sha(PRIVATE/n) for n in ['samurai-gauge-protection.c','gauge-i2c.h','gauge-protocol.h']},
  test_receipt_sha256=sha(HERE/'test-result.json'),builder_sha256=sha(Path(__file__)))
except Exception as e:report.update(error=type(e).__name__,message=str(e))
(HERE/'build-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k) for k in ['passed','returncode','pid','error','message','object_sha256','shared_original_inputs_unchanged']}))
raise SystemExit(0 if report['passed'] else 1)
