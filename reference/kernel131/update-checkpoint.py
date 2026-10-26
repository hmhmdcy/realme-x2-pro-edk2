#!/usr/bin/env python3
from pathlib import Path
import json

root = Path('/mnt/e/RealmeX2Pro edk2')
summary = '阶段131已证明旧glmark离屏尺寸错误：同一FD640/Mesa26.2.4场景在1080×2259失败、固定实际FBO800×600按原阈值通过；随后1.993/2.737秒出现两次不同IOVA的CCU READ TRANSLATION，GPU整体仍失败。新转储/7BO离线解码及59+21成员SHA验证完成，停止GPU负载，无GPU重置/桌面重启/刷机。转充电观测：当前129已含87 ADC重试/ENODATA修正，临时绑定8份标准uevent均非空、ONLINE1/Full；ADC电压5/8、电流4/8，其余ENODATA，11配置读数保持，测试后客户端移除。当前内核仍#129、最新完整rootfs130，15组功能边界/稳定回退保持，完整系统goal active。'
session = 'sessions/131-fixed-size-pixel-validation-and-delayed-gpu-fault.md'
doc = root / session
with doc.open('a') as file:
    file.write('\n充电实际追加：首次SCP复制的Windows二进制无执行位，在任何临时绑定前PermissionError失败，原目录保留；固定SHA通过后仅给工具执行权限，新r2目录测试。当前129已有正确驱动，8次标准uevent均非空且ONLINE=1/STATUS=Full，5次电压4.550–4.650V、4次电流162.500–256.250mA，另3/4次属性读ENODATA且未使整份事件丢失。11个配置寄存器前后保持、busy所有权拒绝/属性0444、包数据库保持、无新增GPU故障，临时客户端已移除。16成员SHA验证通过；输入ADC数值仍无外部校准，不是充电控制/快充或持久绑定验收。下一项推进只读观测持久DT接入，保持保护链/预算与控制待办。\n')
for name in ['README.md', 'FLYWHEEL.md']:
    path = root / name
    body = path.read_text()
    first, rest = body.split('\n', 1)
    path.write_text(first + '\n\n' + summary + '\n\n[阶段131](' + session + ')。\n' + rest)
path = root / 'DOCS-INDEX.md'
first, rest = path.read_text().split('\n', 1)
path.write_text(first + '\n\n- [阶段131](' + session + ')：固定离屏尺寸实机对照通过，但迟发GPU故障仍存在；当前129充电观测事件8次非空验收。\n' + rest)
path = root / 'linux-port/docs/HARDWARE-STATUS.md'
body = path.read_text().replace('阶段130）', '阶段131）', 1)
first, rest = body.split('\n', 1)
body = first + '\n\n' + summary + '\n\n[阶段131](../../' + session + ')。\n' + rest
lines = body.splitlines()
for i, line in enumerate(lines):
    if line.startswith('| GPU |'):
        lines[i] = '| GPU | FD640/ES3.2 Mesa26.2.4硬件绘制；131固定FBO800×600同一场景像素通过，原1080×2259对照失败；退出后两次不同IOVA CCU READ TRANSLATION，GPU整体失败，新转储已解码 | 不把单场景尺寸修正扩展到全GPU验收；释放/映射/缓存/迟发故障根因未证实，禁止全33场景重跑/重放/全局debug，长稳与持续显示开放 |'
    if line.startswith('| 电池与充电 |'):
        lines[i] = '| 电池与充电 | 电量可读；当前129已含87观测修正，131临时绑定8份uevent非空/ONLINE1/Full，ADC电压5/8及电流4/8，其余ENODATA未丢整事件；11配置保持，测试后移除客户端 | 只读观测持久DT、ADC外部校准、2719/短路保护/热敏/USB预算/失联与实际充电控制待办；近满电不能判速率 |'
path.write_text('\n'.join(lines) + '\n')
path = root / 'NEXT-SESSION.md'
old = path.read_text()
path.write_text('# Realme X2 Pro 继续检查点（阶段131，2026-10-12）\n\n' + summary + '\n\n先读[阶段131](' + session + ')、reference/kernel131/fbo-comparison-validation.json、core-decode-validation.json及mp2650-event-validation.json。所有131下载/构建/实机测试/转储作业均terminal，失败现场保留，不能重放prepare/test脚本。当前仍与130相同boot，身份只取E私有kernel130/embedded-boot-id-private.txt或手机k130-warmboot-r2。现boot GPU翻译故障累计2，桌面原PID/taint0，不认定硬件健康全通过。\n\n下一项：当前#129 MP2650观测驱动可工作，但无持久DT节点。先检查本机QUP1/0x5c唯一身份、固件资源、binding schema并隔离构建正确持久只读节点；不要重刷旧#87或移植厂商复位/关安全计时器probe。GPU先留档换项，未来需新故障证据支持有界诊断，不重跑旧33场景。\n\n131 SDK仅在/tmp/k131-native-sdk，包数据库未改，源码/15签名包及输入tar保留E:/edk2-samurai-out/kernel131/native-sdk；原版/修正版程序、源patch和构建失败日志已私有归档。新转储364548字节，两个不同IOVA，离线7 BO均未包含fault、TTBR匹配/零PTE1/无VM历史，估计命令停点非根因。E118解码卷已卸载。完整镜像/稳定构建不删除。\n\n以下是130产物和挂载操作说明，历史0故障仅130启动窗口，不能作为当前GPU健康判断：\n\n' + old)
