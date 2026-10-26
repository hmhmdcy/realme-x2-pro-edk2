# A640 降级功能与同平台 Linux 移植比较

2026-10-13核对。用途：解释内核兼容候选关闭的功能，并比较其他SM8150手机的公开移植做法。本次只检查文档和源码，未部署候选或修改手机图形栈。

## 关闭功能的实际用途

| 功能 | 用途和例子 | 关闭后的影响 |
| --- | --- | --- |
| Sparse binding 稀疏绑定 | 将一个GPU资源分块映射到多段物理内存，运行期间替换其中部分块；适用于大资源与按需加载 | 显式使用vkQueueBindSparse的应用失去该能力，需自行选择普通资源路径 |
| Address capture replay 地址捕获重放 | 记录GPU命令后，在重放时复用原GPU地址，保证嵌入命令或着色器数据的地址仍有效 | 影响依赖固定GPU地址的图形追踪与调试；普通buffer device address在本机探测中仍为1 |
| Lazy BO 延迟分配 | 为GPU临时资源先保留地址，等实际需要系统内存时再提供存储；对tile GPU的临时附件有价值 | 本机has_lazy_bos变为false，LAZILY_ALLOCATED内存类型消失；资源可能需要普通分配，内存压力与性能须实测 |
| VM_BIND提交路径 | 用户态单独管理映射，并通过绑定操作及同步完成驻留管理 | 回退到旧提交方式，可能增加BO列表与内核处理开销；没有实测性能百分比 |

