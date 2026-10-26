from pathlib import Path
import hashlib

root = Path('/mnt/e/RealmeX2Pro edk2')
private = Path('/mnt/e/edk2-samurai-out/kernel184')
current = root / 'NEXT-SESSION.md'
(private / 'NEXT-SESSION-before-trim-private.md').write_bytes(current.read_bytes())
assert (root / 'archive/NEXT-SESSION-through183-2026-10-15.md').stat().st_size == 6094
text = '''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段184，外设适配goal active。当前仍kernel183/logdump183、boot/DTB172、software/modules132/Mesa149/UCM173；本轮两次同镜像重启，未刷分区。规则见[边界](WORKING-BOUNDARIES.md)。用户暂无耳机，不重复问。

## 当前部署与实机依据

| 项目 | 最后核对结果 |
| --- | --- |
| 当前组合 | #183 SMP PREEMPT Oct15 00:20:49 CST；Image bfa72dd9…、logdump e73754c7…、boot172 77e1a272…及DTB172 22c1f2ad…保持 |
| 光线接口修复 | 本机00121的wise_light实体可用，ambient_light为空；独立QRTR客户端96个1025测量/非法帧0/停止ACK通过。lux均0，原始通道有变化，准确度未验收 |
| libssc候选 | 0.4.4名称配置补丁，ARM64编译/117个验签SDK包/SONAME与导出函数名检查通过；库SHA45570ea4…，未替换系统库，未启用自动SLPI服务 |
| 标准客户端与桌面 | 新boot v4同一库默认查询254/0样本、OEM查询0/41样本/正常禁用。SensorProxy光线与接近识别、单位lux、ClaimLight/ReleaseLight/退出0；加速度未注册，LightLevel仍0 |
| 当前最终534.62秒 | Phosh运行、taint0，ADSP/modem running；SLPI offline/供电0，临时进程退出，PCM闭/双功放静音，来源/NV/boot/logdump/persist核验 |
| 故障范围 | 当前所列WARN/Oops/GPU/DPU/ASoC/IRQ读取/SLPI启动超时0；蓝牙仍2条phase2/115200/chunk1/partial0/first00，不称整机清零 |
| 历史音频183 | 前一boot活跃双工合成crash原客户端恢复、左右匹配声学及两次s2idle/醒后回归通过。当前相同镜像的新boot未重复这些测试，不混用启动证据 |

本轮完整依据：[184](reference/kernel184/README.md)、[v4](reference/kernel184/userspace-v4-validation.json)、[最终](reference/kernel184/final-validation.json)。前183完整音频与失败记录见[183](reference/kernel183/README.md)、[182](reference/kernel182/README.md)、[181](reference/kernel181/README.md)、[171人工听音](reference/kernel171/README.md)；原检查点逐字保留在[through183快照](archive/NEXT-SESSION-through183-2026-10-15.md)，其中相对链接按原工作区根解释。

## 源码、产物与回退依据

- 内核WSL /home/cy122/pmos-samurai-kernel136/kernel：tracked12，完整hash见[183](reference/kernel183/source-validation.json)。SLIM/WCD离线清理183、MFD181/PDR180、MBHC172/machine175、15显示源163及缓存策略保持；现有签名保持但新增两个导出API，不声称全部ABI未改。本轮未改内核源码。
- 当前镜像及回退在E:/edk2-samurai-out/kernel183、181等。logdump181 56aa1c46…仍有活跃STOP问题；更早180/176/175各自失败保留。SD1的172/171原件保持，164/168为SD0。BDS源164/固件172/FdtBlob129保持。
- 184源码/脱敏收据在[reference/kernel184](reference/kernel184/README.md)，补丁及配置见[SSC兼容层](linux-port/ssc/README.md)。官方原版源包716d6bd6…；实测候选是手机k184-libssc-r2/build-r4/src/libssc.so.2。整理单脚本未另做全新干净构建；初始下载/SDK/链接失败原件保留。
- 当前boot身份在手机k184-final及私人k184-final-evidence包；完整证据在E:/edk2-samurai-out/kernel184。k183-final/k183-all属于上一boot，183 preflash属于旧181；184两份preflash也各属于切换前boot，下一次操作新取身份。
- 本轮两次RESTART2各1，fresh fastboot后各reboot1，无flash。第二次即时枚举空只读等待，未重发切换。当前SLPI已在此boot停过，不盲目重放start；下一试验先解决停启问题或取得新的受控启动。
- UCM173由callaudiod管理端口，勿强制补载Pulse端口切换模块。软件/rootfs132更新可能覆盖UCM173/Mesa149；原132 UCM和所有重要备份保持。

## 续作与已知风险

1. 当前主要目标是GPS、摄像头、蓝牙、传感器、蜂窝等完整适配。优先SLPI停启ready握手、持续文件服务、光照准确度及本机OEM元数据/惯性注册。C28/C35与A.11历史尝试各自保留，不导入他机校准。
2. 184首次SLPI停止后同boot第二次启动−110，未进入候选库测试；根因未证明。v3误用SensorProxy --debug导致daemon退出1，CLI已通过；检查实际帮助改日志方式后独立新boot v4通过。保留所有失败，不用旧样本证明新启动。
3. 蓝牙两次新boot均有phase2 NUL重组错误，继续核对power pulse与H4边界，测试只扫描、不连接；振动不新增脉冲。GPS的LOC控制历史可用，但真实fix/标准服务/时间辅助仍开放。蜂窝sim-missing，注册/数据/通话/SMS未验收。
4. 摄像头仍缺PM8008四输入/冷地址/复位及chip-enable的完整本机依据，先补供电契约，再验证实体CCI/C-PHY出图；内部TPG不代替实体摄像头验收。
5. 音频耳机/耳麦/按钮、真实watchdog、更多跨启动/长时可靠性、音乐人声/瞬态/保护仍开放。183前boot的合成故障与两次s2idle不代表所有SSR、deep STR或休眠音频无损；178/180/181旧失败保持。
6. 其它功能及独立Wi-Fi/USB/充电/显示等问题继续见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。保护NV/校准/私人数据和电池保护；不因本轮有限窗口健康认定全部可用。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
raw = text.encode()
assert len(raw) <= 6500, len(raw)
current.write_text(text, encoding='utf-8', newline='\n')
print('Current checkpoint updated:', len(raw), 'bytes; original183 checkpoint preserved.')
