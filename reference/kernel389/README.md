# 389：正式 CAMSS/ICP 平台所有者与板级部署候选

将 SM8150 ICP/IPE 接入正常 qcom-camss 模块，去掉正式路径对测试模块、测试兼容串、全局绑定标志和内嵌 overlay 的依赖。已完成模块构建、实际板级 DTB 语义核对、绑定校验和26个资源生命周期 provider 用例。设备仍运行原388收尾后的版本；**389正式驱动尚未实机部署，完整多摄／ISP目标继续active**。

## 复用与分层

先复核现有仓库的CAMSS、355资源后端、388直接DMA及352固定的[上游原型评估](../kernel352/icp-reuse-assessment.json)，并搜索当前相关工作。固定X1E原型的MDT/PAS加载器、HFI寄存器布局和不完整构建清单不能直接替换已验证的SM8150 A5实现；这一判断限于已取固定提交，不断言其它树均不可用。继续使用原厂ELF和HAL反编译所得的既有HFI、条带、SID和固件窗口证据，没有重新读取个体校准或工厂分区。

SoC平台层新增 [camss-icp-platform.c](camss-icp-platform.c)，匹配qcom,sm8150-camss-icp，获取标准DT资源并注册m2m，probe不加载固件、不释放A5 CPU。firmware-name可来自DT，默认qcom/sm8150/camera-icp.elf，拒绝空名称；资源不是机型硬编码。检查独占IOMMU设备组及完整七SID。运行时PM沿用已验证后端，系统挂起委托runtime PM，仍有DMA/backing时拒绝断电。

驱动所有权收敛到同一个qcom-camss模块：正常CAMSS先注册、ICP后注册；退出逆序。IPE打开上下文、导出DMA-BUF及未知完成的DMA都会保留该模块，因此也保留共享CAMSS供应者及CPAS。该静态设备实现禁用CAMSS/ICP手动driver unbind；没有声称任意热拔插、强制卸载或硬件错误并发已经验证。正常移除先销毁m2m，再停PM并释放资源。可读state/m2m_status只导出计数，cleanup供已有失败保留状态重试；不提供固件RAM或图像读取接口。

媒体适配层把绑定回调改为按device查询device_is_bound，保留测试模块的调用适配；允许内建模块的NULL owner，状态计数也安全处理NULL。模块态依赖链已经实际构建验证；内建owner参数在provider中验证，未构建完整内建vmlinux。通用SG owner API、核心DMA/IPE代码、传感器驱动、libcamera/IPA与调校配置不变。

SoC DTS补齐七组流，保持默认disabled；Samurai板级候选启用ICP，引用原有9ab00000/5MiB/no-map固件RAM，并加入五个仅含iommu-addresses的地址保留节点。它们描述原厂固件IOVA ABI，不新增物理RAM预留。新[绑定草案](qcom,sm8150-camss-icp.yaml)仍属本地提案，未提交上游或得到维护者评审。

## 源、构建与验证

主源/mnt/samurai-full282/source354，branch samurai-icp-platform389，最终HEAD a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，父388 95caf30a629bbaf454ebfc9ed25ce16ea3a952b5。以[source-state.json](source-state.json)、[最终补丁](platform-and-board.patch)、[源核对](source-validation.json)为准；源码干净。模块r4构建于fcaf366...，最终只修绑定的pattern语法；DTB构建于bdce399...，后续DTS未变，均经git diff核对。访问源码／build仍先用284 mounted_build保护。

[in-tree r4](intree-build-r4-validation.json)使用现有k363配置，通过真实olddefconfig选择CONFIG_VIDEO_QCOM_CAMSS_ICP=y，CAMSS/core/m2m仍为m。W1/-Werror，11目标，无诊断；共享CAMSS/V4L2/vb2输出和config/symvers恢复。qcom-camss 2838304B，SHA256 24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288；adapter118944B，SHA256 a0167f6acce4edad159d43101a723846ed494cf71fe3bb27857d2d145b44a7b8。

