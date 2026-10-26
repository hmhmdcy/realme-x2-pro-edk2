# 阶段134：USB输入额度标准接口、真实部署及显示启动失败

2026-10-12。上一轮冗余rootfs清理完成，为progress。本轮完成真实源码补丁、静态测试、完整构建/镜像、自动双分区刷入和有界实机验核；全部自动，无人工检查步骤。完整系统目标未完成。

阶段134已实际刷入boot/logdump及770匹配模块，新内建只读USB supply自动注册：42.113秒8份标准事件均ONLINE1/CDP/CURRENT_MAX1500000，属性0444。首次启动却发生继承INTF停帧及CTL reset -22，KMS失败/无DRM；失败现场保留，一次原生panel bind恢复card0/renderD128，保存当前greetd初次会话标记后原配置Phosh/Phoc恢复，不能宣称永久显示修复。恢复后taint0/BlueZ/5180MHz及11来源保持，42秒无新增故障；新boot累计DPU timeout1、UART2、GPU0仅无专项负载窗口，GPU131迟发CCU故障仍未修。完整rootfs134为936包/770模块/21,137条目反向内容metadata零差异、双fsck、encoded UID10000读写及四件套通过，完整userdata未全量刷入。实际清理120/121旧对象1.78GiB、旧129/130 exports与冗余132 raw7.14GiB内部占用，134卷零区原生稀疏回收E盘2.30GiB，稳定源码/镜像和原WSL VHD保持。15组功能边界、完整充电控制及完整系统goal仍开放。

## 预算证据和实际实现

133 gadget MaxPower100mA只是声明，不是当前真实源的全部许可。按本机OEM SMB5 header固定7个只读状态地址，经当前132 regmap-debugfs实现确认9字节记录、range metadata及pread读取边界后，56次状态读取证明APSD完成、CDP、default Rp、legacy cable。没有全PMIC dump、寄存器写、PD/role动作或重新绑定。

