from pathlib import Path
import json

w=Path('/mnt/e/RealmeX2Pro edk2')
ref=w/'reference/kernel75'
r=json.loads((ref/'evidence-validation.json').read_text())
assert r['second_boot_verified'] and r['second_boot_dsi_errors']==0
session='75-a640-render-and-sofef03f-clock-fix.md'
state=f'''当前#76：A640/GMU已启用，本机签名固件加载和Turnip真实渲染通过，
累计{r['total_gpu_submissions']}次交替红/绿三角形渲染、4096像素读回及fence校验成功。
用户照片及纯白测试曾确认静止彩色噪点；关闭EOT单独无效，补齐原厂非连续DSI时钟并
清除继承的controller/PHY强制时钟位后，用户确认全白及重新启动后的首次彩条正常。
最终两次#76启动完整日志无DSI worker错误、SMMU context fault或Oops，taint0；
混合GPU/显示回归共12次显示关闭/开启通过。当前boot_id={r['second_boot_id']}。
DTB只有GPU/GMU status及板级ZAP路径三处语义变化；EUD、触摸、RPMh、init/SSH身份保留。
仅部署boot一次/logdump七次，Android/全部数据/GPT保留；专有固件及密钥不入Git。
下一项电池/充电、无线/音频等；冷断电、90Hz、休眠、全部GPU频点压力仍未验收。
'''
for name in ('README.md','RX-CONSOLE.md','FLYWHEEL.md','linux-port/README.md'):
    p=w/name
    s=p.read_text()
    start=s.index('当前硬件接入：')
    end=s.index('\n\n',start)
    prefix='../' if name.startswith('linux-port/') else ''
    p.write_text(s[:start]+f'当前硬件接入：[session75]({prefix}sessions/{session})。\n'+state.rstrip()+s[end:])
