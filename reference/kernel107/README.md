# 阶段107：HELLO先应答，再公告服务

[session107](../../sessions/107-qrtr-hello-reply-and-automatic-wifi-start.md)、[下一轮](next-session.md)。实际Linux #106，仅logdump；首次auto Wi-Fi成功、5GHz全流程通过，无手动modem恢复。2.4GHz认证/DHCP/网关/DNS/577B HTTP内容通过，wget结束超时仍判完整失败。

prepare-source/build/audit只改变QRTR两源，保留主动endpoint/MHI resume API/流控、其它源码/配置/DTB/CPIO/模块/原bootconfig。prepare-tools/package/flash-radio使用80个新备份块和独立F1/fastboot guards，传输中断块和枚举早期失败原件保留，最终仅logdump一次写入。

first-radio-trace/runtime、有限auto-network/播放/DMIC0、一次24g尝试和final-network原包由verify-tests/verify-checkpoint校验；154文件/七原包/嵌套SHA通过，首次trace零丢失。analyse-band-failure保留认证成功与HTTP退出失败边界。update-docs/audit-public保留15组/F2FS段落。所有固件/日志/录音/凭据/身份/镜像私有E:\edk2-samurai-out\kernel107，不提交推送，不重放旧guards。
