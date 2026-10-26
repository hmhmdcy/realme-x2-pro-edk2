> 当前后续见 [阶段104](../../sessions/104-native-digital-microphones-and-first-boot-radio-failure.md) 和 [最新交接](../kernel104/next-session.md)。下文保留阶段103历史；其core重绑重试解释已由阶段104的APR IDR源码审计补充。

# 下一阶段：Realme X2 Pro数字麦克风与APR版本回复

当前真实部署Linux #102，逻辑阶段103，详见[session103](../../sessions/103-native-max98937-card-pcm-and-zero-microphone.md)和[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无token预算，尚未完成。

原生声卡/正确双MAX98937 ID43/WCD934x与DSP服务已接入。2秒-48.16dBFS stereo/S16/48k播放退出0，双方starts1/stops1、global00/amp80/failed0，物理听音无人验证。两次mono/48k各241920帧/5.04秒DMA正常但全零，不能宣称麦克风可用；AMIC1/DEC0和原厂DMIC0/DEC5/TX5均失败。当前card缺DMIC Pin->麦克风widget->MIC BIAS1路径，原厂Digital Mic0/1用BIAS1，其它DMIC源按同机官方DTS逐项核对。先补板级电源/路由并真EDK2重建刷机、观察非零实采；若仍零，核查SLIM trigger实际返回/AFE通道与IOMMU映射，不盲目旁路或扩大mask。代码里Handset Mic目前仍AMIC1，需要修正。没有物理反馈要求的未答问题。

原生q6core版本属性读取exit1；仅一次精确service@3正常unbind/bind后仍exit1，两个DSP/声卡保持，未重启DSP。不能断言仅早期缓存。下一步记录实际APR opcode/status/length和合法payload分支，再修native查询与依赖；不能把timeout0/缺服务默认0当ready。旧#101 API7/ASM2实测保留为历史，不覆盖本轮失败。

本轮首次MPSS自动启动/worker0、5GHz认证/DHCP/网关3/3/DNS/HTTP通过，未manual恢复；相邻阶段两次暖启动成功不等于可靠性修复。原CPIO/模块/无线源码不变，历史首次40秒fatal/2.4GHz reason7/删除等待/冷启动/休眠继续。当前#102 uptime1005.42、双DSP running/fatal0/taint0/显示超时2/BT错误2；蓝牙正常stop/HCI空，不配对或连接。振动ID97/standby/starts0，无新脉冲，机械确认暂缓。

240文件checkpoint SHA `c97b8765c3c5e704ef29e845e4b3f1ec2bbc3aca9a8c8ca80f409b0506057826`，私人E:\edk2-samurai-out\kernel103/checkpoint-retry2.tar，tests-validation/checkpoint-validation.json绑定六个原包。runtime完整包retry1，capture与capture-dmic0均全零；first runtime/API错误、原checkpoint模块路径错误、retry1 nested manifest缺失均保留。原UUID第一次文件只是误命名first-empty，实际有效，不要错误推断熵故障。工具脚本已有输出目录/guards，不能盲目重放。

下一轮使用kernel104/新PID与输出prefix，先重核当前真实boot ID、哈希、进程、目录与owners。旧前缀不覆盖，当前真实boot ID在私人kernel103/runtime-boot-id-after-private.txt。内核/home/cy122/x2pro-linux/linux HEAD e42788e，EDK2/home/cy122/edk2-samurai/repo HEAD f23a9f8；实际DTS对应reference/kernel103/sm8150-samurai.dts.after，linux-port/dts镜像故意保留早期状态。新源sound/soc/codecs/max98937-samurai.c及sound/soc/qcom/samurai-audio.c，四个Kconfig/Makefile改动已应用、无提交。

GPIO148/37现在由正确功放驱动拥有，空闲物理高/逻辑解除复位，但global00/amp80；不能继续用旧ID工具直接I2C_SLAVE或GPIO申请。i2c编号功放1/振动2/触摸4，MPSS用/usr/sbin/samurai-modem-remoteproc，振动按唯一driver/OF的haptics-device。QUP4 GPIO51/52、QUAT I2S137/138/139、WCD143/IRQ123已核对，GPIO54触屏保持。SMMU SID1b21 strict0、NGD1b46 strict0；不采用其它SoC/手机资源。

原factory参考固定Realme9668fcdc C/H在/home/cy122/x2pro-linux/refs/realme-amp-git-k102（无checkout、FETCH_HEAD），表55项/地址/thermal与brownout互证；固定SM8150 403b56源码在refs/sm8150-audio-k102-retry1。private kernel102/stock-audio-contract.tar包含只读同机XML；kernel103/oem-mic-contract-derived-private.json只本机。tinyalsa v2.0.0 ARM64静态四工具在私人kernel103，v2需要tinymix -D 0 contents/set/get；period要480整数倍，capture设备1。

手机仅boot/logdump刷机，DTB改变必须真EDK2重建；full80块backup和current完整readback匹配。CPIO SHA `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`，Image `c730a9d7ebe73aff8b393c4940be03e196c365b2ceec750872bb99334be2b82e`，DTB `e6350842005bed457f5545650ef068ba08c464f47a5d54b937c55539f7d90b99`，boot `301a958c440cadecd8d465c7c3f1918860b61fc0ee665410bc3632f9a45e3048`。NV RAM COW仅，充电不重跑旧探针；Android/data/GPT/NV/persist/SSH/旧显示85–88/另一rootfs01全部文件及F2FS段落保留。仅自写代码/脱敏记录公开，固件/OEM XML/库/原日志/身份/密码/音频/镜像/二进制私人，不提交推送。剩余摄像头、SLPI传感器、指纹、蜂窝、GNSS等仍在全硬件目标。
