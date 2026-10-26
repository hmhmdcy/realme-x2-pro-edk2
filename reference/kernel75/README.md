# kernel75：主线 A640 渲染与 SOFEF03F 花屏实测

最终 #76：用户确认纯白正常、重新启动首次彩条清晰；两次完整启动日志无
DSI/SMMU/Oops，taint0。GPU 累计 39,096 次实际 Turnip 渲染/读回/fence 通过，
最终两启动混合回归共 12 次面板电源循环。详见 [session75](../../sessions/75-a640-render-and-sofef03f-clock-fix.md)。

| 文件 | 作用 |
|---|---|
| evidence-validation.json、capture-validation.json | 独立光学报告、GPU 提交数量、数字测试和日志长度/CRC/SHA |
| display-failure.md、flower/static-white/no-eot 日志 | 静止噪点照片哈希、数字 scanout 正常但物理失败、EOT-only 失败 |
| final/reboot 日志、tests 及 .gz | 最终两启动、GPU 渲染与 12 次显示电源循环 |
| gpu-boot/failed/reboot-blocked 日志 | drain timeout、旧二次释放和 shutdown 阻塞失败 |
| gpu-render.c、shaders.h、triangle.* | GPU 硬件身份、着色器渲染、逐像素读回及 fence 检查 |
| userspace-manifest.json、gpu-installed-manifest.json | Ubuntu 验签包/ELF 和本机专有固件身份，不包含专有 blob |
| dpu_*.after、dsi_host.c.after、panel*.after、sm8150-samurai.dts.after | 实际最终源码；0011/0012 精确应用和 checkpatch 通过 |
| final-validation、dtb-validation、initramfs-validation | 保留核心源/config、三处 DTB 语义、FW FV/FFS、FAT Image、CPIO 与分区回读 |
| prepare/build/flash/reboot 脚本与部署 JSON | 可复现过程、失败保护及仅 boot/logdump 写入证据 |
| research.md、mainline-gpu-findings.md | 主线/原厂/同 SoC 作者资料，实际本机验证优先 |

最终本地产物在 `E:\edk2-samurai-out\kernel75`，不作为公共附件上传。
大镜像、专有固件、CPIO、客户端/设备密钥、用户照片均保持本地。
只读校验：`python3 verify-evidence.py`；`SHA256SUMS` 封存本目录文件。
准备、构建、刷写脚本是一次性过程证据，含首次备份/新输出前缀检查，不应原样
重跑覆盖备份。最终部署是 flash-final.ps1；其它 flash-* 均为历史候选。

有效修正是匹配原厂 NO_EOT_PACKET/CLOCK_NON_CONTINUOUS，并清除继承的
controller/PHY 强制时钟位。EOT-only 不足。未改 PPS、DSC 几何、链路频率、
供电电压或 EUD 内核传输。主线已有 A640/GMU；本机的节点禁用和板级固件已补齐。
冷断电、90Hz、休眠、完整桌面、GPU 全频点压力及其他硬件仍需独立完成。
