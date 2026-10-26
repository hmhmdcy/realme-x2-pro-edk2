# GNSS 初始化对照：尚无新的可部署 RF 修复

2026-10-16，已授权只读子代理继续核对，主线程本轮没有操作GNSS。此前221配置读取、226四轮同CID/全事件/aiding试验、228 OEM资源及231文件服务审计的结论保持：有效raw CNR零、SEARCH、无TRACK/fix。

[公开SM8150 GnssAdapter固定57ced1d](https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/57ced1dc07cd15aaedbee0f98a3384ac837c4ce5/gnss/GnssAdapter.cpp#2571)的engine-up包含setConfig、SV配置、平台power通知、secondary-band、CDFW和恢复会话。setConfig包括GPS-lock/SUPL/LPP/LPPE/NMEA、CTU/PACE及sensor参数，没有在这条链发现明确板级LNA/GPIO/regulator开关。该公开版本是2024合并后的代码，不能直接等同本机Android10 vendor。

[Qualcomm SDK固定a581b6c](https://github.com/qualcomm-linux/location-apis-qcom/blob/a581b6c9ee15e3fdbb0e15f43cd37b97616b0948/loc_api/loc_api_v02/LocApiV02.cpp#L399)有master注册、feature/measurement配置和平台电源接口，但没有找到它们是本机standalone必需或会解释全零CNR的证据。不能把接口存在或名称含clock estimator视为RF时钟漏开。

[Surface Duo固定源码树](https://github.com/agentsco-lab/surfaceduo-droidian/tree/7cb53ddca60590b1f44c402d1b5bfd333b44fa66)的真fix使用原Android11 vendor HAL，未公开其GNSS HAL源码/设备配置。GeoClue只展示HAL入口，不能还原其内部比当前QMI多做了哪些初始化。此前一加gps.conf 39项对比仅LPP_PROFILE不同，也无证据解释本机全部零CNR。

最具体的剩余证据缺口是本机匹配版本vendor GNSS二进制、rc、配置和实际调用对应。下一步只读核已有vendor镜像的GNSS service rc、gps.conf/izat.conf/sap.conf、ELF DT_NEEDED与版本字符串，不执行这些二进制。发现明确资源/缺失依赖后才形成实验；本轮没有这样的阳性证据，不增加SET、伪服务、MEMSHARE盲分配或供电票。
