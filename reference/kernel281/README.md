# 281：原厂 HAL 静态依据与 VFE175 CAMIF 候选

后续[282](../kernel282/README.md)在本轮CAMIF之上复用公共多流修复并加入175 FULL传输候选，未部署；完整构建r2已发起，硬件成像/统计/IPA仍待完成。本文281证据按本阶段保留。

2026-10-18。继续多摄和骁龙 ISP 适配。本轮将原厂资料落实为新的 CAMIF 源码，并取得本机用户态 ISP 模块的可核对位置。**仍未实现或部署完整 Spectra 硬件成像，完整目标保持 active。** 上一轮问答仅复核既有状态，没有新增适配；本轮实际进展如下。

## 原厂资料与现有方案

继续检索 VFE175/CAMIF、VFE175/libcamera、NV12 和 CamX。公开 Qualcomm GPL 提交明确了 SM8150 从 170 到 175 的匹配调整，不能因共用后端名称而套用整个新版 ISP。[Qualcomm 原始变更](https://android.googlesource.com/kernel/msm/+/b60faaba3b5b4ffa9d6fcf5af64c3d8dadbf46a9%5E1..b60faaba3b5b4ffa9d6fcf5af64c3d8dadbf46a9/)。未核实到可直接用于本机的完整主线 VFE175 PIX 后端；[279 固定的 IFE780/OPE/libcamera 方案](../kernel279/README.md)仍用于公共框架参考，不能当作175成像实现。

从现有 realme 官方内核本地仓库的固定提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 提取 `cam_vfe175.h`、`cam_vfe_camif_ver2.c/h`、`cam_vfe_bus_ver2.c/h`，记录逐文件 SHA256。[源码依据](oem-programming-sources.json)

本机原厂 vendor 分区经过当前276 boot guard、分区标签/容量及挂载状态核对，以 `ro,noload,nosuid,nodev,noexec` 挂载，只读取得 `lib64/hw/camera.qcom.so`，随后正常卸载并移除临时挂载点。原件6087920字节，SHA `e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde`。压缩包分128KiB片段传回并核完整哈希；没有执行OEM库、启动Android服务、读写校准或改重要分区。[采集来源](oem-hal-source-validation.json)、[卸载确认](vendor-unmount-validation.json)

ELF含 `.gnu_debugdata`，解压得到341080字节调试ELF，可对应本机CamX函数与地址。只用静态符号、反汇编及常量建立互操作事实；二进制、调试ELF和反汇编均保留私人目录，不放入公开补丁。[静态分析收据](hal-static-analysis-validation.json)。自动收据中的 preceding_literal 只是调用前窗口，可能跨控制流或包含前次调用的值，不能未经逐条核对当作所有调用的实参。

手工核对的部分寄存器范围如下；这不表示已经重建算法、选定所有硬件变体或恢复原厂调参：

| 原厂函数 | 写入范围/字数 | 能证明的事实 |
| --- | --- | --- |
| IFECAMIF::Execute | 0x478/2、0x488/3、0x49c/1、0xce4/2 | 与GPL175 CAMIF表相符；清状态命令4、默认配置0x4000c0、基础skip周期0x0f0f可交叉核对 |
| IFEBLS12::Execute | 0x6b0/3 | 黑电平模块命令范围，不等于已获得逐模组黑电平值 |
| IFEDemux13::Execute | 0x560/7 | Demux模块范围；增益、排列语义还需继续核对 |
| IFEWB12::Execute | 0x6fc/4 | 白平衡寄存器块范围；不能将任意原厂常数直接当当前场景AWB |
| IFEDemosaic36/37::Execute | 0x6f8/1及0x71c/2 | 两种算法均存在，不能仅凭符号存在判定当前模组选择哪一种 |
| IFECC12::Execute | 0x760/13 | 颜色校正块范围；系数格式和触发插值仍需核对 |
| IFECST12::Execute | 0xf30/12 | 色彩空间转换块范围 |
| IFEMNDS16::Execute | 0x9ac/0x9d8、0xa3c/0xa68、0x1040/0x106c各11 | 多组缩放块存在；完整路径选择、尺寸/相位和使能仍需核对 |

GPL bus代码进一步确认：FULL Y/C固定client3/4，RAW dump为9；NV12 packer为 **0xe**，与279导入的新平台后端写入的0x3不同。175有24个client，寄存器地址、打包和完成分组都须按175核对，不能复制780/880配置。尚未据这些范围新增任意寄存器用户接口或宣称NV12已可用。

## 新源码分层

独立候选树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，新分支 `samurai-vfe175-281`，提交 **`21facb9a7941ecd0a624a9e4fccd9ae544dde7b5`**，父280/`7f81d76ee7e05c1713ca87b59fc31df806ae0295` 保留。生产维护树仍为 `samurai-cci-io276` / `0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，干净且未修改。[完整补丁](vfe175-camif-candidate.patch)、[提交与最终源码哈希](candidate-commit-validation.json)

| 层 | 本轮修改 |
| --- | --- |
| SoC资源 | 只为SM8150两个full IFE选择显式vfe_ops_175；其它平台及Lite保持原有ops；line_num仍3，未开放PIX节点 |
| VFE175 CAMIF | 验证解码Bayer RAW8/10/12/14和尺寸后才MMIO；按CFA设置core pattern，保留无关core字段，配置full-frame RAW crop、CAMIF输出、skip/IRQ采样及epoch。没有在准备阶段提前发PIX reg update |
| 共用17x传输 | PIX用更新命令bit0、ACK bit4、SOF bit0；RDI和Lite RDI3使用各自既有位，不把第四个索引自动当成PIX |
| 公共生命周期 | line_prepare由void改int，17x与公共v2调用路径都在失败后释放预约并恢复stream_count，失败时不继续参数/DMA启用；780回调配套返回0 |
| 事件接口 | 保留SM8150标准FRAME_SYNC订阅/事件标志，适配显式175 ops选择 |
| 板级DT、固件、用户空间 | 无变更；未增加板级条件、OEM HAL运行依赖或应用专用接口 |

这是一段待与成像处理/输出组合的真实驱动源码。当前三个RDI均不调用CAMIF MMIO；没有通过增加第四条假PIX线路来冒充完整硬件支持。后续仍必须补处理模块、NV12双WM/完成分组、逐帧统计/参数及pipeline/IPA，再进行完整链接和硬件验证。

## 验证与保留失败

- 当前候选31个CAMSS组件ARM64 `W=1 KCFLAGS=-Werror` 聚合对象构建通过、零诊断；DTB逐字匹配部署版本。**不是完整vmlinux/模块链接、启动或硬件CAMIF验收。** [构建](camif-build-validation.json)
- 从实际CAMIF、17x reg-update/ISR/enable及公共v2 enable提取函数，编译后在ASan/UBSan下执行。核对10项OEM175寄存器地址及6项控制字段；覆盖16种Bayer输入、尺寸上下边界、未知/YUV/RAW16/packed输入拒绝且零MMIO、core字段保留、不提前更新、PIX/RDI3 IRQ隔离、更新累积/清除、当前三line边界和两个调用方的错误回滚。[测试](camif-host-tests-validation.json)
- 初次测试器编译失败：负例用了不存在的RGGB packed宏，且循环写法触发误导缩进诊断。保留原测试器和编译日志，改用真实BGGR packed宏及清晰语句后通过；不是内核构建或手机运行失败。[初始失败](camif-host-initial-failure-validation.json)
- checkpatch为0 error、1条通用“新文件是否需更新MAINTAINERS”提示。已核现有CAMSS目录维护匹配覆盖两个新文件，无须另加维护者条目；没有将它记成零warning。[检查与解释](camif-checkpatch-validation.json)
- 当前源码、公共补丁和文件哈希已保存；未推送、未部署。闭源原厂实现没有被复制进补丁。

## 现机与下一步

现机仍boot276/Image183、776模块/961包、libcamera r24/config-r19。最终50载荷、全部776模块保持，十个加载note匹配，原Phoc/Phosh/PW/WP进程身份保持；四sensor/lens/双CCI/CAMSS suspended，九rails及共享I/O OFF/users0、四MCLK和双CCI时钟0，fault0/taint0/pstore空、无CCI错误，SSC和SensorProxy正常。[现机核验](final-health-validation.json)。本轮没有新增相机采集或画质验收，仍RAW RDI→CPU ISP；连续AF、画质、四摄GUI/录像及其它整机未完成项保持。

下一步基于本机符号及GPL175 bus继续核对模块使能、定点位域、去马赛克/白平衡/CST、缩放和round/clamp配置，补175 FULL双WM和completion/统计，再连接280 IPP与281 CAMIF；保留标准typed参数/统计接口并配套libcamera pipeline/IPA。不能仅凭寄存器范围推导出全部模块语义，更不能用对象编译替代实机成像。最新完整统一Image/rootfs与上游合入仍未完成，不能承诺免补丁升级。

续作用 [host.py](host.py)，仍核276 boot guard；私人资料在 `E:/edk2-samurai-out/kernel281`。采集及构建均已终态，已有脚本的非幂等源码修改和提交步骤不要直接重放。
