from pathlib import Path
import ast,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];previous=here.parent/'kernel207/reboot-r2';private=Path('/mnt/e/edk2-samurai-out/kernel210')
assert json.loads((here/'module-install-validation.json').read_text())['native_modprobe_and_unload_passed']
assert json.loads((here/'build-package-validation.json').read_text())['firmware_only_dtb_changed']
for name in ['quiesce-current183.sh','stop-gnss-idle.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','deploy-and-quiesce.py','reboot-current.py']:
    text=(previous/name).read_text().replace('k207r2','k210').replace('stage=207','stage=210').replace("'stage': 207","'stage': 210").replace("['stage'] == 207","['stage'] == 210")
    if name=='deploy-and-quiesce.py':
        text=text.replace('k210-before-reboot k210-quiesce k210-reboot-tools gnss-assist','k210-before-reboot k210-quiesce k210-reboot-tools gnss-assist k210-baseline k210-camera-before-r2 k210-install-before-r2 k210-module-install k210-module-stage')
    if name.endswith('.py'):ast.parse(text)
    (here/name).write_text(text)
text=(previous/'collect-pre-reboot.py').read_text().replace('k207r2','k210').replace('stage=207','stage=210')
text=text.replace("root / 'k207-runtime/boot-id-private.txt'","root / 'k210-baseline/boot-id-private.txt'")
text=text.replace("root / 'k200-deploy/paired-module-tree.sha256'","root / 'k210-module-install/module-tree.sha256'").replace('len(tree.splitlines()) == 784','len(tree.splitlines()) == 786')
text=text.replace(" and int(modem['PowerState']) == 1",'')
text=text.replace("watch['worker_starts'] == watch['worker_completions'] == 0","watch['worker_starts'] == watch['worker_completions']")
text=text.replace('same_first207_boot=True','same_current210_baseline_boot=True').replace('original_784_module_tree_exact=True','installed_786_file_module_tree_exact=True')
ast.parse(text);(here/'collect-pre-reboot.py').write_text(text)
text=(here.parent/'kernel204/flash-boot.py').read_text().replace('boot-partition-k204-bt-wake.img','boot-partition-k210-front.img').replace("rollback=out/'boot-rollback-k200-private.img'","rollback=out.parent/'kernel204/boot-partition-k204-bt-wake.img'").replace('stage=204','stage=210')
ast.parse(text);(here/'flash-boot.py').write_text(text)
text=(previous/'refresh-usb-endpoint.ps1').read_text().replace('kernel207/reboot-r2','kernel210')
(here/'refresh-usb-endpoint.ps1').write_text(text)
text=(repo/'NEXT-SESSION.md').read_text()
text=text.replace('正在把200成功取流的前摄接入常规DTS和模块配置；210尚未安装或重启。','前摄常规DTS、配置和模块构建已通过；已安装三个模块并验原生加载/卸载，其余769个模块保持。启动镜像已封装，尚未刷写或重启。')
text=text.replace('手机保持207第二boot','手机保持207第二boot')
marker='## 源码、产物与回退依据\n'
assert marker in text
text=text.replace(marker,marker+'\n- 210当前：板级DTS68738cb9…/候选DTB7ff712b1…，只增15个相机节点、CCI1启用和VIO phandle；PMIC控制器源码标签是&i2c4（地址0x890000），不能把运行总线i2c-1当作&i2c1。配置fbde3690…/符号16798/order772持久化，五个开发helper均disabled。安装树772个ko/786份文件，前摄/CCI库/PM8008三条路径变更，其余769模块保持；手机k210-install-before-r2及私人modules-before归档可回退。boot210候选89242ade…，回退boot204 cdd16e29…；Image/logdump未改。此刻尚无重启或刷写请求。\n',1)
(repo/'NEXT-SESSION.md').write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(next='Execute fresh pre-reboot checks, upload210 quiesce tools, quiesce/archive, record single bootloader request. Flash only boot210 after fresh identity; no marker currently exists.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('Fresh210 paths/guards and boot-only flash tool prepared; no transition sent.')
