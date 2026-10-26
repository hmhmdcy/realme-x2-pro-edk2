# kernel73：本机SOFEF03F原生DSI/DSC显示证据

结果与限制见[sessions/73](../../sessions/73-native-sofef03f-dsi-dsc-display.md)。
#64自动1080×2400@60，A/B/A硬件CRC、两次启动各三次电源循环、亮度写入和面板
状态0x9c通过；启动接管SMMU故障仍保留，GPU/90Hz/休眠/光学图像与亮度硬件读回未验。

| 文件 | 用途 |
|---|---|
| before/first/reprobe/deps/tested/cycled/reboot/final-dmesg.txt及.gz | 手机保存的完整日志；#62基线、#63失败/定位、#64成功及重启 |
| cycled-facts.txt及final-facts.txt、capture-validation.json | 原始状态与设备SHA/gzip CRC/字节数；前者sde9=dsp不能作logdump证据 |
| display-cycle-tests.txt、reboot-display-tests.txt、kms-smoke.c | 两次真实A/B/A硬件CRC/60Hz同步/电源循环与可重建工具 |
| evidence-validation.json、verify-evidence.py | 可离线复核十份导出、CRC/循环、实际分区哈希与明确未验项 |
| live-display-properties.json、live60/90-on/off.*、live-phy-supplies.json | 本机原厂live命令/DSC/供电来源及逐条解码 |
| panel-samsung-sofef03f.c、panel-binding.yaml、panel-template.c | 新面板实现、binding与源命令生成模板 |
| dts-before/after、firmware-before/after.dtb、dtb-validation.json | 板级增量及只改变显示的DTB语义校验 |
| config-before、config-display-deps、kernel/clock-build.log | 实際#62→#63→#64配置与构建记录；clock命名脚本实际修REFGEN/defer |
| firmware-validation.json、verify-firmware.py | 全101个FFS/header/LZMA/gzip/shim/Android与兼容append审核 |
| core-before/preservation.json、initramfs-validation.json | EUD/RMI/真实init/USB保存与root权限/本地SSH身份核对 |
| *-f1-wsl.*、native/reboot-eud.*、confirm/deps/same-image-* | 新F1/独立fastboot/部署、同镜像重启、原生EUD与释放记录 |
| gpu-firmware-manifest.json | 本机只读固件身份与ELF几何；GPU未启用，专有blob留本地 |
| patch-validation.json、verify-patch.py | 0009增量在已核验旧源上应用，并与真实Linux源逐字匹配 |

离线只读复核：`python3 verify-evidence.py`。SHA256SUMS封存本目录文件；大Image、
boot/logdump/FD、kms binary、专有GPU blob和私钥不进入Git，都保留在本地kernel73。
构建/部署脚本使用实际WSL与本地路径，刷机前必须取得当次F1及独立fastboot确认。
prepare-display.py/build-firmware.sh/pack-logdump.sh带首次产物存在检查，不能原样重跑
覆盖回退。当前版本是阶段证据，不是无条件通用刷机工具或上游支持声明。

已保留的失败：#63 REFGEN/defer、无后续提交的CRC超时、错误deps-reboot参数、
过早fastboot/SSH查询、旧cycled-facts错误分区选择。verify-evidence首次宽松正则把
printk debug/ramoops和已有initial-console Warning误命中，已改为异常回溯匹配；
最终校验仍明确报告SMMU故障。未把这些失败当成成功数据。
