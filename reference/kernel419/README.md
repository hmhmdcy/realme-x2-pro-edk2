# 419：逐帧IQ失ACK恢复与错误缓冲出队

完整多摄/骁龙ISP目标继续active。本轮推进驱动恢复与用户空间完成通知，没有启用自动原厂画质，也没有永久安装候选。设备已恢复正式395核心、393适配器、CAMSS389与libcamera r30/配置r25。

## 实际改动

维护内核`samurai-ipe-error-buffer419`，提交`07d2ca735f88649587c0e89802febff6dbf2b443`，父提交417 `f0b6ea869e3e748e6c1ccfe06865ac8d02c3ef3a`。仅改`camss-icp-a5-m2m.c`：局部拒绝或已证明硬件停止并释放逐帧所有权时，正常完成ERROR缓冲；仅仍有七项逐帧所有权之一时调用`vb2_queue_error()`。保留全局fatal门控、复位顺序及无法证明停机时的额外DMA引用。

实际vb2等待函数先检查queue error，再检查done_list。旧实现无条件queue error使已完成ERROR缓冲也返回EIO，用户空间等待看门狗。[Linux vb2接口说明](https://docs.kernel.org/driver-api/media/v4l2-videobuf2.html)与本机源代码一致。[补丁](error-buffer-fix.patch)、[24项ASan/UBSan模型](adapter-validation.json)覆盖实际worker与vb2函数、七项所有权、失败停机保留引用等。模型不等于所有硬件失败均实测。

## 真机验证及报告差异

复用418实际libcamera库，两个wrapper先各完成非零LA帧；A提交有效LTM+Gamma组合后，临时测试核心只吞一次已验证的成功帧ACK。保留旧idle上下文，验证全局fatal门控；复位前后核对IQ与整个DMA parcel的保留、双会话fresh ACK、退映射及PM释放顺序；最后新wrapper恢复帧全部460800字节等406参考。故障帧仅在证明停机后检查，不作为成功图像交付。

修改前后各一次故障，共两次；第二次因为生产适配器确有改动。修改后blocked新上下文失败回调约0.00666163秒；修改前相关看门狗日志间隔约3.006532秒，计时起点不同，不作严格加速倍数比较。完整超时/复位约5.1017秒。[严格故障证据](fault-validation.json)。两个wrapper失败、第三上下文被fatal拒绝共三次失败；关闭最后旧idle上下文后恢复。导出图像FD存活时owner_refs=8，client退出后为0。

**原始r2 worker报告仍为false**：[原报告](runtime-validation.json)。它把printk时间戳与`/proc/uptime`比较，将四条预期故障日志错分为unexpected；client passed、清理成功、正式恢复成功。没有改写原报告或为修报告再注入故障。`verify-fault.py`改用保存日志中唯一drop到下一次SYS_INIT的顺序边界，要求恰好一条-110核心错误与[-110,-5,-5]三条适配器错误，且原报告unexpected恰等于这四条；其余故障关键词为零。将原报告失败与后续证据结论分开保留，时钟差异原因未证明。未来launcher模板也改用dmesg锚点，不依赖跨时钟比较。

## 构建与最终设备

[生产in-tree构建](intree-build-validation.json)使用W=1/KCFLAGS=-Werror，无诊断。正式候选核心419848字节SHA256 `63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632`，与417相同；新适配器132400字节SHA256 `46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f`。临时吞ACK核心SHA256 `e27ad5242e374140b6bc2a308ba020b612f7c300c4b5ee71e9e6e414346991a6`只用于故障测试，禁止混作生产模块。[测试hook模型](hook-validation.json)七项通过；去除宏块恢复生产核心源码。

[最终设备证据](current-state-validation.json)：四摄各12帧，共48应用帧/48IPE完成、无额外帧、失败/取消0；ICP/CAMSS/双CCI suspended，17时钟0，九路电源disabled/users0，逐帧DMA/映射/导入/CPU/IRQ/PM释放。PW9335/WP9340各一，uid10000，owner_refs53为桌面CAMSS句柄。所有419事务终态，无需重启；guard394保持。taint512来自417-r2已修WARN，保留历史，不声称taint0。未向硬件注入物理停机失败，也不声称全部硬件错误已验证。

## 下一步与范围

将生产419驱动与418 libcamera通道打包收敛，再接IPA prepare/result及原厂算法；必须以真实统计、曝光、增益及IFE/IPE输入域生成参数，仅最终图像处理成功提交历史，失败丢弃。Media Request完成本身不代表图像成功。当前pipeline仍提交旁路包，非零参数仅诊断验证；基础AE/AWB/IFE调校保留。避免重复IFE已有CC/Gamma。无需扩大已通过的TMC离线矩阵。

四摄指GW1主摄、IMX319广角、S5K3M5长焦与IMX471前摄，基础取流不等于原厂完整画质。[第五摄与完整验收范围](../kernel363/REMAINING-CAMERA-SCOPE.md)继续有效：2MP身份/共享mux、多模式/帧长/防频闪、连续AF/光学/几何/同步及未全复验项继续推进。SoC/板级DT/主线实验UAPI/驱动/用户空间分层说明；本轮只改驱动适配器，未改板级/传感器/IPA算法。原厂二进制、样本、日志和系数私存；公共仅作者代码及脱敏证据，本地镜像提交不push。
