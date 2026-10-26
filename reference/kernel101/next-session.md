后续实际状态已推进至[阶段102交接](../kernel102/next-session.md)：WCD934x通过、真实双MAX98937已识别并解绑错组件；一次自动无线成功，历史失败仍开放。以下保留阶段101历史交接。

# 下一阶段：音频codec、SLIMbus、功放及声卡（session101）

继续用户全硬件goal。先读 [session101](../../sessions/101-adsp-native-apr-reply-and-radio-regression.md)、本目录README、[15组硬件](../../linux-port/docs/HARDWARE-STATUS.md)及私人 `E:/edk2-samurai-out/kernel101/checkpoint-validation.json`。每轮重新读实际boot ID/uptime/进程/目录/驱动/路由/哈希；旧PID、starts=0脚本或已存在前缀不能重放。

手机已部署Linux #100（阶段101），ADSP自动加载本机签名固件并运行，APR原生版本回复AFE API7/ASM API2通过；ALSA尚无声卡，扬声器/麦克风/耳机未验收。
振动FF/电气状态、close/SIGKILL/1秒看门狗已通过；用户无人测试，按日志和代码复查暂缓机械确认，继续音频，无新增振动播放。
首次MPSS仍在up后39.986571秒fatal，自动无线启动失败；一次有界手动恢复后MPSS与ADSP均running、taint0、5GHz认证/DHCP/DNS/HTTP通过，蓝牙关闭、不配对连接。
误用早期2.4GHz配置的原失败保留，该频段又出现一次非主动reason7；改用已验证5GHz配置后网关首轮2/3回复，后续5/5无丢包，不能宣称无线稳定性修复。
当前113文件checkpoint/5包原现场绑定/80块完整备份/boot与logdump读回/6NV与persist不变通过；当前checkpoint显示超时0、三次BT错误均phase2，历史显示与删除等待问题保持。
DTB改变已真正重建EDK2；新增私有ADSP固件、按本机身份寻找MPSS的服务及只读版本查询，已有init/模块/振动驱动保留。下一项核对codec/SLIMbus/功放并接入声卡。
保留15组硬件、Android、数据/GPT、SSH身份、旧显示快照和另一线程rootfs/F2FS；固件/镜像/身份/凭据/原日志仅私人目录。冷启动/休眠/长期稳定待办，全硬件goal仍active。

用户已回答振动问题：“无人测试，先按照日志代码静态分析，没问题就下一个”。机械确认暂缓，**没有待答的振动问题，也不因缺少触感反馈阻止下一硬件**。代码复查未发现需立即修改的问题；保留阶段99三次20%150ms、close/SIGKILL/1.02秒看门狗及error0证据。当前starts0/standby，无重播；不把电气状态当机械输出。

本轮ADSP在18.900281秒up，保留本机原30MiB carveout `0x9b200000/0x1e00000/no-map`。本机modem分区RO取得17个拆分签名文件12,420,754字节，ELF32/Hexagon/可重定位段30MiB严格校验；只存私人输出/私有initramfs。固件JSN核对 `avs/audio` / `msm/adsp/audio_pd`，APR只描述core service3；SOUND/QDSP6/APR/PDR内建，codec/功放/机器声卡未启用。SLPI/CDSP保持禁用。

`q6core`本机只读 `samurai_api`调用原生GET_FWK_VERSION/不支持时legacy fallback；100ms单次等待、缓存，不走“timeout也ready”的API；sentinel要求真实服务4/7条目，拒绝缺失/超时。回复解析加入header与变长条目长度检查。实机首次/恢复后均AFE7/ASM2，ADSP恢复过程中持续running、无ADSP fatal、taint0。未打开PCM、未进行声音输出/录音，也无ALSA卡。

无线helper新增 `samurai-modem-remoteproc`，严格检查唯一name=modem、SM8150 MPSS compatible、真实DT路径及firmware名，不依赖编号。当前MPSS仍remoteproc0、ADSP remoteproc1，这只属本次启动；后续脚本一律动态解析。初始MPSS43.886772秒up、83.873343秒fatal，相隔39.986571秒，原boot-finished=1/自动日志保留；回收一次BT/ath10k/MPSS后running，NV仅复用已校验RAM COW。不能宣称自动启动修复或由ADSP引发已有40秒问题。

