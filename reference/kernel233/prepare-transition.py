"""Derive fresh233 tools while retaining old Q until reboot and correct manifests."""
from pathlib import Path
import json,subprocess
R=Path(__file__).resolve().parent;OLD=R.parent/'kernel230';P=Path('/mnt/e/edk2-samurai-out/kernel233')
assert json.loads((R/'module-stage-validation.json').read_text())['old_mfd_runtime_note_unchanged']
def clean(text):
 text=text.replace('k230','k233').replace('K230','K233').replace('stage=230','stage=233').replace("'stage': 230","'stage': 233")
 text=text.replace("read_text().strip() == '4096'","read_text().strip() == '0'").replace("read_text().strip()=='4096'","read_text().strip()=='0'")
 text=text.replace("=={'fastrpc':'O'}","=={}").replace('taint=4096','taint=0')
 text=text.replace('tainted)" = 4096','tainted)" = 0').replace("proof['taint'] == 4096","proof['taint'] == 0").replace("camera['taint']==4096","camera['taint']==0")
 return text
names=['quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py',
 'freeze-for-bootloader.sh','linux-restart2-bootloader.py','preflight-transition.py','run-quiesce.py','poll-quiesce.py','reboot-current.py',
 'launch-newboot-observer.py','poll-newboot.py','refresh-usb-endpoint.ps1']
for name in names:
 text=clean((OLD/name).read_text())
 if name=='quiesce-camera.py':
  needle="['qcom_camss','imx471','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']";assert needle in text
  text=text.replace(needle,"['qcom_camss','imx471','v4l2_cci','i2c_qcom_cci']")
  text=text.replace('all_six_camera_modules_unloaded=True','all_four_endpoint_modules_unloaded=True,old_q_mfd_and_regulator_retained=True')
  needle="report.update(all_four_endpoint_modules_unloaded=True"
  extra="""assert Path('/sys/module/qcom_pm8008').exists() and Path('/sys/module/qcom_pm8008_regulator').exists()
assert Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()==(root/'k233-baseline/mfd-loaded-note-private.bin').read_bytes()
q=json.loads((root/'k233-baseline/pmic-q-before-private.json').read_text())['device']
assert Path('/sys/bus/i2c/devices',q,'driver').resolve().name=='pm8008'
"""
  assert needle in text;text=text.replace(needle,extra+needle)
 if name=='check-quiesce.py':
  text=text.replace("camera['all_six_camera_modules_unloaded']","camera['all_four_endpoint_modules_unloaded'] and camera['old_q_mfd_and_regulator_retained']")
  text=text.replace("# This boot has no baseline kernel warnings.","""assert Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()==(before/'mfd-loaded-note-private.bin').read_bytes()
assert Path('/sys/module/qcom_pm8008_regulator').exists() and not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
# This boot has no baseline kernel warnings.""")
 if name in ['quiesce-current183.sh','freeze-for-bootloader.sh']:
  text=text.replace('/var/lib/samurai/k233-baseline/module-tree.sha256','/var/lib/samurai/k233-module-stage/module-tree-after.sha256')
  text=text.replace('sync\n', 'sha256sum -c /var/lib/samurai/k233-module-stage/loader-config-after.sha256 > /var/lib/samurai/k233-quiesce/loader-config-check.txt\nsync\n')
 if name=='reboot-current.py':
  text=text.replace("proof['stage'] == 230","proof['stage'] == 233")
  text=text.replace("flash_requested=False","flash_requested=True")
  text=text.replace("Verify fresh fastboot identity; issue one fastboot reboot without flash, then new Linux identity","Verify fresh fastboot identity/geometry; flash only locked232 boot image once, then new Linux identity")
 if name=='poll-newboot.py':
  text=text.replace('new FastRPC loaded and automatic real sensor readiness passed','new PMIC modules/provider/P identity and automatic services verified')
  text=text.replace('Verify module refcount open/close delta and five SSC sensors; then preserve candidate provenance and final health','Verify Q warm/provider cold managed unbind cycles with no front client, then front RAM-only regression and final health')
 if name=='linux-restart2-bootloader.py':
  assert "os.sysconf('SC_PAGE_SIZE') == 4096" in text and 'mmap.mmap(fd, 4096,' in text
 if name.endswith('.py'):compile(text,name,'exec')
 if name.endswith('.sh'):
  # Validate only; executing these scripts is a separate guarded operation.
  result=subprocess.run(['sh','-n'],input=text.encode(),capture_output=True);assert result.returncode==0
 assert "'4096'" not in text and 'taint=4096' not in text and "'fastrpc':'O'" not in text,name
 (R/name).write_text(text)
# Build post-flash partition expectations without weakening other partition checks.
lock=json.loads((P/'deployment-lock-private.json').read_text())
proof=json.loads((R.parent/'kernel232/build-package-validation.json').read_text())
assert proof['boot_sha256']==lock['files']['boot_candidate']['sha256']
(P/'build-package-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(stage=233,transition_tools_prepared=len(names),old_q_retained=True,taint0_only=True,restart_page_constants_preserved=True)))
