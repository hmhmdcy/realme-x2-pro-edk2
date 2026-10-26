# Samurai SSC 用户态兼容层

原厂00121 SLPI将Sensortek光线实例发布为`wise_light`。libssc 0.4.4默认请求`ambient_light`，因此标准光线客户端枚举失败。设备配置[iio-sensor-proxy.conf](iio-sensor-proxy.conf)配合[补丁](../../reference/kernel184/libssc-wise-light.patch)选择同协议的OEM类型；其它设备保持默认名称。

补丁已在本机编译并通过原装ssccli及SensorProxy D-Bus实测：[184证据](../../reference/kernel184/README.md)。同一候选库的默认名称返回254且无测量，指定OEM名称收到41条测量并正常停止；SensorProxy报告HasAmbientLight和HasProximity，ClaimLight/ReleaseLight及正常退出通过。

187使用同机型A.11 SLPI后，原始加速度204、陀螺仪202、磁力计197样本及五种标准CLI流通过，SensorProxy同时报告加速度/光线/接近；光照观测0至2 lux，未验证亮暗响应或精度。[187](../../reference/kernel187/README.md)

188的[samurai-ssc.py](samurai-ssc.py)、[OpenRC服务](samurai-ssc.initd)及[SensorProxy依赖](iio-sensor-proxy.initd)已做实际开机验证：只写本机配置/校准的私有RAM副本，固定文件服务维持到DSP先停，核验进程身份才发送TERM，每boot只允许一次启动；等待真实加速度/光线测量后启动SensorProxy。兼容库使用独立目录，不替换系统包。实际active本地Wayland会话UID10000三项Claim/Release通过，原Polkit策略保持。

**188自动部署因休眠恢复SLPI frpc_dsp fatal而回退。** 这是188当时的现场，原失败仍保留。[完整188证据与回退](../../reference/kernel188/README.md)

189加入[FastRPC freezer等待补丁](../../reference/kernel189/fastrpc-freezer-wait.patch)，同ABI模块与自动服务重新部署，实际加载build-id已核对。连续三轮完整s2idle实际驻留45.2至45.3秒，醒后四类标准CLI流及SensorProxy正常，原daemon身份保持；实际active Wayland用户在三轮之后再次Claim/Release成功。[189实测](../../reference/kernel189/README.md)。当前SLPI/文件服务/SensorProxy运行，A.11独立路径供电开启，原固件文件、系统库及APK数据库保留。

传感器这三轮通过不代表整机PM完成：第二轮Wi-Fi在35秒窗内未关联，189当时的boot还有一条3.2Mbps/phase5/firstff的蓝牙启动错误。普通信号重试、freezer竞态审查、stop/start共享池−22及SSR仍开放，服务保持每boot一次启动门控。

228已部署并实测FastRPC完整发布、端点owner与模块保活修复：refcount1→2→1、五类SSC流和活动Wayland用户Claim/Release通过。230真正树内模块已受控新启动并核验，taint0；五路真实取流和活动Wayland三项Claim/Release再验通过。[230](../../reference/kernel230/README.md)。[完整源码/补丁/锁](kernel/README.md)、[228实测](../../reference/kernel228/README.md)。

完整启用仍需修复FastRPC/SLPI停启与PM、补人工运动/方向/光照准确度及长稳，再将兼容库、同机型固件来源和服务纳入可复现rootfs包。安装配置中的本机只读来源/校准清单属于私人部署数据，不公开打包。
