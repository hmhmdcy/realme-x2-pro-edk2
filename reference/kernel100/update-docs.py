from pathlib import Path
import json, re

root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel100')
paths=['README.md','FLYWHEEL.md','linux-port/README.md','linux-port/docs/HARDWARE-STATUS.md',
    'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','HANDOVER-NEXT.md','DOCS-INDEX.md']
saved={name:(root/name).read_text() for name in paths}
target=out/'public-docs-before.json'
assert not target.exists()
rootfs='2026-10-11 rootfs 进展：用户选择 userdata/F2FS，已制作 ARM64 console rootfs 和配套原生内核候选，离线文件系统及 sparse 校验通过，尚未刷机。镜像、启动衔接和实机验收边界见 [F2FS 镜像说明](docs/ROOTFS-F2FS-IMAGE.md)。以下硬件状态保留原有实测记录。'
assert saved['linux-port/README.md'].count(rootfs)==1
target.write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
summary='''手机已部署Linux #99（阶段100），AW8697已接入；标准FF/电气状态、close/SIGKILL/1秒看门狗停振通过，物理振动待用户确认。
当前5GHz经一次有界手动恢复：认证/DHCP/网关/DNS/HTTP通过，MPSS running/taint0、蓝牙关闭，不配对连接。
全源就绪等待已刷入并执行14次、firmware/NV prepare成功；首次MPSS仍在up后39.988秒fatal，自动无线启动未通过，原失败日志/标记保留。
阶段98两次2.4GHz掉线、单播删除约3.1秒等待未修复；本次两次显示超时、三次BT上电脉冲错误、两次USB备份传输超时保留。
完整备份分块/整体SHA及86文件checkpoint/部署读回通过，原NV/persist不变；CPIO仅无线等待服务变化，DTB/真实EDK2 boot/驱动/模块保持99。
下一项继续振动机械确认及其它硬件接入，NFC无标签先控制器、充电收尾；冷启动/休眠/长期稳定仍待办，全硬件goal仍active。
保留Android、数据/GPT、SSH身份、旧显示快照和另一线程rootfs/F2FS；固件/镜像/身份/凭据/原日志仅私人目录。'''
for name,start,end,link in [
    ('README.md','当前状态：','\n\nUnofficial','sessions/100-all-source-readiness-and-first-mpss-crash.md'),
    ('linux-port/README.md','当前连接状态：','\n\n硬件功能清单：','../sessions/100-all-source-readiness-and-first-mpss-crash.md')]:
    text=saved[name];a=text.index(start);b=text.index(end,a)
    next_link='../NEXT-SESSION.md' if name.startswith('linux-port/') else 'NEXT-SESSION.md'
    text=text[:a]+f'{start}[session100]({link})，[下一阶段]({next_link})。\n'+summary+text[b:]
    if name.startswith('linux-port/'):assert text.count(rootfs)==1
    (root/name).write_text(text)
text=saved['FLYWHEEL.md'];a=text.index('当前硬件接入：');b=text.index('\n\n> 2026-10-08',a)
text=text[:a]+'当前硬件接入：[session100](sessions/100-all-source-readiness-and-first-mpss-crash.md)与[下一阶段](NEXT-SESSION.md)。\n'+summary+'\n每轮先新现场、完整boot/logdump备份及实际EDK2/FAT Image审计；受控停止WPA→BT→ath10k→MPSS，F1后独立fastboot核对。'+text[b:]
(root/'FLYWHEEL.md').write_text(text)
text=saved['linux-port/docs/HARDWARE-STATUS.md'];b=text.index('| 功能组 |')
text='# RMX1931 Linux 硬件接入清单（2026-10-11，session100）\n\n15组用户可使用硬件保持。\n'+summary+'\n\n'+text[b:]
rows={
'原生显示面板':'| 原生显示面板 | 75光学/84翻页通过；#93–#99首次DRM/fb0注册；#99两次frame-done timeout在321.63/438.71秒，最终underrun0/frame_done_cnt2；#98两个及#97/#96历史失败保持 | 独立超时/恢复根因，保留SMMU/CTL保护与旧快照；冷/暖启动、90Hz、亮度及休眠 |',
'Wi-Fi':'| Wi-Fi | 本机board/API5/MPSS/ath10k；#99全源等待14次/prepare成功，首次MPSS up后39.988秒fatal，自动启动失败；一次手动恢复后5GHz认证/DHCP/网关/DNS/HTTP通过；阶段98双频/双向4MiB及两次2.4GHz掉线证据保留 | 首次MPSS崩溃/自动启动可靠性、2.4GHz BT-off对照、WCN3990删除等待；冷启动/热循环/宽信道/吞吐/休眠/长期稳定；自动热点连接/公网ICMP未通过 |',
'蓝牙':'| 蓝牙 | UART13/hci0/revision21；#99自动地址因MPSS崩溃失败，手动恢复后独立DMS查询/同机地址/关闭策略通过；三次上电脉冲单00帧错误；阶段98扫描13个地址/类型组合、阶段96已有RAM身份MPSS-off扫描证据保留 | 上电脉冲错误、全新离线身份/真实失败、冷启动/休眠；暂不配对连接，扫描之外验收待用户恢复 |',
'蜂窝网络/数据':'| 蜂窝网络/数据 | MPSS/QRTR用于Wi-Fi；94–98五次首次暖启动通过，99在源就绪前失败，100首次MPSS约40秒fatal且一次手动热恢复通过；只读DMS成功，无SIM/拨号/蜂窝数据验收 | 首次MPSS崩溃、冷启动/长期可靠性、SIM/实际蜂窝连接；Wi-Fi/DMS不能当蜂窝通过 |',
'振动':'| 振动 | 本机AW8697/QUP7/0x5a、reset116/IRQ24；#98标准FF_RUMBLE、三次20%150ms电气状态、close/SIGKILL/1.02秒看门狗停振通过；#99暖启动ID97/standby/error0 | 用户机械触感确认仍待答；本机profile/Shipping API核对、强度/效果、冷启动/休眠/恢复；GO/STATE不等同物理输出 |'}
for name,row in rows.items():
    pattern=r'^\| '+re.escape(name)+r' \|.*$'
    text,count=re.subn(pattern,row,text,flags=re.M);assert count==1,name
