# 440：四摄原厂自动调校整合版 r32 已安装

手机已正式安装五个 libcamera 运行包 `99990.7.2-r32`、config／stack `0.1.0-r27`、434 的三份生产模块，以及四份私有原厂调校配置。默认查找路径的四摄 GStreamer、主摄 RAW／双流、主摄与前摄自动调校、普通用户 PipeWire 均通过。磁盘文件、已加载模块 build-id 和实际系统库映射相符；最终新增内核故障0、taint0，ICP／CAMSS／双CCI均已休眠。[当前状态](current-state-validation.json)、[安装事务](install-r3-validation.json)。

这是已验证模式的自动链路发布检查点。绝对色准、均匀场、噪声、清晰度、更多尺寸／视频／HDR、第五2MP及多摄几何同步仍未完成，完整目标保持 active。

## 原厂数据和分层

主摄 S5KGW1、广角 IMX319、长焦 S5K3M5、前摄 IMX471 的私有配置分别复用437、438、438、439原厂导出数据，不重新读取 NV／OTP。原厂表和个体数据不进入公共 APK。公共通用 YAML 内容不变，配置包只更新依赖版本。

三路后摄保留原厂 IFE CCM 与各自 TMC／GTM／LTM／Gamma 开关；前摄2304×1728保留原 IFE CCM、TMC10／11、GTM关闭和 IPE CCM13、LTM／Gamma开启。前摄非单位 CCM 不套用后摄处理域。四路黑电平、归一化及各自模式绑定沿用已核对原件。

SoC／板级、sensor、Image363／DT389没有变化。内核仍为 source354 的 `9bc07e63…`，本次安装匹配434的 CAMSS／ICP core／m2m模块，均无测试参数；尚未重启验收。用户空间合入0042—0050自动观察、数学历史、真实PD10、GTM实际生效版本和前摄色彩支持，再增加[0051 RAW-only修复](0051-camss-raw-only-pd10-policy.patch)。

## RAW-only 修复与构建

首次整合实测发现：原 IPA 模式提示需要 PD10，管线却在只请求 RAW、没有 IPE 消费者时仍强制配置 PD10，导致配置返回 ENOTSUP。修复将需求收敛到通用 `processedEnabled && sensorConfiguration.pd10` 条件；保留 RAW 内部 AE／AWB 统计，观察正常释放，不提交不存在的 IPE 数学历史。IPA协议、调校及内核没有为此改动。

新源码 `/mnt/samurai-full282/libcamera440-release-r32/src/libcamera-v0.7.2` 从439保留副本创建，旧439未覆盖。420基线叠加0042—0051共10补丁，零 fuzz／offset重放，48个受影响文件与当前源码一致。[补丁重放](patch-chain-validation.json)、[源码](source-state.json)。

13个子包完整构建，7个运行包和离线回滚仓库签名有效；6个IPA均对包内核心验证签名，其余5个IPA与r31逐字节相同。实际剥离后库／IPA／代理的 ARM64 检查覆盖前摄、旧主摄、旁路和GTM，构建与安装ELF只允许精确的Meson RPATH删除差异。[包检查](package-artifact-validation.json)、[实际包内合约](packaged-contract-validation.json)。安装核心 SHA256 `0884c734…`，IPA `8703093d…`，私有协议仍5。

## 实机证据与计数

同一最终包、三模块和四配置的原生／隔离共8条路径交付406帧，其中386次成功数学提交、20帧显式bootstrap；每路末尾连续8帧AWB锁定。每帧核对同SOF真实PD10、实际GTM cookie／generation、WB上下文和最终成功历史，前摄同时核对IPE CCM及矩阵元数据。后摄覆盖两个GTM bank，前摄保持GTM关闭并只观察bank0。[逐帧审计](hardware-validation.json)。

主摄RAW-only连续72帧、其它三摄各6帧，共90帧，无IPE作业／数学提交；主摄RAW＋NV12六帧同SOF匹配。该临时套件共412次IPE完成，随后恢复旧正式环境；不能把这412次写成最终安装后的当前计数。

正式默认路径证据分布在安装r2／r3：四摄GStreamer各12帧共48、主摄双流6、主摄自动52、前摄自动44、普通用户PipeWire12，共162次IPE完成；另有主摄RAW-only6帧无IPE。自动主摄49math＋3bootstrap、前摄42＋2，均8连续locked。没有库、IPA或调校路径覆盖；实际加载 `/usr/lib` 库和 `/etc` 私有配置。r3核对相同载荷和既有证据后复用已通过的7个案例，只新跑前摄44和PipeWire12；当前驱动计数为56，不把跨事务历史相加冒认单一运行期。

安装r1／r2原始失败记录保留：[r1](install-r1-validation.json)、[r2](install-r2-validation.json)。它们是验收计数假设错误，均已实际回滚全部包／三模块／四配置，服务恢复、故障0。r1交付6张双流图像时，另1份已入队作业在停机中止，未推进IPA历史。r2主摄52张成功图像之外有3份观察未入队，均释放；57个PD10就绪信号也不能直接当作57张图像。修订后的审计逐SOF／令牌验证入队、回执、GTM来源、前序成功lux、提交／丢弃／中止／pending，以及实拍字节数和亮度；没有修改运行库来凑计数。[缓存原件审计](installed-auditor-prior-validation.json)。

## 恢复和后续

成功事务为手机 `/var/lib/samurai/k440-install-r3`，worker／client均终态。旧r31／r26七包、签名索引、world／仓库入口、旧三模块和四配置备份保留，可离线恢复。当前仓库入口指向该事务的签名前向仓库。不要重新启动已结束事务，也不要恢复429越界诊断。

原厂文件、完整日志、ELF、RAW／PD10和照片仅存私有 `E:/edk2-samurai-out/kernel440` 及手机事务目录。源码／可重建中间产物遵守284原32GiB构建卷挂载规则；SDK绑定串行。20261022两轮清理保留了当前候选和回滚材料。

下一步优先把真实PD10双遍链路从当前640×480处理输出扩展到已支持的其它预览／录像尺寸，并核对各尺寸的striping、DC网格和原厂模式绑定；RAW保持原生尺寸。然后继续完整legacy／manual／v2／HDR分支、光学校准、连续AF、第五2MP、个体与多摄几何／同步等[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。AWB锁定及非零图像均不等于绝对画质验收。
