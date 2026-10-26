# 280：纠正 ISP 型号依据，补 CSID175 像素输入路径

后续[281](../kernel281/README.md)在本轮候选之上增加VFE175 CAMIF源码及原厂HAL静态依据，未部署；本文280结果与失败均按本阶段保留。

2026-10-18。上一目标轮属于进展：279 保存了公共 ISP 框架候选并完成对象编译。本轮继续优先搜索现有方案和原厂实现，**纠正此前把本机直接称为 VFE170 的说法，并实现 CSID175 IPP 传输候选。没有部署新模块，也没有实现 VFE175 的完整硬件成像。** 完整多摄／骁龙 ISP 目标保持 active。

## 必须纠正的硬件依据

维护源码的 `vfe_ops_170` 是共用 RAW 驱动的符号名称，不能据此断定 SM8150 的实际 ISP 是 VFE170。固定原厂提交 `9668fcdc6ec15be7a10d66f7b93c347829e0fdb6` 的 `19781/sm8150-camera.dtsi` 及 `sm8150-v2-camera.dtsi` 对两个 full 实例均指定 **`qcom,vfe175`／`qcom,csid175`**；同仓的匹配表选择 `cam_vfe175_hw_info`。本机后续 PIX 实现应依据这些 175 描述，不能继续把读取到的 170 表当成已匹配本机的完整寄存器表。

