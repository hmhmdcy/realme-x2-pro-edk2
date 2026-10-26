# 346：原厂 EV／FPS 动态曝光表

2026-10-20。完整恢复原厂 `UpdateEVKnee` 与 `ApplyActiveTableEVFPSKnees`，在345通用曝光表数学上加入活动表生成。224张来源表按表和策略去重为59组，主机与AArch64各2515项、368836字节，全部拐点、FPS/EV拐点及索引偏移与保留原指令零差。[结果](active-program-validation.json)。

已沿 `OnExposureCompChange`、DataManager虚表及ELF RELR重定位确认额外策略标志来自 `getHDR3Enable()`，没有按字段位置猜作普通HDR或其它开关。[身份](hdr3-policy-binding-validation.json)。正EV在普通路径可提高增益，HDR3路径保留FPS增益；负EV不会简单截短整个活动表。FPS截短后仍可能追加同时间增益段，以恢复原表最大增益。

通用实现位于 [aec_exposure_table.cpp](libipa/aec_exposure_table.cpp)，尚未接入IPA或安装。调用者仍负责EV表调整开关、真实传感器行/帧限制及防频闪。原指令离线运行；powf/log10/exp2、memcpy和日志使用明确桩，没有启动Android加载器或原厂服务。本阶段未改变手机状态；344默认四摄私有校准及342 r27/r22保持。

用户现已开灯，但没有色卡，要求继续从原厂刷机包提取数据。后续优先复用已解包BIN/算法库，提取尚未接入的Gamma等调校；工厂通用IQ与EEPROM/OTP个体数据分别处理。正常场景可验证链路和收敛，不能据此宣称绝对色彩精度。完整多摄/ISP目标仍active。
