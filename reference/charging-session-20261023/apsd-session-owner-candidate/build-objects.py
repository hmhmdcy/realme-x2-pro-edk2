"""Three private objects using exact cached Image commands, W=1 + Werror.
No make, AutoGen, SDK, shared writes, config regeneration or module/Image link.
"""
from pathlib import Path
import hashlib, json, os, shlex, subprocess
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BUILD=Path('/mnt/samurai-full282/build')
SOURCE=(BUILD/'source').resolve()
OUT=Path('/home/cy122/charging-management-20261023/apsd-session-owner-objects-02')
assert not OUT.exists(),'Unique private output already exists; do not replay'
assert SOURCE==Path('/mnt/samurai-full282/source354')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[BUILD/n for n in ['.config','include/generated/autoconf.h','include/generated/utsrelease.h',
       'drivers/usb/dwc3/.core.o.cmd','drivers/usb/dwc3/.gadget.o.cmd',
       'drivers/usb/dwc3/core.o','drivers/usb/dwc3/gadget.o']]
paths += [SOURCE/'drivers/usb/dwc3'/n for n in ['core.c','core.h','gadget.c','Makefile','Kconfig']]
before={str(p):sha(p) for p in paths}
config=(BUILD/'.config').read_text().splitlines()
required=['CONFIG_USB_DWC3=y','CONFIG_USB_DWC3_GADGET=y','CONFIG_SERIAL_EUD_CONSOLE=y',
          'CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y','CONFIG_POWER_SUPPLY=y','CONFIG_USB_QCOM_EUD=m']
assert all(x in config for x in required)
OUT.mkdir(parents=True)
(OUT/'tmp').mkdir()
headers={
 'samurai-apsd-once.h':REF/'charging-oem-audit-20261023/apsd-once-candidate/samurai-apsd-once.h',
 'eud-com-window.h':REF/'charging-session-20261023/eud-runtime-window-candidate-r2/eud-com-window.h',
 'phy-qcom-snps-femto-v2-window.h':REF/'charging-oem-audit-20261023/apsd-phy-window-candidate/phy-qcom-snps-femto-v2-window.h',
 'linux/usb/samurai-apsd-backend.h':HERE/'samurai-apsd-backend.h'}
for n,p in headers.items():
 dest=OUT/'include'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
commands=[];phases=[]
for name,template in [('core','core'),('gadget','gadget'),('samurai-apsd-owner','core')]:
 saved=BUILD/f'drivers/usb/dwc3/.{template}.o.cmd'
 line=saved.read_text().splitlines()[0]
 assert line.startswith(f'savedcmd_drivers/usb/dwc3/{template}.o := ')
 argv=shlex.split(line.split(' := ',1)[1])
 assert argv[0]=='aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in argv
 assert argv[-1]==str(SOURCE/f'drivers/usb/dwc3/{template}.c')
 argv[-1]=str(HERE/f'{name}.c')
 argv[argv.index('-o')+1]=str(OUT/f'{name}.o')
 dep=f'-Wp,-MMD,drivers/usb/dwc3/.{template}.o.d';assert argv.count(dep)==1
 argv[argv.index(dep)]='-Wp,-MMD,'+str(OUT/f'{name}.d')
 argv[argv.index(f'-DKBUILD_BASENAME="{template}"')]=f'-DKBUILD_BASENAME="{name.replace("-","_")}"'
 argv[1:1]=['-Werror','-DCONFIG_USB_DWC3_SAMURAI_APSD_OWNER=1',
             '-I'+str(OUT/'include'),'-I'+str(HERE),'-I'+str(SOURCE/'drivers/usb/dwc3')]
 # ep0.h in the original directory includes core.h before gadget.c does.
 # Force the one candidate layout after the cached compiler/kconfig includes.
 index=argv.index('-c');argv[index:index]=['-include',str(HERE/'core.h')]
 commands.append(argv)
 q=subprocess.run(argv,cwd=BUILD,env={**os.environ,'TMPDIR':str(OUT/'tmp')},capture_output=True)
 (OUT/f'{name}.stdout').write_bytes(q.stdout);(OUT/f'{name}.stderr').write_bytes(q.stderr)
 phases.append({'name':name,'returncode':q.returncode,'stderr':q.stderr.decode()})
 if q.returncode:break
after={str(p):sha(p) for p in paths}
result={'passed':len(phases)==3 and all(x['returncode']==0 and not x['stderr'] for x in phases) and before==after,
        'phases':phases,'commands':commands,'private_output':str(OUT),'shared_before':before,'shared_after':after,
        'shared_unchanged':before==after,'actual_config':required,
        'candidate_sources':{n:sha(HERE/n) for n in ['core.c','core.h','gadget.c','samurai-apsd-owner.c','samurai-apsd-owner.h','samurai-apsd-backend.h']},
        'component_headers':{n:sha(p) for n,p in headers.items()},
        'objects':{p.name:sha(p) for p in OUT.glob('*.o')},
        'make':False,'sdk':False,'shared_write':False,'image_or_module_link':False,'device_access':False}
(HERE/'object-build-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'private_output':str(OUT),
 'phases':[{'name':p['name'],'returncode':p['returncode'],'diagnostic_bytes':len(p['stderr'])} for p in phases],
 'objects':result['objects'],'shared_unchanged':before==after},indent=2))
raise SystemExit(0 if result['passed'] else 1)
