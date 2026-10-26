# 阶段125：原厂CPAS、完整IOVA窗口与挂载并发修复

2026-10-12。阶段125完成本机CPAS版本守卫、175_100/101原厂IFE十项QoS、masked urgency和读回/时钟/ICC失败回滚；IOVA改用原厂完整窗口0x07400000..0xe0000000及两侧保留策略。实际C/ASan/UBSan、1024次真实内核分配器/rbtree测试及严格DTB正反例通过，#125完整Image/770模块包已构建；CAMSS disabled且未部署，真实SMMU/TPG DMA尚未验收。最新完整rootfs仍122匹配121；手机118/DPU2/GPU1/11来源hash保持，goal active。

## 版本与资源决定QoS配置

本机AndroidR active camera_8150的cam_cpastop_hw.c读取CPAS_TOP+0的camera版本和+4的CPAS版本。camera1.7.5配CPAS1.0.0/1.0.1/1.2.0分别选择175_V100/101/120。原厂CPAS_TOP=0xac40000/0x1000，CAMNOC=0xac42000/0x5000。候选通过platform resource/devm管理两个MMIO和七个时钟，保持runtime-PM/top domain/ICC次序；慢AHB80MHz、CAMNOC source150MHz满足native 3GB/s、32byte总线和10%margin得到的103.125MHz下限。

独立解析活动原厂cpastop_v175_100.h/101.h，两个IFE端口的五项配置完全相同：priority low/high、masked urgency、danger/safe，共10次ordered update；其他端口和disabled UBWC不写。urgency只更新mask0x70的值3<<4，保留其余位，每项读回按mask核对。native120布局不同，所选IFE地址越过本机0x5000资源边界，候选只接受camera1.7.5和raw CPAS0x10000000/0x10000001；其他camera/CPAS含120在QoS写入前返回EOPNOTSUPP。硬件版本当前未读取，不能把101当成本机已测版本。

