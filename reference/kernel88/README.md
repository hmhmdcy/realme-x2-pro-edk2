# kernel88：Wi-Fi构建与部署前交接

关联 [session88](../../sessions/88-wifi-dependency-build-and-read-only-firmware-service.md)。手机仍#86，无Wi-Fi接口；宿主#89构建完成，尚未部署、启动MPSS或验证实际服务。

- manual-mpss-node.patch、build-kernel.sh：最小MPSS手动启动节点和#89依赖内核构建；Wi-Fi节点仍关闭，PAS auto_boot=false。
- ro-firmware.c、tqftpserv-read-only.patch、build-tools.sh：限制固件路径/符号链接、拒绝WRQ和可写命名空间；完整第三方源及二进制留私人目录。
- test-ro-tftp.c、tools-test-audit.json、test-compile.log/test-run.log：实际翻译/WRQ函数本地测试，socket使用桩；不代表真实QRTR/固件运行通过。
- inventory-mpss.sh、extract-mpss.sh、mpss-inventory.txt、mpss-extract-*.txt、mpss-firmware-summary.json：同机modem分区只读归档33文件、逐项摘要、160MiB布局和PD域/实例对应；无NV服务或DSP启动。
- build-wifi.log、build-hashes.txt、config-normalization.json：实际#89构建完成；第一次仅配置生成注释差异导致守卫退出，随后核对仅注释变化再成功。
- qrtr-tools-source-manifest.json：gh获取固定来源的27项源码摘要和URL；不包含完整源码。
- collect-handover.sh、audit-handover.py、handover-audit.json、handover-*.txt/gz：保存并核对#86现场、全部此前修复/模式、initramfs身份及配置/DT增量边界。
- private-artifact-manifest.json：私人产物的大小/摘要；不提供固件、镜像、完整配置或身份内容。

关键点：Linux实际DT来自EDK2内嵌DTB；单改logdump DTB不生效。当前内嵌DTB未改，新boot未构建，#89未打包/部署。后续按新会话新守卫处理已授权boot/logdump，保留Android/数据/GPT及显示故障快照。

本地测试与构建通过，MPSS/WLFW、chip/board ID、无线扫描/连接/流量仍待实测。充电阶段保持收尾；不写充电配置/NV或启动未审阅可写存储服务。历史85/86/87封存不修改。

脚本含固定boot ID/哈希和拒绝覆盖检查，供本次证据复核，不能原样重放。SHA256SUMS覆盖本目录所有文件，不含清单自身。
