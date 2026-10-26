"""Record the actual userspace277 deployment without inventing a new boot."""
from pathlib import Path
W=Path(__file__).resolve().parents[2]
(W/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-18：[277 RAW清晰度/标准FocusFoM部署](reference/kernel277/README.md)、[276公共CCI与标准镜头](reference/kernel276/README.md)。完整多摄及骁龙ISP目标active，按SoC/板级/公共驱动/用户空间收敛。三后摄＋前摄可取流；AF搜索/标定、画质、GUI/录像、Spectra仍未完成。

## 当前部署与启动身份

boot276/Image183、`7.3.0-rc6-rmx1931-samurai-k132+`，776模块/961包；libcamera五组件r23/config-r18，PW/SPA/Gst1.6.9-r3。277只更新七包，未刷写/重启/替换或卸载驱动。boot SHA `0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64`，DTB `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`。[部署锁](linux-port/camera/deployment-lock.json)

运输用`reference/kernel277/host.py`，仍核`/var/lib/samurai/k276-work/boot-id-private.txt`，严格原SSH密钥/276USB端点；没有k277启动guard。实体按名称查找，编号会变。服务见手机`/var/lib/samurai/k277-services-verified-private.json`及[最终健康](reference/kernel277/final-health-validation.json)：Phoc3586/Phosh3803保持，PW10140/WP10143正常重启后加载r23系统库。续作重核，不复用已终态采集。

## 已验证与边界

- 276标准LC898219XI/VAF唯一消费者、sensor lens-focus及公共CCI可选vddio已部署；SoC域原本正确，板级仅双CCI共享I/O。CameraManager常驻枚举不持lens fd，所有sensor休眠时lens可独立打开。13镜头/14CCI实际回调主机用例、schema与W=1通过。[276](reference/kernel276/README.md)
- 277通用软件ISP新增RAW绿色空间统计，4×3分区、平滑梯度、亮度归一化，有界320×240取样；标准FocusFoM仅在统计有效且frame匹配时报告，每4帧一次，无机型/应用分支。20组格式/绿色相位、CSI-2/非打包等价、边界与ASan/UBSan通过。[源码](reference/kernel277/focus_stats.h)
- 原r22独立helper和新r23两轮各96组同请求RAW/RGB，固定31999us/1倍增益，位置208/304/880/208。r23中位FoM3921/4204.5/684/3945；失焦下降并返回恢复。全部已报告元数据与同request RAW重算一致，稳定阶段12个报告样本。独立重算约10ms，不是整链时延/30fps验收。[元数据](reference/kernel277/focus-metadata-r1-validation.json)
- FoM硬件光学曲线只验证GW1；其它三摄取流已回归。镜头GET是缓存目标，无位置反馈/距离标定。没有AF搜索、AfMode/AfTrigger/AfState产品实现，不能以扫描探针代替AF。
- 完整13签名包正常abuild及功能/五IPA签名/ARM工具/Qt/Python QA通过；原214工作区2254项恢复、r22缓存2274项保持。原生七包更新及精确降级模拟通过，其余954包记录、全部776模块保持，49载荷与十模块加载note匹配。[最终健康](reference/kernel277/final-health-validation.json)
- r23前＋三后摄18段241帧交替、SIGINT正常退出37帧及重开通过，无强杀，回归期无服务重启。最终四sensor/lens/双CCI/CAMSS suspended，九rails/共享I/O OFF/users0，四MCLK/双CCI clocks0，fault0/taint0/pstore空、CCI无错误。[四摄](reference/kernel277/four-camera-regression-validation.json)
- SSC/SensorProxy/greetd正常、三DSP运行，三Has为true；物理旋转未重测，273 EPERM根因未证明修复。GPU默认故障/Cairo CPU回退、旧modem watchdog开放。273严格手动矩阵失败及274同矩阵两次通过均保留；r23完整矩阵/GUI/录像与新像素视觉复核仍待做，第四枚物理后摄未确认。

## 源码回退与下一步

内核维护树`/home/cy122/x2pro-linux/camera270-kernel`仍干净`samurai-cci-io276`/`0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，未推送；父0798ee688及原3184c56保留。实际r23/r18配方/锁已提升，旧r22/276归档；0027是下游公共软件ISP补丁，未上游接受。Image183未整体重编，269完整候选未部署，最新完整统一内核/rootfs待做。

277七包匹配回退2529160字节，SHA `fb587046bc48d22fc9e23b3ddd1cb0a1a0a802ec53f0250c9564191b8beab039`，含实际旧r22/r17签名包及配置/数据库/服务备份，手机PC双份，未实际往返。276另有boot275/旧CCI回退a12acbdf（24228955字节），275另有boot273/r21/r16回退7fadb874（26120859字节）。私人资料`E:/edk2-samurai-out/kernel277`，不公开像素/校准/密钥。

继续libcamera标准AF控制/搜索与模组标定，处理移动稳定、陈旧帧、低纹理失败、取消/连续模式；再做完整矩阵、四摄GUI/录像/画质、旋转。同步推进VFE170公共硬件PIX/统计、参数接口、pipeline/IPA；当前CSIPHY/CSID/VFE RDI→RAW→CPU ISP，Spectra硬件成像未接通。[ISP边界](reference/kernel274/ISP-ADAPTATION.md)、[原厂资料用途](reference/kernel276/OEM-TUNING.md)。普通相机测试已授权，规则见[边界](WORKING-BOUNDARIES.md)，其它硬件见[清单](linux-port/docs/HARDWARE-STATUS.md)。
''')
(W/'NEXT-SESSION-PROMPT.md').write_text('''接手Realme X2 Pro Linux适配。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel277/README.md、276及硬件清单。

完整active目标继续：多个摄像头及骁龙ISP，按SoC/板级/公共驱动/用户空间收敛。现机仍boot276/Image183、776模块/961包；277七包升级libcamera r23/config-r18，PW/SPA/Gst r3保持。标准镜头/共享CCI供电保持，新增公共RAW空间统计与标准FocusFoM，主摄真实失焦/返回及同request RAW重算与元数据一致已验证；四摄241帧回归通过。没有AF搜索/距离标定/GUI录像/Spectra完成记录。

运输reference/kernel277/host.py仍使用276guard。服务身份k277-services-verified-private.json，Phoc/Phosh保持，PW/WP已正常换新。内核分支samurai-cci-io276/0d692761保持未推送，统一最新内核/rootfs未部署。继续将统计接入标准AF控制与搜索，处理低纹理/稳定延迟/取消与模组标定；继续VFE170公共PIX/统计/IPA、GUI录像与画质。物理旋转待重测，旧273 EPERM根因、GPU和modem watchdog仍开放。先核实际状态，不重放已终态任务，普通相机测试已有授权；目标不可缩减为只有FoM或手动对焦。
''')
banner='277当前：boot276/Image183、776模块/961包，libcamera r23/config-r18。公共RAW空间统计及标准FocusFoM已部署；主摄固定曝光失焦/返回、同request RAW与元数据一致、四摄241帧回归通过。AF搜索/标定、画质、GUI/录像、Spectra与完整统一构建仍未完成。'
for rel,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=W/rel;p.write_text(banner+'[277证据]('+prefix+'reference/kernel277/README.md)。以下按历史阶段阅读。\n\n'+p.read_text())
p=W/'HANDOVER-NEXT.md';s=p.read_text();lines=s.splitlines();old=next(x for x in lines if x.startswith('按用户任务和'))
new='按用户任务和[检查点的续作项](NEXT-SESSION.md#源码回退与下一步)推进；现机RAW空间统计/FocusFoM与四摄回归见[277](reference/kernel277/README.md)，标准镜头/CCI供电见[276](reference/kernel276/README.md)，原厂资料见[调校分层](reference/kernel276/OEM-TUNING.md)。早期验证按对应阶段阅读，归档中的active和健康值不代表当前部署。音频任务读[音频提示词](AUDIO-NEXT-SESSION-PROMPT.txt)，完整导航见[DOCS-INDEX](DOCS-INDEX.md)。'
p.write_text(s.replace(old,new))
p=W/'DOCS-INDEX.md';s=p.read_text();lines=s.splitlines();old=next(x for x in lines if x.startswith('| Camera应用'))
new='| Camera应用、实体前后摄与内部TPG | [277 RAW统计/FocusFoM](reference/kernel277/README.md)、[276 CCI/对焦](reference/kernel276/README.md)、[原厂调校](reference/kernel276/OEM-TUNING.md)、[275生命周期](reference/kernel275/README.md)、[274光学/ISP](reference/kernel274/README.md)、[273主摄](reference/kernel273/README.md)、[271增益/AE](reference/kernel271/README.md)、[270分层](reference/kernel270/LAYERING-AUDIT.md)、[269统一候选/旋转](reference/kernel269/README.md)、[268跨框架](reference/kernel268/README.md)、[265公共缓冲修复](reference/kernel265/README.md)、[公共配方](linux-port/packages/pipewire-common/README.md)、[262前摄JPEG](reference/kernel262/README.md)、[240 CPU预览](reference/kernel240/README.md)、[239相关机型](reference/kernel239/RELATED-LINUX-SOLUTIONS.md)、[214完整包](reference/kernel214/README.md)、[126 DMA](sessions/126-tpg-dma-guards-full-rootfs-and-real-deployment.md)；其余历史见[会话索引](sessions/INDEX.md)。 |'
p.write_text(s.replace(old,new))
assert (W/'NEXT-SESSION.md').stat().st_size<=6500 and (W/'DOCS-INDEX.md').stat().st_size<=10000
print('Current277 entry points updated; NEXT bytes:',(W/'NEXT-SESSION.md').stat().st_size)
