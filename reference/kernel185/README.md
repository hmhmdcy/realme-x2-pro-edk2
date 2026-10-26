# 185：蓝牙功率脉冲与H4边界修复及实机部署

2026-10-15。无人值守外设适配goal仍active，范围包含GPS、实体摄像头、蓝牙、传感器、蜂窝通信等。185是工作阶段号；实际仍kernel183/logdump183、boot/DTB172、runtime/modules132、Mesa149、UCM173。本轮仅替换同release的一个hci_uart模块，未刷分区。边界见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 修复与构建

184两次新启动均有两条`phase=2 baud=115200 chunk=1 partial=0 first=00`重组错误；185扫描前的原模块对照又出现一次相同错误。现场及[上游QCA源码](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux.git/+/f5ca7a7161028db5ac5bcd06db03d7f2e340a20d/drivers/bluetooth/hci_qca.c)表明功率脉冲阶段先发送原始UART单字节，再重开端口进入HCI。

[补丁](qca-power-pulse-rx.patch)只在有限功率脉冲窗口、没有未完成帧和padding时接收前导NUL，并使用只读`ibs/pulse_rx_nuls`计数；后续有效数据继续送原H4解析器，普通模式、帧内0、padding及其它异常保留。开/关控制器延迟保持，同时拒绝0字节写入并在写失败时恢复flow control与标志。补丁针对本地原源SHA8f50e48f…，新源645ded49…，需要原有phase诊断上下文，不能称为直接适用于任意主线版本。

实际提取qca_recv、qca_send_power_pulse及当前h4_recv_buf的C验证：ASan/UBSan、1049场景、1030次分配与释放匹配；五种故意破坏窗口/部分payload/消费计数/短写/flow恢复的负例全部被检出。[主机验证](host-tests-validation.json)、[源码检查](source-validation.json)。仅主机报告中的runtime=false表示当时尚未进行实机试验，后续依据单独记录。

目标模块与依赖共同Kbuild、W=1告警0，vermagic和183构建符号核对通过，Image/DTB/config及原183的12个tracked源保持。单目标modpost会产生局部符号表，因此已恢复完整16793行Module.symvers及770模块的modules.order。[构建](module-build-validation.json)里的runtime_deployed=false是构建时快照。只安装hci_uart，btqca/btbcm保持原文件；最终784个树文件含770个模块仅1个明确覆盖。[清单](module-override-validation.json)

## 扫描对照与默认部署

原模块LE12秒、BR/EDR12秒、混合20秒均收到响应，但新增一次UART重组错误。候选同样三轮通过、错误增量0，独立HCI/MGMT均见真实Inquiry与LE scan，未见配对/连接命令；每组23个桌面/Wi-Fi/DSP/taint健康样本通过。[对照](scan-comparison-validation.json)

发现缓存中已存在1组配对/绑定，未删除或改写。为只扫描测试暂时设置ReconnectAttempts=0及空ReconnectUUIDs，原配置逐字备份；D-Bus保持Pairable/Connectable/Discoverable=false，DiscoveryFilter AutoConnect=false，未调用Pair/Connect。各次结束均关闭扫描/控制器，原密钥逐字段核对保持，新缓存中没有密钥。

候选SHA256 f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020，已原子安装到`/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k132+/kernel/drivers/bluetooth/hci_uart.ko`。标准OpenRC服务重载使用默认路径，已加载ELF build-id匹配，依赖保持，taint0，原BlueZ配置恢复。[部署](deployment-validation.json)

## 新启动与PM

按本次启动身份/分区哈希、784文件模块清单、GUI/无线/音频/DSP离线核验，完整证据取回并验证SHA后，冻结F2FS，发一次审查过的RESTART2进入bootloader。查到新的fastboot身份及产品后仅发一次reboot，**没有flash**。新183启动服务自动加载默认候选、0秒日志及九类所列故障均0，脉冲计数3、Phosh/声卡/Wi-Fi5180/ADSP/modem恢复，SLPI未启动。[新启动](reboot-runtime-validation.json)。这是受控热重启验证，未做物理断电冷启动。

