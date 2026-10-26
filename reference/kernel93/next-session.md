# 下一阶段：连接与显示启动稳定性（session93）

继续完整 Realme X2 Pro Linux 全硬件目标，优先 Wi-Fi、蓝牙和 NFC。用户最新范围：蓝牙只扫描附近设备，暂不配对/连接；NFC 无标签，先验证控制器。充电阶段收尾；显示、充电和其它硬件未解决项保留。

先读 sessions/91–93、reference/kernel92–93，并检查私人 kernel93 当前现场。不能重放历史固定守卫。

当前已刷逻辑阶段93的 Linux #92，仅boot/logdump。2.4GHz和5GHz（5180MHz）WPA2、DHCP、网关、DNS、HTTP及双向各4MiB TCP校验通过；公网ICMP失败。蓝牙扫描期间2.4GHz双向流量与90秒/45样本共存通过。密码仅存私人派生PSK配置，不能写入公开文件或内核。

蓝牙 UART13/hci0、实际 SOC/ROM版本已读取；原机revision-21固件的RAM加载和扫描通过，#92标准firmware-name双字符串直接选择原文件。#92首次加载两次TLV超时后第三次成功，启动可靠性仍待修复。NVM默认地址需配置，扫描用RAM临时测试地址；出厂地址接入未完成。用户暂不连接，不能自行恢复配对测试。

NFC I2C9 / GPIO36 VEN / GPIO47 IRQ / GPIO48 FW 注册；实际GET_DEVICE、DEV_UP（NCI初始化）、powered=1、DEV_DOWN和三轮重复通过，#92也重复通过。RF/tag/eSE/固件更新未测试，GPIO113时钟请求与实物读卡仍待办。

#91发现Wi-Fi resolve在条件上下文中失去set-e，UFS缺失时把空分区名当成功；#92加入4个显式return1。#92不再空分区挂载，但首次MPSS启动40秒fatal，无RMTFS/TFTP请求/WLFW，未产生wlan0。失败现场已封存。关闭BT、解绑ath10k再stop/start MPSS的受控RAM重试成功，随后两个频段网络及共存通过；首次启动根因未证明。

当前显示回归：继承INTF1在约87秒帧停滞，CTL0 reset返回-22，KMS/panel绑定失败，DRM/fb0未注册；显示源码/配置未改变。不能把连接通过当完整保留成功，也不能忽略reset错误绕过SMMU切换保护。优先恢复显示并协调BT早期固件初始化与MPSS；可调查将HCI UART模块按就绪条件加载，需先审计依赖并实测，不永久关闭蓝牙。

1. 重新确认启动标识、Linux版本、MPSS/wlan0状态，保存dmesg、DRM/display/pstore、QRTR、私人retry/coexistence日志与NV校验。
2. 优先解决首次MPSS、BT初始化和显示CTL接管；验证冷/暖启动、失败路径和服务退出，不隐藏fatal或盲加无限重试。BT关闭启动与Wi-Fi稳定后BT开启已有对比；6个NV仅RAM COW。
3. 保留两频段网络与共存结果，做启动、宽信道/吞吐、休眠与长期回归；没有匹配证据时不改TX、国家码或校准数据。
4. 蓝牙仅扫描，后续接入工厂地址；NFC保持控制器范围。保留全部其它硬件目标。
5. 修复后重新审计真实EDK2内嵌DTB、CPIO文件/模式/308链接、配置、FV模块与镜像。每次新备份boot/logdump、保存现场和建立守卫，F1后等待独立fastboot枚举，finally释放EUD。

93 Image SHA256=f0a38e19b70d59da8ed3114c7935cc1e453b3239a03f8bd4a9802a7a8549cb7d；DTB=adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4。
boot=0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158；logdump=7905d198f229f44cfd279d14f044bf659b050be0baa02a3d1a5d67c135f9c4ee。
详细设备身份和当前boot ID保留私人证据；阶段号与uname构建号分别描述。
最终checkpoint-final.tar=b96c71dbb8e24c90b1f542f6525781a579e5336d8136bde38cb1abf6fb964037，48文件及网络/共存/NFC/扫描/分区读回检查通过，明确保留MPSS首次失败、BT重试与DRM缺失。

Linux /home/cy122/x2pro-linux/linux；initramfs /home/cy122/x2pro-linux/initramfs；EDK2 /home/cy122/edk2-samurai/repo；私人 E:/edk2-samurai-out/kernel91、kernel92、kernel93。
公开仅自有源码/patch/脱敏摘要/docs；固件、二进制、完整日志、地址、凭据和SSH身份不入Git。本轮无提交/推送，其它线程rootfs工作保留。
只有boot/logdump在刷写授权范围。Android、userdata、GPT、NV、persist均保留。UART/NFC依据本机证据，不照搬其它机型VEN/rail/校准。
充电不写配置/解封/NVM/OTP/FET/OTG/GPIO/MCU，不跑旧OEM探针，不用I2C_FORCE。历史85–88显示快照不清空/重武装；taint0不能证明显示修复。
