from pathlib import Path
import json

ref=Path(__file__).resolve().parent;root=ref.parent.parent
readme='''# 阶段200：静态MMCX设备树与CAMSS成对启动，前摄跨启动取流

静态四电源域设备树和CAMSS运行时MMCX修复已成对部署到真机。新启动kernel183上，两次实体前摄会话共四轮、12帧1928×1088 RAW10；自身MMCX请求活动384、暂停0，原频率表保持，无外部性能helper。803.82秒最终检查taint0，WARNING/Oops/GPU/SLPI fatal/蓝牙重组均0。完整外设goal继续；摄像头尚未成为正常启动即用的完整用户态功能。

## 成对部署与回退

UEFI把板级DT嵌在boot内，Linux Image仍从logdump183加载。基于准确boot172构建，固件模块仅DTB改变，908节点中只有CAMSS的power-domains与power-domain-names两属性改变；其余固件代码、shim、ramdisk、Android头、compat DTB、分区尾部保持。构建诊断仍为原有30条、无新模板。[构建比对](build-package-validation.json)

- 新boot：5109097b…，100663296字节；内嵌静态DTB2e2f8e64…，108410字节。
- 安装CAMSS：82cbc052…；新启动ELF build-id与安装文件逐字匹配。hci_uart185/fastrpc189也核对loaded build-id，784个模块树文件保持准确预期。
- logdump183 e73754c7…、Image183 bfa72dd9…保持；persist/NV核对保持，没有写这些分区。
- 回退boot172 77e1a272…已另存主机kernel200/boot-rollback-k172-private.img；旧CAMSS e9b73f4c…在手机k200-baseline与k200-deploy中、主机完整私人归档中。实际回退须重新核对设备身份，将旧boot与旧模块配套恢复，保留logdump183。

旧启动已有193内核WARN1与199 OF属性警告2，taint512均据实保留于归档；新启动没有这些事件。只提交一次Linux RESTART2与一次fastboot reboot。[刷写](flash-validation.json)、[新启动读回](runtime-validation.json)、[最终健康](native-health-validation.json)

停机第一版保留Wi-Fi/NetworkManager时，MM被D-Bus重新拉起，两次检查退出且未发重启。改为切断管理网络后，在已归档的独立进程中停MM、Wi-Fi、所有remoteproc、显示/音频，核对、冻结文件系统，再单次RESTART2。重启后的完整停机收据已回读验证。首次fastboot调用使用WSL路径，Windows工具本地打开文件失败、尚未发送数据；保留该失败，改Windows路径并重新核验fastboot身份/geometry后，成功传输与写入一次。没有对未知切换盲目重复。[部署准备](pre-transition-validation.json)

## 新启动的VIO状态与实体前摄

RPMH regulator驱动把enabled初始化为-EINVAL，在首次正常enable之前公开state unknown；这不是已证明关闭的电源。195开发VIO helper的“必须disabled”条件因此拒绝，本次r1准备完整撤销。200 helper仍只做OF精确引用和只读查询，限定PM8150L RPMH父节点，允许0或该provider的初始-EINVAL，拒绝enabled及其它错误。模块加载前后VIO均unknown/1.8V/users0，没有电源写入；标准sensor首轮使用后变为已知disabled。[源码](samurai-vio-phandle.c)、[构建](vio-helper-build-validation.json)

该helper仅用于开发，不替换安装模块；新源5b7aad11…、模块5325464e…，已卸载。W=1、checkpatch及导入符号核对通过，Image/config/canonical DTB/符号表/模块顺序保持，原14个其它修改源及199 CAMSS/DTS/binding保持。[源码收据](source-final-validation.json)

静态四域已存在，不再热替换CAMSS域属性。sensor-only overlay通过新启动重读的phandle编译；普通IMX471在CCI1 master1地址0x10绑定，pattern0的真实媒体链路采集，CAMSS只unbind/rebind刷新notifier，没有替换或卸载其永久模块。四轮均3帧，序号/时间戳递增、>99.9% DMA覆盖变化，活动VFE约847MHz/CSID600MHz，自己的MMCX384，暂停0。四张私人RAW10已解码，行/像素变化且各图不同。[原生验证](front-native-validation.json)

第一会话6帧及资源撤销通过，但GPIO15 CTL从新boot原始1变0，末尾精确恢复断言失败。原sleep bias-disable清掉了初始下拉。标准GPIOv2 bias请求被接受但硬件无变化；该MSM GPIO chip未挂set_config。确认MCLK关闭、GPIO15无owner且input低后，对north CTL0x0390f000的pull掩码3做一次0→1原值恢复，读回/电平检查通过。保留失败摘要与单独恢复记录。

随后只把MCLK sleep状态改为bias-pull-down。第二会话又完成两轮共6帧，全部三个CTL与原值1/1/1、低电平、七Q LDO采样和P0/Q1精确恢复，未需额外寄存器恢复。VDIG/VANA退出恢复关闭状态原VSET，VIO最终disabled/1.8V/users0，S8C1.352V/users3保持。[最终overlay](front-probe-overlay.dtso)、[构建](overlay-build-validation.json)

## 外设回归与开放项

新boot早期74秒SLPI尚offline，随后按既有启动门控运行；最终ADSP/SLPI/modem均running，三项SensorProxy Has true，标准加速度/亮度/接近Claim/Release通过。蓝牙只扫描8秒，发现10个设备，结束停止扫描、恢复原Powered，新增重组/内核故障0。没有配对、连接或振动动作。Wi-Fi启动后connected，早期旧端点两次超时不是最终关联失败。新boot通过新发现USB peer与原严格SSH公钥管理，约6MB归档完整传输并核对；不能将这一个启动窗口称作NCM长期缺陷已修复。[外设回归](peripheral-regression-validation.json)

MM191文件保持，新boot仍可发现XTRA/3服务器、location capabilities103，GPS关闭。MM State−1/PowerState1，旧191的DMS online状态未跨本次重启保持；没有再次盲目online或reset。真实SIM注册/数据/通话/SMS及GNSS fix仍未验收，新boot轨道有效期尚未查询。

168份原生证据逐成员核对，包含四张实体RAW；原图、统计、相关指纹和网络/设备身份均只存E:/edk2-samurai-out/kernel200。[归档收据](evidence-export-validation.json)

下一步继续常规板级相机资源/持久化用户态接入，核对四路PLDO实际输入与双PMIC冷启动，或推进新boot的GNSS-only GeoClue/辅助加载与modem电源策略。其它镜头/模式、曝光色彩方向、完整冷启与长稳、BT phase5历史重组、Wi-Fi/USB PM、FastRPC普通信号/共享池/SSR等仍开放。详见[检查点](../../NEXT-SESSION.md)与[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
'''
(ref/'README.md').write_text(readme)
checkpoint='''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段200，完整外设goal active。静态MMCX四域DT与CAMSS模块已成对启动；新boot四轮前摄12帧RAW10，原频率/自身384→0通过。803.82秒taint0、所列fault全0。见[边界](WORKING-BOUNDARIES.md)、[200报告](reference/kernel200/README.md)。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 已部署 | boot200内嵌DT2e2f8e64…/CAMSS82cbc052…；仍Image183/logdump183、modules132覆盖hci_uart185/fastrpc189、Mesa149/UCM173/MM191 |
| 相机 | 新启动四轮IMX4711928×1088 RAW10共12帧，pattern0/无外部性能helper/频率表保持；VFE约847/CSID600MHz，自己MMCX active384/idle0 |
| 最终现场 | 新200 boot/kernel#183；803.82秒taint0，WARNING/Oops/GPU/SLPI fatal/BT重组均0；ADSP/SLPI/modem running，SensorProxy三Has true，三项Claim/Release通过 |
| 无临时相机 | fixtures/CCI/sensor/PMIC/临时VIO phandle及FW撤销，永久CAMSS绑定四域；GPIO12/15/29 CTL1/1/1、input低，P0/Q1与七Q LDO采样恢复 |
| 无线 | BT仅扫描8秒，10设备、停止/原Powered恢复，fault增量0；Wi-Fi connected。新USB peer/严格原公钥SSH/SCP与归档通过，稳定性未完 |
| MM | 文件b350c55b…保持，State−1/PowerState1/GPS0；XTRA/3服务器/capabilities103。191旧online未跨重启保持，新轨道有效期未核 |

依据：[读回](reference/kernel200/runtime-validation.json)、[相机](reference/kernel200/front-native-validation.json)、[健康](reference/kernel200/native-health-validation.json)、[外设](reference/kernel200/peripheral-regression-validation.json)。旧199状态逐字保留于[快照](archive/NEXT-SESSION-through199-2026-10-15.md)，相对链接按根解释。

## 源码、产物与回退依据

- WSL源码/home/cy122/pmos-samurai-kernel136/kernel；25 tracked改动/11 untracked、未暂存。原14其它源、IMX471/MFD/199 CAMSS/DTS/binding保持；仅开发VIO helper更新。[收据](reference/kernel200/source-final-validation.json)
- boot200主机kernel200/boot-partition-k200-mmcx.img，5109097b…/100663296字节；DTB在kernel199/sm8150-samurai-mmcx-static-private.dtb，2e2f8e64…/108410字节。只CAMSS两域属性改变，其余908节点/固件代码保持。[构建](reference/kernel200/build-package-validation.json)
- CAMSS源CPAS3ee20b59…/core53d8a710…，安装模块82cbc052…，新boot loaded build-id已核；四域ife0/ife1/top/mmcx。runtime前384，暂停0，失败保留请求/恢复ICC；频率表未改、未细分模式。17实际C/ASan/UBSan/缺请求变体及W1/schema/三补丁验证见199。
- 回退boot172 77e1a272…另存在主机kernel200/boot-rollback-k172-private.img；旧模块e9b73f4c…在手机k200-baseline及k200-deploy/原生私人归档。回退须fresh身份及旧boot/旧模块配套，保留logdump183 e73754c7…；persist/NV未改。
- Image183 bfa72dd9…、canonical DTB22c1f2ad…、config55f1f0a3…保持，Module.symvers16793行/modules.order770恢复。只刷boot；Linux RESTART2/fastboot reboot各一次。首次Windows fastboot因WSL路径本地开文件失败未传输，改路径且重核身份后成功写一次；旧失败保留。
- IMX471源110977b8…/模块c49dca63…，CCI库f9c9272a…，MFD195 d1ff82c0…，OF helper92d9176e…固定FW samurai/k196-front.dtbo。新sensor-only overlay5109da88…/3082字节，MCLK sleep改pull-down；不更新既有MMCX属性。
- VIO helper源5b7aad11…/模块5325464e…，仅开发已卸载。限定PM8150L RPMH父节点，允许初始unknown=−EINVAL；只读精确查找前后unknown/1.8V/users0保持。正常sensor首用后disabled；拒绝其它错误/enabled。W1/checkpatch/导入通过。[构建](reference/kernel200/vio-helper-build-validation.json)
- 第一相机会话6帧后GPIO15 CTL1→0，原sleep bias-disable造成；GPIOv2 bias请求硬件未生效，确认无owner/MCLK关后单次masked CTL恢复1。第二会话修改sleep pull-down后另6帧，三脚/PMIC完整恢复，无额外修补。两会话记录均保留。
- 正确GPIO12/15/29 CTL为0x0390c000/0x0390f000/0x0351d000，新boot初值全1（旧boot GPIO15为0）。当前phandles TLMM56/CAMCC201/PM8150L_GPIO240/S8C251/RPMH124/SM8150_MMCX9；临时VIO301已撤销，下次重读。
- P reset0/Q reset1、Q在4/5、8不响应，Q ID[0,0,0,1,0x51,0x2c]；本次重启仍warm，未证明硬断电cold。只有NLDO输入S8C已证，PLDO四输入未知；不套hotdog PM8009/BOB/弹出机构。195冷迁移/失败回退37C场景仍保留。
- FastRPC88553112…/hci_uart f6c5ed35…实际loaded build-id均核。SSC A.11/daemon1902…/184门控保持；MM正式APK化未做、更新会覆盖。用户暂无耳机。
- 新boot身份手机k200-runtime/boot-id-private.txt、主机kernel200/new-boot-id-private.txt。host200已转新发现USB IPv6 peer/原HostKeyAlias公钥；Wi-Fi旧实现host-before-newboot.py，私人端点kernel190文件保留。别用旧189/199 boot guard切换。
- 168原生文件、4张RAW/解码统计/媒体与归档指纹只私人保存E:/edk2-samurai-out/kernel200，全成员验证通过。[收据](reference/kernel200/evidence-export-validation.json)

## 续作与已知风险

1. 相机仍用开发VIO/CCI/sensor/PMIC overlay接入，当前已全部撤销，正常启动空sensor图。下一步板级持久化/用户态、PLDO输入/双PMICcold、其它镜头/模式/曝光色彩方向/持续帧率/长稳；不把12帧当完整相机完成。
2. GNSS191旧boot 303NMEA/online后90秒仍无fix/CNR；200重启MM电源回1但辅助能力1/服务器3保持。继续核轨道有效期、GNSS-only GeoClue/辅助自动加载及合适电源策略，不盲目DMS reset/online。两UIM no-atr/absent不证明物理无SIM，业务均待验。
3. BT phase5历史重组1、Wi-Fi第二PM35秒未关联、190 USB双向IPv6失效均保留；本次新boot短窗未复现不等于根因修好。只扫描、不配对连接。FastRPC普通信号/freezer/共享池−22/SSR、传感器运动亮暗精度、冷启长稳开放。
4. 旧193内核WARN+199热属性OF警告共3/taint512只属于旧boot，新静态DT不替换该属性且本boot0；不要抑制旧记录。core AHB hw0也见于成功帧，不当单独根因。其它见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(checkpoint.encode())<=6500,len(checkpoint.encode())
(root/'NEXT-SESSION.md').write_text(checkpoint)
(root/'sessions/200-static-mmcx-boot-and-front-camera-regression.md').write_text('''# 200：静态MMCX成对启动与前摄跨启动回归

