from pathlib import Path
import ast,json
here=Path(__file__).resolve().parent;previous=here.parent/'kernel210';private=Path('/mnt/e/edk2-samurai-out/kernel211');repo=here.parents[1]
assert json.loads((here/'module-install-validation.json').read_text())['updated_sensor_module_installed']
assert json.loads((here/'heap-access-validation.json').read_text())['protected_dsp_pool_root_only']
names=['quiesce-current183.sh','stop-gnss-idle.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py','collect-pre-reboot.py']
for name in names:
    text=(previous/name).read_text().replace('k210','k211').replace('stage=210','stage=211').replace("'stage': 210","'stage': 211").replace("['stage'] == 210","['stage'] == 211")
    if name=='quiesce-current183.sh':
        first=text.index('if test -d /sys/module/qcom_camss; then');last=text.index('test ! -d /sys/module/qcom_camss',first)+len('test ! -d /sys/module/qcom_camss')
        text=text[:first]+text[last:]
        marker='test -z "$(pgrep -x phoc || true)"';assert text.count(marker)==1;text=text.replace(marker,marker+'\npython3 /tmp/k211-quiesce-camera.py\ntest ! -d /sys/module/qcom_camss')
    elif name=='check-quiesce.py':
        text=text.replace("# This boot has no baseline kernel warnings.","camera=json.loads((out/'camera-quiesce-validation.json').read_text());assert camera['all_six_camera_modules_unloaded'] and camera['taint']==0\n# This boot has no baseline kernel warnings.")
    elif name=='deploy-and-quiesce.py':
        text=text.replace("'linux-restart2-bootloader.py']","'linux-restart2-bootloader.py', 'quiesce-camera.py']")
        text=text.replace('k211-before-reboot k211-quiesce k211-reboot-tools gnss-assist k211-baseline k211-camera-before-r2 k211-install-before-r2 k211-module-install k211-module-stage','k211-before-reboot k211-quiesce k211-reboot-tools gnss-assist k211-baseline k211-module-before k211-module-install k211-module-stage k211-heaps-deploy k211-heap-access-refine k211-heap-stage k211-provider-inspection')
    elif name=='collect-pre-reboot.py':
        text=text.replace('cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082','89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0')
        old="assert all(not Path('/sys/module/' + n).exists() for n in ['samurai_front_overlay', 'samurai_vio_phandle', 'samurai_cci_bringup', 'imx471', 'qcom_pm8008', 'i2c_qcom_cci'])"
        new="assert all(not Path('/sys/module/' + n).exists() for n in ['samurai_front_overlay', 'samurai_vio_phandle', 'samurai_cci_bringup'])\nassert all(Path('/sys/module/' + n).exists() for n in ['imx471', 'qcom_pm8008', 'qcom_pm8008_regulator', 'i2c_qcom_cci', 'v4l2_cci', 'qcom_camss', 'system_heap', 'cma_heap'])"
        assert old in text;text=text.replace(old,new)
        marker="assert all(sha(name) == digest for name, digest in expected.items())"
        assert text.count(marker)==1
        extra="expected['/etc/modules-load.d/samurai-camera-heaps.conf']='"+__import__('hashlib').sha256((repo/'linux-port/camera/samurai-camera-heaps.conf').read_bytes()).hexdigest()+"'\nexpected['/etc/udev/rules.d/70-samurai-camera-heaps.rules']='"+__import__('hashlib').sha256((repo/'linux-port/camera/70-samurai-camera-heaps.rules').read_bytes()).hexdigest()+"'\n"
        text=text.replace(marker,extra+marker).replace('boot204_logdump183_persist_readback_exact','boot210_logdump183_persist_readback_exact')
    if name.endswith('.py'):ast.parse(text)
    assert 'k210' not in text
    (here/name).write_text(text)
text=(here.parent/'kernel207/reboot-r2/fastboot-reboot-current.py').read_text().replace("host.PRIVATE.parents[1] / 'kernel109/fastboot-identity.json'","host.PRIVATE.parent / 'kernel109/fastboot-identity.json'")
ast.parse(text);(here/'fastboot-reboot-current.py').write_text(text)
text=(previous/'refresh-usb-endpoint.ps1').read_text().replace('kernel210','kernel211');(here/'refresh-usb-endpoint.ps1').write_text(text)
text=(repo/'NEXT-SESSION.md').read_text().replace('尚无211产品变更或重启。','已部署heap自动加载与限定video/uaccess权限，UID10000分配/映射/同步/释放通过，DSP专用池保持root-only。已安装新IMX471模块，但当前RAM中仍是旧驱动，待正常重启验证；尚未发送切换。')
(repo/'NEXT-SESSION.md').write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(next='Run fresh211 pre-reboot checks; quiesce camera AFTER GUI/monitor exits, archive, then single guarded bootloader/fastboot reboot of existing boot210. No flash planned or sent.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('211 fresh guarded warm-reboot tools prepared, with camera unload moved after client closure; no flash tool created.')
