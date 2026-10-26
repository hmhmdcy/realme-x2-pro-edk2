# 203：GNSS/MM 签名软件包落地与相关机型对照

2026-10-15。完整外设 goal active。阶段203在202第二次启动内完成，未重启、刷分区或切换modem电源。当前组合仍是boot200/四域CAMSS、Image183/logdump183、modules132覆盖185/189、Mesa149/UCM173。

MM191补丁与helper202现已由APK管理。本轮没有改变已验证的daemon/helper代码；两次构建、签名验证、安装后逐文件校验和真实桌面GNSS-only会话通过。**真实fix、正CNR和坐标事件仍为0；离线rootfs132尚未更新。**

## 源码与软件包

规范源在[linux-port/packages](../../linux-port/packages/README.md)，MM提交/补丁/哈希固定在[source-lock](../../linux-port/packages/modemmanager/source-lock.json)。从原191固定源码在隔离SDK中clean rebuild，raw与处理后的候选均逐字匹配191；没有把未知已安装文件直接当构建输入。[重编译收据](mm-clean-rebuild-validation.json)

官方三个r0 APK的签名/内容固定后，仅替换main包daemon，另外133个文件及插件、mmcli、policy、init、udev保持原内容。三个MM包改为`1.25.95_git20261005-r1`，libmm-glib保持r0；helper/stack为`0.1.0-r0`。stack精确依赖验证过的组合。helper/init仍为42168f33…/54b81745…。[官方输入](upstream-package-validation.json)

APKv3、固定epoch/所有者/模式、deflate9构建五个签名APK；两次独立构建与签名索引逐字相同。签名未知与payload篡改均被拒绝。初始DrvFS提取模式问题和两个失败构建保留私人日志，最终改在Linux文件系统构建；最终有效产物为主机`kernel203/packages-2`和`packages-3`。[构建](package-build-validation.json)、[仓库](repository-validation.json)

私钥仅保留WSL主机私有目录，未进手机、镜像或源码。手机持有公开验签密钥和`/var/lib/samurai/packages/gnss-203`签名仓库，配置于`/etc/apk/repositories.d/50-samurai-gnss.list`。安装前保存APK DB/world/旧文件并模拟solver，实际仅一次事务升级3包/新增2包，所有payload字节与模式一致。[预检](package-preflight-validation.json)、[安装](package-install-validation.json)

MM进程未重启，原已加载inode被APK替换后显示`(deleted)`，但`/proc/PID/exe`内容仍精确为b350c55b…。后续quiesce必须以内容哈希核对，旧路径字符串相等检查不再适用。安装钩子只启用runlevel；随后显式重启helper、等待空闲UTC准备完成，MM owner未变化。[已装服务](packaged-helper-validation.json)

## 实机结果

UID10000真实Phosh会话、独立DesktopId、其它定位源关闭的GNSS-only测试运行约63秒：68条不同NMEA、59个推进GGA时间、6条GSV，checksum错误0；fix/正CNR/坐标事件仍0。辅助数据已有效，自动worker只检查并跳过下载/注入；UTC ACK/完成与QMI client清理均通过。桌面开关恢复false，临时policy/DesktopId/程序移除，原GeoClue配置逐字保持。[桌面验收](geoclue-package-validation.json)

最终健康观测4039.43秒，仍为202第二次boot：taint0，WARNING/Oops/GPU/SLPI fatal/BT重组均0；ADSP/SLPI/modem running，SensorProxy三个Has true。MM Power1、State−1/原因2、bearer0；GPS0/Signalsfalse/rate30。helper重启后准备1/完成1、数据worker1/完成1、idle。独立查询辅助窗口1792047600/168小时保持。分区/NV/784模块及原userspace清单保持，CAMSS四域绑定且无临时camera资源。[健康](native-health-validation.json)

健康原始记录沿用了202的`same_verified_new_boot`字段名；公开收据改成`same_verified_current_boot`，同时明确`new_reboot_not_performed`，私人原件保留。没有新增相机帧或BT扫描，200的12帧/10设备属于历史验收。

USB下载候选时停顿，残缺文件保留且未采用。严格原公钥Wi-Fi确认同一boot后取得完整候选和产物；最终USB/Wi-Fi小命令均响应，未reset/unbind/reboot。此恢复不能证明USB大传输稳定性已修复。[传输](transport-validation.json)

手机226份文件已私有归档并经主机逐成员哈希校验；包含安装前备份、配置/DB、原始NMEA及当前服务证据，不公开设备身份、端点、坐标或归档指纹。[归档](archive-validation.json)

## 相关机型与后续

用户要求补查realme/一加/OPPO，已核对[具体来源、做法与适用限制](RELATED-DEVICES.md)。新增有用线索是realme X3同平台BT的UART sleep/RX wake配置；OnePlus可参考CAMSS/SLPI和PDC启动竞态，但其GPS/蜂窝仍部分完成、BT仍故障；OPPO官方SM8150 GPL可作原厂对照，R11T复盘提供不同平台的RFSA/共享服务诊断方法。

后续回到真实硬件缺口：先只读核对本机UART唤醒/IBS与189 phase5证据、PDC状态/原厂启动合约，再选择有证据的修复；继续GNSS真实接收条件、相机常态sensor图/用户态、PLDO输入和冷启动、蜂窝真实业务及传感器/USB/Wi-Fi稳定性。不能凭外机声明替代本机验收，勿复制外机NVM、校准、MCFG或未知电源连接。
