"""One private object from exact source-float W=1 cached command, no make."""
from pathlib import Path
import hashlib,json,os,shlex,subprocess
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASE=Path('/home/cy122/charging-management-20261023/source-float-candidate')
BUILD=BASE/'kbuild'
SOURCE=BASE/'source-view'
SHARED=Path('/mnt/samurai-full282/build')
OUT=Path('/home/cy122/charging-management-20261023/apsd-input-backend-object-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins={'samurai-usb-input.c':'fc7c42cf6f0df20a522c0d41e8d78d6c50d38dc85ab00f35e3583edf3c4427d7',
      'samurai-apsd-input.inc':'ef6baeeeb927f7e74159ba1f8b339a55f2c7ee3d8f050ebad3d17ee0689f4ff2',
      'samurai-apsd-backend.h':'00d5659e8028a18be6f9db990cb9221af8475cf434693e3b995612f04f6cee94'}
assert all(sha(HERE/n)==h for n,h in pins.items())
tested=json.loads((HERE/'test-result.json').read_bytes());assert tested['passed']
assert all(tested['tested_files'][n]==h for n,h in pins.items())
old=json.loads((REF/'charging-management-20261023/source-float-build-result.json').read_bytes())
assert old['passed'] and sha(Path(old['module']))==old['module_sha256']
assert sha(SOURCE/'drivers/power/supply/samurai-usb-input.c')==old['sources']['samurai-usb-input.c']
assert sha(SOURCE/'drivers/power/supply/samurai-usb-input-decode.h')==old['sources']['samurai-usb-input-decode.h']
paths=[BUILD/n for n in ['.config','include/generated/autoconf.h','include/generated/utsrelease.h',
 'drivers/power/supply/.samurai-usb-input.o.cmd','drivers/power/supply/samurai-usb-input.o','drivers/power/supply/samurai-usb-input.ko']]
paths+=[SHARED/n for n in ['.config','include/generated/autoconf.h','include/generated/utsrelease.h']]
paths+=[SOURCE/'drivers/power/supply'/n for n in ['samurai-usb-input.c','samurai-usb-input-decode.h','Makefile']]
before={str(p):sha(p) for p in paths}
saved=BUILD/'drivers/power/supply/.samurai-usb-input.o.cmd'
line=saved.read_text().splitlines()[0]
assert line.startswith('savedcmd_drivers/power/supply/samurai-usb-input.o := ')
argv=shlex.split(line.split(' := ',1)[1])
assert argv[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in argv
assert argv[-1]==str(SOURCE/'drivers/power/supply/samurai-usb-input.c')
assert not OUT.exists(),'Unique output exists; do not replay'
OUT.mkdir(parents=True);(OUT/'tmp').mkdir()
argv[-1]=str(HERE/'samurai-usb-input.c')
argv[argv.index('-o')+1]=str(OUT/'samurai-usb-input.o')
dep='-Wp,-MMD,drivers/power/supply/.samurai-usb-input.o.d';assert argv.count(dep)==1
argv[argv.index(dep)]='-Wp,-MMD,'+str(OUT/'samurai-usb-input.d')
argv[1:1]=['-Werror','-DCONFIG_USB_DWC3_SAMURAI_APSD_OWNER=1']
q=subprocess.run(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},capture_output=True)
(OUT/'stdout').write_bytes(q.stdout);(OUT/'stderr').write_bytes(q.stderr)
after={str(p):sha(p) for p in paths}
result={'passed':q.returncode==0 and not q.stderr and before==after,
 'returncode':q.returncode,'stdout':q.stdout.decode(),'stderr':q.stderr.decode(),
 'private_output':str(OUT),'command':argv,'saved_command_sha256':sha(saved),
 'tested_receipt_sha256':sha(HERE/'test-result.json'),'candidate_sources':{n:sha(HERE/n) for n in [*pins,'samurai-usb-input-decode.h']},
 'object_sha256':sha(OUT/'samurai-usb-input.o') if not q.returncode else None,
 'before':before,'after':after,'inputs_unchanged':before==after,
 'private_compile_only_owner_config_define':True,'shared_config_changed':False,
 'make':False,'sdk':False,'module_or_Image_link':False,'phone_access':False}
(HERE/'object-build-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['passed','returncode','private_output','object_sha256','inputs_unchanged','stderr']},indent=2))
raise SystemExit(0 if result['passed'] else 1)
