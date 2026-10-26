# 451：一次分配编码 Camss 参数，保留原线格式

2026-10-23。由[450离线时延分析](../kernel450/IPA-LATENCY-NEXT.md)确认，6008字节参数数组字段的旧编码为54076字节；通用逐字节序列化在宿主真实模板中产生12033次分配。本轮只替换Camss worker的prepareIpeParameters／prepareFocusedIpe两处返回字段：预分配结果后写入相同长度／FD头和字节，降为1次分配，**编码仍逐字节相同，不改协议6或算法**。

[0062补丁](0062-camss-worker-byte-vector-wire-compatible.patch)仅改两份生成模板并新增内部helper；条件精确限定Camss方法和parameters字节数组，不是全局serializer特化。[实际生成审计](generated-validation.json)核对十份生成文件：仅Camss worker的一个include和两次编码调用改变，所有host proxy及其它四个IPA worker保持原字节。五种长度0／1／16／256／6008与旧编码、旧解码器对照通过，见[宿主证明](../kernel450/ipa-wire-draft-validation.json)。宿主耗时不能作为手机提速结论。

## 构建与契约验证

在独立451源码／build副本中只请求Camss proxy目标，实际仅编译和链接目标worker，76.35秒，SDK bind已卸载。[构建](build-validation.json)、[源输入](source-validation.json)。新proxy SHA256 `35526054954ce43d1068c710f6be6d4cd172288e4da7ffcab677712815f08f4d`。

450核心`3503c173…`、IPA `4c90047d…`、签名均与构建前逐字节一致；私有接口版本仍6，441 build4模块与原厂调校未变。完整载荷私存在kernel451；构建和离线准备期间没有访问手机，后续仅由主线在新交接窗口运行比较。

随后在SDK内用生产helper和真实旧serializer头编译并执行AArch64契约程序：五种长度全部线字节相同，原解码器均还原原输入，FD集合为空。[ARM契约](arm-wire-validation.json)通过，SDK bind已卸载；实机结果另按下述短比较范围记录。

## 1080p旧／新／旧短比较通过

主线取得明确充电交回后，按[短比较事务](COMPARISON-NEXT.md)与[只读preflight入口](PREFLIGHT-NEXT.md)完成r1。[实机小结](COMPARISON-HARDWARE.md)、[脱敏验收](hardware-validation.json)：三段各180图，共540消费＝540物理IPE；每段177次成功数学提交＋3张bootstrap，严格原始回执、同SOF PD10／GTM／实际WB历史及实际独立proxy exe哈希全部通过。

每段最后120图的tone日志→host返回日志中位为A1旧4.225／B新1.371／A2旧8.185ms，p95为10.440／2.388／12.976ms；本轮返回尾部缩短。Pair→queue中位为10.425／7.940／15.981ms，但B的p95 25.855ms高于A2的22.525ms，不能称所有分位均改善。焦点线程CPU中位从A1的3.195漂移到A2的4.593ms，仍是非受控单次A/B/A。

三段各自均未观测到消费者SOF缺口；正常结束后CPU选择、正式440 r32／r27与434模块、r5充电十字段逐项恢复，外部残留检查通过，四设备suspended、P/W各一个uid10000、taint0。新增内核故障核对改由[452完整dmesg补读](../kernel452/kernel-window-validation.json)支持：覆盖两窗口1057条新记录，指定故障模式0；原worker混用BOOTTIME／MONOTONIC形成的1字节空日志无效，不作零故障证据。候选未永久安装。原始28份收集文件及完整日志仅留私有kernel451；本次文档整理没有SSH、编译或重跑审计。原生IPA路径不经这个worker，本轮未重跑原生生命周期矩阵。

450 r3原始9000图严格回归仍有5个SOF缺口；449历史33个缺口中只有14个在此前四个SOF存在长调用，另19个没有。本轮短测不能写成丢帧根因修复、长期无丢帧或热／功耗验收，也不能由场景hash变化判断画质等价。下一步由主线执行452默认关闭、有界的FULL缓冲所有权诊断，区分捕获缺帧与缓冲／消费者断供；完整录像、画幅和多摄目标仍未完成。
