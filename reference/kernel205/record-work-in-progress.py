from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel205');nextfile=repo/'NEXT-SESSION.md';archive=repo/'archive/NEXT-SESSION-through204-2026-10-15.md';assert not archive.exists();archive.write_bytes(nextfile.read_bytes())
text='''# Realme X2 Pro 阶段205进行中

完整外设goal active。当前仅为启动串口取证准备，未提交本轮重启或刷写。204完整记录已逐字保存至[快照](archive/NEXT-SESSION-through204-2026-10-15.md)，其中旧部署不能代替下面的临时状态。

## 当前临时状态

- 当前boot仍204第二轮；手机guard `/var/lib/samurai/k205-baseline/boot-id-private.txt` 与 `k204r2-runtime` 相同。`reference/kernel205/host.py` 已新核对同boot严格key USB。
- 已加载及暂存默认hci_uart为205诊断ee143106…，vermagic仍183，原185 f6c5ed35…未丢失。`/usr/sbin/samurai-bluetooth` 暂改为30af7a16…，加载hci_uart时开启诊断并启动有限40秒UART trace。
- 原默认模块和启动脚本在手机 `/var/lib/samurai/k205-bootdiag-deploy/hci_uart185-original.ko` 与 `samurai-bluetooth-original.sh`。回退须恢复二者，再启标准服务；临时helper会拒绝在安装前的这个boot再次start，勿盲重试。新manifest `k205-bootdiag-deploy/paired-module-tree.sha256` 只覆盖一个模块，784文件已校验。
- BlueZ当前临时禁止自动重连，原配置与key快照在 `k205-bt-policy`，本机蓝牙保持关闭/不扫描/无连接。取证结束后恢复原配置。没有配对/连接/振动操作。
- 8次上/下电和4次完整驱动重注册未复现phase5。初次重注册测试遇到D-Bus Set推断ssb而非ssv，已以显式variant修正，失败和原trace保留。准备观察真实启动，不能把不复现当修复。
- 205内核hci_qca仅增加默认关闭、32字节上限的BAUD_CHANGE错误诊断与时间点；源码7682145e…，其余205的产品修复尚未形成。原hci_qca源码645ded49…在主机kernel205/hci_qca-before-diagnostic-private.c。
- Kbuild曾为五个新fixture自动补disabled配置；原.config55f1f0a3…已逐字恢复，新构建用私有配置，所有enabled值一致。Image183/旧canonicalDTB22c1…/symbols16793/order770保持。

## 源码、产物与回退依据

boot204 cdd16e29…/DTB b9d9c2a1…/CAMSS82cbc052…、MM191 b350/签名APK203/helper421、SSC9a1诊断保持。根文件系统离线132未更新；重要分区/NV和旧备份保持。内核树、原boot200/172配套回退、相机GPIO/PLDO限制与完整未完成项目见204快照。

本轮进程/新启动状态必须查看主机 `E:/edk2-samurai-out/kernel205/current-work-private.json`、切换marker及真实设备；不得根据计划重复重启。当前没有未完成的八轮或四轮测试worker，两项均已终止。后续启动取证worker按当前boot私有目录记录PID，需核对进程存活。

导航：[边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(text.encode())<=6500;nextfile.write_text(text,encoding='utf-8')
plan=dict(stage=205,state='temporary boot diagnostic staged; no reboot yet',current_boot_guard='/var/lib/samurai/k205-baseline/boot-id-private.txt',current_host='reference/kernel205/host.py',
 installed_and_loaded_module='ee14310674722fda61529a113cc8e90ae3c247e5c36a5a2c95544aed7741b480; diagnostic parameterY; defaultdisk staged for reboot',
 installed_helper='30af7a16128f1c2659b34f3a28acd2ca40dc37e1fd66537e0fabb523baf3fd9f; start hook requires a boot different fromk205baseline',
 rollback_files='/var/lib/samurai/k205-bootdiag-deploy/hci_uart185-original.ko AND samurai-bluetooth-original.sh; restore both before any same-boot standard restart',
 temporary_bluez_policy='/var/lib/samurai/k205-bt-policy/main.conf-before-private; pairingkeysoriginalinpolicy; restore at end',
 module_manifest='/var/lib/samurai/k205-bootdiag-deploy/paired-module-tree.sha256',
 finite_jobs='8 powercycles and4driverregistrations terminal; no tests currently running',next='Prepare fresh205 guarded ordinary reboot with updated one-module manifest/helper hashes, no flash. Boot trace starts beforehci module and stops40sec later; inspect actualPID/data before repeating anything.',
 full_scope='GPS actualfix, cameras persistent graph/PLDOcold,cellular business,sensorphysical/sharedpoolSSR,WiFiUSBPM andotherhardware remain')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print('Archived exact204 checkpoint and recorded temporary205 deployment/recovery state.')