175 的 bus descriptor 有 **24 个 client**，此前 170 参考表为 20 个；两者共享部分 RDI/CAMIF 布局，不证明全部图像处理模块相同。此前阶段的“VFE170”命名及其 20 client 结论只作为通用后端/170 参考的历史检查保留。[原厂文件路径、固定提交与哈希](oem-version-sources.json)。[公开 SM8150 原始描述](https://android.googlesource.com/kernel/msm/+/28cc5c521b21f92fa6f8a5a6be16960100f70a7a/arch/arm64/boot/dts/qcom/sm8150-camera.dtsi)也明确使用 175，但项目本地固定的 realme 源和本机实测优先。

本轮再次检索 VFE175／Titan175 PIX、CamX Titan17x 及既有 CAMSS ISP：没有核实到可直接用于本机的完整主线 PIX 后端。保留[279 的 IFE/OPE/libcamera/同平台方案比较](../kernel279/README.md)；现有新平台 RFC 和旧 RDI 提交不能替代型号匹配。

## 实机只读版本证据与收尾失败

当前内核没有可用的动态调试/函数跟踪入口，但 `/dev/mem` 可用。只在普通 `cam` 客户端取流、CAMSS active 且对应时钟开启时，按**已部署 DT** 的地址各读取一次只读 HW_VERSION；使用 `O_RDONLY` 和 `mmap.ACCESS_READ`，没有 MMIO 写或强制 PM：

| 块 | DT 地址 | 原始寄存器值 | 块版本字段 |
| --- | --- | --- | --- |
| IFE0 | `0x0acaf000` | `0x10020000` | 1.2.0 |
| CSID0 | `0x0acb3000` | `0x10000000` | 1.0.0 |

这些是具体块的版本编码，**不是把数值直接译成“175”**；175 家族选择来自原厂 SoC 描述/匹配表。未读取未开启的第二个实例，未扩大为所有实例版本验收。

宽角采集保留 120 帧单调序号。随后记录脚本中的时钟字典 `counts` 覆盖了健康函数同名函数，导致收尾抛错；原客户端退出码没有保留下来，因此不把这次采集记为完整通过的回归。已核原 worker 和 child 均不再运行、当前 boot guard 仍匹配，再用未被覆盖的健康函数补核并结束原上下文。保留失败文件，不重跑采集或版本读取，计划中的第二段前摄没有执行。[原记录恢复](powered-version-validation.json)、[只读设施检查](trace-facilities-validation.json)。脚本已改名为 `block_clocks`，提交标记阻止误重放。

## 新源码和分层

沿用独立树 `/home/cy122/x2pro-linux/camera279-isp-kernel`，新分支 **`samurai-ipp175-280`**，提交 **`7f81d76ee7e05c1713ca87b59fc31df806ae0295`**，父 `30b0daa8cab27f64be4f058629b65f8af1a7cc6f`。279 分支保留；当前生产维护树仍为 `samurai-cci-io276`／`0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，保持清洁。[候选补丁](csid175-ipp-candidate.patch)、[提交和最终源码哈希](candidate-commit-validation.json)

| 层 | 本轮实际变化 |
| --- | --- |
| SoC 资源 | 仅在匹配的 SM8150 full CSID 声明 `has_ipp`；无机型判断或板级接线写入通用逻辑 |
| CSID175／gen2 驱动 | 独立 IPP `0x200` 寄存器、RAW 解码/PIX_STORE、CID0、接收端、丢帧/采样配置、启动及独立 IRQ；不把 full 的 IPP 当作 RDI3，也不把 Lite RDI3 当成 IPP |
| 生命周期 | 按真实 HALTED 位等待 frame-boundary 停止，再清 enable；超时向调用方返回，不能伪报已经关闭。TPG 在所有路径准备后启动、路径停稳后关闭，超时时不伪造源停止 |
| 公共内核接口 | CSID `configure_stream` 回调改为返回 int，由 s_stream 传回错误；六个后端配套。没有新增任意寄存器用户接口或私有应用协议 |
| media graph | 匹配的 gen2 IPP 源 pad 只接受真正的 VFE PIX 消费者；RAW 源不能冒充 PIX。175 的 VFE 成像后端尚未实现，当前没有据此开放 NV12 成像能力 |
| DT／固件／用户空间 | 均未修改；板级 DTB SHA 与当前部署相同。libcamera r24/config-r19 及所有既有包/模块保持 |

RAW6…RAW16 的输入类型范围被校验；本轮实际主机用例覆盖 RAW8/10/12/16。未知 code、YUV、payload-only 和 VC32 在写寄存器前拒绝，VC31 有边界用例。未声称已实现 3A、降噪或 ISP 输出。

## 验证

- 当前源码 ARM64 `W=1 KCFLAGS=-Werror` 聚合对象构建通过；30 个 CAMSS 组件包含所有改签名后端，最终无诊断。[最终构建](ipp-final-build-validation.json)。没有完整 vmlinux/模块链接、启动或实机 IPP 验证。
- 实际生产 gen2 helper、configure、IRQ 函数被提取编译，在 ASan/UBSan 下执行；15 项地址/位域按固定 OEM175 表核对。覆盖 RAW、VC/格式负向、CID0、C-PHY、drop/subsample、正常 halt、超时保持 enable、重复 stop、RDI0/Lite RDI3、TPG 启停及超时、IPP IRQ/FIFO/reset ACK。[主机测试](csid175-host-tests-validation.json)
- 初次主机测试发现旧 RDI `enable << 31` 的有符号移位 UBSan 诊断，已明确转换为 `u32`，原失败收据保留；它不等于已经证明现机发生该故障。[初始诊断](csid175-host-tests-initial-validation.json)
- 这些测试使用模拟 MMIO，不证明硬件收到 IPP 像素。实机本轮只读了两个版本字，没有写 IPP/CAMIF/ISP 寄存器。
- 最终现机50载荷及全部776模块保持、10个加载note匹配、961包/r24/r19和原桌面/PW/WP身份保持；四sensor/lens/双CCI/CAMSS suspended，九rails/共享I/O OFF/users0、六相关时钟0，fault0/taint0/pstore空、无CCI错误，SSC/SensorProxy正常。[最终健康](final-health-validation.json)

## 继续完整目标

优先继续找/核对 VFE175/Titan17x 成像模块的现有实现，补 VFE175 CAMIF、图像处理模块、24-client 输出和统计后端；与本轮 CSID175 IPP 组成真实管线，再配套 libcamera pipeline/IPA、逐帧参数/统计和硬件像素验证。之后做四摄切换/异常/PM、GUI/录像及完整统一 Image/rootfs，不能直接部署一套只有传输/对象编译证据的候选并宣称成像完成。

连续AF/加速与模组距离标定、其它镜头/第四枚物理后摄确认、颜色/黑电平/阴影/噪声、GPU和旧modem watchdog继续保留。当前仍 RAW RDI→CPU ISP；原厂参数需归入正确层并经过验证，尚不能承诺主线或用户空间更新免补丁。
