# 漫步者低音量连接与重连验收

用户已明确将对端改为漫步者音响，不连接一加15，并要求测试音量不能太大。已存基线中唯一漫步者为 **EDIFIER S2000MKⅢ**，已paired/trusted并声明A2DP Sink；实际地址只在私有参数和证据中。本工具先核新基线与原记录，再复用原bond，不扫描、不Pair、不改Trust、不注册Agent、不删除设备或密钥。

[low-volume-speaker.py](low-volume-speaker.py)默认只做参数检查，只有显式`--run --window-confirmed`才访问BlueZ。运行前必须已有协调好的手机窗口、当前manifest和原boot guard；当前共用清理修复后的GATT身份门禁/原生HCI捕获，固定SHA256为`a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004`。旧r3/r4使用096d历史库，旧结果保持原版本。工具不启动BlueZ或PulseAudio，不触碰USB/充电/模块/整机PM。

测试仅从本机A2DP Source向该已配对音响Sink发音：固定BlueZ unique owner、精确peer path/address、paired/trusted与远端Sink UUID；已有发现、广告、蓝牙连接或活跃音频流时拒绝。每次连接后通过card的`device.string`/`bluez.path`定位，再用共同`owner_module`和`bluetooth.protocol=a2dp_sink`选择唯一sink。现场PA17的card字段为字符串、sink字段为整数，须规范为同一十进制表示；sink JSON没有`card`字段。身份字段依据[固定PA17实现](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/modules/bluetooth/module-bluez5-device.c)。

每轮先静音该sink、设为**10%**并读回，再解除静音播放2秒440Hz短音；PCM峰值为满幅0.10，首尾各50ms渐变。硬件音量离散取整的读回上限为15%，并不请求15%。播放期间继续检查上限，超限、身份/捕获异常就终止自己的paplay并静音；不自动加大音量，不播放用户媒体，不录麦克风。全窗口90秒，只做一次连接→短音→断开→重连→短音，不重试失败事务。

最后静音、断开本次已知peer，恢复原Powered和默认sink，核对其它adapter属性、原密钥和启动身份；关闭HCI FD/线程及私有bus。保留音响低音量，不恢复可能较大的旧蓝牙音量。两次paplay退出、实际MediaTransport active和HCI数据仍须关联现场记录；听见与否单独由用户确认，软件回执不能替代实听。

当前程序另已补齐静态审查发现的验证盲区：解除静音后和播放期读回sink.mute，按本次PID/应用名核对音频流未静音且仍在精确sink；必须观察到本次流uncorked才能给出软件成功。新程序的[九项主机/音频离线验证](../bluetooth-static-fixes-20261023/host/README.md)通过，没有新增实机播放，旧validation仍对应原r1–r4版本。

2026-10-23实际结果见[validation.json](validation.json)。r1/r2分别因错误使用不存在的`card`字段、未兼容`owner_module`类型而停止，未开始播放；修复选择器后r3/r4均完成两轮低音量播放及断开重连。r4为用户要求的重放，用户明确反馈“没有听到”，因此**声音验收未通过，原因未确定**。两轮paplay各发送192000B、退出0并观察到MediaTransport active，属于软件路径证据。

仅重放r4已保存的HCI，确认两次连接、认证、加密成功，两个aptX HD媒体组分别220/230包，RTP序号连续且L2CAP重组无错误。提取本次自生成测试媒体并离线解码，两组均非静音，峰值约0.100/0.102FS、RMS约0.057/0.058FS；这些记录不能证明音响单元实际发声。第一次连接发出的绝对音量13/127收到对端同值accepted，第二次未观察到新SetAbsoluteVolume指令；不能据此推定音响输入选择或物理静音状态。音量映射和应答依据[固定PA17音量实现](https://github.com/pulseaudio/pulseaudio/blob/1f020889c9aa44ea0f63d7222e8c2b62c3f45f68/src/modules/bluetooth/bluez5-util.c)与[固定BlueZ AVRCP实现](https://github.com/bluez/bluez/blob/65d11edee469c24dcc8d075b8be9c040cebaaf98/profiles/audio/avrcp.c)。

四次事务均恢复adapter/默认sink、断开已知peer、保留原密钥并关闭捕获。窗口结束独立核对同boot/release/manifest、模块/BlueZ/音频进程、预算和保护保持、taint0；唯一末64行日志锚点覆盖新增561行，指定故障0。此次由充电会话明确交接的r6安全INHIBIT窗口不计健康充电验收；尝试准备GATT r3时离线preflight因充电health非Good拒绝，手机服务及Windows客户端均未启动。

已明确交回充电会话进行R7 USB源识别更新及正常重启；其后报告新boot已恢复、保护及正式相机配置通过，继续持图标复测窗口。本线没有读回R7现场。用户对音响蓝牙输入及静音状态回答“暂时无法确认”，随后明确要求先停止蓝牙实际测试、只做静态审查。本线不再申请设备窗口或重放音频。私有地址、原始HCI和媒体只存`E:/edk2-samurai-out/bluetooth-speaker-20261023`，不连接一加15。

已找到精确型号的[漫步者原厂支持页](https://www.edifier.com/cn/product/support-418.html)和[产品页](https://www.edifier.com/cn/product/product-418.html)，记录见[factory-support.json](factory-support.json)。原厂支持页列出手册，不提供该型号手机APP或相关软件；其手册PDF本次返回403，未读取正文，不借用其它型号推定遥控器按法或故障原因。
