"""Update current navigation while retaining deployed273 and candidate274 separately."""
from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[2]
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:
 p=R/'archive'/(Path(name).stem+'-before274-2026-10-18'+Path(name).suffix)
 assert not p.exists();shutil.copy2(R/name,p)
text='''# Realme X2 Pro 当前检查点

2026-10-18：[274 镜头光学响应与底层候选](reference/kernel274/README.md)。当前目标继续多个摄像头及骁龙 ISP，按 SoC/板级/驱动/用户空间收敛，保持 active。三后摄＋前摄已有取流；AF、画质、四摄 GUI/录像和 Spectra 尚未完成。

## 当前部署与启动身份

手机仍 boot273/Image183，`7.3.0-rc6-rmx1931-samurai-k132+`，775模块/961包；本轮未刷写、重启或安装产品模块/包。boot SHA `dd4c34e4f18a4292cb70dd9b3d87ad710ce4f6e4e4048fe85c7b94eee911d475`，DTB `615f7523df579313f514d0dfa809fcde96355a419ad24dbb62b1eaa60955d252`。GW1模块0c907b12、S5K3M5模块11791431及既有774模块保持。

libcamera五组件r21/config-r16，PW/SPA/Gst 1.6.9-r3；CPU ISP/system heap、Snapshot Cairo/禁用GL/Vulkan/offload回退保持。默认GPU及旧modem watchdog未修。运输使用 `reference/kernel274/host.py`（复用273严格原SSH密钥与当前USB接口），guard `/var/lib/samurai/k273-work/boot-id-private.txt`；旧270/271/272 guard不适用。服务身份见[最终核对](reference/kernel274/final-health-validation.json)及手机`/var/lib/samurai/k273-services-current-private.json`，续作重核。

## 本轮已经验证

- 273主摄C-PHY RAW/RGB、600帧实景JPEG及四摄18段238帧交替通过。画面仍有虚焦及颜色/噪声问题。[273](reference/kernel273/README.md)
- 274相同八阶段/96组RAW+RGB、全像素统计与原严格阈值：直接线程与独立工作线程均通过、0不匹配。273的66组失败没有稳定复现，未将推测写入IPA或宣称根因修复。[直接](reference/kernel274/main-manual-direct-r1-validation.json)、[工作线程](reference/kernel274/main-manual-worker-r1-validation.json)
- 两种原厂GW1 actuator数据经直接解码与独立XML交叉核对。0x72应答；原厂位置命令208…880及返回208产生明确失焦变化，离线边缘扩散代理约8→46.5→8.71px。自动曝光未锁定，无可读chip-ID/位置反馈；不是自动对焦或距离标定验收。[光学证据](reference/kernel274/focus-optical-analysis.json)
- 标准LC898219XI lens候选：V4L2 focus控制、regulator/runtime PM及静态lens-focus；板级VAF唯一消费者改为lens。W=1对象0诊断，DTB及三组schema通过，13个实际回调主机故障用例/UBSan通过。**未部署**，新供电归属未实机验证。[源码与测试](reference/kernel274/README.md)
- 最终四sensor/双CCI/CAMSS suspended，九rails OFF/users0、四MCLK关闭，无相机客户端，fault0/taint0/pstore空；49载荷、775模块/961包及原桌面/PW/WP身份重核。SSC仍失败、自动旋转不可用，桌面仍是273临时nodeps恢复。

## 源码、回退与下一步

维护树 `/home/cy122/x2pro-linux/camera270-kernel` 当前候选分支`samurai-main-focus274`，干净提交`0798ee688921b987a67c045afeab093f9b0c274d`，未推送。原`samurai-main-camera272`/3184c56保留且仍是现机相机源码来源；[部署锁](linux-port/camera/deployment-lock.json)和[已部署源码锁](linux-port/camera/kernel/source-lock.json)仍273，未冒充部署新候选。269统一Image/773模块未上机，完整最新rootfs待重建。

下一步先修Simple管线的lens生命周期：现CameraLens::init持有subdev，直接部署标准open/close PM会令常驻枚举长期上电。随后构建Image183匹配模块/用户态配套并受控部署，验证枚举不常驻供电、取流/停止/并用/异常退出和四摄回归，再做AF映射与算法、校准/画质/GUI/录像。候选0…1023是接口码范围，仅208…880有本轮部分光学证据。r1错误要求0xe0回显已保留；r2/r3不编造握手，记录命令应答和真实图像。

ISP源码已定位VFE170的RAW writer与原厂FULL/DS4/DS16/统计输出。当前pix格式表仍是RAW占位，成像继续CPU ISP；**Spectra硬件成像未接通**。按[ISP分层](reference/kernel274/ISP-ADAPTATION.md)继续公共内核/UAPI、pipeline/IPA与调校，不能靠DTS或GPU软件处理替代。

SSC默认启动attach返回Operation not permitted/exit4，SLPI停、sensor-power OFF；保留state/log，不盲目清记录重放共享池停启。匹配回退手机/PC双份26116631字节，SHA `209908a882a9508b49adc6b7eed3cf1f4fc726ae0a8d4da4b745a32217aabeac`，含boot270/r20/r15及原配置，未实际往返。私人资料`E:/edk2-samurai-out/kernel274`，所有本轮采集终态。规则见[边界](WORKING-BOUNDARIES.md)，其它硬件见[清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(text.encode())<=6500,len(text.encode());(R/'NEXT-SESSION.md').write_text(text,encoding='utf-8')
(R/'NEXT-SESSION-PROMPT.md').write_text('''接手 Realme X2 Pro Linux 适配。先读 NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel274/README.md 和硬件清单。

继续完整 active 目标：多个摄像头及骁龙 ISP，区分 SoC、板级、公共驱动与用户空间，向底层收敛。手机仍 boot273/Image183、775模块/961包、libcamera r21/config-r16/PW r3；274候选未部署。当前 SSC 启动失败、旋转不可用，桌面是临时恢复，不能引用旧启动通过覆盖现状。

当前维护树候选分支 samurai-main-focus274 / 0798ee688，原部署来源 samurai-main-camera272 / 3184c56 保留。274有主摄镜头真实光学响应和标准V4L2 lens候选及主机/编译验证，尚无实际驱动供电/AF验收。优先处理 CameraLens::init 的常驻open与Simple start/stop生命周期，再进行配套构建和受控部署；同步继续VFE170公共PIX/统计/用户态IPA实现，Spectra仍未接通。读取当前身份后才操作手机，不重放已终态采集。完成后更新证据与检查点，不缩减完整目标。
''',encoding='utf-8')
lead='274：主摄原厂镜头命令已产生真实光学响应；标准V4L2 lens/静态DT/独占VAF候选0798ee688已编译并通过13个回调主机用例，尚未部署，须先配套Simple lens生命周期。相同96组控制两轮通过但旧失败根因未明；现机仍273/r21，SSC失败及Spectra未接通保持。[274证据与分层](%sreference/kernel274/README.md)。以下按各历史阶段阅读。\n\n'
for name,prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
 p=R/name;p.write_text(lead%prefix+p.read_text(encoding='utf-8'),encoding='utf-8')
p=R/'DOCS-INDEX.md';t=p.read_text(encoding='utf-8');old='| Camera应用、实体前后摄与内部TPG | ';assert old in t;t=t.replace(old,old+'[274镜头光学响应/标准候选及ISP分层](reference/kernel274/README.md)、[273主摄实机](reference/kernel273/README.md)、',1);p.write_text(t,encoding='utf-8')
print('Updated current checkpoint and navigation; NEXT bytes:',len(text.encode()))
