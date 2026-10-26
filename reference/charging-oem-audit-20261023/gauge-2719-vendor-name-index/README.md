# F.10 vendor：目录与充电文件只读检查

2026-10-24。复用[已完成的 vendor 提取](../gauge-2719-vendor-extract-candidate/BUILD.md)，镜像为 `905a0f04…bd7f0c`、1711276032 字节。`debugfs` 不带 `-w`，不挂载、不执行镜像内程序，不访问手机。完整私有索引保留在原输出目录，公开副本只列本轮相关事实。

原执行1079终态0：遍历129个目录，取得2884个唯一路径（128目录、2511普通文件、245符号链接）；不跟随符号链接。129个原子进程均终态0，镜像大小、mtime和inode保持。索引前核过镜像SHA，结束后没有再重读大镜像计算SHA。[独立复核](../../charging-session-20261023/gauge-2719-vendor-name-index-independent-review/README.md)核对了实际索引、调用闭合及下述修正，没有重跑工具。

首次38427执行失败已保存在[first-pass-failure.json](first-pass-failure.json)：解析器未处理 `/lost+found` 的三个未分配inode空槽。仅接受inode、mode、uid、gid、size全零的空槽，仍拒绝其它异常；[补丁](inode-zero-fix.patch)可重建原源码。原失败没有改写成成功，也没有修改镜像。

这个vendor的可达文件名中没有 `.bqz`、`.bqfs`、`.df.fs`、`.srec` 后缀。该结论不涵盖嵌入、压缩、改名数据、链接目标、其它分区或其它OTA。四个电池／充电名称候选及其两处服务引用、`build.prop` 共七个普通文件，另用只读 `debugfs cat` 取得；七个原子进程均终态0。具体大小、SHA与范围见[result.json](result.json)，原配置及二进制仅私存。

| 文件 | 静态检查所得 |
| --- | --- |
| `charger_fstab.qti` | Android persist挂载条目；未执行或挂载 |
| `vendor.qti.hardware.charger_monitor@1.0-service.rc` | 引用充电策略脚本和hvdcp_opti服务，含启动／属性触发条件 |
| `init.qti.chg_policy.sh` | 按SoC属性分支调整节点权限，再请求启动服务；脚本文本未提供本机2719协议或充电限流数值 |
| `hvdcp_opti` | 字符串含USB类型、输入限流、温控、PSY/IIO、uevent和QC/PD/充电泵路径；字符串仅证明相应符号／文本存在，未恢复其完整控制流，不能直接移植到MP2650或宣称已支持快充 |
| 两个架构的 `libbatterylistener.so` | 符号／字符串指向Android Health回调和audio_hw BatteryListener；没有据此确认2719查询语义 |
| `build.prop` | Android11、2021-03-05补丁、通用qti/msmnile vendor身份。OTA元数据的F.10标签不足以把这些通用属性认证为本机电池包身份 |

本轮扩大的是原厂资料覆盖范围；未改变生产策略、电压、预算、查询白名单或任何手机载荷。精确2719型号／字段语义、新MAC兼容性和TCA自然事件仍待证。当前手机仍501，现场顺序保持先验证既有prepared502通知修正，其它USB中断／PM候选另立窗口。