静态四域DT与CAMSS已成对部署，新boot四轮12帧真实RAW10、运行时384→0通过，最终taint0且所列内核/蓝牙fault全0。第一会话MCLK下拉恢复失败、单独原值恢复，以及第二会话sleep pull-down修复后的完整恢复均保留。蓝牙8秒只扫描、三项传感器Claim/Release与USB归档通过；完整外设goal继续。

详细源码/失败/回退/验收边界见[阶段200报告](../reference/kernel200/README.md)，当前组合见[检查点](../NEXT-SESSION.md)，未完成项目见[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。
''')
status=root/'linux-port/docs/HARDWARE-STATUS.md';s=status.read_text()
a=s.index('用途：');b=s.index('\n\n',a)
s=s[:a]+'用途：当前硬件验收清单。最后核对：2026-10-15，阶段200。静态MMCX四域DT/配套CAMSS已启动部署，新boot四轮IMX471 RAW10共12帧、活动384/暂停0通过，频率表保持、无外部helper；803.82秒taint0，WARNING/Oops/GPU/SLPI fatal/BT重组0。第一会话MCLK下拉恢复失败已单独恢复，sleep pull-down修复后第二会话完整撤销通过。完整goal active。[200报告](../../reference/kernel200/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+s[b:]
lines=s.splitlines()
for i,l in enumerate(lines):
 if l.startswith('| 摄像头 |'):lines[i]='| 摄像头 | 200静态MMCX四域DT/配套CAMSS成对启动，新boot四轮IMX471 RAW10共12帧，VFE约847/CSID600MHz、自身384→0；无外部helper/限频，最终三脚/PMIC恢复、taint0/告警0；MCLK sleep下拉修复通过 | sensor/PMIC/CCI仍为开发overlay接入，正常启动尚无实体camera图；四路PLDO输入/双PMICcold/其它模式镜头/曝光色彩方向/用户态/持续帧率与长稳待验；第一清理失败与单次原值恢复保留 |'
 if l.startswith('| 其它传感器 |'):lines[i]=l.replace('187 A.11实际', '200新boot三项Has与标准Claim/Release通过，早期门控后SLPI running；187 A.11实际')
 if l.startswith('| 蜂窝通话与数据 |'):lines[i]=l.replace('本轮modem running','200新boot modem running、MM仍failed').replace('DMS已online，但两卡位仍no-atr/slot absent','191旧boot曾DMS online，200重启PowerState回1；两卡位历史仍no-atr/slot absent')
 if l.startswith('| GNSS定位 |'):lines[i]=l.replace('190能力发现', '200重启XTRA/3服务器能力保持；190能力发现').replace('仍无有效GGA','新boot轨道有效期与电源策略待核；此前仍无有效GGA')
 if l.startswith('| 蓝牙 |'):lines[i]=l.replace('185功率脉冲', '200新boot startup及8秒只扫描发现10设备、退出恢复、重组增量0；185功率脉冲').replace('189当前boot出现新phase5','189旧boot出现phase5')
 if l.startswith('| Wi-Fi |'):lines[i]=l.replace('2.4/5GHz通信','200新boot自动connected，早期管理端点超时保留；2.4/5GHz通信')
 if l.startswith('| 普通USB与OTG |'):lines[i]=l.replace('USB 2.0 Type-C；', '200新boot新peer/原严格公钥SSH/SCP、约6MB归档及逐成员核对通过；USB 2.0 Type-C；')
s='\n'.join(lines)+'\n'
s=s.replace('静态四域DT/配套模块尚未部署启动','静态四域DT/配套模块已部署启动')
status.write_text(s)
print(json.dumps(dict(stage=200,next_session_bytes=len(checkpoint.encode()),readme_written=True,status_and_session_updated=True)))
