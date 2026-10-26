# 阶段106：HELLO/公告竞态与音频完成后trace

[session106](../../sessions/106-first-modem-hello-race-and-core-query-tracing.md)、[下一轮](next-session.md)。实际Linux #105，仅logdump；首次无线顺序缺陷有trace证据，尚未部署修复，唯一恢复后5G通过。core首次重绑100ms查询通过，无EUD reader/ADSP重启。

prepare-source/build-kernel/audit-kernel、wire-node trace修正保留原显示配置/CPIO/DTB/模块；prepare-tools/package/flash-radio使用80块全新备份、仅logdump。collect-first-radio-trace先保存启动原件，test-core-rebind-once和recover-after-mpss-crash分别保存新的独立trace且不覆盖旧原件。analyse-trace核验原包SHA/零丢失，inspect-radio-order仅协议元数据。

有限网络/播放/DMIC0回归及八原包检查点由verify-tests/verify-checkpoint校验，194文件、原包与嵌套SHA通过。update-docs/audit-public保留15组和rootfs段落。所有输出、凭据、固件、录音、原日志、镜像只在私人E:\edk2-samurai-out\kernel106；不提交推送，不重放旧guard目录。
