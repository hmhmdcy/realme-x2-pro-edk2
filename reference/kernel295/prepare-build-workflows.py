"""Prepare k295 coherent build and independent deployment paths from actual k294."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel294'
def save(name,s):
 p=ROOT/name;assert not p.exists(),name
 if p.suffix=='.py':compile(s,str(p),'exec')
 p.write_text(s)
def stage(s):
 return s.replace('kernel294','kernel295').replace('k294','k295').replace('K294','K295').replace('initramfs294','initramfs295').replace('modules294','modules295').replace('stage=294','stage=295').replace('kernel_build=294','kernel_build=295').replace("'#294 '","'#295 '").replace('"#294 "','"#295 "').replace("['kernel_build']==294","['kernel_build']==295")
commit=json.loads((ROOT/'source-validation.json').read_text())['commit']
s=stage((OLD/'build-boot-r2.py').read_text()).replace('456e46ca43142e7123a3bd353e559a5cb6bf768d',commit).replace('668a1b37ce96c9cf0e7bc591d3e5f7c418340245ae4156a49512c005a7bc2c97','891bd0f83a9bb94b0e699ba7f22e13febdf88d0ac246f039936c9b91159addb8')
s=s.replace("ROOT/'boot-r1-build-validation.json'","ROOT.parent/'kernel294/boot-candidate-build-validation.json'").replace('completed-boot294-r1','completed-boot294-r2')
s=s.replace('input-initramfs295-r2','input-initramfs295').replace('modules295-r2','modules295').replace('modules-k295-r2','modules-k295').replace('boot-build-r2-state','boot-build-state').replace('boot-r2-','boot-')
s=s.replace("KBUILD_BUILD_VERSION='294'","KBUILD_BUILD_VERSION='295'").replace("{'CONFIG_INITRAMFS_SOURCE'}","{'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'}")
save('build-boot-kernel.py',s)
for name in ['package-boot-candidate.py','stage-device-modules.py','native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-new-runtime.py','flash-logdump.py','prepare-transition.py','check-transition-readiness.py']:
 s=stage((OLD/name).read_text()).replace('modules-k295-r2','modules-k295').replace('input-initramfs295-r2','input-initramfs295')
 s=s.replace('k293-work','k294-work').replace("'#293 '","'#294 '").replace('samurai-k293+','samurai-k294+').replace('current293','current294').replace('current_boot293','current_boot294')
 if name=='check-transition-readiness.py':s=s.replace('be6e413e27cd8914d64ff111e6e7b99941f7dac471c9e2c477e8ee6a2112cf74','82a370391b01c5667add46607215af171a918a6023a34ad805ffc7a9f649d331').replace('current_kernel_build=293','current_kernel_build=294')
 save(name,s)
for name in ['samurai-stats.c','samurai-optical.c','native-stats.py','launch-stats.py','poll-stats.py','analyze-statistics.py','analyze-stats-color.py','native-optical.py','launch-optical.py','poll-optical.py','analyze-optical.py','native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py','inspect-layering.py','final-health.py']:
 s=stage((OLD/name).read_text())
 if name=='final-health.py':
  needle="assert len(prior293_inventory)==778 and prior293_inventory=={str(p.relative_to(prior293)):sha(p) for p in prior293.rglob('*.ko')}"
  assert needle in s
  s=s.replace(needle,needle+"\nprior294=Path('/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k294+')\nprior294_inventory=json.loads((r/'k294-deployment/module-inventory-private.json').read_text())\nassert len(prior294_inventory)==778 and prior294_inventory=={str(p.relative_to(prior294)):sha(p) for p in prior294.rglob('*.ko')}\n")
 if name in ['launch-four-camera-regression.py','poll-four-camera-regression.py']:s=s.replace('four-camera293','four-camera295')
 if name=='poll-stats.py':
  s=s.replace('print(json.dumps(report,indent=2))',"summary=report['summary']\nprint(json.dumps(dict(state=report['state'],matching_worker_live=report['matching_worker_live'],failure=report['failure'],summary=None if summary is None else {k:summary[k] for k in ['tool_exit','actual_frames','statistics_frames','passed','graph_restored','fault_delta']}),indent=2))")
 save(name,s)
print('Prepared coherent k295 build and guarded actual-k294 transition workflows.')
