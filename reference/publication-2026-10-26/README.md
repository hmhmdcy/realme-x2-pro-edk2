# 2026-10-26：已适配内容整理发布

用途：记录本轮 EDK2 仓库公开范围内的适配源码、用户态包、设备树和证据整理。硬件是否验收仍以[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)和[检查点](../../NEXT-SESSION.md)为准；发布不扩大任何实机结论。

## 发布范围

本轮目标分支为 `hmhmdcy/edk2-realme-x2-pro` 的 `master`。在原发布端点 `f28c0035` 之后，分类提交包括：

| 组别 | 提交 | 内容 |
| --- | --- | --- |
| 文档同步 | `14550ff7` | 按文件增量同步、公开 UUID allowlist、充电候选排除规则 |
| 运行时 DTB | `6304026d` | 音频、触觉与 RMTFS 动态节点更新 |
| GNSS | `383e7ca9` | 桌面定位、GeoClue、位置辅助服务及 `kernel250` 至 `kernel260` 证据 |
| 平台/桌面 | `278ea218` | Samurai platform/desktop 软件包、设备服务脚本与 `kernel261` 审计 |
| 蓝牙 | `3770dc6a` | 主机栈、传输、静态修复、原厂对照及 Windows/LE 对端调查 |
| 维护审计 | `9635f869` | 全量升级、仓库审计、包加固与 `kernel314` 相机静态材料 |
| 充电交接 | `dc88f8d7` | 当前只读调查、失败/回退记录和后续交接 |
| 蓝牙索引 | `30c1f4dc` | 蓝牙总体功能状态、协调与运行期窗口工具 |

代码、包、补丁和证据均来自工作区已有内容；本次没有新增设备实机结论。充电仍处于调查和交接阶段，不表示充电控制、PD/APSD 或完整电源管理已经完成。

## 公开边界

公开副本继续使用[同步清单](../../linux-port/scripts/docs-sync-manifest.json)生成。以下未完成且含测试构建产物的候选目录只保留在本地私人工作区，不进入公开镜像或仓库：

- `reference/charging-session-20261023/`
- `reference/charging-ui-audit-20261023/`
- `reference/charging-oem-audit-20261023/`

设备身份、真实无线地址、密钥、原始日志和可执行/归档二进制仍按既有规则排除或脱敏。蓝牙证据保留了来源锁文件对应的原始字节，包括部分 CRLF 文本，以免改写后破坏 SHA256 证据。

## 核对结果

- 完整文档镜像同步覆盖 20,185 个文件，更新 199 个文件，公开镜像检查通过。
- GNSS 电源策略 14 项测试全部通过。
- 相关 Python 编译检查、JSON 解析和 Shell `bash -n` 检查通过。
- 更新后的 DTB 可由 `dtc -I dtb -O dts` 正常解析。
- `reference/kernel259` 与 `reference/kernel260` 的 CRLF JSON 已统一为 LF。
- 本轮提交推送后，应以 `git ls-remote` 读取的分支端点作为最终公开状态。

本次整理提交自身不重复列入上表；当前部署、未完成项与回退边界见[充电交接](../charging-management-20261023/charging-adaptation-handoff-20261025.md)及[检查点](../../NEXT-SESSION.md)。
