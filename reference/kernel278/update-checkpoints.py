"""Write the actual single-AF checkpoint without shrinking the full camera/ISP goal."""
from pathlib import Path
W=Path(__file__).resolve().parents[2]
(W/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-18：[278标准单次AF/帧统计与镜头回执](reference/kernel278/README.md)、[277 RAW统计](reference/kernel277/README.md)、[276镜头/CCI](reference/kernel276/README.md)。完整多摄及骁龙ISP目标active，按SoC/板级/公共驱动/用户空间收敛。GW1单次AF已实机通过；连续/距离标定、画质、GUI/录像、Spectra仍未完成。

## 当前部署与启动身份

仍boot276/Image183、`7.3.0-rc6-rmx1931-samurai-k132+`，776模块/961包；libcamera五组件r24/config-r19，PW/SPA/Gst1.6.9-r3。278只更新七包，未刷写/重启/替换或卸载驱动/改DT/停DSP。boot SHA `0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64`，DTB `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`。[部署锁](linux-port/camera/deployment-lock.json)

运输用`reference/kernel278/host.py`，仍核`/var/lib/samurai/k276-work/boot-id-private.txt`，严格原SSH密钥/276USB端点；没有k278启动guard。按实体名找设备，编号会变。Phoc3586/Phosh3803保持，PW13112/WP13115正常重启加载r24，身份见手机`/var/lib/samurai/k278-services-verified-private.json`和[最终健康](reference/kernel278/final-health-validation.json)，续作重核。

## 实际验证与边界

- 276标准lens独占VAF/lens-focus、公共CCI共享I/O PM保持。CameraManager常驻枚举释放lens fd，所有sensor休眠时lens可独立打开；本阶段没有新增内核硬件ISP功能。
- 278通用libcamera将FocusFoM随frame按值穿过工作线程/IPA，不重读可变共享focus；每buffer明确V4L2单调时钟标志。标准lens控制有串号、结果与完成时间回执，按稳定时间＋曝光/读出预算排除旧帧；停流拒绝晚到动作。其它IPA共享统计未全面重构。
- 标准AfModeAuto、AfTriggerStart/Cancel与AfState已部署，Auto默认等触发，未声明Continuous或伪造LensPosition距离。行程208…926及搜索参数仅在设备数据包s5kgw1.yaml，匹配lc898219xi并校验driver0…1023；不是EEPROM/距离标定。
- 生产引擎Werror/ASan/UBSan覆盖粗细扫/复验、重复触发、取消/旧回执、Focused/Failed时取消忽略、错误/早帧/低纹理/超时/配置及时钟边界。r1编译const接口错误已终止/恢复，r2构建通过但未部署；r3补正确取消语义、两文件增量打包，完整补丁从r23独立重现。[源与失败](reference/kernel278/README.md)
- 原生公共API五场景共890组同request RAW/RGB：无触发48帧零AF命令；搜索293帧Focused选256/FoM4355；取消72帧回Idle；取消后重触发441帧Focused选272/FoM4121；扫描中停流36帧正常回收。扫描中重复Start忽略，Focused后Cancel保持；所有预期每4帧FoM均与同request RAW重算一致。[五场景](reference/kernel278/native-af-r1-validation.json)
- 自动曝光/增益AF另389组通过，曝光33215us、增益1…4.71875，Focused选320/FoM12297。配对测量扫描约9.05秒、AE下12.24秒，需加速；跨增益FoM不能直接比较画质。[AE AF](reference/kernel278/ae-af-r1-validation.json)
- 保持320后普通原生预览无新AF命令，私人JPEG场景/窗帘可辨，边缘代理8.75px，噪声/颜色/整体偏软仍在；与AF请求不同会话，不是完整画质标定。[样片边界](reference/kernel278/af-selected-preview-optical-analysis.json)
- 完整13签名包/全部功能/34 ELF/五IPA签名/ARM工具QtPython QA通过；原214工作区2254项恢复，r23缓存2276项及r2缓存2278项保留。七包原生事务/精确降级模拟通过，50载荷/全部776模块保持核验，十模块加载note匹配。
- 四摄18段232帧/SIGINT正常退出28帧/重开通过，无强杀或回归期服务重启。最终四sensor/lens/双CCI/CAMSS suspended，九rails/共享I/O OFF/users0，四MCLK/双CCI clocks0，fault0/taint0/pstore空、CCI无错误。[最终健康](reference/kernel278/final-health-validation.json)
- SSC/SensorProxy/greetd正常、三DSP运行，物理旋转未重测；旧273 EPERM根因、GPU默认故障/Cairo CPU回退、旧modem watchdog开放。273严格手动矩阵失败与274两次通过均保留，r24完整矩阵/GUI/录像未验收；其它镜头AF和第四枚物理后摄待接入/确认。

## 源码回退与下一步

内核维护树`/home/cy122/x2pro-linux/camera270-kernel`仍`samurai-cci-io276`/`0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，未推送，父0798ee688及原3184c56保留。r24/r19真实配方/锁已提升，旧r23/277归档；0028为下游公共libcamera补丁，未上游接受。Image183未整体重编，269完整候选未部署，最新完整统一内核/rootfs待做。

278匹配r23/r18七包回退2533478字节，SHA `f90a2ba7695c1a0364e6b27e217c91f28c6022508b77243530d7167bab07f570`，手机/PC双份，未实际往返。277另有r22/r17回退fb587046（2529160字节）；276 boot275/旧CCI回退a12acbdf、275 boot273/r21/r16回退7fadb874保留。私人数据`E:/edk2-samurai-out/kernel278`，不公开像素/校准/密钥。全部构建、包事务与采集终态，不重放。

继续AF加速/更多场景、Continuous、手动距离标定及GUI标准控制接入，四摄录像和画质；同步推进VFE170公共硬件PIX/统计/参数接口及pipeline/IPA。当前仍CSIPHY/CSID/VFE RDI→RAW→CPU ISP，Spectra硬件成像未接通。[ISP边界](reference/kernel274/ISP-ADAPTATION.md)、[原厂依据](reference/kernel276/OEM-TUNING.md)。普通相机测试已授权，规则见[边界](WORKING-BOUNDARIES.md)，其它硬件见[清单](linux-port/docs/HARDWARE-STATUS.md)。
''')
(W/'NEXT-SESSION-PROMPT.md').write_text('''接手Realme X2 Pro Linux适配。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel278/README.md、277/276与硬件清单。

完整active目标继续：多个摄像头及骁龙ISP，按SoC/板级/公共驱动/用户空间收敛。现机仍boot276/Image183、776模块/961包；278七包升级libcamera r24/config-r19，PW/SPA/Gst r3。标准单次Auto AF、触发/取消/重触发/停流和自动曝光下AF已实机通过，应用不做搜索/镜头写；FocusFoM随帧按值传递，镜头串号回执与稳定/曝光/读出守卫已接通。四摄232帧回归通过。配对测量AF约9–12秒，连续AF、距离/画质标定、GUI录像及Spectra仍未完成。

运输reference/kernel278/host.py仍用276guard，服务身份k278-services-verified-private.json。内核分支samurai-cci-io276/0d692761未推送、统一最新内核/rootfs未部署。继续AF加速与更多场景/连续模式/距离标定、应用标准控制接入，并推进VFE170公共PIX/统计/IPA、四摄GUI录像与画质。物理旋转待重测，旧273 EPERM根因/GPU/modem watchdog开放。先核实际状态，不重放已终态工作；普通相机测试已有授权，不将完整目标缩成单次AF。
''')
banner='278当前：boot276/Image183保持，libcamera r24/config-r19已部署标准单次Auto AF和帧统计/镜头回执。原生触发/取消/重触发/停流及AE下AF通过，四摄232帧回归。配对测量AF约9–12秒需加速；连续AF/距离标定、画质、GUI录像、Spectra和完整统一构建仍未完成。'
for rel,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=W/rel;p.write_text(banner+'[278证据]('+prefix+'reference/kernel278/README.md)。以下按历史阶段阅读。\n\n'+p.read_text())
p=W/'HANDOVER-NEXT.md';s=p.read_text();old=next(x for x in s.splitlines() if x.startswith('按用户任务和'))
new='按用户任务和[检查点的续作项](NEXT-SESSION.md#源码回退与下一步)推进；标准单次AF与最新四摄回归见[278](reference/kernel278/README.md)，此前RAW统计见[277](reference/kernel277/README.md)，标准镜头/CCI见[276](reference/kernel276/README.md)。历史阶段的active和健康值不代表当前部署。音频任务读[音频提示词](AUDIO-NEXT-SESSION-PROMPT.txt)，完整导航见[DOCS-INDEX](DOCS-INDEX.md)。';p.write_text(s.replace(old,new))
p=W/'DOCS-INDEX.md';s=p.read_text();a='| Camera应用、实体前后摄与内部TPG | ';assert s.count(a)==1;p.write_text(s.replace(a,a+'[278标准AF/镜头回执](reference/kernel278/README.md)、',1))
assert (W/'NEXT-SESSION.md').stat().st_size<=6500 and (W/'DOCS-INDEX.md').stat().st_size<=10000
print('278 actual deployment checkpoint updated; NEXT bytes:',(W/'NEXT-SESSION.md').stat().st_size)
