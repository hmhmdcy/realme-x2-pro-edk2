# 453：当前 HAL 的 AF 外部配置来源核查

2026-10-23。以下保留离线查找历史；后续串行窗口已[匹配当前HAL并从本机ODM补取配置库和实际配置](AF-CONFIG-ACQUIRED.md)。此前假定的vendor单库路径未命中，实际库在ODM。尚未据此接受完整 `OemCamActuatorSettingMap` 分支，已交付nominal／个体AF文件未改，[个体步表](AF-INDIVIDUAL-NEXT.md)仍为条件候选、不可部署。

检查器：[inspect-af-config-source.py](inspect-af-config-source.py)；[脱敏结果](af-config-source-validation.json)。只用本地缓存和只读Git对象／debugfs；每次WSL访问先经449 `mounted_build()`。未访问手机、SSH、SDK或网络，未编译、部署或改生产配置。完整HAL副本、包清单和原始证明均在私有 `E:/edk2-samurai-out/kernel453/af-config-source/`；公开文件不含原厂AF调校实值。

## 版本门槛与现有采集范围

匹配权威仍是[281只读采集收据](../kernel281/oem-hal-source-validation.json)：6087920字节，SHA256 `e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde`。当前HAL实际导入配置库及 `GetKeyCount`／`GetValuesCount`／`GetLocaleIntegerListConfiguration`，在执行器校准前查询该表；没有证明实际选择，不能将数值核心的默认clip条件变成已选事实。

历史时间链另有[251原厂身份](../kernel251/stock-validation.json)的 `RMX1931_11_F.16` 与[257返回Linux](../kernel257/README.md)。242／248是更早的第三方Android／备份；不能把同型号vendor、相近F版本或文件名相同视为匹配。当前是否匹配始终由281的完整HAL SHA判断。

115 `camera-config-list-private.tar.gz`只含 `etc/camera`／BIN文件清单及挂载检查；`vendor-camera-source-private.tar.gz`只保存五个sensor SO，没有此配置库。281只导出了HAL，326保存模组描述和EEPROM读取。额外查看115／251／257／281／326的16份顶层tar清单：15份完整，未见目标库、当前HAL或匹配ROM包成员；115旧 `delay-fix-runtime.tar`不完整，单独记录，不以该归档证明不存在文件。

## 已排除的本地来源

| 来源 | 64位HAL字节数／SHA256 | 本轮结果 |
| --- | --- | --- |
| 原厂C.33，本地1330降级OZIP | 6123848；`bb952783700133ba2e1d65ea7eb22944332cbd4552fd9b626ebaada7f0e1f99a` | 仅重建vendor，ZIP成员CRC、Brotli结束、transfer范围与ext4标识通过；HAL不匹配 |
| 原厂C.34，本地1340 OZIP | 6123880；`9f480ce6e4787dff3826e840c5dd4ee00b4519aca5889673bba68e354f1a49c9` | 按113已固定OZIP分帧来源只读解码；相同完整性检查通过；HAL不匹配 |
| 本地 `X20Pro_F14/vendor.img` | 6088096；`847b1f9e19ef20e58cdf7ac42b0d3ed2c026b1e1b343be28471019c5de8e4ac0` | 已有Android sparse镜像只转换至私有临时文件，块类型／边界／EOF／ext4标识通过；HAL不匹配 |
| 113固定C.38仓库，提交 `0ef1fc05360421845f1ae905852dbfe63b26ba68` | LFS声明6123864；`f9f3cb22971e59f8151ceb7c387dd10334ccfa53ff6629411f9ac2434ed602b8` | 本地真实Git blob是LFS指针，OID已不同；未下载该对象，不当作已持有库原件 |
| 113固定Lineage18仓库，提交 `b94e26044cb95092add5dd8026fab0fdcb61433a` | 6123832；`7389852a9e462748d67fdea718b48c6a41b67f1220a7f5f22bf3142fafc5c3e0` | 本地实际Git blob哈希不同 |
| 242／248 vendor镜像 | 6003640；`660eef76135ef87d2c5c18cd96f2df98b1203c667889ba3460145d833d0c90ef` | 直接复用已交付的只读提取负证据，未重提 |

三个本地镜像均在HAL门槛处停止，未从中提取、解析或套用配置库／表。固定C.38和Lineage18树也未列出目标配置库。本轮没有因此宣称所有原厂版本都不含该库。

另查到本地 `Project_Infinity-X-3.12-samurai-24.07.2026-0750-GAPPS-UNOFFICIAL.zip`：中央目录／metadata／transfer list可读，但目录所指 `vendor.new.dat.br` 的本地头为零，Python ZIP读取以BadZipFile拒绝。它没有通过vendor提取，不能用于版本比较或配置恢复。没有重下整个包或尝试执行其安装器。

本地包与旧备份保持原样；本轮生成的可重建vendor临时镜像已移除，保留抽取的HAL、完整性收据、负证据和源码来源。没有用不完整或不匹配的来源补造参数。

## 后续进展与剩余项

此前枚举范围未命中匹配来源，不是全盘或互联网的不存在证明。后续已从本机[匹配HAL并补取ODM库和真实配置](AF-CONFIG-ACQUIRED.md)，纠正了此前vendor相对路径的假定；无需重采EEPROM或再下载整ROM。

[460实际原指令核对](../kernel460/README.md)已恢复默认路径、四locale及当前长焦HAL边界分支，全部既有表项数值保持，不产生新的正式参数。真实Android文件覆盖／运行时身份、工厂checksum、供应商认证、姿态和光学搜索安全仍待验，不能由默认配置的软件对等替代。
