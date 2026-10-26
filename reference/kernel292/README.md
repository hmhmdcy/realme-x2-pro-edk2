# 292：VFE175 参数节点、稀疏 pad 与真实部署后的 FULL 回归

2026-10-19。本阶段完整部署并启动了 #292 R2，不能视为白平衡或硬件 ISP 验收通过。参数节点出现，但首次图像 QBUF 被 EINVAL 拒绝；后续 [293](../kernel293/README.md) 修复本阶段遗漏的 FULL 输出数量校验，并单独部署验证。R1 从未启动，模块和镜像已保留。

## 原厂及已有实现的复用

继续使用既有 VFE175 寄存器后端、标准 MC/V4L2 路径和公共 typed metadata 参数格式。参数队列参考作者的 [IFE 测试仓库](https://github.com/0xB0D/ife-tests)及[参数节点补丁](https://lists.openwall.net/linux-kernel/2026/10/05/1605)，并补上该测试仓库日志所暴露的 metadata output link_validate 缺失问题。它们是方案来源，不代表本机或主线已完整支持。

三个本地提交分别处理：

- dd9db865b7c097f43ff5bff45d75ba53a2f5b460：按实际输出声明拒绝不存在的 DS/stats pad 格式，保留共享 pad 编号。
- 8a16fbe17010c1eede868f8b8eb7d1dbd77c81ad：在 VFE175 非 lite PIX 注册不占 DMA 的 WB 参数输出，复用已有队列、校验和应用回调。
- 86c7b9df030382efa82d87bc49370b3ad3a07cf3：metadata output link validator 检查源 pad 所有权、接收端固定 metadata 格式及错误传递。

均为通用 CAMSS/SoC 代码，无机型判断，没有改变 DT、固件或产品用户态包。宿主测试覆盖 pad、格式枚举及 link validator，ASan/UBSan 和 checkpatch 通过。但这些测试未覆盖真实 FULL 校验器与新增参数节点的组合，实机因此发现遗漏；保留失败，不以编译通过代替硬件验收。

## 构建、部署与失败范围

R1 构建、打包和模块收据分别为 boot-r1-build-validation.json、boot-r1-package-validation.json、module-r1-staging-validation.json；R1 无 link validator，未启动即由 R2 替代，原 778 模块保存在手机 k292-deployment/modules-r1-preserved。

R2 来源 86c7b9d，完整构建 142.48 秒，778 模块及 3 个 initramfs 蓝牙模块一致。仅刷 logdump，boot276 和 DT 保持；[启动读回](postboot-identity-validation.json)确认实际 #292、镜像及全部模块。桌面和传感器服务先未就绪，随后自然启动，无需补救重启。

真实 S5K3M5 pattern WB 测试 R1、增加 ioctl 诊断后的 R2，以及 IMX319 实景测试均在启动流之前失败：VIDIOC_QBUF 返回 EINVAL，0 帧、0 参数完成。媒体图逐字恢复，五个 sensor/lens suspended、九路相机 rails disabled/0 users、fault delta 0、taint 0。首轮 WB 收据已归档为 r1-wb-params-capture-validation.json，最新 WB 和 optical 失败收据保持原样。

根因是 camss-vfe-175-output.c 的 vfe_175_validate_output() 仍要求 line->num_outputs == 1；新增零 DMA 参数输出使该值变成 2。[293 修复](../kernel293/full-with-params.patch)保留单路 FULL 和地址/格式/client 限制，只允许可选的零 DMA 参数输出。

## 用户摆位答复与光学证据

用户确认后摄无遮挡后，本阶段在部署前的实际 #290 上补做 IMX319 实景 18 帧：Y 均值 74.247→89.203→74.243，高曝光标准差 13.409，私人预览出现可辨识结构和边缘。仍偏暗、偏绿，未完成黑电平、AWB 或画质校准。[实景分析](preboot-optical-pixel-validation.json)、[核看](preboot-optical-review.json)。不能把这份 #290 结果写作 #292 成功证据。

准备过程还保留两项本地错误：R1 首次打包误比对旧 initramfs 路径，候选镜像创建及设备写入前即失败；首次新 runtime checker 残留 #290 宿主断言，SSH 前失败。修正后各自通过。未掩盖失败，也未重复未知状态下的重启或刷写。

统计节点、BLC、IPA、libcamera 硬件 pipeline 和完整调校仍开放。原厂资料迁移原则见 [OEM-TUNING](../kernel276/OEM-TUNING.md)。私人图像、密钥及校准保持在私人输出目录。