[产物核对](artifact-validation.json)：实际CAMSS模块包含两个平台驱动的注册数组、两个OF匹配串和正式firmware元数据；core、m2m helper、标准SG及四个其它vb2模块与388二进制完全一致。现有v4l2-isp文件全哈希与重编译产物不同，但.text和.rodata逐字节相同，保持已安装模块，不因文件哈希差异误换组件。

[平台provider](platform-validation.json)对实际probe/group/PM/remove函数运行模块态与内建owner共26例ASAN/UBSAN：缺组、共享组、分配失败、资源失败、流不全、固件字段错误／缺失／为空、m2m注册失败，以及driver core在remove前恢复PM的路径。它验证失败资源回收与probe不启动固件，不替代真实内核调度或硬件故障证明。

[DT编译与语义](dt-build-validation.json)：115927B，SHA256 0cc9dfd29044d7ca9ed2dbadbb62cedacd0298eba23fce377112ffe70d3b5db7，无诊断。相对运行中的365 DT，只新增五个地址保留节点和明确ICP属性；970个变化引用单元均解析到相同目标路径，其余已有属性语义不变，固件物理reg/no-map保持。

[绑定校验](binding-validation.json)使用[dtschema官方工具](https://github.com/devicetree-org/dt-schema)，版本2026.9。实际候选DTB通过新ICP绑定，六组IOMMU、缺memory-region、未知属性、空固件名四个错误样本均被拒绝。范围是新绑定及独立的全DT差异核对，没有把它描述为全板所有binding或上游验收通过。

## 实际固件载体与部署接续

[boot构建](build-package-validation.json)复用366的EDK2流程，将候选DT放入Linux真正使用的固件卷。与boot366逐FFS核对，仅DT模块改变，其余固件代码和数据、shim/ramdisk/Android头、兼容DT及分区尾部保持。仓库DT和三个共享固件输出在构建退出时恢复。完整固件及私有生成器不进入公共镜像。

下一步将这份boot载体与同一k363 release的五个模块（CAMSS、A5 core、adapter、标准m2m helper、修改后的SG）及已有原厂ELF组成可回退部署；先核对实际加载路径及initramfs是否含旧相机模块，再更新精确文件／depmod并启用板级DT。保留Image363、logdump365、原boot366和原模块离线回退，不重复部署全部778模块。正式驱动必须等加载新SG符号与新adapter，不能把新CAMSS直接载入旧依赖。

恢复／启用后检查真实icp@ac10000绑定、无测试模块和临时overlay，再验证导出FD/mmap保留共享owner、四摄／RAW／隔离IPA及卸载恢复。正式状态owner_refs是整个qcom-camss模块引用数，桌面相机句柄也计入；不能把它直接当作“导出缓冲区数量”，停PW/WP后再判断模块可卸载。完整IQ与[363全部剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续：实际在途取消／错误并发、Gamma/LTM/CCM、第五2MP、多模式、动态帧时长／防频闪、几何／同步和连续AF。

## 失败审计与设备状态

首次模块构建发现ATTRIBUTE_GROUPS宏要求icp_attrs命名，已修；第二次modpost因单独目标清单未包含现有v4l2-isp导出而失败，加入对应构建目标后r3通过。补空固件名称检查后的最终r4通过。这些失败没有上机。[审计](attempts-validation.json)。DT核对器补齐970引用变化涉及的标准／既有phandle属性后逐单元核对，没有放行其它语义变化。绑定最初路径不匹配，且minLength不在DT meta-schema允许的关键词中，已改标准目录和pattern，包含负例重验；检查器同时检查诊断文本，不能只看退出0。

[当前设备](current-state-validation.json)只读确认同一378恢复boot、原CAMSS/SG加载且文件一致、ICP仍disabled、候选模块与正式固件均未安装、taint0、CAMSS/双CCI休眠。389未修改设备。388的99帧是先前直接DMA证据，不移作389正式驱动实测证明。用户关灯条件继续生效，黑场／噪点不单独判故障。FW/HAL/反汇编/完整日志/图像/个体校准私存，公共镜像只本地提交，不push/PR。
