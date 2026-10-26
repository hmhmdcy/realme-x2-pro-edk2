# EUD关闭结果：固件到内核的结构化交接

2026-10-25。当前固件关闭EUD后只向RAM日志记录文本，内核没有可绑定的交接通道。本候选沿已冻结R2的实际BeforeEBS关闭路径，增加独立EFI保留页和真实配置表接收，补齐后续路由supplier所需的启动证据。它本身不是路由租约，没有放开APSD或安装到手机。

固件在arm期间分配一页4096字节EfiReservedMemoryType内存，登记专用GUID，页初始失效。原BeforeEBS一次CSR0写/读回成功后，写入64字节版本化记录：完整arm/before/after值、原EFI status、CSR地址、该保留页自身物理地址、原attempt/direct-FIFO退休及write标志、CRC。MemoryFence后最后提交magic。原全字集合0/1/0x01010101、MapKey重试不重写、direct FIFO退休及panel路径保持。

loader返回先使记录失效，再关闭原事件；只有事件已结束且配置表成功撤下后释放页。关闭或卸表失败保留失效的reserved页，不让晚到callback或EFI表指向已释放内存。初次安装失败可释放尚未发布的页；[固定CoreInstallConfigurationTable源码复核](source-review.json)确认其错误出口均在新增VendorTable前。原EUD日志区0x9ffe3000/0x14000及布局完全保持，没有借用其32字节header或best-effort日志作为授权输入。

内核在实际`efi_config_parse_tables`循环增加接收钩子，只有专用GUID、当前EFI boot/config/64位及samurai机型可用。重复或EFI自身判为不可用的表在本boot永久失效。读取前检查真实EFI descriptor为非runtime、可读WB reserved内存和完整64字节边界；两次拷贝一致后再验证全部字段及CRC，错误不修改caller输出。接收器没有EUD MMIO、IRQ、PD、USB或充电动作。CRC用于识别损坏/撕裂，不是密码学认证；来源信任继承受控EFI启动链。

[十组实际producer/receiver组合C测试](test-result.json)通过ASan/UBSan/Werror，覆盖完整全字集合、真实arm/callback/disarm与保留页生命周期、分配/安装/事件/关闭失败、重复或不可用GUID、EFI来源与descriptor、双读撕裂及64个逐字节损坏。只有BootServices、EFI表枚举调用、内存映射与MMIO边界为模型，失败保留页仅在fixture假关机时销毁；不是手机上的新固件验证。

[实际首次构建](build-result.json)仅编译BDS对象、EFI parser对象和新receiver；三个原子进程终态0/零诊断，kernel两对象沿原W1/Werror命令。新增AllocateReservedPages/EfiGetSystemConfigurationTable/FreePages/MemoryFence四个BDS强导入都在原41库中找到，未重编这些库。内核二对象relocatable内部接口解析成功，仍有正常kernel imports，未链接完整Image/固件。源码复核补上EFI自身的表可用性后，[只重编receiver](build-r2-result.json)，BDS/EFI两个不变对象直接复用；旧接收器及原十组结果保留history。[实际默认关闭配置](default-off-result.json)另编译唯一EFI对象，零诊断且没有handoff强导入，共享配置不变。

[配对补丁](paired-handoff.patch)对固定原BDS/当前EFI源码fuzz0应用后逐字相符；去除新增publish调用，BeforeEBS原CSR动作序列逐字相同。原panel三函数、全字谓词、kernel启动函数及direct FIFO函数保持。实际源码/声明来源见[source-result.json](source-result.json)，原共享树、SDK和手机均未修改。

下一步仍需实际资源独占且可撤销的EUD-off路由supplier、真实client引用/取消join、所有已知COM/earlycon/qcom_eud生产者排斥、PM和解绑语义及DWC消费接线。收到这份关闭记录不能替代这些条件，也不能把COM缺席当成功。Kconfig默认n，Makefile为同Image接线片段；还须最终固件/内核配套构建及新boot验证。当前USB500、保护和手机回充任务保持，完整APSD/Type-C/PD/快充目标未缩减。
