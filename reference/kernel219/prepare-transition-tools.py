from pathlib import Path
import ast,json

here=Path(__file__).resolve().parent;previous=here.parent/'kernel211'
private=Path('/mnt/e/edk2-samurai-out/kernel219')
proof=json.loads((here/'factory-mode-candidate-build-validation.json').read_text())
build=json.loads((here/'build-package-validation.json').read_text())
assert json.loads((here/'legacy-dark-raw-validation.json').read_text())['program_exit']==0
assert json.loads((here/'legacy-white-rgb-validation.json').read_text())['program_exit']==0
names=['collect-pre-reboot.py','quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','reboot-current.py','flash-boot.py','prepare-new-endpoint.py']
for name in names:
    text=(previous/name).read_text().replace('k211','k219').replace('kernel211','kernel219').replace('stage=211','stage=219').replace("'stage': 211","'stage': 219").replace("['stage'] == 211","['stage'] == 219")
    if name=='collect-pre-reboot.py':
        text=text.replace('89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0','c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6')
        old="tree = (root / 'k219-module-install/module-tree.sha256').read_bytes()"
        new="inventory=json.loads((root/'k219-driver-test-r2/module-inventory-after-private.json').read_text())\nassert inventory['kernel/drivers/media/i2c/imx471.ko']=="+repr(proof['module_sha256'])+"\ntree=''.join(digest+'  '+name+'\\n' for name,digest in sorted(inventory.items())).encode()"
        assert text.count(old)==1;text=text.replace(old,new)
        marker='assert all(sha(name) == digest for name, digest in expected.items())'
        text=text.replace(marker,"expected['/etc/libcamera/configuration.yaml']='771c516f85cb3c408e42a561beaa4a4bd56f2db9890c81d40e28468205ecc12e'\n"+marker)
        text=text.replace('same_current210_baseline_boot=True','same_current218_baseline_boot=True').replace('boot210_logdump183_persist_readback_exact=True','boot211_logdump183_persist_readback_exact=True')
        marker="assert json.loads((root / 'k207-tftp-deploy/summary.json').read_text())['block_fix_installed_and_loaded']"
        text=text.replace(marker,marker+"\nassert Path('/lib/apk/db/installed').read_bytes()==(root/'k219-baseline/installed-before-private.txt').read_bytes()\nassert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'")
    elif name=='quiesce-camera.py':
        marker="    p=subprocess.run(['rmmod',name],capture_output=True,timeout=15)"
        assert text.count(marker)==1
        text=text.replace(marker,"    if name=='imx471':\n        Path('/sys/bus/i2c/drivers/imx471/unbind').write_text('7-0010')\n        assert not Path('/sys/bus/i2c/devices/7-0010/driver').is_symlink()\n"+marker)
    elif name=='flash-boot.py':
        text=text.replace('boot-partition-k219-sensor-domain.img','boot-partition-k219-front-modes.img')
        text=text.replace("out.parent/'kernel210/boot-partition-k210-front.img'","out.parent/'kernel211/boot-partition-k211-sensor-domain.img'")
    if name.endswith('.py'):ast.parse(text,filename=name)
    assert not (here/name).exists();(here/name).write_text(text)
text=(here.parent/'kernel212/refresh-usb-endpoint.ps1').read_text().replace('kernel212','kernel219').replace('K202_','K219_')
(here/'refresh-usb-endpoint.ps1').write_text(text)
state=dict(stage=219,state='module219 installed and legacy RAW/white regression passed; boot219 built but not flashed',
           guard='/var/lib/samurai/k219-baseline/boot-id-private.txt',module_sha256=proof['module_sha256'],boot_candidate_sha256=build['boot_sha256'],
           transition_pending=False,next='fresh partition audit, orderly quiesce, one bootloader request, fresh fastboot identity, boot-only flash and runtime readback',
           full_peripheral_goal_active=True)
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print('219 transition tools prepared against current guard, module inventory and boot211 rollback; no transition sent')
