# kernel76：充电来源与安全审查（只读研究）

日期：2026-10-10。这里的 76 是会话号；手机继续运行 session75 的 #76 内核。
详细结论见 ../../sessions/76-charging-source-and-safety-review.md。
本轮没有刷机、重启或修改充电参数，没有把原厂 MP2650 probe 上机。

| 文件 | 用途 |
|---|---|
| charging-source-provenance.json | 43 项公开来源的提交、URL、SHA256；原厂 DT 存档摘要；官方芯片文档版本；检索限制 |
| charging-stock-runtime-facts.json | 本机 Android 存档中的 9 个相关节点、238 个策略属性、引脚与主线配置；不是当前电池读数 |
| stock-source-manifest.json | 初始 Realme 原厂源码文件摘要 |
| stock-live-power-properties.json | 初始电量计/MP2650 的原厂 DT 属性 |
| current-linux-state.txt | 研究末的只读 SSH 状态；与显示/GPU可用基线 boot_id 一致，power_supply 仍为空 |
| research-*.py、fetch-*.py、inspect-*.py、compare-*.py、prepare-source-tasks.py | 本次来源检索/读取脚本；依赖本机已存档的原厂 bare Git、Android DT 和私有输出目录 |
| seal-charging-research.py | 验证来源哈希，生成上述最终 provenance/facts 文件；在 WSL 中运行 |

当前状态采样使用 reference/kernel72/usb-ssh.ps1，远端命令：

```sh
uname -r
cat /proc/sys/kernel/tainted
cat /proc/sys/kernel/random/boot_id
ls /sys/class/power_supply
ls /sys/bus/i2c/devices
```

依赖路径：/home/cy122/x2pro-linux/linux、
/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git、
/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar。
原始公开源码下载和中间分析位于 E:\edk2-samurai-out\kernel76\charging-research；
SSH身份、完整 dmesg、镜像及芯片完整 PDF 不在此目录发布。

后续从只读电量计开始；MP2650 需要单独驱动和完整安全策略，不能冒充 MP2629
或用原厂会自动写寄存器/关闭计时器的 probe 来做只读探测。
