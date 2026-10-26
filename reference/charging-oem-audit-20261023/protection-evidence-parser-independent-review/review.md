# 保存的 MAC 证据解析器：独立薄审

限定于冻结 delivery `cd351b4f3b4268e73111f12229584104c8ade7d8b7a75026078550263f876204` 的源码和已有收据，未发现需要阻止这份离线解析器使用的新增问题。没有执行作者入口、26例、CLI、C 编译或任何设备/存储卷操作；没有新增反例或修改作者文件。

逐项对照了 `parse-evidence.py`、`frame-decoder.c`、新输出 fixture 的构造、26例与 CLI 收据，以及 provider 的 `sm_protection_capture_locked` / `mac_evidence_show`、共享传输和实际 `gauge-protocol.h`。本叶的脚本只读取文件并校验清单、长度、收据与来源绑定，不导入或执行作者代码。它不替代作者已有测试。

完成门与失败保留的关键点：

- `parse-evidence.py:69` 起要求 terminal/claim、尝试计数及 stage6/error0 相符。`:78` 起逐帧检查顺序、大小、选择/读取/校验标志和返回值；只有 read_rc=2 才可同时声明 full_read 与 validate_attempted。
- `:104` 起以明确 SHA 绑定 decoder。完整帧交给直接 include provider header 的 C 解码器；解码的 command、size、validate_rc 必须与缓存记录相同。坏 echo/length/checksum 的完整包仍保留 raw 和负返回，未被当作“必须校验成功才能保存”的输入丢弃。短传输只有 unavailable，不能解释填充缓冲。
- `:118` 起核对两个有效 BatteryStatus 的时间位置；`:127` 的 sequence_complete 还要求八帧均完整、实际 C 校验均为0、0001 的值为2719、两个状态读取有效。因此单帧 select/read/validate 失败、身份错误或任一状态读取失败不能被报为 complete。未尝试输出沿 provider 全零初态处理，expected_size=0；已尝试但未访问的后缀按预置尺寸、其余字段为零处理，与实际 capture/show 一致。
- provider `samurai-gauge-protection.c:76` 至 `:110` 的第一错停止、before/after 读取和 stage 终态与上述门相容。其阶段和错误仍作为原始记录输出；本解析器不证明任意被改写文本都是内核原件，也不是穷尽所有部分失败字段组合的真实性验证器。
- `:133` 起的 mask 稳定性只是两个有效端点在既有 `0xd860` 范围的比较。没有将其转换成全批次原子性、兼容性、TCA 因果或充电许可；`compatibility_verified`、freshness、boot identity、charge/recharge、physical acceptance 均保持 false，TCA 为 UNVERIFIED。

收据中13种实际 provider capture/show 输出覆盖未尝试、固定读取完成、选择/读取失败、短传输、完整坏包、错误身份、before/after 失败以及端点关键/无关位变化；另外13个是文本/身份拒绝边界，CLI另列。旧六命令响应仅复用原缓存，新三命令响应仍明确为合成。源码/收据绑定已核实，旧21/149未重跑。

使用范围仍是“已保存普通文本的离线事实分析”。这份审阅不证明新的 protection ko 已安装、2719 支持新三命令、保存文件的新鲜度/启动身份或物理安全，也不为任何实际查询或充电控制提供授权。
