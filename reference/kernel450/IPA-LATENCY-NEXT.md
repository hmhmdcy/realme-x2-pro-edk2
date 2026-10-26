# 449 缓存中的 IPA 成本与 451 最小候选

2026-10-23，离线分析。450的旧统计淘汰回执修复应先独立回归。本报告不把33个SOF缺口归因于回执重入，也不宣称下面的编码优化能修复丢帧。

## 可确认的成本

[分析程序](analyze-ipa-latency.py)读取449 r2原始9000帧日志，核对精确448源码；450的IPA、序列化、生成的core proxy／worker及IPC源码与448逐字相同。[统计和宿主证明](ipa-latency-validation.json)保留源哈希。逐帧明细与可执行文件只存私有kernel450目录。

| 9000帧区间 | 中位数 | p95 | p99 | 最大值 |
| --- | ---: | ---: | ---: | ---: |
| prepareFocusedIpe同步调用 | 9.137ms | 31.403ms | 32.136ms | 45.408ms |
| 估计调用入口→AF日志 | 0.259ms | 2.819ms | 3.799ms | 8.246ms |
| AF→最后tone／CCM日志 | 1.418ms | 11.101ms | 21.628ms | 25.164ms |
| 最后tone／CCM日志→host返回日志 | 6.909ms | 11.896ms | 30.511ms | 31.695ms |
| FULL焦点采样墙钟 | 3.236ms | 7.382ms | 9.974ms | 11.001ms |
| FULL焦点采样CPU时间 | 3.197ms | 3.239ms | 3.263ms | 3.349ms |

入口由FRAME_IPA_PREPARE时间戳减dispatch-us估计。AF日志在AF状态处理后，tone／CCM日志在参数计算末尾；这些区间含日志、调度及同步等待，不能当成函数CPU计费。返回尾部还含worker编码、socket、host解码和嵌套事件。759次调用超过25ms，其中host同步等待期间记录708次SOF、762次PD10_READY及55次Parameters，符合IPCPipeUnixSocket::call循环processEvents的重入行为。

33个缺SOF均有PD10和统计、没有IPE_PAIR；有33次image/request映射重新同步。仅14个缺口的前四个SOF中存在≥25ms同步调用，另外19个没有。因此长调用不足以解释全部缺口。FULL的QBUF／DQBUF和内部缓冲所有权尚无逐帧记录，不能据此证明FULL断粮或丢弃发生在哪一层。

448容量租约在开流前仅约束CameraManager当前线程；隔离IPA worker更早在枚举时创建。现有日志未记录worker实际CPU、CPU时间或抢占，不能把墙钟长尾直接解释为小核计算。主线程焦点采样CPU p99为3.263ms而墙钟p99为9.974ms，仍存在调度等待。

## 已证明的私有参数编码放大

当前camss.mojom仅两个返回字段是array<uint8> parameters：prepareFocusedIpe和prepareIpeParameters。生成worker的两个分支都调用通用vector<uint8_t>编码器，host两个分支使用对应通用解码器。相关源码与生成include目录没有vector<uint8_t>特化；uint8_t本身使用单字节POD编码。

通用vector编码器对每个字节另记录4字节数据长度和4字节fd数量，故6008字节字段变为4＋6008×9＝54076字节。6008个临时字节vector及tuple复制、目标vector增长，在宿主实际计数中产生12033次new。不能假定IPA字节数组已连续打包。

宿主可执行程序直接提取当前vector模板、POD宏及辅助函数，以合成字节验证0／1／16／256／6008长度。私有快编码逐字节等于旧编码，均由旧解码器读回；快编码一次分配。6008字节的100次编码在本次PC运行中9352→420µs；这只证明实现成本，不代表ARM或相机收益。原件位于私有kernel450/ipa-wire-proof，逐帧关联在ipa-latency-analysis-private.json。

## 可复现的451草稿

[草稿补丁](ipa-wire-generator-draft.patch)只新增私有helper及修改两个生成器模板；[生成程序](prepare-ipa-wire-draft.py)和[生成审计](ipa-wire-draft-validation.json)通过。它在私有overlay使用精确450缓存模块及原generator/filter渲染10份输出：

- 仅Camss worker增加helper include，prepareFocusedIpe／prepareIpeParameters返回的parameters各替换一处编码调用。
- Camss host proxy和其它4个IPA的worker／proxy逐字不变。
- mojom、C++接口、命令编号、IPA算法、签名和所有线字节均保持；没有全局vector特化。

helper预分配原长度缓冲并直接写原有长度／fd头和字节。注意tuple返回使用std::make_tuple明确移动；宿主实验发现花括号形式即使写std::move仍会多复制一次vector。

**协议6与450 core／IPA／签名可以保留，最小只构建Camss proxy worker。** 本方案还保留54076字节字段，主要消除逐字节分配；若以后要改为连续6008字节的紧凑格式，才应显式升协议7，并成套更新core proxy、worker及匹配IPA接口／模块／签名。

实施时检查以下依赖：

1. output中的camss_ipa_proxy_worker.cpp必须由模板生成，不直接手改；确认仅两处调用变化。
2. private helper依赖标准头、libcamera/base/log.h和shared_fd.h；没有引入新的导出core符号。链接仍使用450的libcamera.so.0.7.2和libcamera-base。
3. 模板zip变更可能使Ninja重新生成其它IPA文件；生成审计已确认这些内容不变。限定构建Camss worker目标，不顺带重建核心或重新签IPA。
4. 部署前检查core／IPA／签名逐字保留，proxy载荷为新版本；同SOF PD10、GTM cookie／generation、WB和成功历史继续走原严格审计。

本脚本没有写任何候选源树或git index；父线负责审查并应用到451。复现顺序：在WSL的kernel450目录运行analyze-ipa-latency.py --wire-probe，然后prepare-ipa-wire-draft.py。二者在ext4读取前均调用449/storage.mount.mounted_build；前者仅编译独立宿主证明，后者不编译、不使用SDK。

## 可证伪的下一步

450先独立完成回归。451可打开现有IPAProxyCamssWorker的DEBUG；生成worker已有socket发送后的“Done replying to prepareFocusedIpe()”日志，不需修改IPA。与同worker的AF／tone日志及host返回日志关联，可分开发送前后，但此日志没有SOF，须按该worker的命令顺序匹配。

若加一个诊断点，放在worker参数编码前后，记录命令cookie、长度、线程CPU时钟、单调墙钟和sched_getcpu，慢调用或汇总时才输出。若编码CPU及返回尾部同步下降，说明优化生效；若CPU下降而约30ms墙钟尾部不变，继续定位调度／socket／host嵌套处理。数值包、历史或取消行为发生差异即判候选失败。不要同时修改worker亲和与编码，以免无法区分收益。

要关闭33个SOF缺口，另在FULL路径记录成功QBUF、imageReady的kernel SOF、IPE占有／归还内部FULL及请求重投递，用有界内存环保留缺口前后窗口。只有库存见底且归还／重投递晚于下一SOF，才能证明FULL供给不足；库存充足则继续定位camss驱动和完成队列。不能用增大bufferCount代替根因证明。原厂调校、数学算法与LTM实际消费保持复用。
