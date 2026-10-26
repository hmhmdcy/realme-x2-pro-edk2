# GNSS RF/OEM只读研究补充

本轮授权子代理继续对比realme/OPPO/OnePlus及现有stock来源，没有发现足以指定X2 Pro LNA GPIO、独立GNSS电源或可直接移植RF修复的证据。用户无SIM，不影响独立卫星接收；226的四轮零CNR、HIGH读回及XTRA被采用的证据保持。

固定stock提交`23172a15…`的[19781 MPSS节点](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/arch/arm64/boot/dts/19781/sm8150.dtsi#L1709)使用RPMH_CXO_CLK、CX/MSS代理资源、modem固件及10秒proxy timeout；本地主线SM8150已有同方向资源。主线PAS handover会撤XO/proxy票，不能凭clk_summary prepare0就断言物理XO关闭。[通用GNSS UART注释](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/arch/arm64/boot/dts/19781/sm8150-qupv3.dtsi#L395)没有证明本机LNA走线。

固定社区vendor提交`77f9b7aa…`的[GNSS HAL rc](https://github.com/HyperTeam/proprietary_vendor_realme_samurai/blob/77f9b7aa9445e268d406317bf98db8d6a696a9a9/proprietary/vendor/etc/init/android.hardware.gnss%402.1-service-qti.rc)只有进程与权限，未见GPIO/regulator/clock动作；[天线配置](https://github.com/HyperTeam/proprietary_vendor_realme_samurai/blob/77f9b7aa9445e268d406317bf98db8d6a696a9a9/proprietary/vendor/etc/gnss_antenna_info.conf)属于相位中心/测量增益校正元数据，不能当LNA开关。该仓库[ODM izat配置](https://github.com/HyperTeam/proprietary_vendor_realme_samurai/blob/77f9b7aa9445e268d406317bf98db8d6a696a9a9/proprietary/odm/etc/izat.conf)禁用lowi/xtwifi/slim/DR而保留xtra；这是社区保留文件，不能替代本机原厂运行证据，也不支持“启动全部Android服务即可修RF”。

本轮核对时Hotdog的[GNSS仍为Partial](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/status.md)，[proxy域修复](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-19-proxy-power-domains.md)针对首次suspend的modem watchdog，不是搜星零CNR的已证修复。本机226四轮没有相同故障签名，不据此改电源票。

后续串行区分动作：先审已有TFTP/RMTFS请求日志中的缺失/权限/短读/越界和服务重启；有具体缺失路径才研究修复。下次有信息增量的接收会话同步采集前/中/后的clock/regulator/genpd及文件服务错误，并保留SV/PQWM1；不写寄存器或盲目强持票。已有可用Android启动路径或开阔天空对照可明显缩小范围，但不为对照刷机。PQWM1 xo_state11的语义仍不充分，不标为锁定或失锁。
