from pathlib import Path
import json, re

root = Path('/mnt/e/RealmeX2Pro edk2')
report = json.loads((root / 'reference/kernel112/checkpoint-validation.json').read_text())
checks = report['checkpoints']
latest = checks.get('desktop-ram-v4-after.tar', checks.get('reboot-radio-clean-2.tar', checks['reboot-radio-clean-1.tar']))
status = f'''当前部署Linux #112，boot固件/内嵌DTB为#111；postmarketOS/Nura edge已安装在userdata F2FS并运行Phosh。用户已确认112首次与最新两次完整重启/传感器试验后的画面稳定，解锁及应用正常；恢复启动也确认稳定锁屏。旧滚动花屏和长稳仍未完成；最新桌面检查点DPU超时{latest['dpu_timeouts']}、GPU故障{latest['gpu_faults']}、taint0，计数只代表该快照。

USB NCM/密钥SSH、2.4GHz NetworkManager Wi-Fi、HTTPS/NTP、本机桌面UCM与空闲PCM/功放关闭通过。两次完整停止无线服务后的正常重启均恢复新内核，试验后桌面回归通过；EFI运行时异常仍保留，此前直接重启失败及fastboot仅重启恢复不能记作通过。SLPI/SSC服务能启动，但加速度未验收；256字节接收限制已修复，实机完成370字节请求补取与342字节RAM真实写入，随后仍报传感器I2C超时。六LUN头尾/几何、persist、NV和本机固件/校准来源保持。

全硬件goal active。蓝牙不配对连接，振动不发新脉冲，NFC仅控制器，充电探针已收尾；摄像头、指纹、GNSS、蜂窝通话/数据、休眠及长期稳定仍待验收。私人凭据、身份、固件、校准、日志、录音和镜像不公开，不提交推送。
'''
link='[阶段112](sessions/112-startup-sensor-registry-and-reboot.md)，[下一阶段](NEXT-SESSION.md)。\n\n'
path=root/'README.md'; text=path.read_text(); marker='Unofficial EDK2/UEFI port'
start=text.index(marker)
path.write_text(text.split('\n',1)[0]+'\n\n'+link+status+'\n'+text[start:])
path=root/'FLYWHEEL.md'; text=path.read_text(); start=text.index('> 2026-10-08')
procedure='''持久F2FS日常重启使用kernel109/reboot-pmos-persistent.sh：新前缀、当前bootID，停止桌面/NM/WPA/BT/ath10k/MPSS、核验NV并sync后由OpenRC关机。kernel112/observe-radio-clean-reboot.ps1只做该正常重启和两段有界EUD日志；每个owner先释放再com-up。SSH恢复后核对新boot、完整日志和分区哈希。

F1前必须取得当前启动根文件系统已同步/冻结或只读卸载的独立证据；不能沿用上一启动的关机日志。kernel112/recover-f1-after-reboot.ps1已封禁历史重放。flash-pmos.ps1会erase userdata，不用于内核更新或日常重启。新候选保留完整boot/logdump回退，DTB变更必须同步EDK2内嵌DTB；旧110救援DTB与111/112不匹配，不盲刷。

'''
path.write_text(text.split('\n',1)[0]+'\n\n'+link+status+'\n'+procedure+text[start:])
path=root/'linux-port/docs/HARDWARE-STATUS.md'; text=path.read_text(); table=text.index('| 功能组 |'); tail=text[table:]
lines=tail.splitlines()
replace={
'触摸':'| 触摸 | S3706A注册；用户确认112 Phosh可解锁及打开应用 | 方向/边缘/休眠/长稳 |',
'原生显示面板':f'| 原生显示面板 | 面板错误状态/引用修复；用户确认112首次、恢复及最新两次重启后稳定；最新桌面DPU超时{latest["dpu_timeouts"]} | 111首启动旧滚动花屏记录保留；首次接管/休眠/纯白光学/长稳 |',
'GPU':f'| GPU | FD640硬件GLES2 Phosh；最新正常重启GPU故障{latest["gpu_faults"]}/taint0 | 历史错误自动启动触发恢复保留；应用压力/休眠/长稳 |',
'普通USB与OTG':'| 普通USB与OTG | NCM/密钥SSH/SCP与EUD共存；完整流程正常重启恢复，boot111/logdump112匹配 | 直接重启失败原因；OTG/USB3/休眠/重置/长稳 |',
'蜂窝网络/数据':'| 蜂窝网络/数据 | 自动MPSS、QRTR及固件/RAM COW运行；6个源NV保持 | 通话/移动数据未验收；冷启动/休眠/长稳 |',
'其它传感器':'| 其它传感器 | SLPI手动启动/SSC400服务；实际OEM属性与完整注册表；RAM v4实机370字节补取/342字节真实写入，随后I2C超时崩溃，加速度无样本 | 本机I2C/供电/时钟和固件依赖；光线/接近/陀螺仪等；不能以SSC服务替代验收 |'}
for i,line in enumerate(lines):
    for name,new in replace.items():
        if line.startswith('| '+name+' |'): lines[i]=new
tail='\n'.join(lines)+'\n'
tail=tail.replace('下一项核对Phosh实物显示/触屏、重启音频自动恢复，再查5GHz、显示长稳和其它硬件；', '下一项完成大请求RAM传感器试验，并继续重启、5GHz、显示长稳和其它硬件；')
path.write_text('# RMX1931 Linux 硬件接入清单（2026-10-11，session112）\n\n15组用户可使用硬件保持。\n\n'+status+'\n'+tail)
path=root/'sessions/109-pmos-userdata-phosh-and-desktop-audio.md'; text=path.read_text()
notice='历史阶段109；当前部署与用户物理确认见[阶段112](112-startup-sensor-registry-and-reboot.md)。以下保留109当时检查点及未确认边界。'
if notice not in text: path.write_text(text.split('\n',1)[0]+'\n\n'+notice+'\n'+text.split('\n',1)[1])
print('Public status updated to verified kernel112 evidence; 15 hardware groups preserved')
