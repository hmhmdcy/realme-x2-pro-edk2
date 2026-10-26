# 阶段104：三个数字麦克风原生采样

当前[session104](../../sessions/104-native-digital-microphones-and-first-boot-radio-failure.md)、[下一轮](next-session.md)。Linux #103真实刷机，三个DMIC恢复非零采样；首次MPSS失败后唯一恢复5GHz通过，APR版本与正常重绑登记缺失仍待修，全硬件目标未完成。

| 工具 | 用途 |
|---|---|
| prepare-source.py、build-audio.sh、audit-kernel.py | 同机DMIC供电/时钟、APR包头/回复日志、SLIM真实错误及保留审计 |
| repair-build-format.py | 保存首次格式警告结果与旧split guard，修正后重建，不能重放 |
| prepare-deploy.py、build-firmware.sh、verify-firmware.py | 全新部署工具和真EDK2 DTB FFS校验 |
| collect-preflash.sh、split-backups.sh、receive-backups.ps1、prepare-package.py | 新80块备份、原包SHA、候选FAT/身份/凭据排除审计 |
| stop-connectivity.sh、reboot-f1.ps1、flash-audio.ps1、read-eud.ps1 | 受控停止、F1 receipt、独立枚举后仅boot/logdump、finally释放 |
| prepare-tests.py、collect-audio-runtime.sh、test-capture-dmic.sh、test-playback.sh | fresh boot/真实读回，有限三mic采样与DAPM状态/低幅播放 |
| collect-boot-failure.sh、recover-after-mpss-crash.sh、test-auto-network.sh | 保存auto1/fatal后唯一有界恢复/5GHz验证，BT保持停止 |
| test-core-rebind-once.sh | 本次已执行、保留无回复；APR IDR缺陷已确认，勿重复作为重试 |
| verify-tests.py、collect-checkpoint.sh、verify-checkpoint.py | 九原包/全部nested manifest/174文件与硬件边界校验 |

所有脚本有旧目录/启动/身份守卫，不能盲重放；私人输出在E:\edk2-samurai-out\kernel104，录音/原日志/镜像/固件/OEM XML/身份/凭据不公开。仅自写与修改GPL代码、脱敏记录公开，不提交推送。
