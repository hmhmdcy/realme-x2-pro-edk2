# kernel101：ADSP原生版本回复与无线基线

2026-10-11，Linux #100已真实刷入boot/logdump，ADSP自动运行并通过AFE API7/ASM API2回复，尚无ALSA卡。用户暂缓振动物理确认，继续音频；当前5GHz经一次有界手动恢复可用，首次MPSS40秒fatal、2.4GHz新增reason7未解决，蓝牙关闭、不配对连接。

见 [session101](../../sessions/101-adsp-native-apr-reply-and-radio-regression.md)、[下一阶段](next-session.md)。最终113文件checkpoint `e3f24622bbebe7de770fc9b0eeca136fffa9ba658a8520b9c3ebfd430a7c2354`；所有原包/清单/读回/6NV/persist校验通过。

| 文件 | 用途 |
|---|---|
| collect-audio-preflight.sh、verify-preflight.py | 本机只读vendor/modem预检、固件跨度与内存校验，固件仅私人 |
| prepare-adsp.py、build-adsp.sh、audit-kernel.py | ADSP/APR DTS、配置、CPIO新增项与原文件保持审计 |
| samurai-modem-remoteproc、samurai-wifi、samurai-radio-address | 按唯一真实设备身份定位MPSS，不依赖remoteproc编号 |
| prepare-core-query.py、q6core-samurai-query.patch | 本机只读、实际回复支撑的原生版本查询与解析长度检查 |
| build-firmware.sh、verify-firmware.py、prepare-package.py | 真正重建EDK2嵌入DTB、FFS/FV/boot及FAT审计 |
| collect-preflash.sh、split-backups.sh、receive-backups.ps1、flash-adsp.ps1 | 新现场/完整备份/分块SHA/F1后独立fastboot及只刷boot/logdump |
| collect-audio-runtime.sh、verify-audio-runtime.py | 实际DSP/原生回复/空声卡/部署读回、原NV/persist |
| collect-boot-failure.sh、recover-after-mpss-crash.sh | 保留首轮失败，ADSP持续运行下单次恢复MPSS |
| test-recovered-network-retry1.sh、test-gateway-followup.sh | 私有5GHz认证/网络及首轮丢包后有界网关复测 |
| collect-checkpoint.sh、verify-checkpoint.py | 113文件、nested原包、源码/CPIO/RAM模块与运行状态审计 |

已有目录/PID/启动编号不可重放。初次目录guard、初次错误频段、首次清单遗漏nested manifest均保留失败原件；当前collector以唯一新前缀重采并覆盖校验所有nested manifests。签名固件、OEM XML/库、原日志、身份/凭据、镜像和二进制不在公开目录。

最后8文件只读状态在uptime 1081.81秒确认同一次#100启动：MPSS/ADSP running、5GHz COMPLETED、BT四标志关闭、振动standby/starts0、taint0、NV/persist不变；累计MPSS fatal1、ADSP fatal0、显示超时0、BT phase2错误3，无额外MPSS fatal。原包SHA `cbed4ee09724635e0bf36c512b2588dcf361b977e004d38e0a7e66ba07d6562f`，私人final-status-validation.json；版本为本次原生查询后的缓存，未重复发送查询。
