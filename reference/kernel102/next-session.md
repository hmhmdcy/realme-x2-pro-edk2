当前实际状态已推进到[阶段103](../kernel103/next-session.md)：#102正确功放/原生声卡/有限PCM播放通过，录音全零与版本查询失败待修；当前5GHz可用。以下保留阶段102历史。

# 下一阶段：正确MAX98937驱动与音频声卡（session102）

继续全硬件goal。先读[session102](../../sessions/102-wcd934x-and-real-max98937-identification.md)、[15组硬件](../../linux-port/docs/HARDWARE-STATUS.md)、本目录README与私人 E:/edk2-samurai-out/kernel102/checkpoint-validation.json。每轮重新核对真实boot ID/uptime/进程/目录/驱动/路由/哈希；既有目录/PID和旧adapter编号不能重放。

手机已部署Linux #101（阶段102），WCD934x真实芯片ID 0x108/0x1、SLIMbus与codec绑定通过，ADSP原生回复AFE API7/ASM API2；ALSA尚无声卡。
左右功放实测为MAX98937，地址0x39/0x3a，0x0600均返回0x43；原厂max98927L/R名称不能直接套主线MAX98927。错误组件已解绑、GPIO148/37保持物理低复位；未写功放寄存器数据、未播放。
本次首次MPSS自动启动与Wi-Fi初始化成功，5GHz认证/DHCP/DNS/HTTP、网关3/3通过；未手动恢复MPSS。仅一次暖启动，历史首轮40秒fatal、2.4GHz reason7及删除等待仍待修复。
125文件checkpoint/原包与nested清单/80块完整备份/boot与logdump读回/6NV与persist不变通过；两个DSP running、taint0，本轮显示超时2、BT phase2错误2。
蓝牙控制器已关闭并移除，不配对连接；用户暂缓振动机械确认，当前ID97/standby/starts0/error0，无新增振动播放。
DTB改变已真正重建EDK2；initramfs、已有模块与其它内核源码保持。新增QUP4使I2C编号变化，振动改按唯一驱动/DT路径解析，不重放旧编号脚本。
继续MAX98937正确驱动及声卡/DAI/播放录音接入，保留15组硬件、Android/数据/GPT/原NV/persist/SSH/显示旧快照/rootfs01与F2FS段落；全硬件goal仍active。


当前手机Linux #101、initramfs未改。最新125文件checkpoint SHA `92fd414040265009df106e9a27236be6a7642ecc955f23f6211135cec13b51d8`，uptime673.35、MPSS已运行628.722574秒，worker自动result0、5GHz COMPLETED，双DSP running/taint0，显示超时2、BT phase2错误2。历史首次MPSS失败与2.4GHz掉线没有关闭。蓝牙已正常stop，HCI空；不为mgmt info重新启动它。用户振动机械确认暂缓，不再提问或重放脉冲。

**先修正实际MAX98937，不能继续拿MAX98927组件播放。** 原厂GPL源固定9668fcdc的audio-kernel/asoc/codecs/max989xx/max98937.c/.h已保存在 /home/cy122/x2pro-linux/refs/realme-amp-git-k102，private oem-amp-git-provenance.json记录来源/哈希。其presence检查01ff/0600的bit0x40；本机双通道实测00/43。MAX98937的global enable=0500、soft reset=0501、revision=0600；不能使用MAX98927的00ff/0100/01ff寄存器图。不要整体套用OEM DSM/增益/保护配置或共享static生命周期代码；逐项核对左右通道表、I2S时钟和保护后写自己的正确驱动，ID有效前拒绝配置。当前两个native MAX98927组件已解绑、reset GPIO148/37物理低且unclaimed，WCD934x-codec组件继续绑定；没有ALSA卡/PCM。

下一步实现MAX98937准确DTS/驱动与原生ASOC组件，保留ID-first/失败停机。再接AFE/ASM/ADM、SM8150机器声卡、SLIM codec链和QUAT MI2S3功放链；原厂确认speaker-vendor=maxim、speaker-i2s-id3。每个SLIM rtd配置channel map，避免其它机型per-card全局标志缺陷。先真实PCM时钟/数据/录音，再可控低强度声音；无人物理确认时按日志/代码推进并记录边界，不能把注册卡当声音输出。

codec契约已真机验证：SLIM217:250:1:0与ifd217:250:0:0、reset143ACTIVE_HIGH对native0→1、IRQ123LEVEL_HIGH、LN_BB_CLK2/extclk/MCLK9.6MHz、五路S4a1p8、micbias1/3/4=1.8V及2=2.7V。MBHC buttons threshold缺省warning尚在，声卡/耳机阶段按同机源码校准。SoundWire无本机WSA扬声器，不因共有overlay旧WSA节点而启用它们。NGD/BAM基地址、IRQ和SID0x1b46已互证并真机无SMMU fault；其它音频DMA/ASM资源仍须验证。

QUP4真正是890000/IRQ605/51+52，GPIO54触屏复位保留；本轮motor=2-005a，touch=4-0020，不能重用过去1-005a/3-0020。/tmp/k102-haptics-device按唯一AW8697驱动与完整89c000 DT路径查找。/usr/sbin/samurai-modem-remoteproc同样按唯一设备身份解析MPSS，不假设remoteproc0；ADSP按name/PAS/FW/DT解析，不能强制crash或循环恢复。

新一轮完整boot/logdump备份+真实镜像/FAT/FFS审计。DTB变更必须重建实际EDK2；只刷boot/logdump，NV只RAM COW。currentImage/DTB/CPIO/boot/logdump哈希见session102/private validation，fresh boot ID使用kernel102/runtime-boot-id-after-private.txt。私有5GHzprofile使用kernel102/wpa-5g-private.conf（5180）；旧kernel95 profile限制2.4GHz，勿误用。只有自动真实失败且首轮日志保留后才能一次有界恢复；本轮完全没有运行备用manual recovery脚本。

保留15组功能、充电收尾不跑旧OEM/配置/NV/OTP/FET/OTG/MCU/I2C_FORCE探针、显示85–88失败快照、Android/原NV/persist/GPT/data/SSH及另一rootfs01线程全部文件和F2FS段落。不提交推送，不公开固件/OEM XML/库/二进制/原日志/身份/密码。首次MPSS/2.4GHz/删除等待、显示超时、BT脉冲、USB传输、冷启动/休眠待办持续；摄像头/SLPI传感器/指纹/蜂窝/GNSS等剩余功能仍在全硬件目标内。

当前阶段102代码包含构建前guard失败及运行partial的原脚本，不能盲目重放prepare/collector/backup/flash；使用新编号/前缀并重新审计。实际完成的runtime为retry1，net为auto-network-completion，amp为amp-readonly-ids，最终checkpoint涵盖nested manifests。公开原脚本与出错边界是历史证据，不是无条件可执行的当前命令。

最终9文件只读现场在uptime 949.51秒确认同一次#101启动：5GHz COMPLETED、MPSS/ADSP running、fatal0、taint0，WCD组件仍绑定，错功放组件解绑/两reset低，BT控制器移除、振动standby/starts0、NV/persist不变；显示超时2/BT phase2错误2，无新增fatal。原包SHA `b48f30cb3c22efed6339597b658d22e14c5a813750f2023c3d29d666a3621728`，私人final-status-validation.json；全硬件goal保持active。