蓝牙开启、无连接且不处于discoverable/connectable/pairable状态，先5秒RTC IRQ预检，再45秒s2idle。实际休眠45.205秒，success+1/fail+0、RTC IRQ+1、taint0、同boot且同加载模块；11项错误增量0，2392个PM结束回调全err0，其中QCA4个。前后控制器仍开启、脉冲计数5保持。[PM](powered-suspend-validation.json)

第一组合试验在醒后2秒的Wi-Fi5180检查失败，因而没有进入扫描，**仍记失败**。[失败](combined-trial-failure-validation.json)。随后Wi-Fi自行恢复至5180、无需手动重绑/重连；未测精确恢复时长，不能认定Wi-Fi PM完整验收。[观察](postresume-inspection-validation.json)

同boot另起仅扫描试验，不重复休眠；LE/BR/EDR/混合三轮均通过，独立捕获868个HCI包、MGMT实际LE与经典响应、23个健康样本，无配对或连接指令且协议错误0。[醒后扫描](postresume-scan-validation.json)。此结果是延后独立扫描通过，不将原组合失败改成成功。

## 失败与最终状态

保留初始目标modpost缺btqca/btbcm符号及in-tree extra-symbols无效两次构建失败、checkpatch标题/分隔元数据失败、主机测试stub告警，以及旧验证器假定无既有配对/固定6个MGMT发现事件的失败。改为保存既有配对并核对真实各transport起停事件，允许内核在一个D-Bus扫描内暂停/重启Inquiry，不删除多余记录。

重启前首次核验未规范化`./`路径，修正后又误把784个清单文件等同770模块；均在重启前失败，原partial副本保持。最终所有784文件逐一匹配，仅声明hci_uart覆盖。新启动第一次采集早于正常OpenRC启动bluetoothd，D-Bus激活失败原样保存；改为观察实际service owner就绪，未重复重启或借此手动启动服务。

最终530.53秒：新185所记录183 boot、taint0，原BlueZ配置恢复、服务运行，蓝牙关/扫描关/连接0、密钥保持；候选文件及加载build-id核对，784文件/770模块、NV/原固件/boot/logdump/persist哈希通过。Phosh运行、Wi-Fi5180、PCM闭/双功放静音，ADSP/modem running，SLPI offline/供电0且本boot未启动。十二类所列全boot故障0、脉冲计数6。[最终](final-validation.json)

## 回退与继续

旧模块SHA ae57a822…，在手机`/var/lib/samurai/k185-deploy/hci_uart-original-private.ko`、baseline副本及主机私人包中保持。回退须先核对新取的设备身份、停止BlueZ并按原samurai-bluetooth卸载，再原子恢复此release旧模块、启动标准服务核验；不用rmmod -f，也不用旧boot身份做新切换。原主模块树清单132保留，185清单明确仅此覆盖。软件/rootfs132更新可能覆盖本次修复。

私人原始日志、周围设备/密钥/调制解调器资料在E:/edk2-samurai-out/kernel185和手机k185*；两份完整包SHA验证，公开只含脱敏记录。[切换前封存](before-reboot-archive-validation.json)，最终包SHA见各报告。内核源码tracked13，git diff --check通过，无新整包Image构建或刷写。

此阶段修复并验证蓝牙UART启动错误、规定范围扫描和一次开启状态s2idle；配对/连接/蓝牙音频按边界未测试，物理冷启动及长稳仍开放。184光线名称补丁仍仅独立候选库，lux准确度/惯性/SLPI停启未修复；GPS真实fix、实体摄像头及蜂窝业务也未验收。下一步优先利用当前未启动过SLPI的新boot补文件服务/OEM元数据与ready握手证据，然后推进GPS/摄像头/蜂窝软件路径，完整goal继续active。
