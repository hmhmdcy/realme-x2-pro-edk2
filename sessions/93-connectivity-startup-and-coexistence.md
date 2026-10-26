# 连接启动与 Wi-Fi/蓝牙共存（2026-10-11，session93）

本轮延续全硬件目标。用户最新范围为蓝牙只扫描、不配对或连接；NFC先验证控制器。

## 部署与审计

Linux构建号#92，逻辑阶段93。相对#91，配置不变，CPIO只有 `usr/sbin/samurai-wifi` 的4个显式失败返回改变；既有文件、身份、权限与308链接保留。DTB只新增UART13 bluetooth `firmware-name = "crnv21.bin", "crbtfw21.tlv"`，使用原机文件，没有替换其它机型固件或改变电压。

EDK2 FV 101个模块只改变DTB原始节，其它执行字节、BootShim、兼容DTB、命令行和Android头（除长度/digest）保留。仅boot/logdump刷写；完整原分区和连接现场保存私人目录。F1后初次fastboot枚举过早为空，未执行写入；等独立枚举后重新使用新输出前缀，验证产品与两个分区尺寸后成功写入。

| 产物 | SHA256 |
|---|---|
| Image #92 | `f0a38e19b70d59da8ed3114c7935cc1e453b3239a03f8bd4a9802a7a8549cb7d` |
| DTB | `adff4c2fc1105a3c629f463d8e96a1dfd28c653b5a1dc75de2b8c8754219aca4` |
| CPIO | `cc66291e15321fa864c1882ad342e18061fafe235567d0f5fc17f1e228afab6e` |
| boot | `0974aafc6938726bb24f1bd92b11955bfffe824c3e0c27fa3e97029765fb5158` |
| logdump | `7905d198f229f44cfd279d14f044bf659b050be0baa02a3d1a5d67c135f9c4ee` |
| 完整boot回滚 | `cd75317e7384dd65463982134fd9a9ffdd35cb1f21f06a337824683c18636f48` |
| 完整logdump回滚 | `7972dae9d5f3c709fd41f8b0e577417e1f6278930afa04762bae70dbb85ace86` |
| 首次启动失败现场 | `d3d38a012c8d7a97fad645ed78fd70eb52e07f9399c208d205b54efb9143ab82` |

## 实际启动结果

新Wi-Fi等待逻辑不再对空分区执行mount，原机固件与6个NV RAM副本校验成功，RMTFS/TFTP服务注册。首次MPSS约118秒启动，158秒fatal，恢复禁用，未出现RMTFS/TFTP请求或WLFW/wlan0。taint仍0；这与此前间歇40秒失败一致，不能称Wi-Fi自动启动可靠。

蓝牙确实从真实revision-21文件名加载，但首次两次TLV下载超时，第三次在约115秒setup completed。临时地址仍仅配置在RAM；出厂地址未接入。NFC控制器在新内核再次通过GET_DEVICE、DEV_UP、powered=1、DEV_DOWN，没有RF/tag/eSE/升级操作。

先封存失败现场，再关闭BT、解绑ath10k、stop/start MPSS，保持已验证的RAM服务与原NV不变。受控重试成功出现wlan0，2.4GHz认证/DHCP通过并稳定超过45秒。首次失败的根因尚未证明，BT时序只是隔离变量，不把相关性当因果。

随后重新开启蓝牙和BR/LE联合扫描，45个两秒样本均显示MPSS running、WPA COMPLETED、taint0。扫描产生11个不同 address/type 发现事件，其中BR/EDR 1、LE public 3、LE random 7，具名事件3；身份和名称仅留私人日志，没有配对或连接。

蓝牙扫描期间，Wi-Fi双向各4MiB TCP通过，手机/宿主均绑定WLAN地址，双方校验相同。6个原NV哈希在90秒观测后仍一致。这个有界共存结果不覆盖开机、休眠或长期运行。

| 共存流量 | SHA256 |
|---|---|
| 手机发送 / 宿主接收 4MiB | `65f77025a95f09749f7f624cbea45752fbec271597051a9cfb50416b1d5f745e` |
| 宿主发送 / 手机接收 4MiB | `9e6f8c085eca078993e3018edbf3bb13cffe204278c2e926c5b15787004e2915` |

5GHz实际5180MHz通过WPA2/CCMP、DHCP、网关、DNS、HTTP及双向各4MiB TCP，双方哈希一致；公网ICMP仍失败。第一次修改freq_list后select当前network不会自动断开，仍保持2462，已停止该无效尝试并保留输出。显式reassociate后才发生真实5GHz认证。切换时旧密钥移除-110和regulatory downgrade仍存在，吞吐/宽信道、长期与休眠未验收。

| 5GHz流量 | SHA256 |
|---|---|
| 手机发送 / 宿主接收 4MiB | `1018012774d8faf94357238d08f057611359c8a1a48243046c5fe155cf77bf36` |
| 宿主发送 / 手机接收 4MiB | `f913ba1673611933ab21dc26a37230eb603b7be72c978386fb33544a15750686` |

最终检查还发现当前DRM回归：约87秒继承INTF1帧停滞，CTL0 top/layers/intf/dsc与此前相同，但清理返回-22，KMS/panel绑定失败，当前没有DRM或fb0。CPIO/配置/显示源码字节未变，不能据此称显示保留成功。首次BT固件重试显著延迟probe，时序关系待验证；不直接忽略显示错误或删除保护。完整dmesg已保存。

最终私人checkpoint-final.tar SHA256 `b96c71dbb8e24c90b1f542f6525781a579e5336d8136bde38cb1abf6fb964037`；48个文件哈希、实际boot/logdump读回、两个频段的流量哈希、共存45样本、NFC和BT扫描检查通过。检查明确标记首次MPSS失败、BT首次重试和DRM未注册；通过表示证据校验，不表示全硬件目标完成。最初checkpoint.tar误打包了残留的部分目录，验证因缺少SHA256SUMS拒绝；错误归档保留，最终修正包独立命名并通过完整校验。

## 后续

优先定位首次MPSS启动40秒fatal、蓝牙TLV重试和显示CTL接管失败，收集GLINK/RPMSG/QRTR与显示启动边界，不盲加无限重试或绕过保护。两个Wi-Fi频段已获得数据通路证据，继续启动可靠性、出厂蓝牙地址及长期验证。用户蓝牙仍只扫描，NFC仍只控制器；其它硬件、显示和充电待办保留，完整目标未完成。

私人目录 `E:/edk2-samurai-out/kernel93`。完整日志/固件/可执行程序、PSK、地址和身份不发布。自有诊断脚本在reference/kernel93；含一次性守卫的构建与刷写脚本不可重放。
