# 保护查询原包：保存文本的离线解析器

接续已冻结的[一次采证 provider](../protection-query-observer-candidate/README.md)，补齐其 `mac_evidence` 输出的实际消费路径。只读取已保存的普通文本文件，没有 SSH、sysfs capture、I2C、充电控制或自动重试入口；不加入未来 rootfs 模块包，也不修改桌面。

`frame-decoder.c` 直接 include provider 的实际 `gauge-protocol.h`，调用原 `sm_mac_observe_data_size`、`sm_mac_validate_sized`、LE16/LE32。没有再实现一份 checksum 或把近型号位语义写入生产策略。`parse-evidence.py` 检查9行完整文本、固定字段和命令顺序、原始36字节、尝试/选择/读取/校验标志与返回值、批次和帧的时间顺序，再将所有完整包交给这份真实 C 校验器。坏 echo/length/checksum 的完整包保留并与原 provider 的负返回对照；短传输保持 unavailable，不解释填充缓冲。

`sequence_complete` 只表示原包及固定序列完整、当前 identity payload 为2719。前后 BatteryStatus 的稳定性独立计算，mask `0xd860` 沿既有[分类器](../tca-classifier/tca-reference.h)的 OCA/TCA/OTA/TDA/DSG/FC 范围；不把 INIT 等无关位变化当同一门槛，也不把一次前后相同当全批次原子快照。没有两个有效 BatteryStatus 时结果为 null。失败或未尝试的真实输出仍可解析，不因采证未完成而丢失原件。

解析成功不证明来源、启动身份或新鲜度；任意保存文本都可能被改写。输出的 `compatibility_verified`、`freshness_verified`、`boot_identity_verified`、充电/再充授权与物理验收始终为 false，TCA 分类始终 UNVERIFIED。它不接收手工设 true 的策略参数，也不把 error0、checksum、零状态或所有字段稳定当新三命令的本机兼容/正常终止证据。普通六命令、保护 Health、Full、已有故障和计时器完全不变。

## 已完成的定向检查

[test-result.json](test-result.json) 保存本次26个边界及单次 CLI 结果。13种输入来自原 provider 的实际 capture/show 函数，复用已通过的 actual-provider.inc 与 OS/I2C stubs，仅新编译一个输出 fixture；旧六条读取响应沿原缓存，其它新三响应明确为合成。覆盖正常、选择/读失败、短传输、完整坏 echo/checksum/length、错误身份、前后 BatteryStatus 失败、未尝试、关键状态变化及无关位变化。另13个拒绝覆盖截断/超长/重复字段/错误schema、伪兼容位、命令/原包/完成标志/长度/计数矛盾和错误 decoder 身份。CLI 对保存文件的解析也实际 rc0。

fixture 使用 ASan/UBSan；旧21组 observer、149分类和其它旧套没有重跑。测试仅证明保存文本集成，不是新模块已加载、实机新查询已执行、TCA因果或整机待机验收。原输入逐项前后保持，无 storage guard/内核构建/SDK/设备操作。

私有已构建 decoder：`/home/cy122/charging-management-20261023/protection-evidence-parser-01/frame-decoder`，SHA `58aa5dcc9c15c571310d531d0b530ea024855b18fbcf95af6bb391d6d97e10f2`。构建命令及来源在测试收据，原包/fixture输出留同一私有目录；公共交付只有代码、说明和收据。

## 使用

在 WSL 中对届时已取回的保存文件运行；先用清单核对本叶和 provider header，再使用明确绑定的 decoder SHA。stdout 保存到该次私有采证目录，勿覆盖原始文件：

```sh
python3 -B parse-evidence.py \
  --input /absolute/private/capture/mac-evidence.txt \
  --decoder /home/cy122/charging-management-20261023/protection-evidence-parser-01/frame-decoder \
  --decoder-sha256 58aa5dcc9c15c571310d531d0b530ea024855b18fbcf95af6bb391d6d97e10f2
```

此命令不会启动新 capture。未来实际采证仍须在独立新 cohort/启动身份和已确认的手机窗口内，由同一内核 provider 执行一次固定 batch；当前手机501及prepared的502只写logdump事务均未改变。