text=text.replace('保留待办，转到Wi-Fi；','保留待办，继续下一硬件；')
old='下一项优先单播删除等待修复、2.4GHz BT-off掉线对照、独立显示超时、UART上电脉冲及真实失败/冷启动/休眠稳定性。用户蓝牙暂只扫描，NFC只控制器。'
assert old in text
text=text.replace(old,'下一项优先振动机械确认及其它硬件接入；同时保留首次MPSS崩溃、2.4GHz掉线、删除等待、独立显示超时、UART上电脉冲、USB传输与冷启动/休眠待办。用户蓝牙暂不配对连接，NFC只控制器。')
(root/'linux-port/docs/HARDWARE-STATUS.md').write_text(text)
handoff=(root/'reference/kernel100/next-session.md').read_text()
(root/'NEXT-SESSION.md').write_text(handoff.replace('../../sessions/','sessions/').replace('../../linux-port/','linux-port/'))
prompt='继续Realme X2 Pro下一硬件Linux适配。先读NEXT-SESSION.md、sessions/99、sessions/100、reference/kernel100及私人kernel100/checkpoint-validation.json，重新核对当前boot ID/进程/目录/哈希。Linux #99已刷logdump，AW8697 FF/电气与close/SIGKILL/1秒看门狗通过，用户是否感到三次短振动仍待答；先机械确认再继续其它硬件。Wi-Fi全源等待已刷入并执行14次/prepare成功，但首次MPSS up后39.988秒fatal无原因字符串，自动Wi-Fi/BT地址未通过。一次有界手动恢复后5GHz认证/DHCP/网关/DNS/HTTP通过，MPSS running/taint0/BT关闭；原boot-finished=1和日志保持，不能宣称自动启动修复。阶段98两次2.4GHz reason7和约3.1秒单播删除等待未解决；本次两显示超时/三BT脉冲帧错误/两USB传输超时保留。先有限诊断SMEM错误/长度/空消息和本机QRTR启动链，勿盲加固定延时或无限恢复；蓝牙暂不配对连接、NFC无标签先控制器、充电收尾。86文件checkpoint/部署读回/80块完整备份/6NV与persist不变校验通过。保留15组硬件/Android/userdata/GPT/原NV/persist/SSH身份/旧显示85–88快照/rootfs01和F2FS段落；NV仅RAM COW，只刷boot/logdump，DTB改变须重建真实EDK2。固件/凭据/身份/原日志/镜像/二进制仅私人，无提交/推送，全硬件goal仍active。\n'
(root/'NEXT-SESSION-PROMPT.md').write_text(prompt)
text=saved['HANDOVER-NEXT.md']
header,tail=text.split('\n',1)
text=header+'\n\n当前交接见 [阶段100](sessions/100-all-source-readiness-and-first-mpss-crash.md) 与 [NEXT-SESSION](NEXT-SESSION.md)：Linux #99，振动机械确认待答，5GHz手动恢复可用，首次MPSS崩溃/自动启动仍待修复。以下阶段88记录保留历史上下文。\n'+tail
text=text.replace('> Updated 2026-10-10 (Asia/Shanghai).  Sections 0-7 below are the living part:', '> Updated 2026-10-11 (Asia/Shanghai). Sections 0-7 below retain stage88 history:')
(root/'HANDOVER-NEXT.md').write_text(text)
text=saved['DOCS-INDEX.md'];header,tail=text.split('\n',1)
text=header+'\n\n当前：[阶段100](sessions/100-all-source-readiness-and-first-mpss-crash.md)、[阶段99](sessions/99-aw8697-haptics-and-ufs-readiness.md)、[下一阶段](NEXT-SESSION.md)。\n'+tail
(root/'DOCS-INDEX.md').write_text(text)
assert (root/'linux-port/README.md').read_text().count(rootfs)==1
print('CURRENT_DOCS_UPDATED_ROOTFS_PARAGRAPH_PRESERVED')
