from pathlib import Path
root = Path('/mnt/e/RealmeX2Pro edk2')
(root / 'NEXT-SESSION.md').write_text('''# 继续：112持久Phosh、传感器RAM试验与重启

先读[阶段112](sessions/112-startup-sensor-registry-and-reboot.md)、[硬件状态](linux-port/docs/HARDWARE-STATUS.md)、[聚合核验](reference/kernel112/checkpoint-validation.json)。全硬件goal active，无预算，不能因桌面可用而标完成。

当前内核112，boot固件/内嵌DTB来自111；userdata F2FS上的postmarketOS/Nura edge与Phosh自109延续。111首次出现用户确认的滚动花屏；112首次用户确认稳定、解锁和应用正常，后续fastboot恢复启动确认稳定锁屏。DPU帧完成超时仍存在，显示长期稳定未完成。已有物理反馈不能重复询问；最新检查点计数以聚合JSON为准。

USB NCM/密钥SSH、2.4GHz NetworkManager Wi-Fi、HTTPS/NTP、桌面扬声器/DMIC0 UCM通过；完整关机流程的正常重启已恢复。空闲PCM关闭、双功放静音、振动starts0通过；实际声音/拾音质量未确认。5GHz最新认证失败及历史107成功均保留。

SLPI手动启动、SSC400与FastRPC节点通过，加速度实际样本未验收。官方本机Android R的100字节ProjectInfoOCDT已匹配，真实OEM属性私有保存；旧13字节/旧布局无效。外部只读SMEM模块卸载，重启后taint0。原厂固件/库/配置/完整注册表来源只读，真实写入仅限RAM副本。

RAM v1安全拒绝及上游NULL处理崩溃已修正；v2同boot第二次SLPI握手超时，未运行查询。新boot v3只打开temp.json，256字节监听限制使内容写入未完成，加速度不可用。v4使用静态hexagonrpcd-v3及FastRPC方法5补取剩余字节；实际监听函数边界ASan/UBSan与真实RAM写入测试通过。实机结果看sensor-ram-v4.tar及聚合记录，不能把文件打开或SSC服务视为硬件通过。

一次直接reboot未恢复NCM，关机EFI运行时异常保留；后续F1回执有新内核时间，不能直接判为EFI重置卡死。那次fastboot只reboot恢复不算正常重启通过。后来两次完整停止无线服务的重启均已恢复新boot/taint0，桌面回归逐项保存。旧F1恢复脚本已封禁；上一boot只读关机记录不能证明当前rw根安全。

源码在/home/cy122/pmos-samurai-kernel112/{kernel,initramfs}；111、109及原106来源保留。规范EDK2目录恢复109产物，手机boot实际为111，改DTB须独立审计并同步内嵌DTB。109初始F2FS sparse只有console，Phosh/UCM随后安装到真实userdata；不能称初始镜像为最终GUI镜像。旧110救援DTB不匹配111/112，不盲刷。

1. 核对当前SSH身份、taint、SLPI状态和新档案。持久SSH/SCP用reference/kernel109包装器和已核验OpenSSH密钥；诊断Dropbear用111包装器。SCP远端须带root@169.254.42.1:，新实验须新prefix/当前bootID。
2. 传感器试验后核验真实请求/样本、SLPI收尾、NV/来源哈希、DPU/GPU和桌面。按具体错误修复；再次启动握手超时时获取完整新boot，避免同boot反复启动SLPI、盲加电源票或全局关闭SMMU。不自动启用试验服务。
3. 日常重启用kernel109/reboot-pmos-persistent.sh；host的112 observe-radio-clean-reboot.ps1分段有界抓日志，owner释放后com-up。等NCM/SSH及300秒root发现路径，不能暂时无SSH就F1。F1前必须取得当前boot同步/冻结或只读卸载的独立证据。
4. 六LUN头尾/geometry18项、boot111/logdump112、persist、6个NV和4个传感器来源核验通过。新候选保留完整回退并逐项核对；flash-pmos.ps1会erase userdata，不用于内核更新。
5. 保留15组硬件，继续显示/重启长稳、5GHz、摄像头、指纹、GNSS、蜂窝通话/数据及休眠。蓝牙不配对连接，振动不发脉冲，NFC仅控制器，充电探针收尾。

凭据/SSID/PSK/PIN/身份/固件/校准/原始日志/录音/镜像只在E:/edk2-samurai-out，不公开、不提交推送。PIN只供本机解锁，SSH密钥认证。临时包代理、反向隧道和转发已关闭。EUD每个owner finally关闭/Dispose/detach；hrdevmon警告保留，不forcebind。不要运行旧sync-docs-to-repo.sh或重放旧bootID守卫。
''')
print('Kernel112 continuation checkpoint saved')
