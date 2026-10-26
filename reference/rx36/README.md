# Session 36：USB 描述符、旧 qcusbser 审查与已完成对照

2026-10-09；详细结论见 `../../sessions/36-rx-usb-descriptors-and-legacy-qcusbser.md`。
`.raw` 是手机 TX 的原始字节，`.txt` 是解码；`rx36-usb-*.usbmon` 是 WSL 虚拟
主控目标设备的 URB 记录，包含本轮 libusb OUT，**不包含旧 qcusbser 的 OUT 或物理
总线 ACK**。`rx36-cmdline` 是未完成命令，不能当运行中 cmdline 证据。
文件 SHA-256 / 大小见 capture-manifest.json，源码固定 URL / SHA 见 source-manifest.json。

## 证据与结论

| 捕获前缀 | 内容 |
|---|---|
| rx36-windows-descriptors | 只读 Windows 描述符：IN 81 / OUT 02 / max packet 16，无 MDLM extras |
| rx36-wsl-descriptors | 初次 attach 后 WSL lsusb -v 的工具输出转存（去行尾空格），与 Windows 描述符一致 |
| rx36-state-ctrlc、rx36-clear-line | 本轮开始确认 Linux，以及未完成命令的清行回执 |
| rx36-cmdline | 输入停在 cat /proc/cmdl，69 无回执；未发换行 |
| rx36-usb-drain | 第一版只读捕获，USB 已释放但 usbmon 线程退出失败；无 OUT |
| rx36-usb-drain-nonblock | 修正非阻塞读取后正常只读退出；无 OUT |
| rx36-usb-ctrlu | 900115 首次写入 3 / 3 成功，手机 tty byte=15 |
| rx36-usb-ABC | 9003414243 首次写入 5 / 5 成功，手机受理但为 41 90 90 |
| rx36-usb-DEFG | 900444454647 首次写入 6 / 6 成功，手机受理但为 44 90 90 90 |
| rx36-windows-restored-ctrlu | detach 后第一次 Windows 捕获为 0，无受理，不能算 payload 失败 |
| rx36-windows-reenum-ctrlu | 一次 com-off/up 后首次发送取得 tty byte=15；finally 关闭 |

手机仍为 rx33-console 的 Linux，没有刷机。9505 已 detach 回 Windows，仍保留 Shared；
COM14 回执已恢复。**绕开 qcusbser 仍出现同样多字节问题；不再把重装驱动作为首选。**
下一步查 SM8150 RX advance/初始化/时钟的具体依据，勿原样重跑本轮对照。

## 本轮操作记录与工具用法

以下仅用于复核流程或带有新依据的后续对照。每步独立进程，前缀不可重用。
本轮用户已执行管理员 bind；未来 busid 可能变化，先查 list：

```powershell
& 'C:\Program Files\usbipd-win\usbipd.exe' bind --busid 6-5
```

确认 Shared 后，在普通终端手动分步执行：

```powershell
& 'C:\Program Files\usbipd-win\usbipd.exe' list
& 'C:\Program Files\usbipd-win\usbipd.exe' attach --wsl Ubuntu --busid 6-5
wsl.exe -d Ubuntu -u root -- lsusb -v -d 05c6:9505
wsl.exe -d Ubuntu -u root -- modprobe usbmon
wsl.exe -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' `
  --seconds 3 --out /mnt/e/edk2-samurai-out/NEW-usb-drain
```

工具已完成本轮单步设备验证。核对描述符和只读排空后，单独用 `--hex '90 01 15'`
与 `--ack 'tty byte=15'` 验证安全清行。ABC 的本轮命令形式如下：

```powershell
wsl.exe -d Ubuntu -u root -- python3 '/mnt/e/RealmeX2Pro edk2/linux-port/scripts/eud-usb-step.py' `
  --hex '90 03 41 42 43' --repeat 5 --seconds 20 --ack 'byte[3/3]=' `
  --out /mnt/e/edk2-samurai-out/NEW-usb-ABC
```

不要把这些命令拼成无人值守循环。输出前缀必须全新，工具拒绝覆盖已有证据。
看 `.usbmon` 中对应的 Bo 提交和完成、`.events.jsonl` 的长度及回执、`.txt` 的
全部 payload。USBmon 记录 URB，不是物理总线包；超时/未受理不能计为有效失败。
本轮 ABC/DEFG 的回执均在首次写入后出现，TX 解码 0 stray / 0 pending。

进程正常退出、USB 资源关闭后再把设备交还 Windows：

```powershell
& 'C:\Program Files\usbipd-win\usbipd.exe' detach --busid 6-5
& 'C:\Program Files\usbipd-win\usbipd.exe' list
```

bind 的共享配置会保留；detach 结束当次转发，不会卸载 qcusbser。确认 COM14 正常
再开单步串口/临时终端。移除持久共享需管理员 `unbind --busid 6-5`。
遇到 hrdevmon 警告/attach 失败先停止，不自动 force、不重启主机、不动其他设备。
