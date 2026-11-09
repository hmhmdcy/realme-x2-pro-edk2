# 当前：thin-private 已部署；普通重启全绿，suspend 待物理唤醒复测

目标（2026-11-09）：Wi‑Fi、CDC NCM、SSH 仅作强制回归门禁；相机
Selection API、PM8150L 闪光灯/V4L2、蓝牙主机模块、NFC 控制器和
MAX98937/AW8697 私有 `status` 删除已关闭。
继续用 Linux 主线模型/API 适配其余硬件，私有层只保留不可标准化的
板级接线。`boot`/`logdump` 在 Linux 侧成对写入；不擦写
NV/persist/校准/userdata。

## 设备状态

**设备当前在 suspend 尝试后离线。** 最后一次 SSH 可达的 boot 为
`2b17a67a-841a-4fe5-9db4-ec8daf19d078`；执行 detached
`loginctl suspend` 后 NCM/Wi‑Fi 在 140 秒内未恢复，Windows USB 和
fastboot 也均未枚举。需要先物理按电源键唤醒；醒来后先保存
`/tmp/samurai-suspend-test.log`、`/sys/kernel/debug/suspend_stats` 和
`dmesg`，不要直接再次 suspend。

- 最后一次完整门禁 boot ID：`2b17a67a-841a-4fe5-9db4-ec8daf19d078`；
- boot：`5b4dd4871f6856710ff58e722ffd8b2c30d04baf0104b262adcb02e46a7651bf`；
- kernel FAT：`1f4bbb302a62d1f8a950994ac93b00ca194a41c768d4d11b1b97c69f5702574b`；
- Image：`f8d8962197827dafbe50e551f5df03391c43ec0269449fa87b833e57799656a5`；
- DTB：`b244b3f10a14811dca2e808efa8c840f432cac69020e66b60eba97d02794a18e`；
- stripped 模块 777 个。

## 已完成：Linux 侧成对刷写

`linux-port/scripts/flash-pair-linux.sh` 按 GPT label 找到 `boot`
(`/dev/sde11`) 和 `logdump` (`/dev/sde32`)，校验镜像大小、SHA-256、
挂载状态和只读性，先写 logdump、整块回读，再写 boot、整块回读。
实际写入日志见
`E:/edk2-samurai-out/standard-arm64-v731/thin-private-final-20261109/flash.log`。

thin-private 两次普通重启用时：NCM SSH 31.905/38.284 秒，Wi‑Fi SSH
47.984/59.074 秒。两次都在同一 boot 内通过 777 模块完整门禁。这个
结果证明常温普通重启，不证明拔电冷启动或 suspend/resume。

## 已完成：闪光灯/V4L2

- 标准 `leds-qcom-flash`、LED flash class、V4L2 flash subdevice；
  S5KGW1 通过 `flash-leds` 加入 CAMSS 媒体图；
- `white:flash` 存在，亮度 26/255、torch 200 mA、`faults=0`；
- 开灯 RAW 均值 `177.04 -> 407.147`（+130%），0% 饱和；
- 774/777 模块普通重启前后，四路 RAW、thermal、网络和 `taint=0`
  门禁均通过。

## 已完成：蓝牙主线模块

签名 `samurai-bluetooth-host-0.1.0-r0` 已安装；`bnep`、`uhid`、
`uinput` 自动加载，`/dev/uhid`、`/dev/uinput`、BNEP socket、BlueZ
`hci0` 和 777 模块 gate 通过；外部 PAN/HID 对端未验。详见
[BLUETOOTH-HOST-MODULES](linux-port/docs/BLUETOOTH-HOST-MODULES.md)。

## 已完成：NFC/nfc0/neard

Alpine `neard-openrc`/`neard 0.20` 和签名 `samurai-platform 5-r22`
已安装；普通重启后 `nfc0`、`neard`、D-Bus 属性及电源/轮询启停通过。
无实体标签，不声称读卡；一次 NCM 探针 `Connection reset` 仍保留为
未闭环的 USB 瞬态。详见 [NFC-NEARD](linux-port/docs/NFC-NEARD.md)。

## 已完成：private status sysfs 删除