BC1.2 CDP允许1.5A，与gadget descriptor的100mA相互独立；这不是电流测量，也不能用133的声明差异证明实际900mA输入限值超标。参考[USB-IF充电合规资料](https://compliance.usb.org/index.asp?Format=Standard&UpdateFile=Battery+Charging)及[TI CDP资料](https://www.ti.com/lit/ds/symlink/tps2549-q1.pdf)。OEM header来自realme-kernel-opensource/realmeX2Pro-kernel-source固定commit9668fcdc6ec15be7a10d66f7b93c347829e0fdb6，实际header SHA和URL见usb-source-static-validation.json。

新samurai-usb-input内建platform driver提供标准ONLINE/USB_TYPE/CURRENT_MAX，只读属性。仅本机compatible与PM8150B/pmic@2/reg1300可probe，7状态寄存器连续双快照，IO失败/变化/过渡/水/错误/不合规状态返回不可用；SDP配置/挂起额度及QC/PD不推断。1秒有界通知，devres停止work先于注销供电对象。MP2650源码不变，没有充电配置、GPIO、role、PD写入。289场景实际执行生产reader/decoder、全部14个IO失败位置、快照改变/歧义/故障组合通过GCC warnings-as-errors、ASAN/UBSAN；binding正反例及真实单节点schema通过，占位维护者邮箱仍只是本地候选。

134完整Image/DTB/770模块通过；新built-in符号已链接，无外部模块taint。初始power_supply_config.of_node API编译失败保留，按当前实际header改fwnode后完成W1无警告及整树构建。所有旧模块可执行段与132一致，仅匹配vermagic/initramfs BT及一个新USB DT节点；旧节点属性保持。UEFI canonical只改变内嵌DTB，实际132所有其它可执行模块保持，原firmware源码/构建产物已恢复。

## 自动刷入与失败现场

新鲜132同boot、GPT18、11来源、persist、旧模块、用户态与音频守卫通过；134模块独立staging不加载。quiesce停止桌面/BlueZ/Wi-Fi/MPSS/ADSP和tracer，零DRM clients/CRTC inactive、sensor power0、amps idle、taint0；fsfreeze后仅一次90 02 OUT收到F1。转换后的USB read错误留档，没有第二次OUT/reset。

初始flasher在读取不存在的私有build报告时退出，尚未任何fastboot操作；改为读实际公开报告。随后getvar product虽然返回正确值，Start-Process等候退出超时，仍未flash；检查当前设备、独立原生只读getvar后，用新鲜resume日志和同一F1证据执行boot/logdump写入，各收到OKAY并reboot。没有重发F1或复用flash记录。新boot真实分区SHA/GPT/persist、全live DT及784个模块树文件通过。

首次显示启动失败：INTF1高度2400/行2337/继承autorefresh，停帧超时后CTL0 reset poll返回-22，KMS失败、Phoc找不到GPU。四个DPU交接源码与132逐字节相同，不能据此把原因归给USB节点。首次只读现场和首次完整捕获保留，初次runtime验核因Phosh缺失失败。

一次原生mipi-dsi panel bind使内核完成msm注册，DRM实际为card0而非过去card1。普通greetd restart进入默认Phrog，因为initial_session每boot只执行一次；随后保存当前/run/greetd.run并在既有fbcon守卫下恢复原配置/launcher的Phosh。恢复前后SHA保留，taint0，未改永久服务。后续全新只读recovered-runtime证明当前Phosh/Phoc/card0、标准BlueZ、console及全部DT/模块/11来源。不能把恢复后的桌面作为自动首次启动或永久显示验收。[显示检索与原作者邮件](../reference/kernel134/display-internet-findings.md)记录相关clocks/domains/boot路径问题，SDM630 reset补丁不是本机可直接套用方案。

## 连续观测和完整rootfs

42.113秒8样本：USB事件全部ONLINE1/CDP/1.5A；MP2650 ONLINE1/Charging，输入电压4/8有效4.450–4.475V、另4份ENODATA，输入电流6/8有效406.25–418.75mA、另2份ENODATA。属性只读，桌面PID保持，taint0/BlueZ/5180MHz及包数据库/11来源保持，窗口各类故障增量0；全boot DPU timeout1/UART2/GPU0并不覆盖首次KMS失败或GPU专项绘制验收。

从稳定132完整模板复制，936包、凭据/校准/固件/UID10000 home及标准BlueZ/default/AutoEnable false/双频Wi-Fi保留，仅770匹配134模块和两个stage标记不同。F2FS稀疏为1817957988字节，SHA a7d3b11b17d83e72361937dcb8ce2daf3078e52beb4d86f2bc603a9d260bb2ff，逻辑展开119033245696字节；21,137条目反向内容、uid/gid/mode/link/xattr/device零差异，双只读fsck及真实encoded降权create/read/write/unlink通过。完整userdata未bulk刷入或擦除。

重建最后fsync ENOMEM并非可忽略：保留失败、现有文件后续fsync成功但只读proof仍发现一个1,601,536字节范围缺失。对照完整source与sparse证明后，仅修补失败raw的这一范围，inode/size保持，最终fsync和全payload/holes证明通过，再继续原未执行的第二fsck/export/metadata阶段；没有重打包或重放原构建。

## 存储和后续

120/121从未部署对象按ELF REL、唯一链接及稳定源码/Image/DTB/module包全hash证明后删11268个.o，释放1907175424字节内部空间。稳定132稀疏新鲜hash及两份raw全payload/holes、旧129/130 exports全部内容metadata与保留源一致后清理，仅删已证明重复的数据，释放7666491392字节E129内部空间。所有129/130/132完整源和稳定sparse、最新132 export保留。新134卷先卸载/只读fsck，再验证23个全零范围，Windows fsutil sparse setrange实际释放2470445056字节E盘，整8GiB卷处理前后SHA相同且fsck0。Linuxfallocate不支持的失败证据保留，原WSL VHD未resize/compact。

boot/logdump/modules/rootfs SHA和实际字节见complete-bundle-validation.json。首次启动失败使134不能替代132为稳定无恢复的基线；132稳定四件套保留，134当前桌面已恢复，自动初次启动缺陷优先留档分析，完整充电控制继续待办。0x2719是电量计扩展标识，不是已证明的短路保护芯片型号。其它15组中物理camera/PM8008/HAL、真正GNSS fix、SIM/通话/数据、指纹/IMU/休眠、DPU持续显示、UART和GPU迟发CCU仍开放；禁止靠开机重绑循环、删错误或重跑旧33场景宣称完成。

全部一次性prepare/build/repair/pack/collect/stage/quiesce/freeze/F1/flash/reprobe/initial-session/cleanup脚本已执行，禁止重放。观察超时先查原handle/实际状态，只有终态且明确未执行阶段才补做。私有UUID/地址/凭据、raw和固件仅E:/edk2-samurai-out或设备/var/lib/samurai。
