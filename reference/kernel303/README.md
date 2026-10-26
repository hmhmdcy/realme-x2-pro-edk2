# 303：硬件 AE 候选与联合锁存验收准备

2026-10-19，按新目标恢复适配。开始时USB不可达；随后Windows报告端口重置失败，已通过原严格密钥Wi‑Fi连回并核实同一#298启动。联合控制480帧、硬件AE960帧实测通过所述检查；AE目前验证低照度上限，目标亮度收敛尚待更明亮场景。没有安装、刷写或重启，产品仍为RAW＋CPU ISP。目标未完成、继续active。

## 方案与分层

先复核已有[279仓库检索与固定版本](../kernel279/existing-solutions-validation.json)、[299原厂BLS／EEPROM结论](../kernel299/README.md)和[302有效帧控制](../kernel302/README.md)。重新搜索公开方案后，复用SDK已有的libipa `AgcMeanLuminance`、`Histogram`、`ExposureModeHelper`及sensor helper，不另写一套曝光搜索器。[上游算法源码镜像](https://github.com/libcamera-org/libcamera/blob/master/src/ipa/libipa/agc_mean_luminance.cpp)已变化接口，候选以保留SDK的实际接口构建，不能直接替换为master示例。主站抓取遇到验证页，不作为已读取源码。

| 层 | 本轮处理 |
| --- | --- |
| SoC／CAMSS | 沿用#298的VFE175输出／参数／BHIST，没有新增MMIO、内核或UAPI补丁 |
| 板级DT／供电 | 不变；不写入曝光、WB或本机个体标定 |
| sensor驱动 | 源审确认IMX319曝光与增益分写、未用group-hold控制簇；联合锁存仍须实测，必要时在此层修正 |
| libcamera pipeline | 按epoch／SOF／revision验证自动更新，送入既有DelayedControls；按SOF排序提交待处理统计；configure后公布该模式的Auto能力 |
| 硬件IPA | 从已确认BLS生效且有真实曝光／增益上下文的线性BHIST产生控制；等待上一revision实际生效，避免延迟反馈重复积累 |
| 模组数据 | [独立YAML](imx319-ae.yaml)限定IMX319 1632×1224／209066666 pixel/s／2080行长／3350最小帧长。0.16目标及曝光策略属实验值，原厂BLS参考不等于本机正式校准 |

[源补丁](libcamera-hardware-ae.patch)、[IPA](ipa/camss.cpp)、[统计适配器](ipa/hardware_agc.cpp)、[pipeline](pipeline/camss_vfe.cpp)。未修改公共libipa算法实现、产品配方或应用程序；通用算法源哈希见[分层收据](checkpoint-validation.json)。

Auto只在明确、通过校验的AGC配置和延迟控制均存在时开放。启动支持曝光／增益同时Auto或同时Manual；混合模式及运行中切换暂未实现并明确拒绝。手动WB保持启动时固定值。BHIST为线性Y，不能用于声称RGB AWB完成。没有应用算法返回的额外digital gain，也未开放动态帧长／防频闪／曝光补偿策略。

自动提议携带revision；下一次计算须看到对应revision及量化后曝光、增益在统计SOF上下文中生效。handler拒绝过旧、重复、越界或上下文丢失的更新并使上下文失效至重启。元数据报告该帧实际有效值，不回填尚未生效的提议。这些失败路径的完整硬件注入矩阵仍未完成。

## 主机验证

- [构建](build-validation.json)：AArch64、`-Wall -Wextra -Werror`；真实IPA、签名、生成proxy／worker及handler构建成功。
- [真实DSO契约](ipa-contract-validation.json)：映射标准参数／统计缓冲，保留56字节逐字节协议、Manual及错误用例；独立三帧延迟模型720帧／170次提议／340帧等待抑制通过。三档可达场景收敛，极暗不可达目标受上下限限制；旧epoch、重复／错误统计、未知上下文及停流／重开检查通过。
- [线程proxy](proxy-contract-validation.json)：真实生成线程通道又测720帧／170次提议，元数据与有效上下文逐帧对应。两组均为合成输入，合计1440帧不计作摄像头出帧。
- 独立进程proxy在主机QEMU中调用`SYS_clone3`返回ENOSYS，worker未启动，完整结果保持`passed=false`；本轮未验证真正隔离IPC。没有改生产库绕过namespace或隔离。[序列化检查](serializer-validation.json)另验证真实生成的控制结构往返及13字节独立字段布局，不等同完整IPC。
- [上机程序](runtime-tools-validation.json)：联合曝光／增益和AE两种标准libcamera应用均Werror编译；[joint包](bundle-joint-validation.json)和[AE包](bundle-ae-validation.json)含真实库、签名IPA、worker及fixture，未安装。

首轮构建因ControlInfoMap键类型误用失败，已修；首次线程测试的测试事件循环在回调后仍等到定时器，60秒超时，修正测试唤醒后通过。失败未变成通过。QEMU隔离失败仍开放，未以线程或序列化检查替代。

## 真机验证

[当前启动与资源核对](current-preflight-validation.json)确认同一#298 guard、5传感器／镜头、两CCI和CAMSS均自然休眠，9供电关闭、taint0。USB端口错误未修；使用已存原公钥的Wi‑Fi传输，没有放宽主机密钥校验。

- [joint-r1](joint-physical-validation.json)：隔离模式两轮各240帧，20000µs×2与10000µs×4共18次联合变化、36个真实写入逐项对应SOF＋2。BHIST及四个输出Y分区共90个过渡域未检出混合EV瞬态；限定该模式和所测场景，不是逐像素锁存证明。
- [AE-r1](ae-r1-association-validation.json)：真实隔离worker两轮480帧，10个生效revision／20个写入；50个可辨识统计／图像分区响应与有效元数据同帧变化。控制提议到有效帧为4个SOF，实际写入到有效帧为2个SOF，不混淆两种延迟。
- [AE-r2](ae-r2-association-validation.json)：签名线程两轮480帧，分别从5000µs×2和30000µs×16启动；7个生效revision／14个写入，31个可辨识响应域同帧对应。应用源和包版本分别保存在r1／r2收据，不能混计。
- 两种AE路径均逐帧核对标准Auto模式、量化后的曝光／增益和SOF上下文；增益文本仅6位有效数字，分析按5e-6相对精度核对，没有将文本舍入误判为控制错误。每个提议写入双控，未变化的成员写入也纳入核对。
- **当前低照度未达到0.16目标。** 四轮最终曝光3331行、模拟增益16倍，亮度稳定在传感器上限下；严格0.01目标误差检查保持false，另记录稳定上限结果，不称目标收敛。等待后摄朝向更明亮的普通场景后补双起点收敛。

三次运行均正常终态、全部候选文件哈希与手机读回相符；图／控制恢复，PM及9供电自然回收，匹配worker退出，四类新增fault为0、taint0。[joint恢复](joint-r1-capture-validation.json)、[AE隔离恢复](ae-r1-capture-validation.json)、[AE线程恢复](ae-r2-capture-validation.json)、[总收据](checkpoint-validation.json)。未重跑961包／778模块全量检查或其它相机产品回归。

主机QEMU的隔离worker仍因clone3无法运行；真机隔离IPC已独立验证，两个结论不互相覆盖。[304](../kernel304/README.md)继续离线EEPROM错位与WB／LSC解码，个体校准尚未应用。

## 上机顺序与恢复

私人根`E:/edk2-samurai-out/kernel303`。joint-r1、AE-r1／r2均已终态，不重放。Wi‑Fi已通过原严格密钥连回同一启动；旧#298 guard不能用于切换到未知启动。[操作边界](../../WORKING-BOUNDARIES.md)继续适用。以下命令为新运行目录的调用方法。

在WSL以root运行本目录脚本。`launch-capture.py joint r1 isolated`只启动一个新目录，使用原严格密钥与双重boot guard；随后`poll-capture.py joint r1`核对确切worker身份与终态。不得因传输超时重复launch同一目录。签名线程模式参数为`direct`。

联合试验每轮240帧、停流后重开一轮；20000µs×2与10000µs×4交替，18次双控变化。[独立分析](analyse-joint.py)已核对上述480帧有效元数据、36个写入和SOF＋2关系。它要求实景平台足够稳定；场景不稳不能记为联合锁存通过，更不等同逐像素物理锁存。启动器要求`joint-physical-validation.json`实测passed才允许AE；新运行使用未出现过的r编号。

AE实机还须补独立控制／像素关联、变光收敛、线程／隔离、停流重开和资源恢复；捕获摘要不是完整AE画质验收。之后继续RGB统计／AWB、多摄多模式、EEPROM布局与校验、暗场／颜色／阴影和完整IQ。用户此前延期遮光，仍可先推进普通场景测试。

SDK `work/libcamera299-inline` **现为303源码**；续作使用[303构建脚本](build-candidate.py)，不要无意重放302或更早源码安装器。已测302源码保存在私人`tested302-source-private.tar.gz`，最终302 runnable bundle已逐字哈希核对，见[保全收据](baseline-preservation-validation.json)。需要明确回退源码时解开该保全包，再用302构建入口；302独立可运行包本身不依赖SDK目录当前内容。

本轮核实并使用原#298启动，没有重启或完成新的桌面功能验收。旧GPU故障、modem watchdog、SSC偶发EPERM及多摄完整校准缺口继续保留；没有上游接受或跨版本零补丁升级证明。
