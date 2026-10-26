from pathlib import Path

here=Path(__file__).resolve().parent;repo=here.parents[1];out=Path('/mnt/e/edk2-samurai-out/kernel203')
text='''# Realme X2 Pro 当前检查点

2026-10-15，阶段203，完整外设goal active。MM191/helper202签名APK已实机落地，GNSS-only复测68条NMEA/59推进时间，仍无fix/正CNR。仍202第二次boot，无新重启/刷写。最后4039.43秒taint0/fault0。[203报告](reference/kernel203/README.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与实机依据

- boot200/四域DT2e2f8e64…/CAMSS82cbc052…；Image183/logdump183、modules132覆盖hci_uart185/fastrpc189，Mesa149/UCM173。
- MM/openrc/udev 1.25.95_git20261005-r1，libmm-glib原r0；helper/stack 0.1.0-r0。MM b350c55b…、helper42168f33…/init54b81745…字节不变，已APK管理。
- helper显式重启后UTC准备1/完成1、worker1/完成1、idle；每MM owner在GPS空闲/chrony同步时准备UTC，仅GPS active刷新数据。窗口1792047600/168小时，10-15 07至10-22 07UTC，203有效跳过下载/注入。
- Power1/State−1/原因2/bearer0；GPS0/Signalsfalse/rate30，桌面定位恢复false、测试资源移除；三个DSP running、SensorProxy三Has true；CAMSS四域绑定/无临时camera资源。
- 200四轮12帧IMX471 RAW10/自身MMCX384→0、扫描10设备属于历史；203无新增帧/扫描，正常boot仍空sensor图。USB大SCP停顿，残缺候选保留不用；Wi-Fi取得完整文件，最终USB/Wi-Fi小命令响应，无reset/unbind/reboot，未证明大传输稳定。

[安装](reference/kernel203/package-install-validation.json)、[会话](reference/kernel203/geoclue-package-validation.json)、[健康](reference/kernel203/native-health-validation.json)。历史逐字快照：[202](archive/NEXT-SESSION-through202-2026-10-15.md)、[200相机完整索引](archive/NEXT-SESSION-through200-2026-10-15.md)，相对链接按根解释。

## 源码、产物与回退依据

- 内核WSL /home/cy122/pmos-samurai-kernel136/kernel，200源保持，25 tracked/11 untracked未暂存；Image bfa72dd9…、canonicalDTB22c1f2ad…/config55f1f0a3…、符号16793/顺序770保持。[收据](reference/kernel203/source-final-validation.json)
- 规范源linux-port/packages；source-lock固定上游与190/191补丁，原SDK clean rebuild逐字匹配191；官方APK签名核对，另133文件保持，五APK及签名索引双构建相同/篡改拒绝。仅用Linux文件系统构建。[包说明](linux-port/packages/README.md)
- 手机仓库/var/lib/samurai/packages/gnss-203，配置/etc/apk/repositories.d/50-samurai-gnss.list；仅公开验签key在手机。私钥仅主机/home/cy122/x2pro-linux/samurai-packages203/signing-private，勿复制或重生成；主机产物kernel203/packages-2及3。离线rootfs132未更新，未来升级须保持补丁与配套依赖；Mesa仍可能被官方包覆盖。
- MM未重启，/proc/PID/exe现为(deleted)inode但内容仍b350。下一次quiesce校验内容SHA，旧189/202路径字符串检查会误拒绝。PID/owner手机k203-package-preflight/processes-private.json。
- 当前身份手机/var/lib/samurai/k203-baseline/boot-id-private.txt，与202r2相同；reference/kernel203/host.py严格原key Wi-Fi，host-usb-before-recovery.py为同boot USB；kernel202主host已旧。当前Phosh bus在k203-baseline/desktop-env-private.json，勿猜/run/user/10000/bus。
- helper核心37/6watch/6退避既有检查通过；首次请求抢先/SSR/活跃worker停机未原生验收，非零过期窗口未造出，201旧注入Core.Aborted及202前两次下载失败原因未记录保留。普通reboot不等于断电冷启；203未查实际DMS模式，201 Power3不沿用。
- boot200 kernel200/boot-partition-k200-mmcx.img，5109097b…/100663296字节，与82cbc052 CAMSS成对。回退boot172 77e1a272…在kernel200/boot-rollback-k172-private.img，旧CAMSS e9b73f4c…手机k200-baseline/k200-deploy及归档；fresh身份后成对恢复，保留logdump183 e73754c7…/persist/NV。
- 相机sensor-only overlay5109da88…/MCLK sleep下拉，FW固定samurai/k196-front.dtbo；VIO允许RPMH初始unknown。200 GPIO12/15/29 CTL1/1/1，0390c000/0390f000/0351d000；旧boot15=0不沿用，临时phandle301已移除。PM8008 P0/Q1、Q4/5与8无响应仅warm证据，仅S8C输入已证；四PLDO输入未知，勿套Hotdog PM8009/BOB/master0。详见200快照。
- 203手机226文件私有归档/逐成员校验通过，原始NMEA/端点/身份/归档指纹仅E:/edk2-samurai-out/kernel203；200 RAW/历史备份保持。[收据](reference/kernel203/archive-validation.json)

## 续作与已知风险

1. [realme/一加/OPPO对照](reference/kernel203/RELATED-DEVICES.md)：X3固定91911e…/6.12rc7声明BT工作，同UART13/WCN3990/3.2Mbps，额外sleep/GPIO46 RX wake；先查本机GENI PM/IBS与189phase5证据，不把差异当根因或复制01固件/NVM。
2. GNSS真实fix/CNR/RF/LNA/接收条件/电源/精度长稳开放；Hotdog GPS也Partial。OEM19781仅通用GNSS UART注释，勿杜撰LNA电源。可只读查PDC/MCFG和原厂时序，勿停当前MM或激活外机配置。
3. 相机常态资源/用户态、PLDO输入/双PMIC真cold、其它镜头模式/曝光色彩方向/持续帧率；helper/MM已APK化，新完整rootfs和其它补丁软件包仍待整合。
4. 蜂窝真实注册/数据/通话/SMS、BT后段重组、Wi-Fi/USB PM、FastRPC普通信号/freezer/共享池−22/SSR、传感器物理精度长稳继续。SIM-missing/no-atr不证明物理无卡；用户无耳机勿再问，BT只扫描，振动不新增脉冲。[硬件清单](linux-port/docs/HARDWARE-STATUS.md)

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(text.encode())<=6500,len(text.encode())
target=repo/'NEXT-SESSION.md';(out/'checkpoint203-first-draft-private.md').write_bytes(target.read_bytes());target.write_text(text,encoding='utf-8')
# Preserve the original one-shot writer's final template with the same byte limit.
writer=here/'write-checkpoint.py';source=writer.read_text();start=source.index("text='''");end=source.index("'''\nassert len(text)",start)
source=source[:start]+"text='''"+text+source[end:]
source=source.replace('assert len(text)<=6500,len(text)','assert len(text.encode())<=6500,len(text.encode())');writer.write_text(source)
print('Checkpoint bytes:',len(text.encode()))