p=w/'HANDOVER-NEXT.md'
s=p.read_text()
start=s.index('## 0. ')
end=s.index('## 2. ',start)
s=s[:start]+'''## 0. TL;DR - where the project stands (2026-10-10, session75)

'''+state+'''
补丁0011在旧命令帧无法排空时停TE/trigger，且必须成功复位覆盖对应INTF的CTL；
保留0010双复位/清输出顺序，换IOMMU域前完成，并修正初始化失败时private object二次释放。
补丁0012设置NO_EOT_PACKET/CLOCK_NON_CONTINUOUS，并显式清除继承的强制时钟请求。
PPS、DSC几何、DSI链路频率、电压、EUD传输保持；只读DSC寄存器诊断已从最终版本移除。
session74的数字CRC证据不代表当时已通过光学验收；session75的用户观察单独保存。

## 1. What to do next, in order

1. 通过169.254.42.1密钥SSH保存新日志，保留#76可显示/可GPU渲染基线。
2. 优先查本机电池电量计/MP2650、原厂配置及主线支持，再推进无线/音频等硬件。
   禁止套用其它手机的电压/充电参数；不把注册节点或warning消失当成功。
3. 后续独立完成90Hz、休眠恢复、GPU各频点压力、触摸校准和OTG/USB3。

实际Linux源码/home/cy122/x2pro-linux/linux，initramfs/home/cy122/x2pro-linux/initramfs。
不运行旧build-image.sh；保留init/USB hook/SSH身份、TOP_CFG0x11/整帧/RX53/F1/两终端。
只写boot/logdump，按PARTNAME核对，保留Android/全部数据/GPT；只推fork/master。
临时Turnip测试包仅位于本地kernel75和手机/tmp，不代表完整桌面/rootfs已经建立。
回退GPU关闭基线需同时使用kernel75/boot-before.img与logdump-before.img，两个哈希见
reference/kernel75/final-validation.json；最终可显示基线为kernel75/boot-k75-gpu.img+
logdump-k75-final.img。COM/USB owner必须finally释放；早期console未排完时不能称启动失败。

'''+s[end:]
p.write_text(s)
(w/'NEXT-SESSION.md').write_text('''# 下一阶段交接：电池/充电与剩余硬件（session75）

'''+state+'''
先读sessions/75-a640-render-and-sofef03f-clock-fix.md与reference/kernel75/README.md。
实际#76源码与配置、DTB/FW、FAT Image/CPIO及分区回读均已核对；0011/0012补丁对
session74基线精确应用复现当前源码，checkpatch零错误/警告。GPU-SUDO没有启用。
GMU固件v2.0.261；本机a630_sqe.fw/a640_gmu.bin/完整签名a640_zap.mbn仅本地，
七固件预检及MDT可重定位4KiB LOAD适配8KiB carveout，真实渲染已验证认证路径。
CPU framebuffer正常但物理噪点，证明截图/CRC不是屏幕验收。EOT-only失败；最后
非连续时钟+清继承位在纯白和fresh-boot彩条通过。不要再改DSC PPS/时钟频率来猜测。
#75诊断版早期有147条DSI worker消息，首次电源循环后结束；最终#76两次日志均为零。
#69 drain超时导致旧private-object二次释放，F1后shutdown阻塞，曾用sysrq b恢复fastboot；
之后cleanup和对应INTF复位修复。#71只构建未刷；一次EOT部署F1回执未捕获，采用单次
OUT完成+独立fastboot枚举验证，日志没有伪造回执。其余最终F1均有回执/枚举。

SSH/SCP工具在reference/kernel72；地址169.254.42.1，私钥/known_hosts仅本地kernel72。
真实内核/home/cy122/x2pro-linux/linux、initramfs/home/cy122/x2pro-linux/initramfs，
实际Git /home/cy122/edk2-samurai/repo；Windows镜像不是Git。保持REFGEN内建/defer60秒。
EUD重启先com-up，早期verbose输出需排完才发原生命令；COM和USB接口单owner/finally释放。
专有blob/完整Image/logdump/CPIO/SSH身份不发布。只boot/logdump写入且PARTNAME核对，
本机boot=/dev/sde11、logdump=/dev/sde32；不要猜DSP或其它分区。保留Android/数据/GPT。
最终boot sha43ddcba2444e1672cd95205f6984c761eaeb59c83162cffdffb371c50a29c37b，
logdump sha607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0。
回退GPU关闭基线使用本地kernel75/boot-before.img与logdump-before.img，见final-validation。
全硬件目标仍active；下一轮从原厂电量计/MP2650资料和真实日志推进，不按注册数量验收。
''')
(w/'NEXT-SESSION-PROMPT.md').write_text('''继续无人硬件接入目标。先读NEXT-SESSION.md、sessions/75和reference/kernel75/README.md。
当前#76已启用A640/GMU，本机签名固件、Turnip真实渲染/读回与fence累计39096次通过。
物理花屏已通过非连续DSI时钟/清继承位修正；用户确认全白及fresh-boot首次彩条正常，
最终两启动日志无DSI/SMMU/Oops、taint0，12次混合显示电源循环通过。保留0011/0012、
EUD/TOP_CFG0x11/整帧/RX53/F1/两终端、触摸/CPU/UFS/NCM SSH及本地SSH身份。
下一项查本机电量计和MP2650原厂资料/主线支持，再无线/音频；不套其它板电压。
实际WSL源码/initramfs，别运行旧build-image.sh；DT变更必须进实际UEFI；仅boot/logdump、
PARTNAME核对，保留Android/数据/GPT，专有固件/镜像/密钥不发布，只推fork/master。
冷断电、90Hz、休眠、GPU各频点压力、OTG/USB3仍待验。全硬件目标active。
''')
p=w/'linux-port/docs/HARDWARE-STATUS.md'
s=p.read_text().replace('（2026-10-10，session74）','（2026-10-10，session75）')
start=s.index('按用户能使用的功能')
end=s.index('| 功能组',start)
s=s[:start]+'按用户可使用功能分14类。触摸基本输入、普通USB NCM/SSH/SCP、原生60Hz显示和GPU真实渲染已获得数据流证据。\n'+state+'\n'+s[end:]
s=s.replace('| 原生显示面板 | SOFEF03F 1080×2400@60 DSC、DCS状态0x9c、硬件CRC、显示接管、两启动18次电源循环及亮度写入通过 | 冷断电、90Hz、亮度硬件读回/光学输出及休眠恢复 |',
            '| 原生显示面板 | SOFEF03F 1080×2400@60 DSC；用户确认全白和重启首次彩条正常；最终两启动无DSI/SMMU错误，12次混合电源循环通过 | 冷断电、90Hz、亮度校准和休眠恢复 |')
s=s.replace('| GPU | 设备树禁用；本机七固件哈希/ELF/MDT LOAD几何通过预检，运行未验收 | GMU/Adreno固件及供电、MSM DRM、渲染/恢复 |',
            '| GPU | A640/GMU主线驱动和本机签名固件；Turnip真实渲染/4096像素读回及fence累计39096次通过 | 各频点压力、休眠恢复及完整桌面应用 |')
s=s.replace('优先GPU/GMU、\n电池/充电、无线/音频，','优先电池/充电、无线/音频，')
p.write_text(s)
p=w/'DOCS-INDEX.md'
s=p.read_text().replace('| sessions/74-sm8150-display-boot-handoff.md、reference/kernel74/ |',
    '| sessions/75-a640-render-and-sofef03f-clock-fix.md、reference/kernel75/ | A640真实渲染、花屏失败证据及非连续DSI时钟的光学验收 |\n| sessions/74-sm8150-display-boot-handoff.md、reference/kernel74/ |',1)
s=s.replace('session74显示交接验证、GPU/GMU接入、自动USB SSH通道与短提示词','session75 GPU渲染/花屏修正、电池充电等剩余硬件、自动USB SSH与提示词')
p.write_text(s)
print('Living docs updated from final device and optical evidence.')