- 最终 FAT 以当前 flash/V4L2 FAT `c99c690e…` 为底，只替换 `/Image`；
  boot `5b4dd487…` 和 DTB `b244b3f1…` 逐字节不变；
- 刷后三处节点均消失：两个 `samurai-max98937` 的 `status` 和一个
  `samurai-aw8697` 的 `status`；
- 标准 ALSA playback/capture、AW8697 input/FF、四路相机 RAW、
  flash/V4L2、蓝牙三模块、NFC `nfc0`、thermal 和 Wi‑Fi/NCM/SSH
  全部通过；两次普通重启 `taint=0`，CAMSS `suspended`，MMCX 128。

## 恢复后先做：设置来源清理

唤醒后先只读保存日志，不再次 suspend。设置分层、候选 `5-r23`/`4-r11`
和清理步骤见[SETTINGS-PROVENANCE](linux-port/docs/SETTINGS-PROVENANCE.md)；
有回滚条件时安装候选并运行来源检查，PowerDevil 覆盖先 dry-run 再
`--apply`，`sshd` 的 `boot` runlevel 另案恢复官方 `default`。

## 剩余候选与未验项

- suspend：本次 `loginctl` + 直接 sysfs RTC alarm 测试未恢复，不能
  声称通过。上次干净 s2idle 用的是 `rtcwake`；物理唤醒后必须用
  `rtcwake -m mem -s 30` 复测，并保留串口/人工恢复路径。
- NFC：真实标签读写、eSE 和长时间轮询功耗未验。
- 蓝牙 PAN/HID：外部对端、配对/路由、冷启动和带业务 suspend 未验。

私有层审计覆盖 14 个 C/H、11 个 DTS/表文件，无私有 ioctl、用户态
拷贝或 Android/Binder 入口；唯一保留的旧只读面是
`sensor-power/state`。

## 已确认的网络/相机基线

- `samurai-platform` 5-r22 / `samurai-desktop` 4-r10 已安装；普通重启
  后 UDC `configured`、`usb0` carrier 1，configfs `qmult=20` 自动恢复。
- NCM 24/24、1798.828 秒心跳；Wi‑Fi 1810 样本/1820.51 秒。旧 Genesys
  Hub 的 Code 43 仍归主机/物理路径；主板直连口已通过。
- 相机四路自动 probe，flash/V4L2 boot 的 RAW 各两张 100% 非零、
  0% 饱和、帧间变化 26.012–48.634%；IMX471/S5K3M5 Selection API
  已无 EINVAL，libcamera 0.7.2 四路 640×480 RGB888 单帧成功。
- 内置麦克风 PulseAudio 连续采集 61.98 秒，RMS 15.053、0% 削顶、
  stderr 空；原始音频未保留。
- 时钟只读审计：358 个时钟中 55 个“硬件使能但无逻辑 consumer”，
  含 `gcc_cpuss_rbcpr_clk`；这不是逐项 critical 证明。

## 其余未完成

- 闪光灯拔电冷启动、重复冷启动和长时间热升；当前控制/光学/普通重启
  已通过。
- thin-private 的联合 suspend/resume、拔电冷启动和回滚演练；
- 蓝牙外部对端、音频耳机/watchdog、传感器 SSR、相机画质/录像/热功耗。
- NFC 标签、指纹认证、真实 SIM、高压充电、实体电源键、deep sleep、
  真正断电冷启动和长期功耗。
- `clk_ignore_unused` 仍是实测必要约束；无 flag 的 kexec 预检曾使
  设备离线超过 255 秒，禁止无人值守重试。UEFI/GRUB 和 RBCPR 候选
  仍未刷入。
- 真正拔除外部供电的物理按键冷启动、多次冷启动、长期 suspend/sleep
  与功耗测量仍需现场条件。

## 约束

- 不重刷/擦除 NV、persist、校准、userdata；不做 boot-only 半套部署。
- 不热反复 unbind PM8008/CAMSS；不以 OOT 模块冒充最终验收。
- 不把私密 RAW、音频或场景哈希写入公开文档。
- 根仓库有大量既有脏改动；不要 `git add -A`，不要提交无关文件。
