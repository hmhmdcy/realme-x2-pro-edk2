# realme、OnePlus、OPPO 相关适配对照

核对日期2026-10-15。远端项目的成功记录属于其设备；本机验收单独保留。原文快照、URL、内容哈希及失败请求留在主机私有 `kernel203/related-device-sources`，未执行远端脚本、替换固件或照搬板级地址。

| 来源 | 实际找到的内容 | 对 RMX1931 的用途与限制 |
| --- | --- | --- |
| [realme X2 Pro 官方 GPL](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source)与现有 Android R 原厂派生源 | 本机19781设备树、camera与外设驱动 | 本机走线/电源/时序优先依据；Android 驱动存在不能证明主线功能完成 |
| [realme X3 pmOS](https://github.com/sm8150-linux-mainline/pmos_realme_x3) | README 列 Wi-Fi/BT 工作、suspend/resume 故障，未给 GNSS/相机完成证据 | 同 SM8150 的参考基线；README 声明仍需结合版本/源码和实机记录 |
| [OnePlus 7T Pro 主线适配](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/status.md) | 四实体镜头通过 libcamera，SLPI/传感器、IPA局部接入；GNSS和蜂窝部分完成，BT故障 | camera/SSC/电源域与服务协议可比；不是完整 GPS/蜂窝/BT 答案 |
| [OPPO 官方 SM8150 GPL](https://github.com/oppo-source/android_kernel_oppo_sm8150) | `oppo/sm8150_s_12.1_oppo_reno10` 分支；已读取通用 `sm8150.dtsi` 和 DTS Makefile | 可查原厂协议与SoC资源；本轮未取得 Reno/Ace 全功能主线实机成功证明，板级匹配尚未建立 |
| [OPPO R11T 主线项目](https://github.com/CPH1707-Mainline/oppo-r11-archlinux-sdm660-oppor11-t) | SDM660/WCN3990 Wi-Fi 适配复盘，有扫描、关联和联网记录 | 可借鉴 stock 启动时间线、QRTR/RMTFS/RFSA 诊断方法；平台不同，保留地址和老固件时序不得直接套用 |

## 已具体核对的解决办法

**相机。** OnePlus [实体长焦取帧记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-09-mainline616-camera-telephoto.md)指出补齐两个 VFE 的 `GCC_CAMERA_HF_AXI_CLK` 消费者后消除 CAMNOC disconnected-target。195已固定其 IMX471/供电和CAMNOC相关源码，见[195对照](../kernel195/README.md)。本机200已有独立四轮12帧；但本机PM8008、CCI1 master1和2.8V VANA与Hotdog PM8009/master0/弹出前摄不同。后续应对照缺失的通用CAMSS条件和sensor持久资源，不重抄整棵Hotdog DTS。

**蓝牙。** realme X3 的[内核包](https://github.com/sm8150-linux-mainline/pmaports/blob/master/device/testing/linux-realme-x3/APKBUILD)固定 `91911e069acbb9d38e5dcc633d454f7b1ff9bc4b`/6.12-rc7。该提交[板级DTS](https://github.com/sm8150-linux-mainline/linux/blob/91911e069acbb9d38e5dcc633d454f7b1ff9bc4b/arch/arm64/boot/dts/qcom/sm8150-realme-x3.dts)使用 uart13、WCN3990、3.2Mbps和与本机相同名字的四路供电，另有 sleep pinctrl 与 GPIO46 RX 唤醒中断。本机板级UART只有default状态，构成下一步可验证的PM差异；尚不能将其定为189 phase5重组错误的根因。其[固件包](https://github.com/sm8150-linux-mainline/pmaports/blob/master/device/testing/firmware-realme-x3/APKBUILD)安装01系列固件，本机使用原机21系列，不能只按文件名替换；不下载或复制外机NVM。新旧 hci_qca 源码也已留作对照。

**GPS。** Hotdog 的[QMI LOC记录](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-10-gnss-qmi-loc.md)仅证明会话与代理保留客户端，明确没有卫星获取；后续状态仍是 Partial。本机已经走通 MM→GeoClue、推进NMEA时间及自动辅助刷新，真实fix/CNR仍0；重复更换桥接服务缺乏依据。下一步核对本机 RF/固件接收条件和原厂启动合约，保持真实接收验收独立。

205补查了[GNSS专门对照](../kernel205/GNSS-RELATED-DEVICES.md)：一加6的辅助数据/固件版本/运营商配置报告、X2 Pro与一加SM8150 Android配置的唯一LPP差异，以及仅GT2 Pro验证的跨品牌L5 NV项目。新增线索尚未形成X2 Pro真实定位修复。

**传感器。** Hotdog [固件版本对照](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-23-the-firmware-version-was-the-cause.md)定位到适配的OOS10 SLPI版本和私有设备registry；其源说明传感器数量随固件组合变化。本机187选A.11已取得独立数据。可比较FastRPC堆、文件服务、项目身份和启动门控，不能把对方19801身份或per-unit校准复制到本机19781，也不能凭SensorProxy Has标志宣布物理精度通过。

**蜂窝。** Hotdog [pre-online gate](https://github.com/Sr-0w/hotdog-linux-bringup/blob/main/docs/evidence/2026-08-25-modemmanager-preonline-gate.md)修复PDC/MCFG准备前被D-Bus偷偷拉起MM的竞态；其实际注册、LTE数据、SMS/通话仍未完成。可先只读检查本机PDC配置和启动先后；不直接停掉当前可用GNSS后端或选择/激活外机MCFG。SIM-missing/no-atr不能反推物理未插卡。

**Wi-Fi/共享服务。** OPPO R11T [复盘](https://github.com/CPH1707-Mainline/oppo-r11-archlinux-sdm660-oppor11-t/blob/main/OPPO_R11T_WIFI_MAINLINE_BRINGUP.md)把缺少 RFSA shared-memory discovery 定为原故障核心，并修正 QRTR 重播、RMTFS IOVEC和TQFTP路径处理。本机WCN3990已能联网，不据此增加无证据服务或修改reserved-memory；用于后续复现失败时对照原厂协议。当前203 USB大传输停顿与Wi-Fi PM问题仍分别记录。

本轮搜索未找到可直接证明 RMX1931 全部目标外设完成的公开主线方案；这限定本轮已核对范围，不表示不存在其它实现。
