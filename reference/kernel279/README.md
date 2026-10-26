# 279：优先复用现有方案的 CAMSS ISP 源码候选

280更正：原厂SM8150选择VFE175/CSID175。本文VFE170指共用`vfe_ops_170`后端及此前170参考表，不再作为本机硅型号/全部寄存器已匹配的结论；175有24个client。后续候选在同树新分支，279提交保持。[280来源、版本与IPP](../kernel280/README.md)

2026-10-18。完整多摄与骁龙 ISP 目标保持 active，并按用户更新优先搜索现有仓库和方案。上一目标轮主要解释已有状态，本轮按无实现进展复核后继续：固定了外部源码、迁移公共输出/参数/统计框架，并保存可编译的独立候选。**本机 VFE170 硬件成像尚未接通，手机部署没有变化。**

## 已有方案与选择

| 来源 | 实际查到的能力 | 本项目采用范围 |
| --- | --- | --- |
| [Bryan 的 2026-10-05 IFE RFC](https://lore.kernel.org/all/20261005-linux-mainline-7-2-sm8650-hdk-rfc-0-v1-0-ed985aefd611@kernel.org/)和[测试仓库](https://github.com/0xB0D/ife-tests) | SM8650/VFE780 的 PIX NV12、BHIST、参数节点；公共输出数组、分组 WM 和 metadata 框架 | 本轮公共接口候选的基础；不是 VFE170 支持，也不是已合并版本 |
| [Qualcomm OPE v10](https://lists.openwall.net/linux-kernel/2026/09/25/547)及[测试工具](https://github.com/loicpoulain/camss-isp-m2m-test) | Agatti/Shikra 的离线 ISP；共享 `qcom-camss-config.h` 和参数块 | 复用公共参数方向和验证方法；不能把该 OPE 的地址/模块当作 SM8150 IFE |
| [Hans 的 libcamera CAMSS 分支](https://github.com/jwrdegoede/libcamera/tree/camss_pipeline_v2.1) | CSI/ISP 抽象及 OPE backend；实读源码仍使用 `SwStatsCpu` | 后续 pipeline/IPA 接口参考；不能称其已提供本机 inline IFE 或全硬件统计 |
| [hotdog 同平台项目](https://github.com/Sr-0w/hotdog-linux-bringup)与[libcamera focus 提案](https://lists.libcamera.org/pipermail/libcamera-devel/2026-February/057562.html) | 四摄及实验 AF；其 S5K3M5 采用另一镜头器件 | 多摄生命周期、AE 稳定门控、AF 方法可参考；不能照搬模组/距离单位或据此认定本机硬件 ISP 可用 |
| [realme 原厂内核](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)固定 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` | VFE170/CSID170 的资源、CAMIF、DMA、IRQ 描述 | 本机寄存器和通道依据；完整画质算法不因内核公开而自动具备 |

[仓库版本和逐文件哈希](existing-solutions-validation.json)、[原厂固定源码](oem-source-layout.json)、[RFC 下载](inline-source-fetch-validation.json)。OPE v10 的 14 封邮件也已固定到私人参考目录。`loicpoulain/linux` 的 `camss-isp-dev` 分支实际停在 2026-04-03，不把它当成 9 月的 v10。最初两个猜测文件路径的 404、一次 GitHub API 限流保留为检索失败；按真实目录找到 `camss-ope.c` 后完成读取，未执行外部脚本。

另外发现的 `arm64-laptops-v7.2-rc1-camss-v6-ife-bringup` 是旧 WIP，tip `8fba120842097db3284f4b1c7fa7351b6cbe3f93`，不是这份 74 补丁 RFC。候选由准确邮件提取。作者随后要求拆分/压缩此系列，[讨论仍有 NAK](https://lists.openwall.net/linux-kernel/2026/10/08/1320)；统计 DMA 对齐/拷贝方案也[仍在讨论](https://lists.openwall.net/linux-kernel/2026/10/08/1587)。这里不承诺临时 UAPI 已稳定或已经上游接受。

## 实现及分层

独立树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，分支 `samurai-isp279-candidate`，提交 **`30b0daa8cab27f64be4f058629b65f8af1a7cc6f`**；父提交为当前维护树的 `0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`。31 文件、3192 增/474 删；未推送。[完整候选补丁](camss-isp-candidate.patch)、[提交收据](candidate-commit-validation.json)

| 层 | 本轮实际变化 |
| --- | --- |
| 内核公共接口 | 沿用当前内核已有的 V4L2 extensible ISP helper；引入 RFC 的 CAMSS typed params/stats 与 QCIP/QCIS metadata 格式，保持新版其它格式 |
| CAMSS 公共驱动 | 输出数组、每输出 video node、多 WM 分组、metadata capture/output、参数内核副本/验证与统计框架；CSID 每次 s_stream 均配置，避免停开期间旧配置 |
| VFE170 后端 | 与新的 output/wm 结构配套，RDI 使用硬件固定编号；BUS IRQ 固定读取三个硬件 bank；先验证 WM/line 再索引；SM8150 不再把未实现的 PIX 误报为第四 RDI |
| 原有本机修复 | 保留 regulator/parent PM 失败回收、SOF 标签、完整 DMA 映射检查及 buffer 去重/分离；gen2 metadata 停止时清 active_num，保留 gen1 union |
| VFE780 候选后端 | 引入公开 PIX/统计实现；额外修复 header-only DISABLE 校验及 enable/disable 语义。此后端在本机没有运行 |
| SoC/板级 DT、固件、用户空间 | 本轮未修改；不是把曝光、AE/AF 或模组参数塞入设备树。板级 DTB 与现机 SHA 完全一致 |

[逐补丁应用/重定位记录](inline-candidate-apply-validation.json)：74 项中 57 项直接应用、6 项已在当前内核存在、11 项适配上下文。没有重复引入已存在的公共 helper。初次导入编译在 VFE170 旧单输出字段处失败并报告一个未用 helper；之后修正并完成最终构建。适配脚本过程中的括号/头文件导出宏问题、58 的部分执行及重定位脚本空白/替换顺序问题均已终止后按实际文件校正，没有对手机重放实验。

## 验证与证据强度

- 最终 ARM64 `W=1 KCFLAGS=-Werror`：30 个 CAMSS 组件对象、聚合对象、V4L2 ioctl/ISP 对象及板级 DTB 构建通过，零 warning/error。[构建](candidate-build-validation.json)
- DTB SHA `dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d`，与 boot276 部署相同；没有更改 SoC 或板级 DTS。
- 使用实际 core/parser 和 VFE780 callback，在精确长度的合法 DISABLE 缓冲区上，修前 ASan 检出读取有效载荷之外的数据；修后 ASan/UBSan 通过合法/非法尺寸、版本、类型、保留 flag、奇数/空 ROI、header-only disable。另对实际 apply/MMIO helper 检查禁用、启用、保留其它位、ROI 裁剪和无 flag 不改变启用状态。[负向](params-before-fix-validation.json)、[修后](params-after-fix-validation.json)、[源修复](params-fix-source-validation.json)
- 精确缓冲区测试证明原函数读取提交数据之外；实际驱动分配最大尺寸的内核副本，因此该主机 ASan 报告**不等于已经证明现机存在内核堆溢出**。本机没有加载该后端。
- 尚未完成完整 vmlinux/模块链接、启动、四摄运行回归、VFE170 硬件 PIX/统计采集或 IPA 逐帧验证；对象编译不能代替这些验收。

## 现机与后续完整目标

本轮只读复核现机仍 boot276/Image183、776 模块/961 包、libcamera r24/config-r19。50 个包载荷和全部 776 模块不变，10 个加载 note 匹配磁盘；四 sensor/lens/CCI/CAMSS 休眠、rails/clocks 回收，fault0/taint0/pstore 空、无 CCI 错误，原桌面/PW/WP 身份保持，SSC/SensorProxy 正常。[最终复核](final-health-validation.json)。未新增照片、镜头动作、安装、刷写或重启。该复核不扩大 278 单次 AF 的验收范围。

后续先继续查找与核对现有 Titan17x/VFE170 实现；按原厂布局实现 CSID170 IPP→VFE170 CAMIF/PIX、真正处理模块、分组输出和统计。已确认 FULL Y/C 为 bus client 3/4，RAW_DUMP 为 9，不能照搬 VFE780 编号。需要配套可审查参数/统计接口、CAMSS pipeline/IPA、同 request 参数/统计与硬件像素证据，然后再做四摄切换/异常/PM 和普通应用验收。

连续 AF/AF 加速及本模组距离标定、其它镜头/第四枚物理后摄确认、颜色/黑电平/阴影/噪声、GUI/录像、完整统一 Image/rootfs、GPU 与旧 modem watchdog 仍开放。当前仍 RAW RDI→CPU ISP，尚不能承诺主线/用户空间升级免补丁。降低维护量依靠通用实现与上游对齐，设备差异留在标准 DT、固件及调校数据；本轮实验候选没有替代当前产品配方或部署锁。