初次网络误用了旧 `freq_list=2462` 私有配置，2.4GHz认证成功但不满足5GHz测试条件；原partial目录/配置/失败保留，并观察一次非主动reason7（蓝牙关闭）。5GHz使用阶段100已验证私有配置重试；认证/DHCP/路由/DNS/HTTP577字节通过；首轮ping3发2收33%丢包，之后5发5收0丢包。原2.4GHzreason7和主动换5GHzreason3/locally_generated=1都保留，不以重测覆盖首轮丢包。没有重测双向4MiB或单播删除跟踪；历史阶段98证据与未解决项继续。

接下来：

1. 音频：只读核对本机未改动dtbo/原厂DT选择及vendor实际mixer路由，确认WCD934x SLIMbus/reset/IRQ/MCLK/供电与Maxim双功放具体芯片/接线。19781公开overlay是候选来源，当前通用vendor XML不能独自确定活动路由。先SLIMbus/codec枚举及ID，再机器声卡/DAI/功放；每步保留原声卡空与实际版本回复边界，不能把hotdog其它功放/资源直接套入本机。
2. 无线：给首轮MPSS空原因增加有限SMEM返回值/长度诊断，并收集QRTR/rmtfs请求链；先保留失败再做单次恢复。2.4GHz BT-off掉线、3.1秒删除无确认等待继续，勿盲增固定delay/无限重启或以公网ICMP失败替代HTTP结果。
3. 当前三次BT错误仍phase2/power-on pulse/115200/chunk1/partial0/first00；不改baud/parser/重试窗口作为掩盖。蓝牙继续不配对、不连接；NFC无标签先控制器；充电收尾不跑旧探针。
4. 下一次完整boot/logdump新备份；本次80x2MiB块8192Kbit/s全通过。只停止核对当前cmdline的自有SCP，不杀rootfs01任务。真实DTB改变须重建EDK2，F1 receipt后独立fastboot身份/产品/分区大小审计。ADSP不做强制crash，不循环DSP恢复；对照仓库有强制ADSP crash卡住PM的记录。

最终113文件checkpoint SHA `e3f24622bbebe7de770fc9b0eeca136fffa9ba658a8520b9c3ebfd430a7c2354`，uptime 586.99秒，所有原包/nested清单/读回/服务及模块/6NV/persist通过；后续网关包uptime 646.07秒、5/5、双DSPrunning。当前checkpoint显示超时0、BT错误3；这不消除旧显示失败、USB大传输/删除等待及冷启动/休眠/长期可靠性问题。

当前Image SHA `6edfea9d5c23bd55b623b8f57f21937f1f8c3e63467b0437ffe5021ae8aab19d`；DTB `2fac32706a56743294f17d108e207937b237be0ef2d1a7c27bff5bcf8fe57f46`；CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`；boot `ea123f3aa112f477d979444f5d620b4b378ef09ef2f55c140658b65407b57cc0`（6680576字节）；logdump `2545f18650669910b1923d99dffbd802bc426438327619890150d98832f3d8fe`。完整boot读回 `b71044d4cee6190e433878af8bc6be12e8179adcf1219981faeb4309c4406543`，与新boot前缀+原分区尾部逐字节SHA相符。

Linux `/home/cy122/x2pro-linux/linux`，initramfs `/home/cy122/x2pro-linux/initramfs`，EDK2 `/home/cy122/edk2-samurai/repo`，私人 `E:/edk2-samurai-out/kernel101`。当前启动ID只存 `runtime-boot-id-after-private.txt`；不使用旧 `runtime-boot-id-private.txt`（#99刷入前）。HEAD仍e42788eafb0bb9d8dfce319c71ca54c5207b2295/f23a9f8aa619388412c8aad5834a460e51eae9eb，无提交/推送。实际DTS在WSL及本目录after快照；linux-port/dts旧镜像保持原件，不能直接构建。

只刷boot/logdump，保留Android/userdata/GPT/原NV/persist/SSH身份/显示85–88快照/rootfs01及F2FS段落。NV仅RAM COW；签名固件/镜像/二进制/OEM库/XML/原日志/身份/凭据/密钥不公开。充电相关配置/解封/NV/OTP/FET/OTG/MCU/GPIO不操作，不用I2C_FORCE。振动reset116与充电控制无关。

最后8文件只读状态在uptime 1081.81秒确认同一次#100启动：MPSS/ADSP running、5GHz COMPLETED、BT四标志关闭、振动standby/starts0、taint0、NV/persist不变；累计MPSS fatal1、ADSP fatal0、显示超时0、BT phase2错误3，无额外MPSS fatal。原包SHA `cbed4ee09724635e0bf36c512b2588dcf361b977e004d38e0a7e66ba07d6562f`，私人final-status-validation.json；版本为本次原生查询后的缓存，未重复发送查询。
