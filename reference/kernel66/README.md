# kernel66 校验与修复证据

结论以 [session66](../../sessions/66-verified-kernel-logs-and-builtins.md) 为准。本目录是离线证据，不访问 USB/串口。执行 `python3 verify.py` 可重新核对整帧解码、events/usbmon/raw、设备 export SHA256、gzip CRC、修复摘要、原文件哈希和释放状态。`manifest.json` 固定各文件长度/哈希；`analysis.json` 保存核验结果。

## 先读

- `map-dmesg.validated.txt`：最后 #59 的完整保存 dmesg，53866 字节，设备/导出 SHA256 和 gzip CRC 全通过；早期 ioremap 堆栈已消失。
- `map-facts.validated.txt`：#59、boot_id、taint=0、CPU 三策略/PMIC 三温度、USB deferred 和 CPU7 OPP 余留。
- `cpu-dmesg.validated.txt`：第一步 #57 的完整保存 dmesg，55416 字节，设备/导出哈希和 CRC 全通过。
- `facts.validated.txt` / `issues.validated.txt` / `config.validated.txt`：初始 #56 摘要，含缺 provider 的实际证据。
- `cpu.validated.txt` / `adc.validated.txt`：两个配置改动后的独立有效摘要。
- `source-audit.md`：异常优先级、已有权威仓库与尚需核对的本机事实。
- `finish-state.json`：三次 logdump 刷写后的最终主机状态；三节点 OK、Shared/unattached、无 owner/临时日志/ETW，旧驱动/终端/回退文件哈希不变。

## 原件和失败边界

`logs`、`facts`、`cpu`、`adc-followup`、`map` 的 `.raw/.txt/.events.jsonl/.usbmon` 用确定性 gzip 压缩（mtime=0），相应 `.json` 是原始 helper 元信息。raw 包含真实收到的整帧；txt 是原 helper 的 ASCII replacement 解码，不补字符。所有这些 manual owner 没有使用 overlap/reset/ZLP、自动重发数据、修改 gap/receipt 参数。

有效 export 的 `*-received.gz` 是设备 gzip 的原样导出，`*.validated.txt` 是校验后解压结果。`*-validation.json` 固定设备哈希、收到长度和 CRC 判定。

以下只作失败证据：初始 `received.tgz`、`console-received.tgz`、`dmesg.partial.txt`、相关 validation；ADC 的 `adc-followup-failed-received.gz` 哈希/CRC 不通过，不能用于完整启动结论。保存这些失败不撤销其他独立通过的快照。

原 `adc` 214895-byte 抓取含 GPT 34扇区过读后的分区内容，本目录不收录整个 raw/text/events/usbmon。只存 `adc-prefix.raw.gz/.txt.gz`（raw 前10564字节，止于独立有效 ADC 摘要导出）及 `adc-external-capture.json` 的外部长度、哈希和关闭状态。该大抓取、stop-export 和 GPT 内容仅在 `E:\edk2-samurai-out\kernel66` 本地保留；没有假装完整校验。

`baseline-state.json` / `final-state.json` 都属于**首次刷机前**初始采集；后者 `phone_flashing=false` 不能解释为本轮未刷机。真正末态是 `finish-state.json`。GPT audit 是旧备份离线 CRC 复核，不是当轮当前 GPT 导出；用途见 [rootfs 研究](../../linux-port/docs/ROOTFS-PRESERVE-ANDROID.md)。

## 构建及刷写

`config-before-cpu/config-cpu/config-adc` 已压缩，实际配置差异只有 OSM_L3 m→y、ADC5/VADC_COMMON m→y。`build-cpu.sh/build-adc.sh/build-map.sh/package-map.sh` 和 logs/hashes 是已运行步骤的可审查记录，依赖本地现有完整源码、initramfs 与前一镜像；不能当全新 checkout 的一键构建。禁止调用旧 build-image.sh 覆盖实际 initramfs。

map 编译产出成功，存在唯一原有未使用 `eud_wait_tx` 警告；`map-build-diagnostic.json` 和 package-map.sh 记录明确验收例外。`eud_earlycon-before.c/after.c` 是实际内核修复前后，`eud_earlycon-mirror-before.c` 是落后的 Windows 镜像。`early-map.patch` 只含本轮映射修复；pacing 是原来已运行的内核实现，本轮仅同步旧镜像差异。

CPU/ADC F1 和 flash/reboot 文件，加上 map-f1-owned（已回执后断开 EIO、finally dispose）、map-confirm-*、map-flash-validation.json，证明每一步独立核实 fastboot 后只刷 logdump。早前 map-f1 两次 raw=0 和 map-product 超时仍保留，不算受理；发现 WSL stopped 后用普通常驻 shell 保持会话并核对枚举，未调整 EUD 或 Windows 驱动。

最后镜像 `E:\edk2-samurai-out\logdump-k66-map.img` 64 MiB，SHA `c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d`。Image/镜像不入此证据包。原 `logdump-rx53-console-rx.img` 和 RX48 回退保留。
