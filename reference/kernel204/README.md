# 204：补齐蓝牙 UART RX 唤醒与休眠引脚

2026-10-15。完整外设goal active。新增候选已在boot中部署，Image183/logdump183、全部模块、MM191/helper202、Mesa149/UCM173保持；本轮仅刷boot一次，第二轮为同一boot镜像普通重启。第二轮自动启动状态的最终记录另列于收据，不把第一轮失败改成成功。

## 依据和改动

203找到realme X3固定91911e…/6.12rc7的同平台参考，204实机确认现有UART13只有主中断、无sleep状态，GENI未暴露`power/wakeup`。本机原厂19781也给UART配置GPIO46作为RX唤醒源；主线SM8150 PDC映射GPIO46→50，GENI支持第二中断并注册dedicated wake IRQ。[现场对照](uart-current-validation.json)、[相关机型来源](../kernel203/RELATED-DEVICES.md)

[DTS补丁](samurai-bluetooth-rx-wakeup.patch)保留现有default、21系列原机固件、3.2Mbps和四路供电，增加GPIO46下降沿唤醒及两组sleep状态：CTS/RTS下拉、TX/RX上拉，均GPIO功能/2mA。没有按外机包替换NVM或固件。

完整修改后板级DTS编译通过。为保持现有boot200全部phandle及其它资源，部署DTB从已验证的四域静态DTB生成，仅改变UART四项属性、新增两个sleep节点；源码与产物的UART资源一致，CAMSS四域与其余属性逐项保持。[候选](uart-candidate-validation.json)、[GENI绑定](uart-schema-validation.json)

EDK2重新构建并解析FV/FFS/gzip/LZMA，确认仅DTB模块变化，所有固件代码、bootshim/ramdisk/header/compat及boot尾部保持，旧有30条诊断无新模板。boot镜像100663296字节，SHA cdd16e29…，DTB b9d9c2a1…；回退为boot200 5109097b…，继续配CAMSS82cbc052…。[构建](build-package-validation.json)

首次切换前以当前身份、分区/NV/784文件模块树、空闲GPS/helper和资源排空核验，处理了APK采用后MM加载inode的`(deleted)`路径，以内容SHA核对。F2FS冻结并仅发一次RESTART2；EUD断线前观察到冻结/验证收据，最终console收据未到，但fresh fastboot身份/product/几何确认后仅刷boot一次并reboot。未因SSH断线重发切换。[刷写](flash-validation.json)

## 第一轮实机结果与失败

新启动读回boot204、logdump183/persist/NV及模块树通过；UART已注册`power/wakeup=enabled`，sleep属性存在，CAMSS正常自动绑定。GNSS/helper由签名APK自动启动，时钟未同步重试后第8次准备成功；早期75秒观察窗口超时原件保留，服务未重启，仍Power1/GPS0。[启动](runtime-validation.json)

启动仍出现一次`phase=5 baud=3200000 chunk=13 partial=0 first=ff`重组错误，和189同型。**补齐RX wake没有修复该启动错误。** 不能把它与185已修复的phase2前导NUL混为一项。

首次蓝牙测试脚本在未上电时写Discoverable，收到`Not Powered`，尚未扫描/休眠，清理恢复成功。修正前置步骤后，在独立r2目录执行一次扫描/休眠/扫描：前9设备、实际驻留45.1438秒、success+1/fail0/RTC IRQ+1；醒后仍开启且13设备，扫描结束关闭。11项故障增量0、taint0、原模块build-id/脉冲计数保持；配置逐字恢复、既有配对密钥保持，无配对/连接/振动操作。[PM与扫描](bluetooth-pm-validation.json)

该PM由RTC唤醒，只证明RX wake配置存在且此负载休眠恢复通过，**未证明外部蓝牙事件经GPIO46唤醒**；SLPI因另一个启动失败而offline，本次也不能当成传感器并行PM验收。

本轮SSC在启动20秒文件服务就绪检查失败，清理后SLPI offline、供电关闭；boot日志确认`File server exited`，没有SLPI fatal/WARN/Oops。未在该boot重新启动SLPI。已保存RAM状态/日志并补充daemon退出码、ownership及SLPI状态记录，源码9a1fd03f…；这是观测改动，不能称修复已知根因。[观测部署](ssc-observation-validation.json)

第一轮468文件私有归档及逐成员核对通过，包含失败、蓝牙配置/密钥备份、NMEA服务状态与RAM SSC日志，不公开端点、身份或归档指纹。[归档](first-boot-archive-validation.json)

## 第二次普通启动与最终现场

第二次按fresh当前身份、完整排空/私有归档/F2FS冻结后单次RESTART2及fresh fastboot确认，只发普通reboot，无flash。候选boot204读回保持，RX wake/sleep和CAMSS四域自动接入；130.77秒已见三个DSP running、UTC第3次自动准备成功、所列故障0。[第二次启动](reboot-r2/runtime-validation.json)

第二次SSC自动启动的加速度readiness54条、光线10条均正常disable，SensorProxy三Has true；没有readiness_failure记录。该恢复不能证明新增退出状态记录修复了首次故障，根因仍待复现。

早期final-health错误假定空闲新boot仍持有辅助数据而停止；独立只读查询确认窗口315964800/0小时。随后首次UID10000桌面GNSS-only运行182.40秒，188条不同NMEA、176个推进GGA时间、9条GSV，checksum0；自动1次下载/1次注入后1792054800/168小时，并独立复核。fix/正CNR/位置事件仍0。[首次会话与自动刷新](reboot-r2/geoclue-first-session-validation.json)

会话返回时报告清理成功，稍后再次出现已知晚到Signals=true/rate0，GPS仍0且GeoClue bus已无owner；原状态保留，随后恢复测试前false/30。这不是GNSS真实定位通过，也没有将恢复动作伪装成始终保持。初次错误假设、两份未完成final-health和导出缺少收据的失败保留。[最终健康](reboot-r2/native-health-validation.json)

最后610.72秒taint0，WARNING/Oops/GPU/SLPI fatal/BT重组全boot0；三个DSP、SensorProxy、Wi-Fi正常；MM Power1/failed原因2/bearer0、GPS0/Signalsfalse/rate30；helper准备3/完成3、数据worker1/完成1、idle。五APK payload及分区/NV/784模块通过。当前没有新增相机帧，第一轮BT/SSC失败未改成通过。

第二轮441文件已私有归档并逐成员校验；当前管理入口为`reference/kernel204/reboot-r2/host.py`，当前boot guard在手机`k204r2-runtime/boot-id-private.txt`。kernel204主host属于首轮旧boot，勿沿用。[归档](reboot-r2/archive-validation.json)

内核代码子集/Image/config/符号/模块顺序保持，board DTS439db943…已编译为私有候选；旧canonical DTB22c1f2ad…未覆盖。部署稳定phandle DTB是b9d9c2a1…，不能混淆。Python/shell语法和内核diff检查通过。[源码收据](source-final-validation.json)

## 后续范围

继续定位启动phase5错误、SSC偶发启动退出及Wi-Fi/USB恢复；GNSS真实fix/正CNR、相机常态sensor资源/用户态/PLDO输入与冷启动、蜂窝真实业务、传感器物理精度/长期与FastRPC SSR等仍未完成。旧rootfs132未更新，不能把此boot镜像当成完整发行镜像。
