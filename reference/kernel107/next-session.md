# 下一阶段：重复自动启动与2.4GHz数据/HTTP收尾

当前[session107](../../sessions/107-qrtr-hello-reply-and-automatic-wifi-start.md)和[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)，全硬件goal active、无预算。

手机已部署Linux #106（阶段107），仅刷logdump；DTB、完整boot分区、CPIO/模块、配置及显示/radio bootconfig字节保留。
QRTR恢复收到远端HELLO后先应答HELLO、再公告服务，移除会丢包返回-EAGAIN的hello_sent门控；保留endpoint初始化/MHI恢复的主动HELLO与既有重试/API。新boot首次14/64/4096三个公告成功，真实固件/RAM COW NV请求、原生PD mapper回复通过，auto worker0，无手动MPSS恢复；5GHz认证/DHCP/网关3/3/DNS/HTTP及切回5GHz复测通过。
2.4GHz单次2462MHz认证、DHCP、网关3/3和DNS通过，收到577字节HTTP内容，但wget20秒未正常退出，完整测试仍失败；本轮未见WRONG_KEY或reason7，历史reason7/删除等待及新HTTP收尾问题保留。首次自动启动已在一轮新boot验证，重复冷启动/休眠/长期稳定仍待验收。
首次音频API7/API2、2秒低音量有限播放与DMIC0回归通过，双功放start1/stop1/failed0；DMIC0 5.04秒/241920帧，稳态非零208180/80种值/无削波，实际声音/质量无人确认。本轮没有core重绑或ADSP重启，106阶段首次100ms重绑成功记录保留。
检查点154文件/七原包及所有SHA通过，首次radio trace无丢失；uptime216.9、首次MPSS连续约171.1秒，双DSP running、taint0、fatal0。本次显示超时1、BT phase2错误2仍在待办；蓝牙停止不配对连接，振动standby/starts0无新脉冲，机械确认暂缓。
下一轮kernel108优先重复干净启动与2.4GHz数据/HTTP收尾，随后继续其它15组。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私人固件/日志/身份/凭据/音频/镜像不公开，不提交推送；全硬件goal active。

当前私人kernel107/runtime-boot-id-after-private.txt绑定实际#106，checkpoint SHA `62dfd166ac909bc46cca464e13ad88ee28cf3f98561cee17d4fe4c68e52ea59c`、154文件/七原包；next kernel108/全新输出前缀，不重放旧boot/PID/guard目录。本轮无MPSS手动恢复/core重绑/ADSP restart。仅一轮新boot自动初始化成功，重复干净重启与物理冷启动仍未验收。

源码仅af_qrtr.c/ns.c改变，kernel107/*.after与实际匹配，NS HELLO先回复成功再服务公告，移除hello_sent丢包门控，主动endpoint/resume HELLO/API和流控生命周期全部保留；不是全量回退544d85d。原radio/display trace来自kernel106私有不可变bootconfig，CONFIG与106完整相同，DTB/CPIO/模块/boot不变。若未来改DTB必须真重建EDK2嵌入DTB；保留旧显示85–88，linux-port/dts旧镜像不覆盖。

优先同一#106干净重启，使用新的bootID和输出前缀/目录/guards，保留107首轮原件后验证auto0、三个公告、固件/RAM COW/5G，无须重新刷相同镜像。物理冷启动无人操作不能假称已验收。2.4GHz2462MHz认证/握手/DHCP/网关3/3/DNS及577B HTTP内容已到达，wget20秒未正常退出，测试result保持FAIL；本轮只有换频reason3，没有WRONG_KEY/reason7。当前5GHz5180已恢复并再次通过全网络流程，勿把单次HTTP结束超时等同2.4未认证或密码错误；下步先对照TCP FIN/ACK/重传和用户态wget响应长度/连接结束，历史reason7/删除等待独立保留。

MPSS用/usr/sbin/samurai-modem-remoteproc完整OF与固件定位，不固定remoteproc编号；ADSP qcom/sm8150/realme/samurai/adsp.mdt。amps1-0039/1-003a归驱动，GPIO148/37不要重新直接操控；WCD143、QUP4 GPIO51/52、QUAT137–139和触屏54保持。motor唯一driver/89c000 OF，现2-005a starts0无新脉冲。5G私有配置kernel107/wpa-5g-private.conf限制5180，不要用kernel95的2462配置。

DMIC0回归5.04秒非零230111、稳态208180非零/80种值/无削波；DMIC1/2保留104历史。两个PCM关闭，功放global00/amp80/start1stop1failed0；实际声音/已知声源质量无人确认，勿称完整音频可用。振动按用户日志/静态分析推进，不提问/不重放脉冲；BT保持停止不配对连接；NFC仅控制器。

保留Android/data/userdata/GPT/NV/persist/SSH/rootfs01/F2FS/显示85–88所有内容。只刷boot/logdump，DTB不变优先logdump；每轮全新完整两分区备份。NV RAM COW，不持久写。充电收尾不再执行旧OEM/NV/OTP/unseal/FET/OTG/MCU/GPIO/I2C_FORCE探针。所有固件/原日志/身份/凭据/音频/镜像私人，公开仅自写/GPL修改与脱敏记录，不提交推送。USBipd保持Running，EUD最终detached，hrdevmon警告保留、不forcebind。继续15组硬件优先无线可靠性。


