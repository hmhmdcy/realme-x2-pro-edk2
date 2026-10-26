# realme、一加、OPPO 的 GNSS 实现与本机差距

2026-10-15 补查。203已查过同平台主线项目，本次新增一加6的实际使用记录、X2 Pro与一加SM8150的Android设备树，以及跨品牌L5项目。公开源码快照固定提交；没有运行下载的脚本或更换手机固件/NV。[源码收据](gnss-related-source-validation.json)、[配置比较](gnss-config-comparison-validation.json)。

| 对象 | 查到的具体方法与证据 | 本机适用程度 |
| --- | --- | --- |
| [一加6/6T，SDM845，pmOS讨论](https://gitlab.com/postmarketOS/pmaports/-/issues/1505) | 有用户报告真实卫星接收，讨论涉及MM启用GNSS、MSB与XTRA注入；也有运营商相关失败。后续用户报告恢复OOS9固件后可用 | 提供固件版本、运营商配置和辅助数据的对照方向；是不同用户的现场报告，没有证明单个修改是全部失败的统一根因。不能照搬其固件或MCFG |
| [一加7T Pro，SM8150，QMI LOC记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-10-gnss-qmi-loc.md)及[状态](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/status.md) | QMI代理保持会话、LOC启停和能力查询已走通；记录明确没有获取卫星，状态仍Partial | 同SoC、协议接入可比；没有可以直接移植的真实定位完成方案 |
| [X2 Pro社区Android设备树](https://github.com/HyperTeam/android_device_realme_samurai/tree/e7c13c14b4b31cff2d914df5a7a47d7b32e72147)与[一加SM8150设备树](https://github.com/LineageOS/android_device_oneplus_sm8150-common/tree/6cdabfa3f3c930975f6e1ac0916a2251610add65) | 前者安装ODM gps.conf，保留QTI GNSS HAL、loc_launcher、xtra-daemon、libloc_api_v02等依赖。两份gps.conf的39个启用项仅LPP_PROFILE不同：2与3 | 说明Android沿用厂商定位栈；配置文件存在不证明主线MM读取它，更不证明本机RF初始化已等价。尚未把社区配置认定为原厂当前配置 |
| [realme/OPPO/一加L5 Enabler](https://github.com/rapperskull/realme_gps_l5_enabler/tree/bdec3a145e803c48f28e020f8ff3edafd6ae9883) | 作者仅声明在GT2 Pro/RMX3301测试；补丁修改静态NV备份中的gnss_multiband_configuration，并将本次启动的块设备链接指向修改副本 | 是开启额外频段的Android方案；不同SoC，未证明能修复X2 Pro所有正CNR为0。仅阅读，未执行或修改本机NV |
| [realme X3主线](https://github.com/sm8150-linux-mainline/pmos_realme_x3)、[OPPO SM8150官方GPL](https://github.com/oppo-source/android_kernel_oppo_sm8150) | 203已保存具体源码与来源；已核对材料没有给出GNSS真实fix完成记录 | 继续作板级/原厂资源参考，不能以同品牌或GPL仓库存在推定GNSS完成 |

配置的唯一差异由完整文本diff和启用项解析分别核对。LPP_PROFILE的注释定义2为LTE控制面、3为控制面与用户面；它属于辅助定位协议配置，尚未建立与本机standalone会话无正CNR之间的因果关系。两份文件含旧编码注释，首次UTF-8解析失败后按CP1252读取；原始字节保持。GitHub匿名API返回403的记录保留，随后通过公开Git固定提交并提取文件，未执行仓库代码。

本机已有独立进展：204第二次启动的首次桌面GNSS-only会话运行182.40秒，188条去重NMEA、176个推进时间，自动一次下载/注入后辅助数据窗口为当前168小时；有效fix、正CNR及位置事件仍全部为0。[实机收据](../kernel204/reboot-r2/geoclue-first-session-validation.json)。205第二次启动只验证空闲UTC自动准备，未运行新的GNSS接收会话，不能把204结果当成本次定位通过。

下一步优先核对本机原厂modem固件组合、配置/文件服务装载与GNSS启动协议，参考一加6的版本及配置差异排查；同时保留真实天空接收条件、RF/LNA/时钟诊断。现有OEM19781 DTS搜索只命中通用CDP/MTP GNSS UART注释，没有足够依据指定本机LNA GPIO或供电。标准MM/GeoClue和辅助数据路径已验证，后续改动要用正CNR、有效fix及真实位置事件验收。

207更新：按本机原厂文件服务方向查到缺失的`modem_pr/mcfg`目录，已从本机只读modem分区将173文件复制到私有RAM；正常新启动自动复制和基带读取`mdtime.txt`通过。TFTP块号回绕也已修复。随后181.37秒实测187NMEA/174推进时间，自动一次下载/注入168小时辅助数据，fix/正CNR/位置事件仍0。这是本机配置文件服务的具体修复，尚未证明是GNSS接收根因。[207完整记录](../kernel207/README.md)、[实机接收结果](../kernel207/reboot-r2/geoclue-first-session-validation.json)。

221按[高通公开LOC实现](https://github.com/qualcomm-linux/location-apis-qcom/tree/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948)补齐独立只读查询：GPS强制启用、四星座内部启用，四个返回的黑名单掩码0。新多频GET被当前接口拒绝，不等于硬件不支持；未返回字段不当0。它缩小软件禁用排查范围，没有取得真实fix/CNR，也不替代本机RF/天空基线。[221原生证据](../kernel221/README.md)。
