# kernel87：阶段收尾、未部署的显示候选与 Wi-Fi 依赖

关联 [session87](../../sessions/87-stage-wrap-up-and-wifi-prerequisites.md)。优先级按用户要求
转到 Wi-Fi；充电未解决项保留。手机仍 #86，宿主显示候选 #88 未部署。

- dpu-frame-watchdog-lifecycle.patch：相对此前 dirty 源码的两个 DPU 文件增量；同步
  timer/忙位/截止时间，保留真正超时，增加生命周期事件并提前超时 trace。
- test-watchdog.c/py、watchdog-test-results.json、test-*.log：从实际旧/新函数提取并运行
  的确定性回归；旧函数失败，候选六场景通过；不代表 SMP/硬件验收。
- build-watchdog.sh、build-watchdog.log、build-hashes.txt：真实 #88 构建退出码 0；
  配置、CPIO 保持；没有 Image 刷写、FAT 候选或重启。
- audit-preservation.py、preservation-audit.json：既有 dirty 源码、模式、initramfs 文件/
  链接、配置/CPIO 保留，以及实际 Image 头、版本和增量 patch 检查。
- handover-state.txt、handover-dmesg.txt.gz、snapshot-hash.txt、handover-hashes.txt：
  USB SSH 设备端原始读数及摘要；2140.55 秒超时 2/下溢 0、taint 0；已触发快照保持。
- wifi-prerequisites.config、prepare-wifi-profile.py、wifi-profile-audit.json、wifi-kconfig.log：
  最小 Wi-Fi 诊断依赖片段，私人候选经过实际 Kconfig 解析、27 个符号变化；35 项私人
  固件重新校验。本机 Wi-Fi/MPSS 仍禁用，未安装固件，未构建该配置的 Image 或部署。
- source-reference-audit.json、wrap-up-audit.json：当前无线/加载器源摘要、tqftp 固定
  来源及采集/构建/候选边界；审计 PASS 表示记录完整，不表示硬件功能通过。

完整旧源/当前源、配置/生成头、提取函数、Image/CPIO、固件和身份文件保留私人目录，
均未发布。日志压缩可逐字节恢复；SHA256SUMS 覆盖同目录所有文件，不包含自身。
历史 kernel85/86 封存不修改。当前没有新的光学验收或充电配置测试。
