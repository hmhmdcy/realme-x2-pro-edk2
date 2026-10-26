# 阶段105：APR登记与首次MPSS诊断

[session105](../../sessions/105-apr-rebind-and-first-modem-crash-smem-diagnostics.md)、[下一轮](next-session.md)。真实Linux #104，仅刷logdump；APR登记/API恢复，首次MPSS约40秒fatal仍未修，唯一恢复后5G和有限音频回归通过。

prepare-source/build-kernel/audit-kernel用于三C源及保留校验；add-private-smem-diagnostic和repair-srcu-error-cleanup是刷机前修正，guard不能重放。prepare-tools/package与flash-radio仅logdump，80块完整备份及F1独立枚举审计。

collect-audio-runtime/test-core-rebind-once与core-followup原件保留第一次100ms超时及EUD读取期间复测成功；first-boot-failure/recover-after-mpss-crash/test-auto-network保留auto1和唯一恢复。test-playback/test-capture-dmic仅有限低音量/DMIC0回归，无振动脉冲/BT配对。collect/verify-checkpoint绑定八原包及149文件，update-docs/audit-public保留15组与rootfs段落。

输出、固件、录音、凭据、日志、镜像均在私人E:\edk2-samurai-out\kernel105；仅源码/脚本/脱敏文档公开，不提交推送。所有boot/PID/prefix/旧目录守卫必须保留，不重放现有输出。
