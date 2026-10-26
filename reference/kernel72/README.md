# Session72：普通USB NCM与自动SSH证据

实现/范围见[sessions/72](../../sessions/72-usb-ncm-and-autonomous-ssh.md)。
实际initramfs增加CDC NCM、USB link-local地址、静态公钥SSH和PTY支持，仅部署logdump。
Windows原生UsbNcm、手机high-speed、双向4MiB SHA、设备保存日志和EUD共存均有实测。

- `baseline-dmesg.validated.txt`：#61设备保存73173字节日志，EUD完整压缩导出校验。
- `usb-dmesg.validated.txt`、`boot62-dmesg.validated.txt`、`finish-dmesg.validated.txt`：
  手机保存的后续完整日志，经SSH/SCP按设备SHA/CRC/长度校验。
- `traffic-validation.json`：部署前后的两对4MiB随机文件哈希和真实错误计数。
  随机原件保留在本地构建目录，没有把报告当原件。
- `autostart-facts.txt`、`independent-ssh-ready-facts.txt`、`independent-ssh-validation.json`：
  自动启动、新boot_id、taint、配置和无需host com-up的已认证SSH复测。
- `init-before`、`init-after`、`config.diff`、`initramfs-validation.json`：最小hook与
  CPIO权限/UID/GID/内容验证。主机/客户端私钥没有归档或提交。
- `core-before.sha256`、`kernel-build-hashes.txt`、`flash-validation.json`：EUD/RMI/DT
  源码保留、FAT内容及仅一次logdump部署。
- 原始Windows/WSL EUD capture、发送事件、F1和fastboot输出保留；无回执/未完成的
  首次枚举、日期解析错误等失败记录不补字、不冒充硬件失败。

`verify.py`离线校验归档日志、raw解帧、接受报告与SHA256SUMS。
`validate-initramfs.py`需实际本地内核CPIO/源树；`build-kernel.sh`和
`install-initramfs.py`记录本轮一次性操作，不能在现有init重复安装。
日常构建Dropbear使用linux-port/scripts/build-dropbear-usb.sh。

本地大产物和私钥在E:\edk2-samurai-out\kernel72；原#61立即回退在kernel71。
整体硬件目标仍未完成，下一项是原生显示/GPU。
