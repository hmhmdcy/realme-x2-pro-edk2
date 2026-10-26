"""Preserve the interrupted 205 checkpoint and record verified current state."""
from pathlib import Path
import json

here = Path(__file__).resolve().parent
repo = here.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel205')
health = json.loads((private / 'reboot-r2/inspect-current-idle-host-private.log').read_text().strip())
assert health['fresh_same_r2_boot_verified'] and health['taint'] == 0
assert health['gnss_enabled'] == 0 and health['bt_connections'] == 0
assert health['original_bluez_autoenable'] == 'false'
(here / 'reboot-r2/idle-state-validation.json').write_text(json.dumps(health, indent=2) + '\n')
archive = repo / 'archive/NEXT-SESSION-205-before-gnss-review-2026-10-15.md'
assert not archive.exists()
archive.write_bytes((repo / 'NEXT-SESSION.md').read_bytes())
plan_path = private / 'current-work-private.json'
plan = json.loads(plan_path.read_text())
plan.update(state='Both ordinary 205 diagnostic boots completed. R2 runtime receipt passed at 378.96s; fresh read-only idle snapshot passed at 864.16s. No 205 flash or functional Bluetooth fix.',
            current_boot_guard='/var/lib/samurai/k205r2-runtime/boot-id-private.txt',
            current_host='reference/kernel205/reboot-r2/host.py',
            finite_jobs='8 power cycles and 4 driver reprobes terminal. First boot 40s trace completed and isolated instance removed. R2 helper has no trace hook. No test started during GNSS source review.',
            next='Continue GNSS firmware/config load contract review or finish GENI contract harness. Before ending diagnostic work restore original185 module, original Bluetooth helper and BlueZ policy under fresh r2 guard. No pending reboot request; do not repeat either reboot.',
            original_bluez_autoenable='false (fresh read-only file check)',
            source_contract_harness='First build failed because userspace ioctl headers lack kernel TIOCM_LOOP; log preserved in rts-contract/current-build-private.log. No successful contract receipt and no GENI product-source patch.',
            gnss_research='Three new public source repositories pinned; Android configs have 39 active keys, sole LPP_PROFILE2/3 difference. L5 patch read only; no NV changes. OnePlus6 firmware/carrier reports not controlled RMX1931 evidence.')
plan_path.write_text(json.dumps(plan, indent=2) + '\n')
text = '''# Realme X2 Pro 阶段205进行中

完整外设goal active。205做了两次普通重启，均无刷写；第二次启动已完成采集。不要依据旧计划再发重启。204完整检查点保存在[through204快照](archive/NEXT-SESSION-through204-2026-10-15.md)，原205中途检查点在[补查前快照](archive/NEXT-SESSION-205-before-gnss-review-2026-10-15.md)。

## 当前实机与临时状态

- 使用 `reference/kernel205/reboot-r2/host.py` 严格key USB；当前guard为 `/var/lib/samurai/k205r2-runtime/boot-id-private.txt`。主目录205/host.py属于第一次205启动，不能用于当前切换。
- R2在378.96秒完成[启动采集](reference/kernel205/reboot-r2/runtime-validation.json)，864.16秒[只读复核](reference/kernel205/reboot-r2/idle-state-validation.json)：taint0、五类故障0，ADSP/SLPI/modem均running；BT关闭/无扫描/无连接，GPS0/Signals false/刷新30。没有新的GNSS接收测试。
- 暂存默认及已加载hci_uart仍是205诊断ee143106…；helper为ae46b800…，仅insmod诊断参数，无UART trace hook。首轮205启动40秒trace已结束、无overrun/无phase5；第二轮error-only启动也未捕到错误。8次上下电和4次完整重注册均未复现，不能称为功能修复。
- 原185模块f6c5ed35…与原helper在手机 `/var/lib/samurai/k205-bootdiag-deploy/hci_uart185-original.ko`、`samurai-bluetooth-original.sh`。诊断工作结束须恢复两者，再按标准helper重载并核对loaded build-id。原784文件manifest用k200-deploy版本，诊断manifest仅覆盖一个模块。
- BlueZ仍是临时禁重连策略，原件 `/var/lib/samurai/k205-bt-policy/main.conf-before-private`；已只读确认原AutoEnable=false，恢复后核对key、关闭/无连接状态。没有配对/连接/新增振动。
- R2 helper无trace hook；8轮/4轮测试已终止，第一boot40秒trace已完成。早期75秒UTC观察超时保留，同一新boot随后自动第3次UTC准备成功；没有因观察超时重复重启服务或设备。

## 源码、产物与未完成工作

205 hci_qca仅增加默认关闭的BAUD_CHANGE错误取证，源7682145e…；原645ded49…保存在主机kernel205/hci_qca-before-diagnostic-private.c。诊断模块W=1构建通过，.config55f1f0a3…和全量sym/order已恢复。Image183/boot204 cdd16e29…/实际DTB b9d9c2a1…/CAMSS82cbc052…保持，canonical旧DTB22c1…未覆盖。未修改GENI产品源码。

GENI流控模式改变后未重放相同mctrl是待证假设；C harness首次编译因userspace头缺TIOCM_LOOP失败，日志留在私有rts-contract/current-build-private.log，目前没有成功测试收据。不能把假设或未完成测试当成历史phase5根因。若继续应修复harness的真实内核常量stub并保留失败，之后再决定实际驱动修改/原生验证。

用户专门询问GNSS，已补查[相关机型GNSS对照](reference/kernel205/GNSS-RELATED-DEVICES.md)：一加6的A-GPS/固件/运营商报告，同平台7T Pro仍Partial，X2 Pro与一加Android配置39项只有LPP_PROFILE2/3不同，跨品牌L5项目仅GT2 Pro测试且本次只读。源码三仓库固定提交；API403和配置首次UTF8失败均保留。没有执行远程脚本、替换固件或修改NV。下一步核对本机固件与配置装载合约及真实RF接收；204的188NMEA/176推进时间/自动168h辅助数据仍无fix/CNR，不能算205新接收证据。

MM191 b350/签名APK203/helper421/init54、SSC9a1诊断保持。SSC第一次204启动退出根因仍未解决。旧rootfs132未更新；相机正常sensor资源/PLDO输入/冷启、GNSS真实定位、蜂窝真实业务、传感器物理精度/FastRPC SSR、BT启动故障、Wi-Fi/USB PM及其它外设仍开放。完整板级限制及回退见204快照。

导航：[边界](WORKING-BOUNDARIES.md)、[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。主机私有 `E:/edk2-samurai-out/kernel205/current-work-private.json` 同步记录临时状态。
'''
(repo / 'NEXT-SESSION.md').write_text(text, encoding='utf-8')
print('GNSS sources/config comparison recorded; fresh r2 idle receipt saved; interrupted diagnostic deployment and recovery checkpoint corrected.')