稀疏资源的绑定和重绑定语义见[Khronos Sparse Resources](https://docs.vulkan.org/guide/latest/sparse_resources.html)。地址捕获重放的定义见[Khronos buffer device address features](https://docs.vulkan.org/refpages/latest/refpages/source/VkPhysicalDeviceBufferDeviceAddressFeatures.html)。延迟分配的内存类型见[Khronos memory flags](https://docs.vulkan.org/refpages/latest/refpages/source/VkMemoryPropertyFlagBits.html)。

这些关闭项不会把已经通过的绘制变成CPU软件渲染，也没有关闭GMEM、普通着色器、常规纹理、多重采样或基础Vulkan。对Phosh和基础GTK绘制，现有测试支持继续硬件加速；所有浏览器、游戏和特定扩展仍须按实际应用验证。地址capture/replay指GPU地址，不等于截图、录屏或游戏录像。

## 延迟分配还有未覆盖的扩展风险

本机Mesa 26.2.4源码在`tu_device.cc`按`has_lazy_bos`决定是否公开LAZILY_ALLOCATED内存类型；但是`VK_EXT_multisampled_render_to_single_sampled`及其feature仍无条件报告支持。内部`tu_get_msrtss_temporary`为颜色临时资源调用lazy内存路径。

这意味着不能把关闭lazy BO简单描述为“只可能多耗一点内存”。MSRTSS是允许应用以单采样附件使用多重采样渲染的一项可选扩展，内部需要临时资源。上轮1x/4x MSAA测试使用普通多采样附件加resolve，没有验证MSRTSS扩展。当前发现是源码层的兼容风险，没有新实机失败证明；在该扩展和功能一致性检查完成前，内核兼容候选仍保持未部署状态。

原版源码的版本与摘要已在[主验证收据](compatibility-validation.json)核对。此前发现的`sparseBinding=0`但部分sparse residency标志仍为1，也应纳入完整Vulkan能力一致性验收。

## OnePlus 7T Pro 的已验证路线

该机使用855+及A640，和Realme X2 Pro很接近。移植者在2026-08-04公开的验证栈是Linux 6.16与Mesa 26.1.6：启用SM8150已有GPU/GMU节点，指定本机签名ZAP固件，使用MSM DRM、Freedreno与Turnip。公开记录包括真实Vulkan提交和后续kmscube、Weston、Plasma Mobile加速。[GPU验证记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-04-mainline616-gpu.md)、[图形桌面记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-04-mainline616-graphical-userspace.md)

检查的移植仓库提交为`47087509c4289c2580c54f5433e55366b2e00445`，内核包指向ClearStaff源码提交`403b56c33e2ccdda25d90378970a5e5b928dee19`。[内核构建配方](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/aports/device/testing/linux-oneplus-hotdog-mainline616/APKBUILD)

对应UAPI没有EN_VM_BIND，内核VA_START/VA_SIZE接口仍存在，地址分配器使用PAGE_SIZE，配置为4 KiB。新增GPU启用补丁只启用节点和选择ZAP路径；检查的追加补丁中没有本机150方案的两项能力拒绝。因此它不是“主动关闭VM_BIND与SET_IOVA，再强制64 KiB”的先例。[内核UAPI](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/include/uapi/drm/msm_drm.h)、[旧地址分配器](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/drivers/gpu/drm/msm/msm_gem_vma.c)

Vulkan具体选择SET_IOVA还是GET_IOVA还取决于该次进程的VA查询结果；公开记录没有ioctl轨迹，不能从内核版本独自确定。公开vkmark和桌面通过也没有覆盖我们释放图像前方BO的空洞复现。

## Realme X3 的公开路线

Realme X3同属855系列、使用A640。可读取的Wiki快照标记3D加速Works，页面最后编辑于2025-05-29；其记录不能当作2026-10-13当天的实机状态。[设备Wiki](https://wiki.postmarketos.org/wiki/Realme_X3_%28realme-x3%29)

实际检查的设备构建配方依赖`mesa-vulkan-freedreno`和`linux-realme-x3`，带GPU固件清单。内核配方为6.12_rc7，固定源码提交`91911e069acbb9d38e5dcc633d454f7b1ff9bc4b`。GPU与GMU在DT启用，ZAP为X3自己的固件；配置使用4 KiB页面和MSM DRM。[设备包](https://github.com/sm8150-linux-mainline/pmaports/blob/ffed2c8413d0480fc22209f5e2d9b87b87d1a833/device/testing/device-realme-x3/APKBUILD)、[内核包](https://github.com/sm8150-linux-mainline/pmaports/blob/ffed2c8413d0480fc22209f5e2d9b87b87d1a833/device/testing/linux-realme-x3/APKBUILD)、[X3设备树](https://github.com/sm8150-linux-mainline/linux/blob/91911e069acbb9d38e5dcc633d454f7b1ff9bc4b/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts)

该版本也没有MSM VM_BIND，并保留VA属性查询与PAGE_SIZE地址分配。设备包使用发行版Mesa包的做法可借鉴，但这个配方并不能单独证明其Mesa构建没有发行版补丁，也不能证明它已解决我们新内核上的CCU空洞问题。

## OnePlus 7 Pro 与 Xiaomi Mi 9 的记录范围

OnePlus 7 Pro是855/A640。可检索Wiki记录主要描述6.2-rc3时代主线启动，公共7系列页将3D加速列为Untested；不能把早期可启动状态当作当前GPU稳定验收。[7 Pro记录](https://wiki.postmarketos.org/wiki/OnePlus_7_Pro_%28oneplus-guacamole%29)、[7系列公共记录](https://wiki.postmarketos.org/wiki/OnePlus_7_%28oneplus-guacamoleb%29)

Xiaomi Mi 9同为855/A640。可检索的设备Wiki中，屏幕为Partial、3D加速Untested。2021年的移植合并请求同时保留4.14下游探索和最低限度主线启动。这是适配进度材料，没有足够证据支持“已解决同类GPU故障”。[Mi 9设备记录](https://wiki.postmarketos.org/wiki/Xiaomi_Mi_9_%28xiaomi-cepheus%29)、[原移植合并请求](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2346)

这些Wiki页面的live访问受验证页或重定向限制，采用的是搜索工具可读取的旧快照。GitHub API还出现公共额度限制；实际源码比较改为Git浅克隆及固定提交的raw文件，没有把受限响应当作源码。

## 对本机修复方向的意义

MSM VM_BIND在6.17进入主线；以上6.12和6.16验证栈尚未进入这条新路径。[VM_BIND上游提交](https://github.com/torvalds/linux/commit/2e6a8a1fe2b262a6dfd0a65041fcd830ee1e7143)

可以确认别的机型采用同一MSM加Mesa图形架构，并且存在旧栈的加速成功记录。没有找到可直接复制、同时适用于本机新VM_BIND空洞故障的永久修复。版本差异能解释地址路径不同，但不能完全解释本机历史GLES故障：还应比较GPU/CCU/UBWC初始化、固件、引导接管和实际复现负载。

本机150兼容候选应保留为可测试的降级选项。现有149库方案保留新地址管理功能，应继续作为对照；完整功能根治需要在同一负载下验证根因修复与上游合同，而不能只凭其他机型的桌面截图或GPU Works标签作结论。
