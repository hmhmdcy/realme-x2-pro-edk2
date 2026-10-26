# 最短原生CVSD/HCI验收

这是供主会话在已协调的设备窗口执行的步骤，本研究代理未执行。无需重启、刷写或更换内核模块。对端必须是用户明确指定、当前在场且已配对的测试耳机，支持HFP HF UUID `0000111e-0000-1000-8000-00805f9b34fb`；设备不在场时不以扫描附近耳机代替。

## 静态前提已经核对

- 当前源码 `net/bluetooth/sco.c:sco_sock_init()`创建socket时默认 `codec.id=BT_CODEC_CVSD`、`codec.data_path=0`。连接路径复制该codec给hci_conn。
- `hci_conn.c:hci_enhanced_setup_sync_conn()`的CVSD分支将 `conn->codec.data_path`写入input/output data_path，TX/RX coding format=2(CVSD)，input/output linear PCM16、16000B/s，即8kHz单声道。
- WCN3990 socdata没有HFP_HW_OFFLOAD capability，所以不会由QCA驱动安装data_path_id=1的get_data_path_id回调。PA17 native不使用BT_CODEC offload选项，走标准SCO socket。
- PA17 `module-bluez5-discover.c`在编译native后端时默认 `headset=native`，`enable_native_hfp_hf=true`。这个`_hf`和PA profile枚举表示**对端HF**；`profile_init(HFP_HF)`实际注册本机 `/Profile/HFPAGProfile`与UUID111f。本机手机AG→耳机HF是默认native支持方向；不能误读为本机默认也注册了HF UUID111e。
- PA17 HFP profile名称是 `handsfree_head_unit`；`headset_head_unit`是HSP。不能用PipeWire的连字符profile名称替代。

## 条件与准备

主会话先确认当前设备身份/空闲状态和该会话持有设备窗口；现有相机/充电会话不受影响。PulseAudio必须是UID10000原桌面实例，WirePlumber的`hardware.audio/bluetooth=disabled`保持。没有其它正在运行的音频流、没有其它蓝牙音频连接，原模块参数、原profile、原对端连接状态与控制器电源状态写入私人目录后再操作。

以下PA命令在**当前桌面用户会话**执行，不以root启动新的PulseAudio。PEER、目录和对端标识不写进公开日志。

```sh
PEER='用户已指定的既有耳机地址'
bluetoothctl info "$PEER"
pactl info
pactl list short modules
pactl list cards
pactl list short sinks
pactl list short sources
```

要求既有配对且对端UUID含111e；没有这个条件就停在待现场验收，不自动配对其它设备。当前PA的module-bluetooth-discover/module-bluez5-discover应只有一套；若已经用 `enable_msbc=false`，直接复用。否则在音频空闲时保存原wrapper模块ID和原参数，只临时重载蓝牙发现模块强制CVSD：

```sh
# ORIGINAL_DISCOVER_ID来自上面pactl实际输出，不能猜ID。
pactl unload-module "$ORIGINAL_DISCOVER_ID"
pactl load-module module-bluetooth-discover headset=native enable_msbc=false enable_native_hfp_hf=true
```

这会短暂撤销再注册PA蓝牙profiles/endpoints，保留BlueZ配对和本机地址；原参数必须留存供清理恢复。不可在原wrapper尚存在时重复加载另一套。若PA当前蓝牙模块本就缺失，先定位包/加载失败原因，不同时打开WirePlumber抢占蓝牙。

root仅启动一次有界私人HCI capture：

```sh
umask 077
# PRIVATE_DIR为当前事务新建的0700私人目录。
timeout -s INT 25 btmon -i hci0 -w "$PRIVATE_DIR/cvsd.btsnoop" > "$PRIVATE_DIR/btmon.txt" 2>&1 &
```

然后桌面用户只连接指定耳机，不重新扫描：

```sh
bluetoothctl power on
bluetoothctl --timeout 12 connect "$PEER"
MAC_U=$(printf '%s' "$PEER" | tr ':' '_')
CARD="bluez_card.$MAC_U"
pactl set-card-profile "$CARD" handsfree_head_unit
pactl list short sinks
pactl list short sources
```

从实际输出选择该CARD的HFP sink/source ID赋给HFP_SINK/HFP_SOURCE，不盲猜注册名。预期为s16le/1ch/8000Hz。选profile或创建节点本身不算通过；启动一个短采集和已知的低音量短测试音播放，才能要求SCO实际传输：

```sh
# CVSD_INPUT_WAV是预先准备的8kHz/单声道/16bit、约5秒低音量测试音。
# 现场可在该窗口正常讲话；录音仅保留在PRIVATE_DIR。
timeout -s INT 6 parec --device="$HFP_SOURCE" --file-format=wav --rate=8000 --channels=1 --format=s16le "$PRIVATE_DIR/headset-mic.wav" &
CAPTURE_PID=$!
paplay --device="$HFP_SINK" --volume=8192 "$CVSD_INPUT_WAV"
wait "$CAPTURE_PID" || test "$?" -eq 124
```

如果25秒捕获窗口不足就先把窗口按实际前置操作调整；不把capture超时与蓝牙失败混为一项。不得为得到成功结果重复上下电或任意修改NVM/发送厂商opcode。

## 判定与清理

需要同时满足：HFP RFCOMM negotiation选择CVSD/codec1；同步连接status0；若使用Enhanced Setup/Accept，input/output data_path均0；在客户端活动期间有真实HCI SCO TX和RX数据；采集为有效PCM且能区分现场说话/静音。协议/PCM通过与人工听音分别记录；若只有包计数或节点，不能宣称耳机听音/话筒完整通过。mSBC、AVRCP、A2DP、重连、蓝牙事件唤醒另行按缺口验证，不混入这次CVSD结果。

失败时保存HCI status、command opcode/参数、SCO TX/RX方向、PA日志和资源清理，先区分HFP negotiation、同步连接、数据路由或声学条件。SCO0包不能直接解释为硬件不支持；若HCI path0被明确拒绝或连接成功但无HCI数据，再与本机HAL的路径和原厂SLIM配置对照。

结束停止上述客户端并等待capture退出，恢复原PA蓝牙模块参数、原card profile、原连接和控制器电源状态；保留既有keys，不调用remove/unpair，不重启BlueZ/PulseAudio/其它服务。控制器或profile实际状态不明时先读取，避免重复切换。
