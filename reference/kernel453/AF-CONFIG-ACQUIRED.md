# 453：本机匹配 HAL 与 ODM 配置已补取

2026-10-23。新的串行相机窗口已只读补齐缺项：当前 vendor HAL 完整 SHA 与281权威相同；`libhwconfigurationutil.so` 实际位于 **ODM**，此前假定的 vendor `/lib64/` 路径不存在。没有下载ROM、重新采EEPROM、挂载分区或在手机执行原厂ELF。

| 原件 | 实际来源／长度 | SHA256 |
| --- | --- | --- |
| 已有 HAL 身份权威 | 当前 vendor `lib64/hw/camera.qcom.so`，6087920B | `e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde` |
| 配置解析库 | 当前 ODM `lib64/libhwconfigurationutil.so`，109784B | `9b317c9e3154929964aef1cca37b79fda00f7201c119d5f4cf9656f5c1917548` |
| 实际配置 | `/odm/etc/camera/CameraHWConfiguration.config`，1121B | `4d73f1ad3216bc9338e9113cd23d2b1ea68403cee3ab0b3c9fe718aa3f4e37f0` |

先核当次完整boot／既有k449 guard、新r6交接和正式440基线，再按实际标签、块设备、major:minor、sysfs及限定 `blkid -p` 证明vendor／ODM均为未挂载ext4。默认只读debugfs核普通文件，先计算HAL完整SHA，仅在精确匹配后取库；然后由库里的真实路径补取这一份配置。完整库与配置直接流到PC私有目录，核长度／SHA／ELF64 AArch64，前后挂载状态及充电稳定字段不变。

最初vendor单库读取失败，随后只列vendor的lib64／hw／camera／components目录并检查ODM来源，未把“vendor路径缺失”解释为覆盖表为空。HAL匹配证明当前vendor身份；ODM原件有独立现场来源证明，不宣称仅凭这个HAL指纹就认证所有分区的整套ROM版本。

原件与元数据保留在PC私有 `kernel453/af-config-source/`；公开不复制配置值或个体系数。[检查脚本](check-acquired-config.py)与[收据](acquired-config-validation.json)仅证明补取完整性。[460](../kernel460/README.md)后续已执行原库有限加载／locale解析及HAL实际覆盖分支：匹配默认配置不改变当前长焦的边界、initial、步距和任何既有表项，无需改写原候选；provider及未执行范围单独列出。checksum、实时姿态和实际光学验收仍开放，不升级为可部署AF配置。

本窗口相机采集结束后的用户真实USB拔插使充电进入waiting_source，已由充电任务接手；这不改写补取时的原件和前后检查，也不将末次充电恢复记为通过。
