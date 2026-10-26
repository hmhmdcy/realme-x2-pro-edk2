# 213：暗场与首帧全黑的区分，IMX471用户态候选

关灯后的物理RAW有暗噪声；CPU ISP另有独立的首帧查找表初始化缺陷，已在隔离候选中修复并通过固定输入对照。当前仍是212同一启动，系统libcamera及包数据库尚未替换，没有刷写或重启。完整外设goal继续active。[判别与修复对照](dark-and-first-frame-validation.json)、[最终健康](final-health-validation.json)。

用户确认房间关灯、手机此前放在室内窗边。UID10000取6帧1928×1088 packed RAW10，每行stride2416，排除6字节填充，并对DMA buffer执行READ START/END同步。六帧平均63.9491～63.983 DN、标准差0.441629～0.476061，相邻帧34.6%～36.3%像素变化，排除了全零或冻结RAW。RGB黑位扣除和量化之后仍可能全零；不能仅凭RGB全黑或非全黑判定故障和图像质量。[同步后的暗场](helper-raw-p0-sync-probe-validation.json)。

验证了0.7.2源包及原发行版六个补丁，取回官方helper提交e64b507d和属性提交59e7f189。helper模型为1024/(1024-code)，范围0..800；黑位4096来自上游同传感器测量，尚不声称本机暗场校准。属性原上游1400nm与一加官方同款IMX471的1.0µm不符，候选改为1000nm；控制延迟留空，不捏造值。[源与补丁](helper-source-validation.json)、[一加官方规格](https://www.oneplus.com/hk/9/specs)。

首帧缺陷位于`DebayerCpu::configure()`：注释要求把缓存gamma设为非法值以强制生成查找表，实际却设为有效的1.0，与首帧默认参数相等。最终补丁仅将其改为−1.0；头文件和ABI保持，未采用早期仅在宿主准备的bool标记方案。[补丁](../../linux-port/camera/libcamera/0009-softisp-cpu-initialize-luts.patch)、[构建](lut-build-validation.json)。

与室内光线无关的正对照采用CAMSS CSID内部全1数据，临时断开CSIPHY2→CSID0输入；同步后的6帧RAW所有有效像素均为1023。仅helper/属性候选的首帧RGB全零、后5帧所有字节254；加一行修复后6帧所有RGB字节均254。两候选只有libcamera核心库不同，未丢弃首帧；控制和链路已恢复，内核taint/新增fault均0。这证明首帧软件缺陷，与暗场分开验收；不证明传感器光学质量。[RAW正对照](helper-raw-csid-p4-sync-probe-validation.json)、[修复前](helper-rgb-csid-p4-sync-probe-validation.json)、[修复后](lut-rgb-csid-p4-sync-probe-validation.json)。

物理暗场中，修复后首帧为14～16灰阶（初始黑位参数0），后5帧全零（随后应用黑位约64 DN），与RAW噪声及量化行为相符；不把后5帧判作同一个首帧bug。[实际物理取流](lut-capture-validation.json)。helper缺失提示消失，实际增益元数据约1.001～1.060，公布范围1～4.57143；本机控制延迟仍未标定。

传感器内部图案第一次输出仍像暗场，**未接受为正对照**。当前驱动向`0x0600`写8位，而本机原厂BIN的SOLID_COLOR记录向`0x0601`写1，存在地址/位宽疑点，尚未改驱动或声称已修。仅通过V4L2控制读回2不能证明图案在硬件生效。初版统计器未做DMA同步时，CSID全1输入出现少量旧缓存像素；补上同步后所有像素准确1023，旧数据保留且不作为最终验收。[原图案尝试](helper-pattern-probe-validation.json)、[本机离线核对脚本](inspect-stock-test-pattern.py)。

首次SDK fetch遇不存在的libglvnd-dev，apk返回0却输出ERROR，原脚本又把零文件当成成功；已保留错误报告，修正为检查错误及请求包实际存在，随后108份签名APK验证通过。Meson缺xorgproto/openssl及首次链接缺递归动态依赖的失败均保留；补齐独立SDK后两候选编译成功，51份运行库只进入SDK。探针首次Span API编译错误及CSID预检未兼容菜单描述的失败也保留，均未被写成硬件通过。[fetch失败](sdk-fetch-first-failure-validation.json)、[输入](build-inputs-validation.json)、[helper构建](helper-build-validation.json)。

最终三个DSP running、sensor/CAMSS/CCI suspended、VDIG/VANA disabled且users0、MCLK及自身MMCX vote0；taint/五类fault0。GPS0/Signalsfalse/rate30、BT关闭无连接，UTC第8次准备成功/chrony Normal，NV和产品程序保持。手机已生成含227份文件的私人归档及逐文件清单，包括候选二进制、构建/失败日志和场景文件，排除SDK和IPA私钥。但主机下载在第三个1MiB块截断，完整下载和逐成员核对尚未完成；不能把本轮归档写成验收通过。[归档](final-evidence-archive-validation.json)、[源码核对](source-final-validation.json)。

USB截断后小SSH超时；Wi-Fi通过原密钥两次核验同一启动/taint0，随后Windows及WSL原生SSH归档取回均失败或超时，最新完整健康复查也未响应。前述完整健康样本发生于传输故障之前，不能冒充故障后的当前状态；未执行盲目重启、USB复位或分区操作。[最新复查](health-after-transfer-failure-validation.json)。

下一步先恢复新鲜连接，并在宿主继续准备原包功能完整的构建；然后把三个补丁整合进可复现相机包并部署，再验系统默认客户端。当前隔离构建仅simple/uvcvideo/virtual，不能直接用它覆盖系统原有auto/virtual与其它IPA的包；应保留原功能、工具、tuning、签名及依赖关系。[产品源码锁](../../linux-port/camera/libcamera/source-lock.json)、[原包清单](camera-packaging-inspection.json)。

所有历史211 GPU告警、212首帧及配置权限失败保持；CPU配置仍为当前兼容路径。后置四摄、完整16MP/图像质量/应用、控制延迟、GNSS真实fix、蜂窝/蓝牙/传感器/电源及完整rootfs目标继续开放。

214后续：重新发现USB邻居后连回同一启动，64KiB续传已核对完整归档和227成员，随后完整基线干净；本轮原失败记录不改为通过。[回收证据](../kernel214/previous-evidence-recovery-validation.json)、[后续基线](../kernel214/baseline-validation.json)。
