# 其它手机移植 Linux：GPS 实际修复点及本机适用范围

2026-10-16。用Exa完成3个检索方向：近机型实际修复、GNSS供电/启动链、Qualcomm诊断传输。按技能的numResults累计口径为78项结果，包含重复，**不是78个已验证案例**；优先阅读作者补丁、提交及实测记录。下面将实际接收成功、仅会话打通和不同硬件架构分开描述。

## 可借鉴的修复

| 机型/项目 | 一手材料中的实际修复或结果 | 对X2 Pro的判断 |
| --- | --- | --- |
| Pixel 3a/sargo，原生QMI | 作者复现开机qmicli早于QRTR就绪，报node0不存在；将modem-gnss排在ModemManager后，执行engine-lock=mt。[2025-12-25提交57c75db](https://git.mrlokop.dev/MRLokop/pmaports/commit/57c75db149a2bf554fc2b2489f0a9aa3be8562a1) | 真正的启动时序修复。本机LOC服务存在、同CIDStart/Stop成功、MT锁历史已核，不能照搬此补丁解释持续零CNR。来源是原提交的镜像，原站抓取受访问限制。 |
| OnePlus 6、PinePhone，gnss-share/MM | 作者测试MM共享定位、修复modem消失后重建及D-Bus初始化超时，最终GPS setup单独允许50秒。[已合并MR12](https://gitlab.com/postmarketOS/gnss-share/-/merge_requests/12) | 属于服务接入与生命周期。**MR最初描述有XTRA文件注入，但作者2023-12-05明确将其移除，不能把旧描述当最终功能**。不启MSA/MSB也能走此路线。 |
| PinePhone，无SIM | gnss-share移除“modem必须enabled”的前置检查；作者以MM1.23.4-dev无SIM实测，MR于2024-03-24合并。[MR15](https://gitlab.com/postmarketOS/gnss-share/-/merge_requests/15) | 无SIM的软件门槛可以修。本机已有较新MM并直接用QMI LOC实测，不因MM State−1就认定接收机不能工作；也不把这个PinePhone结果推广为全部modem均支持无SIM。 |
| POCO X3 NFC/surya，SM7150 | 维护者报告解除出厂GNSS engine lock，补同CID Start+monitor及MM合成缺失的Galileo/BeiDou GSV；声明无A-GPS、冷启较慢，整个干净安装流程尚未端到端验证。[项目实测状态](https://github.com/woodyst/surya-pmos)、[固定同CID补丁](https://github.com/woodyst/surya-pmos/blob/d7eadb03f230506140839f18a6c0ef3c43016d7e/packages/libqmi/0004-qmicli-loc-combine-loc-start-with-monitoring.patch) | 同CID和多星座报告值得参考，本机前者已覆盖；GSV合成不能产生真实CNR。其持久解锁属于另机配置，不能复制MBN/NV或重复盲解锁。 |
| GTA04，W2SG0004/SiRF | 作者明确指出独立LNA需上电才有真实GPS接收，提交新增lna-supply及电源管理。[内核补丁原文](https://lkml.iu.edu/1812.1/00432.html)、[主线sirf驱动](https://github.com/torvalds/linux/blob/master/drivers/gnss/sirf.c) | 这是确有依据的LNA供电修复，但为独立串口GNSS架构，不能据此给集成Qualcomm modem的X2 Pro猜GPIO或新增同名regulator。 |
| Surface Duo，SM8150/Droidian | 维护者固定源码记录vendor HAL经binder/GeoClue取得约4m定位、冷启约100秒、未用XTRA。[适配源码7cb53dd](https://github.com/agentsco-lab/surfaceduo-droidian/blob/7cb53ddca60590b1f44c402d1b5bfd333b44fa66/adaptation/package/build.sh#L280) | 同SoC成功先例，使用完整厂商兼容栈；不是复制一个so或gps.conf。作为架构比较，当前仍遵守用户保留Linux、不刷Android的要求。此项沿用239已固定抓取的证据，未宣称本轮在本机运行。 |

## 相近但尚不能当作定位成功的案例

[OnePlus 7T Pro/hotdog固定实测](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-10-gnss-qmi-loc.md)走pd-mapper/QRTR/QMI LOC，完成能力查询和会话启停；记录明确没有卫星捕获/fix。它是同SM8150的生命周期参考，不能称为已经修好GPS，更不能作为本机RF/LNA补丁来源。当前项目页面检索也没有提供本轮可验证的新RF修复。

本机Halium/GNSS HAL声明及realme/OPPO资料沿用[239研究](../kernel239/RELATED-LINUX-SOLUTIONS.md)；没有查到附带真实fix证据、可直接移植到X2 Pro原生Linux的新板级RF修复。该结论是检索范围内未找到，不是证明不存在。

## 怎样落到当前机器

原生Qualcomm链路按层核验：MPSS固件/文件服务与实际选用配置 → QRTR/QMI LOC → 同CID启动、事件注册与原始接收测量 → MM/GeoClue → 应用。只有最后两层坏时，换gpsd/补GSV/重启GeoClue才可能修复应用显示；本机在原生LOC层已是有效SNR全0/SEARCH，须继续追接收机配置、RF/时钟或接收条件。

标准启动、无SIM接口、同CID、辅助数据采用和厂商初始化差异已有多轮证据。243新增active PDC与厂商init对照，没有找到可归因的MCFG切换或明确LNA动作；开窗后仍无正CNR，随后单独关闭Wi-Fi90秒也未恢复，AGC变化未形成干扰诊断。[本机结果](README.md)因此不能简单判“只缺SUPL”，也不能判定硬件已坏。

诊断工具方面，[linux-msm/diag](https://github.com/linux-msm/diag/tree/23c12c167e93215853af4e59c021551767f6fec8)给出QRTR服务实例、传输feature和非HDLC响应格式。本机首次收到VERSION后控制peer断开，后续重连失败，尚无GNSS DIAG原始测量；工具连通问题与GNSS零CNR分别保留。源码存在可选日志mask/mode修改，不能直接全量运行daemon并把其副作用当必要RF初始化。

下一步应取得能区分“未进入正确RF路径、噪声/干扰、时钟质量、测量报告问题”的原始诊断与有依据的单变量对照。现有AP的clk/genpd/regulator文本不能替代modem内部票或板端测量。本机进一步对ldo10采栈，抓到的两次idle使能确属UFS恢复，运行DT也指向UFS vcc，已说明同名事件不能当LNA证据；未识别本机LNA接线前没有可部署的GPIO/regulator修复。

本轮源网页与协议副本保存在私有研究收据；失败抓取保留为失败。未执行网页给出的刷机命令、第三方仓库安装器或NV操作。
