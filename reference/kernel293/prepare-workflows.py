"""Create independent k293 build/deployment/test paths while retaining actual k292."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel292'
commit=json.loads((ROOT/'source-validation.json').read_text())['commit']
def save(name,s):
 p=ROOT/name;assert not p.exists()
 if p.suffix=='.py':compile(s,str(p),'exec')
 p.write_text(s)
def stage(s):
 return s.replace('kernel292','kernel293').replace('k292','k293').replace('K292','K293').replace('initramfs292','initramfs293').replace('modules292','modules293').replace('stage=292','stage=293').replace('kernel_build=292','kernel_build=293').replace("'#292 '","'#293 '").replace('"#292 "','"#293 "').replace("['kernel_build']==292","['kernel_build']==293")
save('host.py','''from pathlib import Path
import importlib.util,json,types
spec=importlib.util.spec_from_file_location('camera292_transport',Path(__file__).resolve().parents[1]/'kernel292/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel293');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec2=importlib.util.spec_from_file_location('camera276_transport',Path(__file__).resolve().parents[1]/'kernel276/host.py')
baseline=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(baseline)
fresh=types.FunctionType(baseline._fresh_raw.__code__,dict(baseline._fresh_raw.__globals__,PRIVATE=PRIVATE))
def raw_ssh(command,**kwargs):
 if (PRIVATE/'usb-ipv6-candidates-private.json').exists():return fresh(command,**kwargs)
 return previous.raw_ssh(command,**kwargs)
def ssh(command,**kwargs):
 identity=PRIVATE/'postboot-verified-private.json'
 if not identity.exists():return previous.ssh(command,**kwargs)
 expected=json.loads(identity.read_text())['boot_id']
 assert raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15).stdout.decode().strip()==expected,'Boot changed; inspect actual state'
 return raw_ssh(command,**kwargs)
''')
s=(OLD/'build-boot-r2.py').read_text().replace('86c7b9df030382efa82d87bc49370b3ad3a07cf3',commit)
s=s.replace('941e34b3230275060714218e0067da362d04b7d0f33953ce5d1057cdb66f2898','92aabf9ab5add22974567188f217fe711812b730ece1b46d6f3ca1731b16b6d5')
s=s.replace("ROOT/'boot-r1-build-validation.json'","ROOT.parent/'kernel292/boot-candidate-build-validation.json'").replace('completed-boot292-r1','completed-boot292-r2')
s=stage(s).replace('completed-boot293-r2','completed-boot292-r2').replace("ROOT.parent/'kernel293/boot-candidate-build-validation.json'","ROOT.parent/'kernel292/boot-candidate-build-validation.json'")
s=s.replace('input-initramfs293-r2','input-initramfs293').replace('modules293-r2','modules293').replace('modules-k293-r2','modules-k293').replace('boot-build-r2-state','boot-build-state').replace('boot-r2-','boot-')
s=s.replace("KBUILD_BUILD_VERSION='292'","KBUILD_BUILD_VERSION='293'").replace("{'CONFIG_INITRAMFS_SOURCE'}","{'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'}")
save('build-boot-kernel.py',s)
s=stage((OLD/'package-boot-r2.py').read_text()).replace('input-initramfs293-r2','input-initramfs293').replace('modules-k293-r2','modules-k293').replace('logdump-k293-r2','logdump-k293').replace('Image-k293-r2','Image-k293')
save('package-boot-candidate.py',s)
s=(ROOT.parent/'kernel290/stage-device-modules.py').read_text().replace('k290','k293').replace('stage=290','stage=293').replace("'#288 '","'#292 '").replace('samurai-k279candidate+','samurai-k292+')
save('stage-device-modules.py',s)
for name in ['native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-new-runtime.py','flash-logdump.py','audit-preserved-sources.py','prepare-transition.py']:
 s=stage((OLD/name).read_text()).replace('k293-deployment-r2','k293-deployment')
 s=s.replace('k290-work','k292-work').replace("'#290 '","'#292 '").replace('samurai-k290+','samurai-k292+').replace('current290','current292').replace('current_boot290','current_boot292')
 if name=='prepare-transition.py':s=s.replace('logdump-k293-r2','logdump-k293')
 save(name,s)
for name in ['samurai-wb-params.c','samurai-optical.c','native-wb-params.py','native-optical.py','launch-optical.py','poll-optical.py','analyze-optical.py','native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py']:
 s=stage((OLD/name).read_text());save(name,s)
for original,target in [('launch-wb-params-r2.py','launch-wb-params.py'),('poll-wb-params-r2.py','poll-wb-params.py'),('analyze-wb-params-r2.py','analyze-wb-params.py')]:
 s=stage((OLD/original).read_text()).replace('wb-params-r2','wb-params').replace('native-wb-params-r2','native-wb-params').replace('k293-wb-params-r2','k293-wb-params-r1')
 save(target,s)
# All stage293 probes have unique physical run directories.
print('Prepared independent build and workflows; no device changes.')
