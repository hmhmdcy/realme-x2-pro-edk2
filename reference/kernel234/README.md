# 234：蓝牙帧状态诊断与真实串口产物核对

当前仍为233启动，boot232/Image183、PM8008两个实验模块及前摄r13/r8保持。前摄纯色参照按用户延期。本轮没有重启、刷分区或持久替换蓝牙模块；最后已恢复原185 HCI模块、helper、BlueZ配置和关闭状态。完整适配goal active。

## 已完成与实际限制

- 修复旧205隔离模型缺少真实UAPI `TIOCM_LOOP=0x8000` 的编译问题，实际运行三个C变体的ASan/UBSan：当前16例有2个契约反例，末尾同步变体16/0，错误前置同步16/2。旧205编译失败原样保留。模型的锁是stub，不能证明并发正确；裸同步调用不满足真实`set_mctrl`端口锁/IRQ契约，也需避开console/RS485，未部署为功能补丁。[模型结果](rts-mode-contract-validation.json)
- 实际H4函数8例ASan/UBSan通过。只收到`04`后，skb可为非NULL、len0/type4/expect2；同一个`ff`在此状态与新帧边界含义不同。chunk还可在完整帧之后失败，因此旧`partial=0/first=ff`不能定位丢字节。未加入吞FF或补04。[回放](h4-boundaries-validation.json)
- 通过ELF LOAD及真实符号映射，`set_mctrl`436B、`set_termios`964B与保留183 Image逐字一致；源与base提交一致，termios无直接BL到set_mctrl。结合233锁定的logdump183/boot内Image183确定实验针对现有实现，未把canonical新模块误当新内核。[产物核对](uart-artifact-validation.json)
- 新诊断默认关闭、仅phase5、每次qca_open最多16个chunk、每个最多32B。保存解析前had_skb/len/type/expect/padding/phase/baud/drop/时间/RX序号，以及打印前一次保存的解析后标量。H4、185脉冲过滤与错误返回保持。[源码](hci_qca.c)、[补丁](qca-bounded-rx-state.patch)
- 真实树内W=1/匹配183 ABI/intreeY构建通过，canonical after228及全部蓝牙源/对象已恢复。第一构建后审查修正前后时刻混合采样，再构建最终模块`8bfb059f…`/141704B；第一版保留私人证据。[构建](diagnostic-build-validation.json)
- 临时加载最终诊断模块并完成普通地址准备/初始化，实得2个phase5 chunk，各12B：每个含完整vendor event与command-complete event，前后均无剩余skb/padding，原始UART数据与HCI chunk逐字对应。命令到RX为7.352/11.110ms；配置为102.4MHz/div1/32=3.2Mbps，非物理频率测量。共1301条GENI事件，无跟踪溢出/丢失，没有复现历史重组错误。[分析](diagnostic-analysis-validation.json)
- 后续预定扫描未完成：脚本在断电状态设置Adapter1布尔属性时收到`Not Powered`，未记录具体失败属性。原生worker exit1/failed保留，不能称整轮测试通过；清理无错误，原加载note、787模块相关文件、userspace/config、keys逐项恢复。没有为补扫描重复装卸。[原始结果摘要](diagnostic-native-validation.json)
- 最终健康检查通过：taint0、WARN/Oops/GPU/DSP fatal/重组均0，三DSP running、SensorProxy三Has真、Wi-Fi/chrony正常、GPS idle、前摄和Q七路关闭。58个私人原生成员全部校验，原始UART/标识/密钥不公开。[健康](final-health-validation.json)、[证据](evidence-validation.json)

第一次只读baseline因不存在的`/etc/init.d/samurai-bluetooth`路径退出；没有服务/模块变化。改用实际`/etc/init.d/bluetooth`后在独立r2目录完成，保留第一次部分收据。运行脚本均为一次操作并有当前233 guard；不能直接重放已执行的launch或旧boot脚本。

## 下一步

本轮可用的初始化轨迹已经取得，不为“未复现”继续堆扫描次数。若推进RTS功能候选，应先把真实锁、console/RS485/PM和serdev路径纳入实际函数模型，并在独立内核候选中保持233的PMIC/当前相机部署，不能刷canonical整套旧camera产物。若再复现phase5，先关联完整chunk/错误位置与GENI状态，保留解析器语义。

优先推进IMX319实际OF/runtime与严格两路P电源profile；新的模式/错误回收约束和GNSS MEMSHARE研究见[后续依据](RESEARCH-FOLLOWUP.md)。后摄出图、GNSS真实卫星接收、无SIM无法验收的蜂窝业务等仍未完成。