[固定参考0066](https://raw.githubusercontent.com/Sr-0w/hotdog-linux-bringup/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/0066-media-camss-keep-sm8150-dma-in-range.patch)记录过高IOVA导致无buffer写入，属于外部bring-up线索。本候选以本机源码窗口和原厂QoS表为依据，不直接执行参考中的硬地址实验。

## 完整原厂IOVA窗口

本机IFE native iova start0x07400000、len0xd8c00000，end-exclusive0xe0000000。原31bit mask没有表达下界，也浪费窗口上半部。当前内核7.3已有[OF IOMMU地址解析](https://raw.githubusercontent.com/torvalds/linux/master/drivers/iommu/of_iommu.c)，候选在reserved-memory添加**仅IOVA**节点，两段iommu-addresses保留[0,0x07400000)与[0xe0000000,0x100000000)，用memory-region关联CAMSS。没有reg/size，不占物理RAM。SM8150在确认DMA/FQ domain和get_resv_regions回调给出两段精确RESERVED策略后才允许32bit DMA mask；其他SoC路径保持。

**get_resv_regions返回驱动/OF保留策略，不是读取opaque DMA allocator cookie或真实页表。** 本轮离线证明解析、策略合同和内核分配算法；真实启动时的保留安装、SMMU映射及设备DMA必须由下一轮真实buffer地址、IRQ和内容校验确认，不能凭回调或host测试宣称已完成。

当前构建工具固定dtschema2026.9允许无物理reg的IOVA-only节点。[最新dt-schema main](https://raw.githubusercontent.com/devicetree-org/dt-schema/main/dtschema/schemas/reserved-memory/reserved-memory.yaml)已要求reg，[2026-09-26 v5 iommu-ranges提案](https://lkml.iu.edu/2609.3/05737.html)改为设备级范围；当前工作内核尚未实现该接口，因此暂沿当前已支持路径，后续主线迁移开放。没有为通过新schema伪造物理RAM carveout，也没有盲回移广泛IOMMU核心改动。

直接抽取本候选drivers/iommu/iova.c的13个真实函数body、不重写算法，链接实际tools/lib/rbtree.c。无保留时1MiB返回0xfff00000，保留后返回0xdff00000；全窗口分配精确得到[0x07400000,0xe0000000)，额外一页/超额均失败；1024次伪随机大小分配（对齐开关各512）逐条检查范围/不重叠，并测allocation failure。gcc Werror+ASan/UBSan通过。host初次编译因工具kernel.h已有BUG_ON/min重复定义失败，移除host重复定义后使用已有宏通过。[分配器报告](../reference/kernel125/iova-allocator-validation.json)。

## 生命周期与设备树自动验证

[实际C故障测试](../reference/kernel125/cpas-c-validation.json)覆盖45个初始化/版本/clock/QoS读回/ICC resume与suspend场景，另有其他SoC零活动回归。被测CPAS和runtime函数body未重写，MMIO/clock/ICC使用host stub，独立原厂表oracle验证全部十项和masked urgency。未知版本零QoS写入；各读回失败释放时钟并清ICC；resume ICC失败清四票，suspend清票失败恢复四票且保留CPAS开启。恢复失败会记录错误，不保证硬件无法失败的回滚。成功suspend才关CPAS时钟。native CAMNOC internal peak增至3,000,000kB/s，其余DDR路径票仍待实际模式优化，不算所有高分辨率带宽验收。

[实际DTB严格CAMSS schema](../reference/kernel125/camss-schema-validation.json)：10个MMIO、8IRQ、33时钟、4ICC、8个SMMU SID/mask精确核对；8个负控均拒绝，包括缺IOVA引用。disabled必需属性的CLI过滤仍用strict validator关闭。端点保留124的5正例/6反例和共享L3/DSI phandle核对。[IOVA节点](../reference/kernel125/iova-schema-validation.json)逐cell检查两个范围及CAMSS引用，无reg/size；common schema没有standalone selector，先前iter_errors空结果被missing-addresses负控发现，改为显式对common schema验证后缺地址/加物理size两反例拒绝，错误phandle由跨节点精确合同拒绝。没有用exit0/空错误假通过。

首次DTC因候选port字符串offset变量误复用损坏include，第二次因子节点插在父属性前失败；仅候选文件受影响，124源保持。从124恢复并修正offset及节点位置后完整第三次构建通过，失败DTS/log仍私有保存。完整Image 4bded2cb151f910adc3ccd7c6545f4f2702b9a3a1022d4b9dbbcd5364edcf389（59501056 bytes），DTB f938401e441f26bdc26469b6114ea267b6ea8b16e625660d807d09a3fcdf601e，CAMSS c46f9bb9d77006a663d37be777ff1036a55cea970fa53ba4a477c9c8d7d80414。#125 banner、770模块、patch对124 dry-run、whitespace均通过；模块包7068025 bytes SHA 215331b678390ede3d2b25d8bff0a6c080262d419c684912fcfcc1c44758bd9f，depmod System.map零诊断，无symlink/全部依赖存在。与124仅CAMSS改变，其余769个ko逐byte相同，fixed IPA保持。

## 构建卷并发错误与恢复

本轮曾并发启动两个都会ensure122挂载的脚本，实际findmnt/losetup观察到同一E24GiB镜像的两层RW loop挂载。两个脚本在复制/mkdir/源码写入之前被单挂载断言挡住；挂载本身可能触碰journal，不能说完全零卷活动。到恢复脚本运行时WSL已自动停止并卸载，脚本显式卸载数量0，离线readonly e2fsck=0。没有修复原WSL VHD或损坏回退镜像。[恢复记录](../reference/kernel125/stack-recovery-validation.json)。

118/122共享ensure helper现用flock串行化mount/校验，锁放root-owned0700的/run/samurai-build-volume-locks，防普通用户创建sticky /run/lock文件导致root protected_regular拒绝open的问题；要求root运行。两个卷各4个同时helper进程，均成功且实际单挂载；124 Image hash保持。后续依赖步骤仍串行等待前一步terminal，不并发执行mutating mount流程。恢复脚本是一轮事故工具，不应再重跑。

E122内部copy125后余3,829,428,224 bytes，不能再盲复制4.2G候选树。宿主E余量不能代替内卷余量；下一轮应复用经验证隔离源码或先证明过时目录可恢复再清理。此前122删除四obsolete115 raw释放7.26GiB实际空间仍有效，本轮未删除新/回退产物、未resize原VHD。

## 当前手机和后续真实验收

只读同boot SSH：118/taint0、Phosh3492/Phoc3190原PID、DPU累计2/GPU累计1；PCM closed、双amp off/muted1/failed0，SLPI offline电源0，NV6/source4/vendor1共11hash通过。未写phone/重启GUI/执行GPU负载、GPIO/I2C或QoS交易。CAMSS仍disabled，未部署125；完整rootfs最新122匹配121，936包/770模块/21,134条目反向零差异，不能装125包到118冒充匹配。

下一优先完成有回退的TPG部署包和当前118启动守卫：匹配Image/DTB/模块及完整rootfs、实际buffer地址范围检查、有限帧capture内容/IRQ/hash、错误回滚。SoC内部TPG不必先破解未知sensor BIN或PM8008冷启动；GPIO/电源未知项保持关闭。**不要继续只做offline build来代替硬件验收。** PM8008四输入、全芯片enable/复位、sensor/settle、GPU CCU translation故障、GNSS fix、指纹和充电休眠仍15组开放项，长难项按用户要求留档换项。goal active，无人工确认/外发/push。

125收尾：E122与E118构建卷均已同步卸载，离线只读fsck均0；E122内部余3,797,602,304 bytes。C可用14.13GiB，E宿主可用68.47GiB；原WSL VHD未resize/fsck，回退和已验rootfs全部保留。goal active。
